#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作文漫剧成片流水线：分镜图 → 视频 → 画外音 → 混音 → 字幕 → 老电视质感。

用法：

    # 从图片直接出成片（含视频生成，会花钱）
    python3 voiceover.py -s storyboard.json -i images/ \
        --from-images --duration 16 --resolution 480p -o out.mp4

    # 已有视频，只做配音/混音/字幕
    python3 voiceover.py -s storyboard.json -i images/ --video in.mp4 -o out_vo.mp4

    # 复用已生成的配音，不调 TTS
    python3 ... --audio-dir /path/to/mp3

    # 加老电视质感（扫描线/颗粒/暗角/胶片偏灰）
    python3 ... --crt

成本：视频按秒计（wan3.0-video 480p = 225 credits/秒），配音按字符计
（minimax-speech-2.8-turbo = 200/1000 字符）。两者都先打印估价再动手。
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("需要 Pillow：pip install pillow")

DEFAULT_CLIENT = os.path.expanduser(
    "~/.claude/skills/beatra-ai-video-studio/scripts/mcp_client.py")
SAFETY = "cartoon child character, stylized animation, non-photorealistic, child-safe"
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_INDEX = 2          # W6 粗体
DEFAULT_VOICE = "voice_preset_niannian"
DEFAULT_MODEL = "minimax-speech-2.8-turbo"


# ----------------------------------------------------------------- Beatra


class Beatra:
    def __init__(self, client):
        self.client = client
        if not os.path.isfile(client):
            sys.exit(f"找不到 mcp_client.py：{client}\n用 --client 指定路径")

    def call(self, tool, payload):
        p = subprocess.run([sys.executable, self.client, "call", tool],
                           input=json.dumps(payload, ensure_ascii=False),
                           capture_output=True, text=True)
        raw = p.stdout.strip()
        i = raw.find("{")
        if i < 0:
            raise RuntimeError(f"{tool} 无输出：{raw[:200]} / {p.stderr[:200]}")
        return (json.loads(raw[i:]).get("structuredContent") or {})

    def upload(self, path, mime="image/jpeg"):
        p = subprocess.run([sys.executable, self.client, "upload", path,
                            "--mime-type", mime], capture_output=True, text=True)
        raw = p.stdout.strip()
        i = raw.find("{")
        if i < 0:
            raise RuntimeError(f"上传失败：{raw[:200]}")
        return json.loads(raw[i:]).get("artifact_id")

    def wallet(self):
        try:
            return self.call("beatra.wallet.get", {})
        except Exception:
            return {}


# ----------------------------------------------------------------- 工具


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"命令失败：{' '.join(cmd[:3])}...\n{r.stderr[-600:]}")
    return r.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=width,height", "-of", "json", path])
    d = json.loads(out)
    v = next((s for s in d["streams"] if s.get("width")), {})
    return float(d["format"]["duration"]), v.get("width", 740), v.get("height", 554)


def to_jpeg(src, dst, quality=95):
    Image.open(src).convert("RGB").save(dst, "JPEG", quality=quality, optimize=True)
    return dst


# ------------------------------------------------- 镜头切点检测


def map_images(images, shot_ids):
    """把图片文件按 shot_id 排好序并建立对应关系。

    图片文件名常带版本后缀（P02_v6.png / P06_keyframe.png），
    而 shot_id 是 P02 / P06 —— 直接拿文件名当 key 会全部对不上。
    """
    out = []
    for sid in shot_ids:
        hits = [p for p in images if os.path.basename(p).split(".")[0].startswith(sid)]
        if len(hits) == 1:
            out.append((sid, hits[0]))
        elif len(hits) > 1:
            raise SystemExit(f"{sid} 匹配到多张图：{[os.path.basename(h) for h in hits]}")
    if not out:
        raise SystemExit("图片和 shot_id 对不上，检查 images 目录")
    return out


def detect_shots(video, images, step=0.2, workdir="/tmp/_shots"):
    """以分镜图为基准，逐帧比对找出每个镜头的起止时间。

    视频是从这些分镜图生成的，所以画面相似度足以定位切点。
    """
    os.makedirs(workdir, exist_ok=True)

    def feat(img):
        g = img.convert("L").resize((32, 32), Image.LANCZOS)
        import numpy as np
        a = np.asarray(g, dtype="float32")
        return ((a - a.mean()) / (a.std() + 1e-6)).ravel()

    import numpy as np
    refs = [(sid, feat(Image.open(p))) for sid, p in images]
    dur, _, _ = probe(video)
    times = [round(t, 2) for t in np.arange(0, dur, step)]
    labels = []
    for t in times:
        png = os.path.join(workdir, "f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", video,
                        "-frames:v", "1", png], check=True)
        f = feat(Image.open(png))
        labels.append(max(refs, key=lambda r: float((f * r[1]).sum()))[0])
    # 归并成区间
    shots, cur, start = [], labels[0], times[0]
    for t, lb in zip(times[1:], labels[1:]):
        if lb != cur:
            shots.append((cur, start, t))
            cur, start = lb, t
    shots.append((cur, start, dur))
    # 同一个分镜图只出现一次；后面再出现的同名标签是比对误判，
    # 取第一次出现的时间，否则字典会把正确的切点覆盖掉。
    first = {}
    for name, st, _ in shots:
        first.setdefault(name, st)
    return [(name, st) for name, st in sorted(first.items(), key=lambda x: x[1])]


# ------------------------------------------------- 配音


def pick_captions(storyboard, mode="first", only=None):
    """从 storyboard.json 取每格要念的原文。L0 下旁白必须是原文片段。"""
    out = []
    for s in storyboard["shots"]:
        sid = s["shot_id"]
        if only and sid not in only:
            continue
        caps = s.get("captions") or []
        if not caps:
            continue
        text = caps[0] if mode == "first" else "，".join(caps)
        out.append((sid, text))
    return out


def tts_all(beatra, items, voice, model, speed, workdir, lang="zh-CN"):
    os.makedirs(workdir, exist_ok=True)
    results = {}

    def one(idx_item):
        idx, (sid, text) = idx_item
        payload = {"model": model, "voice": voice, "language": lang,
                   "input": text, "speed": speed, "format": "mp3",
                   "sample_rate": 44100,
                   "client_request_id": "vo-%s-%s" % (sid, hashlib.md5(text.encode("utf-8")).hexdigest()[:10])}
        # previous_text 串上下文，保持语气连续
        if idx > 0:
            payload["previous_text"] = items[idx - 1][1]
        for attempt in range(5):
            sc = beatra.call("beatra.speech.synthesize", payload)
            err = sc.get("error") or {}
            if sc.get("task_id"):
                tid = sc["task_id"]
                for _ in range(90):
                    st = beatra.call("beatra.tasks.get", {"task_id": tid})
                    if st.get("status") in ("succeeded", "failed", "canceled"):
                        arts = st.get("artifacts") or []
                        if arts:
                            p = os.path.join(workdir, f"{sid}.mp3")
                            urllib.request.urlretrieve(arts[0]["url"], p)
                            return sid, p, (st.get("billing") or {}).get("net_charged_credits")
                        return sid, None, (st.get("billing") or {}).get("net_charged_credits")
                    time.sleep(5)
            code = err.get("code")
            if code == "rate_limited":
                wait = (err.get("details") or {}).get("retry_after_seconds", 30)
                time.sleep(min(wait, 60) + 5)
                continue
            if code == "insufficient_balance":
                sys.exit(f"余额不足：{err.get('message')}\n"
                         f"{(err.get('details') or {}).get('topup_url', '')}")
            time.sleep(3 * (attempt + 1))
        return sid, None, 0

    with ThreadPoolExecutor(max_workers=4) as pool:
        for sid, path, credits in pool.map(one, enumerate(items)):
            results[sid] = (path, credits)
            print(f"  配音 {sid}: {'OK' if path else '失败'} {credits} credits")
    return results


# ------------------------------------------------- 裁静音（正确姿势）


def trim_silence(src, dst):
    """裁掉首尾静音。

    不要用 ffmpeg 的 silenceremove：它的 stop_periods=1 会在句中第一个停顿处
    就截断，把「把笔全部扫落在地」剪成 0.16 秒。正确做法是先用 silencedetect
    量出首段静音的尾点与末段静音的起点，再按 -ss/-to 显式裁。
    """
    total = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "csv=p=0", src]).strip())
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-af",
                        "silencedetect=noise=-45dB:d=0.06", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r.stderr)]
    iv = list(zip(starts, ends))
    head = iv[0][1] if iv and iv[0][0] < 0.02 else 0.0
    tail = total
    for s, e in iv:
        if e >= total - 0.03:
            tail = min(tail, s)
    dur = max(0.05, tail - head)
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{head:.4f}", "-to", f"{tail:.4f}",
         "-i", src, "-af",
         f"afade=t=in:st=0:d=0.015,afade=t=out:st={max(0, dur-0.02):.3f}:d=0.02:curve=tri,"
         "aresample=44100", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", dst])
    return dst, dur


# ------------------------------------------------- 对齐与混音


def plan(shots, dur_map, order, lead=0.08, gap=0.25):
    """每句旁白尽量落在对应镜头里；上一句没说完就把这句往后推。"""
    bounds = dict(shots)
    out, prev_end = [], 0.0
    for sid in order:
        if sid not in bounds or sid not in dur_map:
            continue
        st = bounds[sid]
        start = max(st + lead, prev_end + gap)
        end = start + dur_map[sid]
        out.append({"sid": sid, "start": start, "end": end})
        prev_end = end
    return out


def mix_audio(video, clips, plan_list, out_wav, keep_original=True, total=None):
    args = ["ffmpeg", "-v", "error", "-y"]
    for c in clips:
        args += ["-i", c]
    if keep_original:
        args += ["-i", video]
    fc = []
    idx = 0
    for p in plan_list:
        ms = int(p["start"] * 1000)
        fc.append(f"[{idx}:a]adelay={ms}|{ms}[a{idx}]")
        idx += 1
    fc.append("".join(f"[a{i}]" for i in range(idx)) +
              f"amix=inputs={idx}:normalize=0[narr]")
    src = idx
    if keep_original:
        fc.append(f"[{src}:a]volume=-12dB,lowpass=f=1200[amb]")
        fc.append("[narr][amb]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    else:
        fc.append("[narr]alimiter=limit=0.95[a]")
    if idx == 0:
        run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "2", "-ar", "44100",
             "-c:a", "pcm_s16le", out_wav])
        return out_wav
    args += ["-filter_complex", ";".join(fc), "-map", "[a]",
             "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", out_wav]
    run(args)
    return out_wav


def apply_atempo(clips, sids, dur_map, tempo, work):
    """用 ffmpeg atempo 给配音整体压速。

    旁白塞不进视频时不要重新合成（会重复扣费），压速是零成本的。
    atempo 单次支持 0.5~2.0，需要更多就串联。
    """
    if abs(tempo - 1.0) < 0.01:
        return clips, dict(dur_map)
    chain = ",".join(["atempo=%.4f" % tempo] * max(1, int(math.ceil(math.log(tempo, 2)) + 1)))
    new_clips, new_dur = [], {}
    for sid, src in zip(sids, clips):
        dst = src.replace(".wav", f"_t{tempo:.3f}.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", chain,
             "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", dst])
        new_clips.append(dst)
        new_dur[sid] = float(run(["ffprobe", "-v", "error", "-show_entries",
                                  "format=duration", "-of", "csv=p=0", dst]).strip())
    return new_clips, new_dur


# ------------------------------------------------- 字幕


def render_subtitles(plan_list, texts, W, H, outdir):
    os.makedirs(outdir, exist_ok=True)
    font = ImageFont.truetype(FONT_PATH, max(20, int(H * 0.065)), index=FONT_INDEX)
    paths = []
    for p in plan_list:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        b = dr.textbbox((0, 0), p["text"], font=font)
        x = (W - (b[2] - b[0])) // 2 - b[0]
        y = H - int(H * 0.13) - b[1]
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)):
            dr.text((x + dx, y + dy), p["text"], font=font, fill=(0, 0, 0, 200))
        dr.text((x, y), p["text"], font=font, fill=(255, 255, 255, 255))
        pth = os.path.join(outdir, f"sub_{p['sid']}.png")
        img.save(pth)
        p["png"] = pth
        paths.append(pth)
    return paths


def write_srt(plan_list, path):
    def ts(x):
        h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    out = ""
    for i, p in enumerate(plan_list):
        out += f"{i+1}\n{ts(p['start'])} --> {ts(p['end'])}\n{p['text']}\n\n"
    open(path, "w", encoding="utf-8").write(out)
    return path


def mux(video, wav, plan_list, out, crt=False, duration=None):
    args = ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav]
    for p in plan_list:
        if p.get("png"):
            args += ["-i", p["png"]]
    n_png = len(plan_list)
    fc = []
    for i, p in enumerate(plan_list):
        fc.append(f"[{2+i}:v]format=rgba[o{i}]")
    cur = "0:v"
    for i, p in enumerate(plan_list):
        nxt = f"v{i}"
        fc.append(f"[{cur}][o{i}]overlay=0:0:enable='between(t,{p['start']},{p['end']})'[{nxt}]")
        cur = nxt
    if crt:
        fc.append(
            f"[{cur}]scale=640:480:flags=bilinear,noise=alls=6:allf=t+u,"
            "eq=saturation=1.14:contrast=1.06:brightness=0.015,vignette=PI/4.5,"
            "colorbalance=rs=.03:gs=.01:bs=-.02,"
            "geq=lum='lum(X,Y)+10*mod(Y,2)':cb='cb(X,Y)':cr='cr(X,Y)',format=yuv420p[v]")
    else:
        fc.append(f"[{cur}]format=yuv420p[v]")
    args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "1:a",
             "-c:v", "libx264", "-crf", "19", "-preset", "medium",
             "-c:a", "aac", "-b:a", "192k"]
    if duration:
        args += ["-t", f"{duration:.3f}"]
    args += [out]
    run(args)
    return out


# ------------------------------------------------- 视频生成


def make_video(beatra, images, out, duration, resolution, aspect, model="auto"):
    aids = []
    for p in images:
        aids.append(beatra.upload(to_jpeg(p, p + ".upload.jpg")))
    payload = {"model": model,
               "references": [{"kind": "image", "media": {"type": "artifact", "artifact_id": a}}
                              for a in aids],
               "prompt": "把这几张分镜图按顺序做成一段连贯的动画短片，镜头平稳，不要快速切换",
               "duration": duration, "resolution": resolution,
               "aspect_ratio": aspect,
               "client_request_id": "video-" + hashlib.md5(
                   "".join(aids).encode("utf-8")).hexdigest()[:10]}
    sc = beatra.call("beatra.videos.generate_from_references", payload)
    if not sc.get("task_id"):
        sys.exit(f"视频提交失败：{sc.get('error')}")
    tid = sc["task_id"]
    for _ in range(600):
        st = beatra.call("beatra.tasks.get", {"task_id": tid})
        if st.get("status") in ("succeeded", "failed", "canceled"):
            arts = st.get("artifacts") or []
            if not arts:
                sys.exit(f"视频失败：{st.get('error')}")
            urllib.request.urlretrieve(arts[0]["url"], out)
            return out, (st.get("billing") or {}).get("net_charged_credits")
        time.sleep(8)
    sys.exit("视频轮询超时")


# ------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser(description="作文漫剧成片流水线")
    ap.add_argument("-s", "--storyboard", required=True, help="storyboard.json")
    ap.add_argument("-i", "--images", required=True, help="分镜图目录")
    ap.add_argument("-o", "--out", required=True, help="输出 mp4")
    ap.add_argument("--video", help="已有视频（给了就不生成）")
    ap.add_argument("--from-images", action="store_true", help="用分镜图生成视频")
    ap.add_argument("--duration", type=int, default=16, help="视频时长秒")
    ap.add_argument("--resolution", default="480p", help="视频分辨率")
    ap.add_argument("--aspect", default="4:3", help="视频画幅")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="TTS 音色 id")
    ap.add_argument("--tts-model", default=DEFAULT_MODEL, help="TTS 模型")
    ap.add_argument("--speed", type=float, default=1.05, help="语速")
    ap.add_argument("--caption-mode", default="first", choices=["first", "all"])
    ap.add_argument("--audio-dir", help="复用已生成的配音 mp3，不调 TTS")
    ap.add_argument("--no-subtitles", action="store_true")
    ap.add_argument("--no-original-audio", action="store_true", help="丢掉原视频音轨")
    ap.add_argument("--crt", action="store_true", help="加老电视质感")
    ap.add_argument("--client", default=DEFAULT_CLIENT, help="mcp_client.py 路径")
    ap.add_argument("--yes", action="store_true", help="跳过估价确认")
    args = ap.parse_args()

    sb = json.load(open(args.storyboard, encoding="utf-8"))
    all_imgs = [os.path.join(args.images, f) for f in os.listdir(args.images)
                if f.lower().endswith((".png", ".jpg", ".jpeg")) and "CHAR" not in f]
    if not all_imgs:
        sys.exit(f"{args.images} 里没有分镜图")
    imgs = map_images(all_imgs, [s["shot_id"] for s in sb["shots"]])
    beatra = Beatra(args.client)
    # 音频缓存在输出目录旁边：脚本中途失败也不丢已生成的配音，
    # 下次用 --audio-dir 指这里就能跳过 TTS，不重复扣费。
    work = os.path.join(os.path.dirname(os.path.abspath(args.out)) or ".", "_voiceover_cache")
    os.makedirs(work, exist_ok=True)

    caps = pick_captions(sb, args.caption_mode)
    if not caps:
        sys.exit("storyboard 里没有旁白可用")
    order = [sid for sid, _ in caps]
    text_of = dict(caps)

    # ---- 估价
    nchar = sum(len(t) for _, t in caps)
    est_vo = nchar * 200 / 1000
    est_vid = args.duration * 225 if args.from_images else 0
    print("=" * 66)
    print("成片入场卡")
    print("=" * 66)
    print(f"  分镜图：{len(imgs)} 张")
    print(f"  配音：{len(caps)} 句 / {nchar} 字，约 {est_vo:.1f} credits")
    print(f"  视频：{'生成 ' + str(args.duration) + 's ' + args.resolution + ' ≈ ' + str(int(est_vid)) + ' credits' if args.from_images else '沿用已有视频'}")
    bal = beatra.wallet().get("balance_credits")
    if bal is not None:
        print(f"  当前余额：{bal}")
    print("=" * 66, flush=True)
    if not args.yes:
        print("加 --yes 才会真的开始花钱。")
        sys.exit(2)

    # ---- 视频
    video = args.video
    if args.from_images or not video:
        if not args.from_images:
            sys.exit("没有 --video 也没有 --from-images，不知道视频从哪来")
        print("生成视频…", flush=True)
        video, c = make_video(beatra, imgs, os.path.join(work, "raw.mp4"),
                              args.duration, args.resolution, args.aspect)
        print(f"  视频完成 {c} credits")
    dur, W, H = probe(video)
    print(f"视频 {dur:.2f}s {W}x{H}")

    # ---- 镜头切点
    shots = detect_shots(video, imgs, workdir=os.path.join(work, "shots"))
    print("镜头切点：" + ", ".join(f"{n}@{s:.1f}" for n, s in shots))

    # ---- 配音
    dur_map, clips = {}, []
    if args.audio_dir:
        for sid, text in caps:
            p = os.path.join(args.audio_dir, f"{sid}.mp3")
            if not os.path.isfile(p):
                p = os.path.join(args.audio_dir, "tts", f"{sid}.mp3")
            if not os.path.isfile(p):
                sys.exit(f"缺 {p}")
            clips.append(p)
    else:
        res = tts_all(beatra, caps, args.voice, args.tts_model, args.speed,
                      os.path.join(work, "tts"))
        for sid, _ in caps:
            p = res.get(sid, (None, 0))[0]
            if not p:
                sys.exit(f"{sid} 配音失败")
            clips.append(p)
    # 裁静音 + 量时长
    trimmed = []
    for (sid, _), src in zip(caps, clips):
        w, d = trim_silence(src, os.path.join(work, f"{sid}.wav"))
        trimmed.append(w)
        dur_map[sid] = d
    print("配音时长合计 %.2fs / 视频 %.2fs" % (sum(dur_map.values()), dur))

    # ---- 对齐（塞不下就自动压速，不重新合成）
    tempo = 1.0
    plan_list = plan(shots, dur_map, order)
    for _ in range(8):
        if not plan_list:
            break
        over = plan_list[-1]["end"] - dur
        if over <= 0.03:
            break
        need = over / max(0.5, dur - plan_list[0]["start"])
        tempo *= (1 + min(need, 0.5))
        if tempo > 1.35:
            print(f"⚠ 压到 {tempo:.2f} 倍仍塞不下，建议改用更短的旁白或加长视频")
            break
        trimmed, dur_map = apply_atempo(trimmed, [sid for sid, _ in caps], dur_map, tempo, work)
        plan_list = plan(shots, dur_map, order)
    if tempo > 1.01:
        print(f"旁白自动压速 {tempo:.2f} 倍以塞进 {dur:.1f}s")
    for p in plan_list:
        p["text"] = text_of[p["sid"]]
        print(f"  {p['sid']} {p['start']:.2f} → {p['end']:.2f}  {p['text']}")
    if plan_list and plan_list[-1]["end"] > dur:
        print(f"⚠ 旁白超出视频 {plan_list[-1]['end'] - dur:.2f}s，末尾会被截断")

    # ---- 混音 + 字幕 + 封装
    wav = mix_audio(video, trimmed, plan_list, os.path.join(work, "mix.wav"),
                    keep_original=not args.no_original_audio, total=dur)
    if not args.no_subtitles:
        render_subtitles(plan_list, text_of, W, H, os.path.join(work, "subs"))
        write_srt(plan_list, os.path.splitext(args.out)[0] + ".srt")
    mux(video, wav, plan_list, args.out, crt=args.crt, duration=dur)
    print("成片：" + args.out)
    if not args.no_subtitles:
        print("字幕：" + os.path.splitext(args.out)[0] + ".srt")


if __name__ == "__main__":
    main()
