#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量出图 + 幂等重试。

把 storyboard.json 的每一格按 production.json 的配方送去 Beatra 出图，
支持：

- **幂等**：请求指纹 → 稳定 client_request_id。同参数重跑命中服务端去重，
  不重复扣费；参数一变指纹就变，ID 也变（符合 Beatra 的「新参数必须新 ID」规则）。
- **断点续跑**：已成功的格子记在 ledger 里，重跑直接跳过。
- **并发受控**：默认 4 并发（Beatra 硬上限），超限会返回 rate_limited，脚本自动退避重试。
- **付费前准入**：先读 live model card，校验模型可用性、画幅档位、negative_prompt
  支持、参考图数量、edit_regions 支持，并给出估价。**不确认不花钱。**

用法：

    # 只看计划，不花钱
    python3 batch_images.py -s outputs/我的爷爷/storyboard.json \
                            -p outputs/我的爷爷/production.json \
                            -o outputs/我的爷爷/images --dry-run

    # 确认后真跑
    python3 batch_images.py -s ... -p ... -o ... --confirm

    # 只跑其中几格 / 忽略 ledger 重来
    python3 batch_images.py ... --shots P03,P05 --force
"""

import argparse
import hashlib
import json
import os
import re
import random
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_CLIENT = Path.home() / ".claude/skills/beatra-ai-video-studio/scripts/mcp_client.py"

# Beatra 同时在跑的任务数硬上限
MAX_CONCURRENCY = 4

CAPABILITY = {
    "generate": "text_to_image",
    "transform": "image_to_image",
    "edit": "image_edit",
}
TOOL = {
    "generate": "beatra.images.generate",
    "transform": "beatra.images.transform",
    "edit": "beatra.images.edit",
}


# ---------------------------------------------------------------- 基础工具


def canonical(obj):
    """稳定的 JSON 序列化，用于算指纹。"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint(payload):
    """请求指纹：去掉 client_request_id 后的内容哈希。

    任何实质参数（prompt / model / canvas / 参考图顺序 / negative_prompt /
    edit_regions）变化都会改变指纹，从而拿到新的 client_request_id。
    """
    body = {k: v for k, v in payload.items() if k != "client_request_id"}
    return hashlib.sha1(canonical(body).encode("utf-8")).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def control_names(card):
    """模型卡 controls 字段可能是字符串数组，也可能是 [{'field': ...}] 数组。"""
    out = []
    for c in card.get("controls") or []:
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, dict) and "field" in c:
            out.append(c["field"])
    return out


def pricing_options(card):
    """取价选项。

    不同能力的 pricing 形态不一样：图片是 dict{'options': [...]}，
    视频是直接 list of dict。两种都兼容。
    """
    pr = card.get("pricing")
    if pr is None:
        pr = card.get("price")
    if isinstance(pr, dict):
        opts = pr.get("options") or []
    elif isinstance(pr, list):
        opts = pr
    else:
        opts = []
    return [o for o in opts if isinstance(o, dict)]


def reference_limit(card):
    """参考图数量上限。

    视频卡的限制写在 max_references，图片卡不写这个字段，要看
    inputs.public_max_count（公开上限）/ inputs.native_max_count（模型原生上限）。
    """
    n = card.get("max_references")
    if isinstance(n, int) and n > 0:
        return n, "max_references"
    inputs = card.get("inputs") or {}
    for key in ("public_max_count", "native_max_count"):
        n = inputs.get(key)
        if isinstance(n, int) and n > 0:
            return n, f"inputs.{key}"
    return 4, "工具公开上限"


# ---------------------------------------------------------------- Beatra 调用


class Beatra:
    """对 bundled mcp_client.py 的薄封装。所有远端调用都走它。"""

    def __init__(self, client_path):
        self.client = Path(client_path)
        if not self.client.is_file():
            sys.exit(f"找不到 mcp_client.py：{self.client}\n用 --client 指定路径")

    def _run(self, args, payload=None):
        proc = subprocess.run(
            [sys.executable, str(self.client)] + args,
            input=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
            capture_output=True,
            text=True,
        )
        raw = proc.stdout.strip()
        i = raw.find("{")
        if i < 0:
            raise RuntimeError(f"客户端无 JSON 输出：{raw[:300]} / {proc.stderr[:300]}")
        try:
            return json.loads(raw[i:])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"客户端输出解析失败：{raw[:300]}") from exc

    def call(self, tool, payload):
        """调用一次工具，返回 structuredContent。"""
        out = self._run(["call", tool], payload)
        sc = out.get("structuredContent")
        if sc is None:
            raise RuntimeError(f"{tool} 无 structuredContent：{str(out)[:300]}")
        return sc

    def upload(self, path, mime_type):
        out = self._run(["upload", str(path), "--mime-type", mime_type])
        aid = out.get("artifact_id")
        if not aid:
            raise RuntimeError(f"上传失败，无 artifact_id：{str(out)[:300]}")
        return aid

    def wallet(self):
        try:
            return self.call("beatra.wallet.get", {})
        except Exception:
            return {}

    def models(self, capability):
        sc = self.call("beatra.models.list", {"capability": capability})
        return sc.get("models") or []


# ---------------------------------------------------------------- 生产配方


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def resolve_ref(name, outdir, ledger, run_ids):
    """解析一个参考图名字。

    返回 ('file', Path) 或 ('dep', shot_id)。
    名字去掉扩展名后若是本批次要生成的格子，就是依赖，等上游产出后再取。
    """
    name = str(name)
    base = name
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break
    if base in run_ids:
        return "dep", base
    for cand in (outdir / name, outdir / base):
        if cand.is_file():
            return "file", cand
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        cand = outdir / (base + ext)
        if cand.is_file():
            return "file", cand
    rec = ledger.get("shots", {}).get(base)
    if rec and rec.get("file"):
        cand = outdir / rec["file"]
        if cand.is_file():
            return "file", cand
    hits = sorted(p for p in outdir.glob(base + "*") if p.is_file())
    if len(hits) == 1:
        return "file", hits[0]
    if hits:
        raise SystemExit(f"参考图 {name!r} 匹配到多个文件，请写全名：{[h.name for h in hits]}")
    if re.match(r"^[Pp]\d+$", base):
        hint = f"  它像是一个格子号：先跑那一格（--shots {base}），产出后再跑本格。"
    else:
        hint = ("  它多半是定妆图：按 SKILL.md「人物一致性」那节出定妆图，"
                "存成 PNG 拷进本目录。")
    raise SystemExit(f"找不到参考图 {name!r}（在 {outdir}）。\n{hint}")


def build_levels(deps_map):
    """按依赖分层：同一层的格子互不依赖，可以并发跑。

    例：P03 拿 P06 当参考 -> P06 在第 0 层，P03 在第 1 层。
    """
    levels = []
    done = set()
    pending = dict(deps_map)
    while pending:
        layer = [sid for sid, deps in pending.items() if all(d in done for d in deps)]
        if not layer:
            raise SystemExit(f"参考图依赖成环：{pending}")
        levels.append(layer)
        for sid in layer:
            done.add(sid)
            pending.pop(sid)
    return levels


def mime_of(path):
    return "image/png" if path.suffix.lower() == ".png" else "image/jpeg"


def prepare_upload(path, card):
    """PNG 带 alpha 时部分模型会拒收（wan2.7 系列 reject_png_alpha），转成 JPEG 再传。"""
    rejects_alpha = False
    inputs = card.get("inputs") or {}
    hard = inputs.get("hard_constraints") or {}
    if isinstance(hard.get("alpha"), str) and "reject" in hard["alpha"]:
        rejects_alpha = True
    if not rejects_alpha or path.suffix.lower() != ".png":
        return path, mime_of(path)
    try:
        from PIL import Image
    except ImportError:
        return path, mime_of(path)
    try:
        with Image.open(path) as im:
            if im.mode in ("RGBA", "LA", "P"):
                rgb = Image.new("RGB", im.size, (255, 255, 255))
                rgb.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
                tmp = path.with_suffix(".upload.jpg")
                rgb.save(tmp, "JPEG", quality=95, optimize=True)
                return tmp, "image/jpeg"
    except Exception:
        pass
    return path, mime_of(path)


def build_payload(shot, cfg, mode, model, refs, prompt, canvas):
    payload = {
        "model": model,
        "prompt": prompt,
        "canvas": canvas,
        "count": 1,
    }
    if mode in ("transform", "edit"):
        payload["images"] = [{"type": "artifact", "artifact_id": rid} for rid in refs]
    if mode == "edit":
        payload["edit_regions"] = cfg["edit_regions"]
    neg = cfg.get("negative_prompt")
    if neg:
        payload["negative_prompt"] = neg
    return payload


# ---------------------------------------------------------------- 准入检查


def admit(beatra, mode, model, canvas, refs_count, cfg):
    """付费前对照 live model card 做准入检查 + 估价。返回 (估价, 说明列表)。"""
    notes = []
    cap = CAPABILITY[mode]
    cards = beatra.models(cap)
    if not cards:
        sys.exit(f"能力 {cap} 没有可用模型卡")
    card = next((c for c in cards if c.get("model") == model), None)
    if card is None:
        avail = [c.get("model") for c in cards]
        sys.exit(f"模型 {model!r} 不支持能力 {cap}。可选：{avail}")
    if card.get("status") != "available":
        sys.exit(f"模型 {model!r} 当前状态 {card.get('status')!r}，不可用")

    names = control_names(card)
    if cfg.get("negative_prompt") and "negative_prompt" not in names:
        sys.exit(f"模型 {model!r} 不支持 negative_prompt（controls={names}）")
    if mode == "edit" and "edit_regions" not in names:
        sys.exit(f"模型 {model!r} 不支持 edit_regions（controls={names}）")
    if mode in ("transform", "edit"):
        limit, where = reference_limit(card)
        if refs_count > limit:
            sys.exit(f"模型 {model!r} 参考图上限 {limit}（{where}），本次要 {refs_count} 张")
        notes.append(f"参考图上限 {limit}（{where}）")

    # 画幅档位
    tiers = ((card.get("canvas") or {}).get("preset_tiers")) or []
    tier = canvas.get("tier")
    if tiers and tier and tier not in tiers:
        sys.exit(f"模型 {model!r} 不支持画幅档 {tier}（可选 {tiers}）")

    # 估价
    opts = pricing_options(card)
    est = None
    for opt in opts:
        dims = opt.get("dimensions") or {}
        if not dims:
            if est is None:
                est = int(opt.get("unit_credits"))
        elif dims.get("resolution") == tier:
            est = int(opt.get("unit_credits"))
    if est is None:
        if opts:
            est = max(int(o.get("unit_credits")) for o in opts)
            notes.append(f"未能按档位 {tier} 唯一匹配价格，按最高档 {est} 估")
    notes.append(f"模型 {model} · 能力 {cap} · 状态 available")
    return est, notes, card


# ---------------------------------------------------------------- 任务轮询


def poll_task(beatra, task_id, timeout=1800, interval=5.0):
    """轮询到终态，返回 (status, structuredContent)。"""
    deadline = time.time() + timeout
    while True:
        sc = beatra.call("beatra.tasks.get", {"task_id": task_id})
        status = sc.get("status")
        if status in ("succeeded", "failed", "canceled", "expired"):
            return status, sc
        if time.time() > deadline:
            return "timeout", sc
        time.sleep(interval + random.uniform(0, 1.5))


# ---------------------------------------------------------------- 主流程


def run_shot(beatra, shot_id, shot, cfg, mode, model, refspecs, canvas,
             outdir, ledger, args, idx, cards):
    """处理一格：上传参考 → 提交 → 轮询 → 下载 → 记账。"""
    tag = f"[{idx}] {shot_id}"
    base = {"shot_id": shot_id, "mode": mode, "model": model}

    # ---- 按配方顺序解析参考图（依赖上游格子的，等它产出后再取）
    refs_files = []
    for spec in refspecs:
        if spec["kind"] == "file":
            refs_files.append(spec["val"])
        else:
            rec = ledger.get("shots", {}).get(spec["val"])
            if not rec or not rec.get("file"):
                raise RuntimeError(f"依赖 {spec['val']} 尚未产出，无法作为参考图")
            dep_path = outdir / rec["file"]
            if not dep_path.is_file():
                raise RuntimeError(f"依赖 {spec['val']} 的文件不存在：{dep_path}")
            refs_files.append(dep_path)

    # ---- 上传参考图（带内容哈希缓存，同文件不重复上传）
    artifact_ids = []
    for path in refs_files:
        digest = file_digest(path)
        cached = ledger.get("uploads", {}).get(digest)
        if cached:
            artifact_ids.append(cached["artifact_id"])
            print(f"{tag} 复用参考图 {path.name} -> {cached['artifact_id']}", flush=True)
        else:
            sel = (cards.get(shot_id) or {}).get("card") or {}
            up_path, mime = prepare_upload(path, sel)
            aid = beatra.upload(up_path, mime)
            ledger.setdefault("uploads", {})[digest] = {
                "artifact_id": aid, "path": path.name, "mime_type": mime,
            }
            artifact_ids.append(aid)
            print(f"{tag} 上传参考图 {path.name} -> {aid}", flush=True)

    # ---- 组装请求 + 稳定 ID
    prompt = cfg.get("prompt") or shot.get("image_prompt_en")
    if not prompt:
        raise SystemExit(f"{shot_id} 没有可用的 prompt")
    payload = build_payload(shot, cfg, mode, model, artifact_ids, prompt, canvas)
    fp = fingerprint(payload)
    rid = f"zuowen-{shot_id}-{fp[:16]}"
    payload["client_request_id"] = rid

    rec = ledger.setdefault("requests", {}).get(rid)
    if rec and rec.get("status") == "succeeded" and not args.force:
        print(f"{tag} 已完成（{rec.get('credits')} credits），跳过", flush=True)
        return rec

    if args.dry_run:
        print(f"{tag} 计划: {mode} / {model} / client_request_id={rid}", flush=True)
        return {"shot_id": shot_id, "status": "planned", "credits": 0}

    # ---- 提交（同一 ID，失败可安全重试）
    attempt = 0
    seen_task_ids = set()
    while attempt <= args.max_retries:
        attempt += 1
        try:
            sc = beatra.call(TOOL[mode], payload)
        except Exception as exc:
            print(f"{tag} 提交异常（第 {attempt} 次）：{exc}", flush=True)
            time.sleep(3 * attempt)
            continue

        err = sc.get("error") or {}
        code = err.get("code")
        if code == "insufficient_balance":
            sys.exit(f"{tag} 余额不足：{err.get('message')}\n{err.get('details', {}).get('topup_url', '')}")
        if code == "rate_limited":
            print(f"{tag} 并发超限，退避重试（第 {attempt} 次）", flush=True)
            time.sleep(5 * attempt)
            continue
        if code:
            print(f"{tag} 提交被拒：{err.get('message')}", flush=True)
            if attempt > args.max_retries:
                return {"shot_id": shot_id, "status": "rejected", "error": err.get("message"), "credits": 0}
            time.sleep(3 * attempt)
            continue

        task_id = sc.get("task_id")
        if not task_id:
            print(f"{tag} 提交未返回 task_id：{str(sc)[:200]}", flush=True)
            time.sleep(3)
            continue
        if task_id in seen_task_ids:
            # 服务端按 client_request_id 去重，返回了同一个任务；没有新的尝试在跑
            print(f"{tag} 服务端幂等命中同一任务 {task_id}，不再重复提交", flush=True)
            break
        seen_task_ids.add(task_id)

        print(f"{tag} 提交 task={task_id}（第 {attempt} 次）", flush=True)
        status, final = poll_task(beatra, task_id)

        if status == "succeeded":
            arts = final.get("artifacts") or []
            if not arts:
                print(f"{tag} 成功但无 artifact", flush=True)
                return {"shot_id": shot_id, "status": "no_artifact", "credits": 0}
            art = arts[0]
            aid = art.get("artifact_id")
            url = art.get("url")
            out = outdir / f"{shot_id}.png"
            urllib.request.urlretrieve(url, out)
            credits = ((final.get("billing") or {}).get("net_charged_credits"))
            rec = {"shot_id": shot_id, "mode": mode, "model": model, "fingerprint": fp,
                   "client_request_id": rid, "task_id": task_id, "status": "succeeded",
                   "artifact_id": aid, "url": url, "file": out.name,
                   "credits": float(credits) if credits is not None else None}
            ledger.setdefault("requests", {})[rid] = rec
            ledger.setdefault("shots", {})[shot_id] = rec
            print(f"{tag} 完成 -> {out.name}（{rec['credits']} credits）", flush=True)
            return rec

        if status == "timeout":
            print(f"{tag} 轮询超时，任务 {task_id} 仍在跑；重跑本脚本会凭同一 ID 接上", flush=True)
            ledger.setdefault("requests", {})[rid] = {**base, "fingerprint": fp,
                "client_request_id": rid, "task_id": task_id, "status": "running"}
            return {"shot_id": shot_id, "status": "timeout", "credits": 0}

        # failed / canceled：同 ID 同参数重试是幂等的，不会重复扣已扣的费
        print(f"{tag} 任务 {status}：{(final.get('error') or {}).get('message')}（第 {attempt} 次）", flush=True)
        ledger.setdefault("requests", {})[rid] = {**base, "fingerprint": fp,
            "client_request_id": rid, "task_id": task_id, "status": status,
            "error": (final.get("error") or {}).get("message")}
        if attempt > args.max_retries:
            break
        time.sleep(3 * attempt)

    return {"shot_id": shot_id, "status": "failed", "credits": 0}


def main():
    ap = argparse.ArgumentParser(description="批量出图 + 幂等重试")
    ap.add_argument("-s", "--storyboard", required=True, type=Path, help="storyboard.json")
    ap.add_argument("-p", "--production", required=True, type=Path, help="production.json 配方")
    ap.add_argument("-o", "--outdir", required=True, type=Path, help="图片输出目录")
    ap.add_argument("--client", type=Path, default=DEFAULT_CLIENT, help="mcp_client.py 路径")
    ap.add_argument("--shots", default="", help="只跑这些格，逗号分隔，如 P03,P05")
    ap.add_argument("--concurrency", type=int, default=MAX_CONCURRENCY, help="并发数（Beatra 上限 4）")
    ap.add_argument("--max-retries", type=int, default=2, help="单格最大重试次数")
    ap.add_argument("--ledger", type=Path, default=None, help="ledger 路径，默认 outdir/batch_ledger.json")
    ap.add_argument("--force", action="store_true", help="忽略 ledger 里已成功的记录，重来")
    ap.add_argument("--dry-run", action="store_true", help="只出计划和估价，不花钱")
    ap.add_argument("--confirm", action="store_true", help="确认按估价付费提交")
    args = ap.parse_args()

    args.concurrency = max(1, min(args.concurrency, MAX_CONCURRENCY))
    sb = load_json(args.storyboard)
    prod = load_json(args.production)
    canvas = prod.get("canvas") or {"type": "preset", "tier": "1K", "aspect": "4:3"}
    args.outdir.mkdir(parents=True, exist_ok=True)
    ledger_path = args.ledger or (args.outdir / "batch_ledger.json")
    ledger = load_json(ledger_path) if ledger_path.is_file() else {}
    ledger.setdefault("requests", {})
    ledger.setdefault("uploads", {})
    ledger.setdefault("shots", {})

    wanted = [s.strip() for s in args.shots.split(",") if s.strip()]
    shot_cfg = prod.get("shots") or {}
    plans = []
    for shot in sb.get("shots") or []:
        sid = shot.get("shot_id")
        if wanted and sid not in wanted:
            continue
        cfg = shot_cfg.get(sid)
        if not cfg:
            print(f"跳过 {sid}：production.json 里没有配方", flush=True)
            continue
        plans.append((sid, shot, cfg))

    if not plans:
        sys.exit("没有可执行的格子")

    beatra = Beatra(args.client)
    wallet_before = beatra.wallet()
    before = wallet_before.get("balance_credits")

    # ---- 解析参考图：能直接找到文件的就用文件，指到本批次另一格的记为依赖
    run_ids = {sid for sid, _, _ in plans}
    cards = {}
    deps_of = {}
    for sid, shot, cfg in plans:
        mode = cfg.get("mode", "generate")
        model = cfg.get("model") or "auto"
        names = cfg.get("references") or ([cfg["base"]] if cfg.get("base") else [])
        deps = []
        refspecs = []
        for n in names:
            kind, val = resolve_ref(n, args.outdir, ledger, run_ids)
            refspecs.append({"name": n, "kind": kind, "val": val})
            if kind == "dep":
                deps.append(val)
        deps_of[sid] = deps
        cards[sid] = {"mode": mode, "model": model, "refspecs": refspecs, "deps": deps,
                      "names": names, "est": None, "card": None}

    # ---- 分层：依赖上游产出的格子排到后面
    levels = build_levels({sid: deps_of[sid] for sid, _, _ in plans})

    # ---- 先做准入检查与估价
    est_total = 0
    print("=" * 68)
    print("出图入场卡")
    print("=" * 68)
    for sid, shot, cfg in plans:
        c = cards[sid]
        est, notes, card = admit(beatra, c["mode"], c["model"], canvas, len(c["names"]), cfg)
        c["est"] = est
        c["card"] = card
        est_total += est or 0
        dep_txt = f"  依赖:{','.join(c['deps'])}" if c["deps"] else ""
        n_file = sum(1 for r in c["refspecs"] if r["kind"] == "file")
        print(f"  {sid}  {c['mode']:<9} {c['model']:<22} 参考{len(c['names'])}张"
              f"（现成{n_file}/待产出{len(c['deps'])}）  约 {est} credits{dep_txt}")
        for n in notes:
            print(f"       · {n}")
    print("-" * 68)
    print(f"  合计估价：{est_total} credits")
    if before is not None:
        print(f"  当前余额：{before} credits")
    print(f"  执行分层：{[[s for s in lv] for lv in levels]}")
    if not args.dry_run and not args.confirm:
        print("\n这是付费操作。加 --confirm 才会真的提交；加 --dry-run 只看计划。")
        sys.exit(2)
    print("=" * 68, flush=True)

    if args.dry_run:
        return

    # ---- 执行：按层跑，同层内并发，每层结束落一次 ledger 供下层取用
    results = []
    idx = 0
    for level in levels:
        futs = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for sid in level:
                shot, cfg = next(((s2, c) for s, s2, c in plans if s == sid))
                idx += 1
                futs.append((sid, pool.submit(
                    run_shot, beatra, sid, shot, cfg,
                    cards[sid]["mode"], cards[sid]["model"],
                    cards[sid]["refspecs"], canvas, args.outdir,
                    ledger, args, idx, cards)))
            for sid_f, fut in futs:
                try:
                    results.append(fut.result())
                except Exception as exc:
                    results.append({"status": "error", "shot_id": sid_f,
                                    "error": str(exc), "credits": 0})
        with open(ledger_path, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, ensure_ascii=False, indent=2)

    with open(ledger_path, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)

    # ---- 汇总
    # 真实扣费看余额差：任务里的 billing 是那次生成的计费快照，
    # 幂等命中时会被重复读出来，不能当本轮开销。
    task_billed = sum(float(r.get("credits") or 0) for r in results)
    ok = [r for r in results if r.get("status") == "succeeded"]
    bad = [r for r in results if r.get("status") not in ("succeeded", "planned")]
    after = beatra.wallet().get("balance_credits")
    print("=" * 68)
    print(f"完成 {len(ok)}/{len(results)} 格")
    if before is not None and after is not None:
        delta = float(before) - float(after)
        print(f"余额 {before} -> {after}")
        print(f"本轮实际扣费 {delta} credits（任务计费快照合计 {task_billed}，"
              f"差额来自幂等命中或退款）")
    else:
        print(f"任务计费快照合计 {task_billed} credits")
    for r in bad:
        print(f"  ✗ {r.get('shot_id')}: {r.get('status')} {r.get('error') or ''}")
    print(f"ledger: {ledger_path}")
    print("=" * 68)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
