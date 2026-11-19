#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 storyboard.json 的结构与安全约束。

用法：
  python3 validate_storyboard.py outputs/我的妈妈/storyboard.json
  python3 validate_storyboard.py -            # 从 stdin 读

退出码：0 通过，1 有错误。

关于中文：image_prompt_en 默认只允许英文。唯一例外是
  handwritten Chinese text "错字"
这种受控形式（用于 L0 错别字梗）。该块内容不超过 40 字，且同样做隐私检查。

关于画风：全篇主体画风统一由顶层 style_prefix 决定，每格 prompt 必须以它开头。
若某一格需要换画风（例如首尾作业本特写用 pencil-notebook 做外壳），
在该格加 "style_prefix_override": "<另一套前缀>"，该格改用覆盖值校验。
"""

import json
import re
import sys

REQUIRED_TOP = ["title", "meta", "style_prefix", "safety_tags", "character_index", "typos", "shots"]
REQUIRED_META = ["level", "art_style", "aspect_ratio", "shot_count", "genre", "source_verdict", "source_signals"]
VERDICTS = {"student_essay", "user_confirmed"}
CONFIDENCE = {"high", "medium", "low"}
# 强信号关键词（判定依据应至少命中 2 条，且不能全是弱信号）
STRONG_SIGNALS = ["方格", "作文纸", "作业本", "答题卡", "红笔", "批改", "评语", "分数",
                  "铅笔", "涂改", "手写", "稚嫩", "橡皮"]
WEAK_SIGNALS = ["口语", "比喻", "儿童视角", "校园", "家庭", "拼音", "字数"]
REQUIRED_SHOT = ["shot_id", "shot_type", "source_text", "description_cn", "image_prompt_en", "captions", "dialogue", "characters"]

SHOT_TYPES = {"ELS", "LS", "MS", "CU", "ECU"}
LEVELS = {"L0", "L1", "L2"}
ASPECTS = {"4:3", "3:4", "16:9", "9:16", "1:1"}
GENRES = {"写人", "写事", "写景", "状物", "想象", "议论", "诗歌"}

SAFETY_TAGS = [
    "cartoon child character",
    "stylized animation",
    "non-photorealistic",
    "child-safe",
]

# 用正则匹配，避免把安全标签里的 "non-photorealistic" 误判为禁止词
BANNED_PATTERNS = [
    (re.compile(r"(?<!non-)(?<!non )photorealistic"), "photorealistic"),
    (re.compile(r"(?<!non-)(?<!non )photoreal\b"), "photoreal"),
    (re.compile(r"\brealistic photo"), "realistic photo"),
    (re.compile(r"\breal person"), "real person"),
    (re.compile(r"\bhyperrealistic"), "hyperrealistic"),
    (re.compile(r"\bphoto of a child"), "photo of a child"),
    (re.compile(r"\blifelike"), "lifelike"),
    (re.compile(r"\bdslr"), "dslr"),
    (re.compile(r"\b8k photo"), "8k photo"),
]

# 受控中文：只允许 handwritten Chinese text "…"，单块不超过 40 字
HANDWRITTEN_RE = re.compile(r'handwritten Chinese text "([^"\n]*)"')
HANDWRITTEN_MAX = 40
CJK_RE = re.compile(r"[\u4e00-\u9fa5]")

# 隐私：作用于整条 prompt（含 handwritten 块）
PRIVACY_PATTERNS = [
    (re.compile(r"1[3-9]\d{9}"), "疑似手机号"),
    (re.compile(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{2}\d{3}[\dXx]"), "疑似身份证号"),
    (re.compile(r"[\u4e00-\u9fa5]{2,6}(小学|中学|初中|高中|附中|实验学校)"), "疑似学校全称"),
    (re.compile(r"[\u4e00-\u9fa5]{2,4}(省|市)[\u4e00-\u9fa5]{2,4}(区|县|镇|街道)"), "疑似地址"),
    (re.compile(r"(?<!Chinese )\b(primary|middle|high)\s+school\b"), "疑似学校全称（改用 a Chinese primary school 等泛称）"),
]

# 启发式：拉丁转写的常见中文姓氏 + 名（如 Li Ming / Wang Fang）
ROMANIZED_SURNAMES = {
    "li", "wang", "zhang", "liu", "chen", "yang", "huang", "zhao", "wu", "zhou",
    "xu", "sun", "ma", "zhu", "hu", "guo", "he", "gao", "lin", "luo", "zheng",
    "liang", "xie", "song", "tang", "han", "feng", "deng", "cao", "peng", "zeng",
    "xiao", "tian", "dong", "pan", "yuan", "cai", "jiang", "yu", "du", "ye",
    "cheng", "wei", "su", "lu", "ding", "ren", "shen", "yao", "jin", "fu",
    "zhong", "qiu",
}
ROMANIZED_NAME_RE = re.compile(
    r"\b(" + "|".join(sorted(ROMANIZED_SURNAMES, key=len, reverse=True)) + r")\s+[A-Z][a-z]{1,10}\b",
    re.IGNORECASE,
)


class Checker:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def strip_handwritten(prompt):
    """移除受控中文块，返回（去掉后的文本, 提取到的中文块列表）。"""
    blocks = HANDWRITTEN_RE.findall(prompt)
    return HANDWRITTEN_RE.sub(" ", prompt), blocks


def check(data, c):
    for k in REQUIRED_TOP:
        if k not in data:
            c.err(f"缺少顶层字段: {k}")
    if c.errors:
        return

    meta = data["meta"]
    if not isinstance(meta, dict):
        c.err("meta 必须是对象")
        return
    for k in REQUIRED_META:
        if k not in meta:
            c.err(f"meta 缺少字段: {k}")
    level = meta.get("level")
    if level not in LEVELS:
        c.err(f"meta.level 必须是 {sorted(LEVELS)}，实际 {level!r}")
    if meta.get("aspect_ratio") not in ASPECTS:
        c.err(f"meta.aspect_ratio 不合法: {meta.get('aspect_ratio')!r}，允许 {sorted(ASPECTS)}")
    genre = meta.get("genre")
    if genre not in GENRES:
        c.err(f"meta.genre 不合法: {genre!r}，允许 {sorted(GENRES)}")
    is_poem = genre == "诗歌"

    # 准入判定：必须是学生作文，且证据充分
    verdict = meta.get("source_verdict")
    if verdict not in VERDICTS:
        c.err(f"meta.source_verdict 必须是 {sorted(VERDICTS)}，实际 {verdict!r}")
    signals = meta.get("source_signals")
    if not isinstance(signals, list) or not signals:
        c.err("meta.source_signals 必须是非空数组，列出判定依据")
    else:
        if len(signals) < 2:
            c.err(f"meta.source_signals 只有 {len(signals)} 条，至少需 2 条")
        strong = [s for s in signals for kw in STRONG_SIGNALS if kw in str(s)]
        weak = [s for s in signals for kw in WEAK_SIGNALS if kw in str(s)]
        if not strong:
            c.err("meta.source_signals 全是弱信号（无方格纸/批改/手写类证据），"
                  "请补强信号或改用 user_confirmed")
        elif len(set(strong)) < 2:
            c.warn(f"meta.source_signals 强信号只有 1 条（{sorted(set(strong))}），建议补足 2 条")
        if verdict == "user_confirmed" and not any("确认" in str(s) for s in signals):
            c.err("source_verdict=user_confirmed 时，source_signals 里必须有一条含「用户确认」")
    if meta.get("grade_confidence") not in CONFIDENCE:
        c.warn(f"meta.grade_confidence 建议填 {sorted(CONFIDENCE)}，"
               f"实际 {meta.get('grade_confidence')!r}")

    shots = data["shots"]
    if not isinstance(shots, list) or not shots:
        c.err("shots 必须是非空数组")
        return

    if meta.get("shot_count") != len(shots):
        c.err(f"meta.shot_count={meta.get('shot_count')} 与 shots 长度 {len(shots)} 不一致")

    if is_poem:
        if len(shots) != 4:
            c.err(f"诗歌必须正好 4 格，实际 {len(shots)} 格")
    elif not (4 <= len(shots) <= 16):
        c.warn(f"格数 {len(shots)} 超出建议范围 4-16")

    cap_limit = 35 if is_poem else 30

    prefix = data["style_prefix"]
    safety = data["safety_tags"]
    for tag in SAFETY_TAGS:
        if tag not in safety:
            c.err(f"safety_tags 缺少必需标签: {tag}")

    chars = data.get("character_index") or {}
    if not chars:
        c.err("character_index 不能为空")
    if len(chars) > 4:
        c.err(f"character_index 超过 4 个角色（{len(chars)}），请合并次要人物")
    for cid, info in chars.items():
        if not isinstance(info, dict):
            c.err(f"{cid} 必须是对象")
            continue
        if not info.get("role"):
            c.err(f"{cid} 缺少 role")
        appearance = info.get("appearance_en")
        if not appearance:
            c.err(f"{cid} 缺少 appearance_en（人物一致性靠它）")
        elif CJK_RE.search(appearance):
            c.err(f"{cid} appearance_en 含中文")
        elif len(appearance.split()) < 5:
            c.warn(f"{cid} appearance_en 过短（{len(appearance.split())} 词），人物容易漂移")

    # P01 必须是作业本特写：硬约束
    first = shots[0]
    if first.get("shot_type") != "ECU":
        c.err(f"P01 必须是 ECU 作业本特写，实际 {first.get('shot_type')!r}")
    desc1 = (first.get("description_cn") or "")
    if not any(w in desc1 for w in ["作业本", "作文本", "方格", "练习本", "纸"]):
        c.err("P01 描述里必须有作业本/方格纸/纸，否则怀旧钩子不成立")

    has_ecu = False
    shot_ids = set()
    for i, s in enumerate(shots, 1):
        for k in REQUIRED_SHOT:
            if k not in s:
                c.err(f"shots[{i-1}] 缺少字段: {k}")
        sid = s.get("shot_id", f"#{i}")
        if sid in shot_ids:
            c.err(f"shot_id 重复: {sid}")
        shot_ids.add(sid)
        if s.get("shot_type") not in SHOT_TYPES:
            c.err(f"{sid} shot_type 不合法: {s.get('shot_type')!r}")
        if s.get("shot_type") == "ECU":
            has_ecu = True

        prompt = s.get("image_prompt_en") or ""
        if not prompt:
            c.err(f"{sid} image_prompt_en 为空")
            continue
        # 每格可用 style_prefix_override 换画风（作业本外壳常用），
        # 但整篇主体画风仍由 data["style_prefix"] 统一。
        shot_prefix = s.get("style_prefix_override") or prefix
        if not isinstance(shot_prefix, str) or not shot_prefix.strip():
            c.err(f"{sid} style_prefix_override 必须是非空字符串")
            shot_prefix = prefix
        if not prompt.startswith(shot_prefix):
            c.err(f"{sid} image_prompt_en 未以 style_prefix 开头")

        # 受控中文：只允许 handwritten 块
        stripped, blocks = strip_handwritten(prompt)
        if CJK_RE.search(stripped):
            c.err(f"{sid} image_prompt_en 含中文。中文只能用 handwritten Chinese text \"…\" 包裹")
        for b in blocks:
            if CJK_RE.search(b) is None:
                c.err(f"{sid} handwritten 块里没有中文，多余的：{b!r}")
            if len(b) > HANDWRITTEN_MAX:
                c.err(f"{sid} handwritten 块超过 {HANDWRITTEN_MAX} 字（{len(b)}）：{b!r}")

        low = prompt.lower()
        for tag in SAFETY_TAGS:
            if tag not in low:
                c.err(f"{sid} image_prompt_en 缺少 safety tag: {tag}")
        for rx, label in BANNED_PATTERNS:
            if rx.search(low):
                c.err(f"{sid} image_prompt_en 含禁止词: {label}")
        for rx, label in PRIVACY_PATTERNS:
            if rx.search(prompt):
                c.err(f"{sid} image_prompt_en {label}")
        m = ROMANIZED_NAME_RE.search(prompt)
        if m:
            c.err(f"{sid} image_prompt_en 疑似人名 {m.group(0)!r}，请改用 CHAR_A 代号")

        for ch in s.get("characters") or []:
            if ch not in chars:
                c.err(f"{sid} 引用了未定义的角色: {ch}")
                continue
            appearance = (chars[ch] or {}).get("appearance_en")
            if appearance and appearance not in prompt:
                c.err(
                    f"{sid} 出场了 {ch} 但 prompt 未逐字内嵌其 appearance_en，"
                    f"人物会漂移。应为：{appearance}"
                )

        caps = s.get("captions") or []
        for cap in caps:
            if len(cap) > cap_limit:
                c.warn(f"{sid} 旁白超过 {cap_limit} 字（{len(cap)}）：{cap}")

        if not s.get("source_text"):
            c.err(f"{sid} source_text 为空，无法对回原文")

        # L0 下旁白必须逐字来自 source_text
        if level == "L0":
            for cap in caps:
                clean = cap.replace("[内心]", "").strip()
                if clean and clean not in (s.get("source_text") or ""):
                    c.err(f"{sid} L0 旁白不是 source_text 的原文片段: {cap!r}")

        # L1/L2 必须保留原文
        if level in ("L1", "L2") and not s.get("source_text_original"):
            c.err(f"{sid} 档位 {level} 必须提供 source_text_original")

    # 诗歌：除 P01 外每格至少一行旁白
    if is_poem:
        for s in shots[1:]:
            if not (s.get("captions") or []):
                c.err(f"诗歌 {s.get('shot_id')} 缺旁白，每格应是一整行原诗")

    if not has_ecu:
        c.err("全篇没有 ECU 特写（作业本/错别字需要特写）")

    # 首尾闭环：第 1 格和最后 1 格都要是作业本特写（怀旧钩子）。
    # 诗歌例外：4 格意象分镜是 作业本 → 核心意象 → 意象转折 → 落点，
    # 末格是意象不是作业本，只校验首格。
    last = shots[-1]
    pairs = [("第 1 格", first)] if is_poem else [("第 1 格", first), ("最后 1 格", last)]
    for tag, sh in pairs:
        if sh.get("shot_type") != "ECU":
            c.err(f"{tag} {sh.get('shot_id')} 应为 ECU 作业本特写（首尾闭环），实际 {sh.get('shot_type')!r}")
        else:
            d = (sh.get("description_cn") or "")
            if not any(w in d for w in ["作业本", "作文本", "方格", "练习本", "纸", "日记本", "格子"]):
                c.warn(f"{tag} {sh.get('shot_id')} 描述里没有作业本/方格纸类词，闭环感会弱")

    for t in data["typos"]:
        if not isinstance(t, dict):
            c.err(f"typos 条目格式错误: {t!r}")
            continue
        ttype = t.get("type", "typo")
        if ttype not in ("typo", "pinyin"):
            c.err(f"typos[].type 只能是 typo 或 pinyin，实际 {ttype!r}")
        if not t.get("wrong"):
            c.err(f"typos 条目缺少 wrong: {t!r}")
        if ttype == "typo" and not t.get("right"):
            c.err(f"typos 条目（type=typo）缺少 right: {t!r}")
        if ttype == "pinyin" and not t.get("right"):
            c.warn(f"typos 拼音条目未给 right，将无法做对照提示: {t.get('wrong')!r}")
        if t.get("gag_shot") and t["gag_shot"] not in shot_ids:
            c.err(f"typos 里 gag_shot={t['gag_shot']} 不存在于 shots")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    try:
        if src == "-":
            data = json.load(sys.stdin)
        else:
            with open(src, encoding="utf-8") as f:
                data = json.load(f)
    except FileNotFoundError:
        print(f"✗ 文件不存在: {src}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析失败: {e}")
        return 1

    c = Checker()
    check(data, c)

    for w in c.warnings:
        print(f"⚠ {w}")
    for e in c.errors:
        print(f"✗ {e}")

    if c.errors:
        print(f"\n失败：{len(c.errors)} 个错误，{len(c.warnings)} 个警告")
        return 1
    print(f"\n✓ 通过（{len(c.warnings)} 个警告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
