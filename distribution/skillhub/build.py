#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打 SkillHub 投稿包。

用法：python3 distribution/skillhub/build.py
改了 skills/zuowen-manju/ 之后重跑，重新生成 zip / 图标 / 概览图 / payload.json。

规格（扒自 skillhub.cn 前端）：
- 上传 ZIP，accept=".zip"，**根目录必须含 SKILL.md**
- iconUrl：64×64 ~ 4096×4096
- overviewMd：中文详情
- payload：slug / displayName / summaryZh / overviewMd / iconUrl / version / files
- 审核常见不通过：SKILL.md 格式不规范、缺少测试案例、定价不合理、描述模糊
"""
import json, os, shutil, zipfile, io
from PIL import Image, ImageDraw, ImageFont

import pathlib as _pl
ROOT = str(_pl.Path(__file__).resolve().parents[2])
SKILL = f"{ROOT}/skills/zuowen-manju"
OUT = f"{ROOT}/distribution/skillhub"
os.makedirs(OUT, exist_ok=True)

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
def F(size, idx=2):
    return ImageFont.truetype(FONT, size, index=idx)

# ───────────────────────── 1. ZIP：SKILL.md 必须在根
ZIP = f"{OUT}/zuowen-manju.zip"
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, dirnames, filenames in os.walk(SKILL):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in sorted(filenames):
            if f.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, SKILL)          # 相对 skill 根 → 根就是 SKILL.md 所在层
            z.write(full, rel)
with zipfile.ZipFile(ZIP) as z:
    names = z.namelist()
assert "SKILL.md" in names, "SKILL.md 必须在 zip 根目录"
print(f"ZIP: {ZIP}  {os.path.getsize(ZIP)//1024} KB  {len(names)} 个文件")
print("   根目录含 SKILL.md ✅")

# ───────────────────────── 2. 图标 512×512
def make_icon():
    S = 512
    im = Image.new("RGB", (S, S), (28, 42, 58))
    d = ImageDraw.Draw(im)
    # 作业本
    d.rounded_rectangle((96, 76, 416, 436), radius=18, fill=(243, 236, 216))
    # 方格
    for i in range(1, 8):
        x = 96 + i * 320 / 8
        d.line((x, 76, x, 436), fill=(206, 196, 172), width=2)
    for j in range(1, 8):
        y = 76 + j * 360 / 8
        d.line((96, y, 416, y), fill=(206, 196, 172), width=2)
    # 蓝色手写标题条
    d.rounded_rectangle((132, 118, 372, 168), radius=8, fill=(38, 82, 148))
    # 红色批改对勾
    d.line((300, 300, 340, 356), fill=(196, 44, 40), width=14)
    d.line((340, 356, 404, 232), fill=(196, 44, 40), width=14)
    # 胶片齿
    for k in range(9):
        x = 40 + k * 50
        d.rounded_rectangle((x, 22, x + 28, 44), radius=4, fill=(214, 168, 92))
        d.rounded_rectangle((x, 468, x + 28, 490), radius=4, fill=(214, 168, 92))
    im.save(f"{OUT}/icon.png")
make_icon()
print(f"icon.png: {os.path.getsize(f'{OUT}/icon.png')//1024} KB  512×512")

# ───────────────────────── 3. 概览图 1280 宽
def make_overview():
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), (247, 242, 231))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 12), fill=(38, 82, 148))
    d.text((72, 74), "小学生手写作文", font=F(46), fill=(38, 82, 148))
    d.text((72, 140), "→ AI 漫剧分镜 prompt 包", font=F(46), fill=(38, 82, 148))
    d.text((72, 218), "错别字、拼音注音，一个字不改，全部做成画面梗", font=F(30), fill=(90, 86, 78))
    cards = [
        ("7 种画风全部实测", "水墨 / 剪纸 / 敦煌 / 赛璐璐\n木偶 / 作业本 / 绘本"),
        ("8 格或 16 格", "起承转合切分\n每格指回原文哪一句"),
        ("人物一致性", "先出定妆图再当参考图\n校验脚本逐字检查"),
        ("批量出图脚本", "幂等重试 · 断点续跑\n付费前准入检查"),
        ("成片流水线", "视频 + 画外音 + 字幕\n老电视质感，一条命令"),
        ("儿童合规", "分数扣分评语\n不出现在对外素材里"),
    ]
    for i, (t, sub) in enumerate(cards):
        x = 72 + (i % 3) * 388
        y = 300 + (i // 3) * 176
        d.rounded_rectangle((x, y, x + 356, y + 148), radius=14, fill=(255, 253, 248),
                            outline=(216, 206, 186), width=2)
        d.text((x + 22, y + 20), t, font=F(25), fill=(196, 60, 44))
        d.multiline_text((x + 22, y + 62), sub, font=F(19, idx=0), fill=(96, 92, 84), spacing=8)
    d.text((72, 656), "zuowen-manju  ·  免费  ·  L0 原汁原味  ·  MIT", font=F(22, idx=0), fill=(140, 134, 122))
    im.save(f"{OUT}/overview.png")
make_overview()
print(f"overview.png: {os.path.getsize(f'{OUT}/overview.png')//1024} KB  1280×720")

# ───────────────────────── 4. payload
payload = {
  "slug": "zuowen-manju",
  "displayName": "作文漫剧",
  "version": "1.1.0",
  "summaryZh": "免费。把中小学生手写的应试作文照片，转成 8 格 AI 漫剧分镜和中英文生图 prompt，错别字不改、拼音注音照留，直接当画面梗。只出 prompt 零依赖零花费；要成片可用附带的脚本走 Beatra 积分。",
  "overviewMd": """# 作文漫剧 · 把孩子的作文变成动画

上传一张手写的语文作文照片，拿到一整套能直接出图出片的 AI 漫剧分镜。

## 它做什么

1. **逐字转录** —— 保留错别字、病句、拼音注音、涂改，不做"顺手修正"
2. **拆 8 格分镜**（可扩 16 格）—— 起承转合切分，首尾两格回到作业本形成闭环
3. **中英文生图 prompt** —— 英文 prompt 直接粘进即梦 / 可灵 / Midjourney
4. **人物定妆图 prompt** —— 先出定妆图再当参考图，8 格同一张脸
5. **错别字与拼音登记** —— L0 原则下原样保留，并给每格标好画面怎么表现
6. **出图与成片脚本** —— 批量出图（幂等、断点续跑、付费前准入检查）+ 成片流水线（视频、画外音、字幕、老电视质感）

## 为什么"不改错字"是卖点

孩子的作文里那些写错的地方，是最有传播力的画面。
"老师圈出来的错别字，我一个字没改"这种内容，天然带话题。
所以本 skill 默认 L0 原汁原味 —— 错字、病句、拼音注音全部保留，并在提示词里
用 `handwritten Chinese text "…"` 把它们放到该出现的地方。

## 画风

7 种中国怀旧画风，全部实际出图验证过，不是纸上方案：

| 画风 | 适合 |
|---|---|
| `shangmei-cel` 上美影赛璐璐 | 写人、有冲突（最好看的一张） |
| `shangmei-papercut` 上美影剪纸 | 写事、热闹（区分度第二高） |
| `shangmei-ink` 上美影水墨 | 写景、抒情 |
| `shangmei-dunhuang` 敦煌壁画 | 想象、神话 |
| `shangmei-puppet` 木偶定格 | 童话、寓言、奇幻 |
| `pencil-notebook` 铅笔作业本 | 作业本外壳（自带红笔批改） |
| `picturebook-cn` 中国原创绘本 | 温情家庭、低年级 |

## 测试案例

输入：一张三年级学生手写的《我的爷爷》作文照片（20×15=300 方格纸，带修正栏，
孩子给不会写的"搪"字整格标了拼音 táng）。

输出：

- 8 格分镜，P01/P08 是铅笔本外壳，中间六格赛璐璐
- P04 画面上写着 `handwritten Chinese text "为人民服务"` 的搪瓷缸子，
  旁边保留孩子自己标的拼音 `táng`
- P08 原文「他这辈子没什么本事，**会**了一样东西」按原样呈现，不改成"学会"
- `source.md` 里有完整的错别字登记与拼音注音登记
- `production.json` 可以直接喂给 `batch_images.py` 批量出图

完整产物见仓库 `skills/zuowen-manju/examples/worked-example-我的爷爷/`。

## 免费怎么用

**这是免费版本，不收 SkillHub 服务费。** 有两条路径：

| 路径 | 需要什么 | 花费 |
|---|---|---|
| **只出 prompt** | 无。要几张分镜就出几张 | **0** |
| **出图 / 出片** | 一个 Beatra 账号（`~/.beatra` 里授权） | 走你自己的 Beatra 积分 |

出图出片那条路的积分价（会随 Beatra 调价变动，以官方实时模型卡为准）：

- 图片 90–240 credits/张（文生图 / 图生图 / 局部编辑）
- 视频 225 credits/秒（480p）
- 配音 200 credits/1000 字符

所有脚本默认只出计划不扣费，必须显式 `--confirm` 才提交；
提交前还会读 Beatra 实时模型卡做准入检查，不合规当场拦下。

> 想省积分的用户，只用 prompt 那条路就够了 —— 中文分镜表 + 英文生图 prompt
> 粘进即梦 / 可灵 / Midjourney 就能出图，一个依赖都不需要。

## 儿童合规

- 作文里的真实姓名、学校、地址一律不进 prompt
- 卷面上老师的分数、扣分、评语进转录稿供家长看，但不得出现在对外素材里
- 强制 `cartoon child character, stylized animation, non-photorealistic, child-safe`
- 校验脚本会硬拦写实类词、裸中文、疑似人名

## 依赖

Claude Code + Beatra 授权 + Pillow + ffmpeg。详见 `skill-card.md`。
""",
  "files": ["zuowen-manju.zip"],
  "_备注": {
    "上传顺序": "先上传 icon.png 拿 iconUrl，再上传 overview.png 拿概览图 URL，最后填 payload 提交 ZIP",
    "slug": "全局唯一，提交前用 /api/v1/community/skills/check-slug 预检",
    "账号": "需 GitHub 绑定 + 手机号绑定，否则 403 PHONE_BINDING_REQUIRED",
    "审核": "有 /admin/skill-reviews 审核环节；常见不通过：SKILL.md 格式不规范、缺少测试案例、定价不合理、描述模糊",
    "版本策略": "本次提交为免费版，不开 Pay Skill、不配支付通道。先跑通审核拿反馈，再决定是否上架按次调用的付费版"
  }
}
json.dump(payload, open(f"{OUT}/payload.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("payload.json 已写")

# ───────────────────────── 5. PASTE.md：表单可直接复制的三段文本
paste = f"""# 表单粘贴稿

发布页：<https://skillhub.cn/dashboard/publish>

本文件由 `build.py` 生成，字段与 `payload.json` 同源，不会漂移。

## ① 基本信息

| 表单项 | 值 |
|---|---|
| slug | `{payload["slug"]}` |
| 名称 | `{payload["displayName"]}` |
| 版本 | `{payload["version"]}` |
| 图标 | 上传 `icon.png` |
| 概览图 | 上传 `overview.png` |
| Skill 包 | 上传 `zuowen-manju.zip` |

**本次为免费版**：不配支付通道、不填定价、不开按次结算。

## ② 一句话简介（粘进 summaryZh）

```
{payload["summaryZh"]}
```

## ③ 详细说明（粘进 overviewMd）

```
{payload["overviewMd"]}
```

## ④ 提交前自检

- [ ] slug 预检通过：`GET /api/v1/community/skills/check-slug?slug={payload["slug"]}`
- [ ] ZIP 根目录含 SKILL.md（平台硬性要求）
- [ ] 账号已绑 GitHub + 手机号（否则 403）
- [ ] summaryZh 说清了「免费」和「零依赖的那条路」
- [ ] overviewMd 里有测试案例（平台审核会挑这条）
- [ ] 定价留空
"""
open(f"{OUT}/PASTE.md", "w", encoding="utf-8").write(paste)
print("PASTE.md 已写")
