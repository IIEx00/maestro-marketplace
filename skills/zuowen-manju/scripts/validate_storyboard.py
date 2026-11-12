#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 storyboard.json 的结构与安全约束。

用法：
  python3 validate_storyboard.py outputs/我的妈妈/storyboard.json
  python3 validate_storyboard.py -            # 从 stdin 读

退出码：0 通过，1 有错误。
"""

import json
import re
import sys

REQUIRED_TOP = ["title", "meta", "style_prefix", "safety_tags", "character_index", "typos", "shots"]
REQUIRED_META = ["level", "art_style", "aspect_ratio", "shot_count", "genre"]
REQUIRED_SHOT = ["shot_id", "shot_type", "source_text", "description_cn", "image_prompt_en", "captions", "dialogue", "characters"]

SHOT_TYPES = {"ELS", "LS", "MS", "CU", "ECU"}
LEVELS = {"L0", "L1", "L2"}
ASPECTS = {"4:3", "3:4", "16:9", "9:16", "1:1"}

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

# 启发式隐私检查：明显的地名/机构/联系方式
PRIVACY_PATTERNS = [
    (re.compile(r"1[3-9]\d{9}"), "疑似手机号"),
    (re.compile(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{2}\d{3}[\dXx]"), "疑似身份证号"),
    (re.compile(r"[\u4e00-\u9fa5]{2,6}(小学|中学|初中|高中|附中|实验学校)"), "疑似学校全称"),
    (re.compile(r"[\u4e00-\u9fa5]{2,4}(省|市)[\u4e00-\u9fa5]{2,4}(区|县|镇|街道)"), "疑似地址"),
    (re.compile(r"(?<!Chinese )(?<!Chinese  )\b(primary|middle|high)\s+school\b"), "疑似学校全称（改用 a Chinese primary school 等泛称）"),
    (re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(Primary|Middle|High)\s+School\b"), "疑似学校专名"),
]


class Checker:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def check(data, c):
    for k in REQUIRED_TOP:
        if k not in data:
            c.err(f"缺少顶层字段: {k}")
    if c.errors:
        return

    meta = data["meta"]
    for k in REQUIRED_META:
        if k not in meta:
            c.err(f"meta 缺少字段: {k}")
    if isinstance(meta, dict):
        if meta.get("level") not in LEVELS:
            c.err(f"meta.level 必须是 {sorted(LEVELS)}，实际 {meta.get('level')!r}")
        if meta.get("aspect_ratio") not in ASPECTS:
            c.err(f"meta.aspect_ratio 不合法: {meta.get('aspect_ratio')!r}")

    shots = data["shots"]
    if not isinstance(shots, list) or not shots:
        c.err("shots 必须是非空数组")
        return

    if meta.get("shot_count") != len(shots):
        c.err(f"meta.shot_count={meta.get('shot_count')} 与 shots 长度 {len(shots)} 不一致")

    if not (4 <= len(shots) <= 16):
        c.warn(f"格数 {len(shots)} 超出建议范围 4-16")

    prefix = data["style_prefix"]
    safety = data["safety_tags"]
    for tag in SAFETY_TAGS:
        if tag not in safety:
            c.err(f"safety_tags 缺少必需标签: {tag}")

    chars = data.get("character_index") or {}
    if not chars:
        c.err("character_index 不能为空")

    # 首格必须是作业本特写
    first = shots[0]
    if first.get("shot_type") != "ECU":
        c.warn("P01 建议用 ECU（作业本特写）作为钩子")
    desc1 = (first.get("description_cn") or "").lower()
    if not any(w in desc1 for w in ["作业本", "作文本", "方格", "练习本", "纸"]):
        c.warn("P01 的描述里没看到作业本/方格纸，钩子可能不够")

    has_ecu = False
    for i, s in enumerate(shots, 1):
        for k in REQUIRED_SHOT:
            if k not in s:
                c.err(f"shots[{i-1}] 缺少字段: {k}")
        sid = s.get("shot_id", f"#{i}")
        if s.get("shot_type") not in SHOT_TYPES:
            c.err(f"{sid} shot_type 不合法: {s.get('shot_type')!r}")
        if s.get("shot_type") == "ECU":
            has_ecu = True

        prompt = s.get("image_prompt_en") or ""
        if not prompt:
            c.err(f"{sid} image_prompt_en 为空")
            continue
        if not prompt.startswith(prefix):
            c.err(f"{sid} image_prompt_en 未以 style_prefix 开头")
        low = prompt.lower()
        for tag in SAFETY_TAGS:
            if tag not in low:
                c.err(f"{sid} image_prompt_en 缺少 safety tag: {tag}")
        for rx, label in BANNED_PATTERNS:
            if rx.search(low):
                c.err(f"{sid} image_prompt_en 含禁止词: {label}")
        if re.search(r"[\u4e00-\u9fa5]", prompt):
            c.err(f"{sid} image_prompt_en 含中文，生图模型效果差")
        for rx, label in PRIVACY_PATTERNS:
            if rx.search(prompt):
                c.err(f"{sid} image_prompt_en {label}")

        for ch in s.get("characters") or []:
            if ch not in chars:
                c.err(f"{sid} 引用了未定义的角色: {ch}")

        for cap in s.get("captions") or []:
            if len(cap) > 30:
                c.warn(f"{sid} 旁白超过 30 字（{len(cap)}）：{cap}")

        if not s.get("source_text"):
            c.err(f"{sid} source_text 为空，无法对回原文")

    if not has_ecu:
        c.err("全篇没有 ECU 特写（作业本/错别字需要特写）")

    for t in data["typos"]:
        if not isinstance(t, dict) or "wrong" not in t or "right" not in t:
            c.err(f"typos 条目格式错误: {t!r}")
        elif t.get("gag_shot"):
            ids = {s.get("shot_id") for s in shots}
            if t["gag_shot"] not in ids:
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
