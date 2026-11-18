# 实测踩坑与出片配方

本文件记录《可爱的弟弟》跑完整流程时的真实数据与踩过的坑。**只出 prompt 的流程不需要读它；用户要自己把分镜做成片时读它。**

金额单位是 Beatra credits，模型卡是唯一真相来源（`beatra.models.list`）。

---

## 一、钱花在哪（2026-11 实测）

| 环节 | 做法 | 单价 | 一次成片花费 |
|---|---|---|---|
| 文生图 | qwen-image-3.0 1K | 140/张 | — |
| 文生图（高清） | qwen-image-3.0-pro 1K | 190/张 | — |
| 文生图（便宜） | gpt-image-2 1K | 90/张 | — |
| 图生图 | qwen-image-3.0-pro 1K | 240/张 | — |
| 局部编辑 | wan2.7-image（唯一支持 `edit_regions`） | 150/张 | — |
| 参考生视频 | wan3.0-video 480p | 225/秒 | 16 秒 = **3,600** |
| 文字转语音 | minimax-speech-2.8-turbo | 200/1000 字 | 65 字 = **26** |

**结论：视频是大头，图片是零头，旁白几乎免费。** 一次 16 秒成片的合理预算是「视频 3,600 + 图片 1,000~2,000 + 旁白 26」≈ **5,000 credits**。偏离这个数就是在返工。

---

## 二、画风的三条铁律

### 1. 画风由参考图/底图决定，不是由 style_prefix 决定

`style_prefix` 每格都要写（漏了会完全失控），但它**只是辅助**。同一套 prefix 在不同出图方式下画风完全不同：

| 出图方式 | 实际画风 |
|---|---|
| 文生图 gpt-image-2 + prefix | 数字插画 / CG 感 |
| 文生图 qwen-image-3.0 + prefix | 厚涂偏插画 |
| 文生图 qwen-image-3.0-pro + prefix | 水彩，**画面会冒出京剧角色** |
| 图生图 qwen-image-3.0-pro + 参考图 + prefix | 赛璐璐 ✅ |
| 局部编辑（以定稿图为底） | 画风 100% 继承 ✅✅ |

> 纯文生图时 `Peking-opera-inspired character design` 会被当成「画一个京剧角色」的指令。补救：正文写 `ordinary modern Chinese children in ordinary everyday clothes`，negative_prompt 排除 `opera performer, chinese opera costume, face paint, headdress`。

**想要某张图的画风，就拿那张图当参考图或底图。**

### 2. 参考图会把场景和道具一起泄漏过去

用带场景的分镜图当参考，新场景里会长出参考图的道具（实测：用室内「弟弟扫铅笔」当参考出草坪，草坪上长出一张课桌）。

- 参考图优先选**纯背景定妆图**，场景靠文字控制
- 跨场景时 prompt 末尾显式排除：`no desk, no table, no indoor furniture, outdoor park only`
- 同时传 `negative_prompt`（只有 `qwen-image-*` 系列有该控制）
- 生成后**先看图再收工**

### 3. 相邻两格不要共用同一张参考图

实测 P07（客厅捉迷藏）用 P06（书桌扫笔）当参考，生成的是弟弟站在**写字台**上、桌上还散着铅笔——跟 P06 几乎同一张。要连贯请用首帧图或 `return_last_frame`，不要拿上一格的分镜图当参考。

---

## 三、每格出图配方

### 模式选择树

```
这一格需要和别的格子同源吗？
├─ 需要同源（同一场景的另一角度 / 同人物的另一动作）
│   └─ 有合适的定稿图吗？
│       ├─ 有 → beatra.images.edit + edit_regions（局部改，150，最稳）
│       └─ 没有 → beatra.images.transform，i2i（240），参考图选最接近场景的那张
└─ 不需要同源（独立空镜 / 作业本特写）
    └─ beatra.images.generate（文生图，140）
```

### 参考图选哪张

| 用途 | 参考图 |
|---|---|
| 锁人物身份 | **纯背景定妆图**（plain background），不要用带场景的分镜图 |
| 锁画风 | 画风基准图（如 gpt-image-2 出的 keyframe） |
| 同场景变体 | 直接用那格的定稿图当底，走 `edit_regions` |

### 定妆图 prompt 要点

- `full body, front view, standing straight, plain light neutral background, neutral relaxed pose`
- negative_prompt 排掉场景：`desk, table, chair, bookshelf, furniture, room, window, indoor scenery, props, toys, other children`

---

## 四、局部编辑（edit_regions）怎么用

改已定稿图的某一块时**不要整张重出**。

```json
{
  "model": "wan2.7-image",
  "images": [{"type": "artifact", "artifact_id": "<底图>"}],
  "edit_regions": [
    {"image_index": 0, "x": 0.27, "y": 0.08, "width": 0.42, "height": 0.92},
    {"image_index": 0, "x": 0.70, "y": 0.40, "width": 0.30, "height": 0.60}
  ],
  "canvas": {"type": "preset", "tier": "1K", "aspect": "source"},
  "prompt": "replace the two boys in the foreground with empty golden autumn grass and fallen maple leaves, keep the distant children in the background, the autumn trees, the blue sky and the whole hand-painted 1980s Chinese cel animation style exactly unchanged"
}
```

要点：

- `edit_regions` 是归一化矩形，x/y/width/height 取 0~1；**每张输入图最多 2 个区域**
- 只有 `wan2.7-image`（150）和 `wan2.7-image-pro`（370）声明支持 `edit_regions`；qwen-image-3.0-pro 只支持整图 edit（等于重出）
- `canvas.aspect: "source"` 跟随**第一张**输入图
- wan2.7 系列 `alpha: reject_png_alpha` —— 上传前把 PNG 转成 RGB JPEG
- prompt 必须写清「把 X 换成 Y，其余完全不变」，并列出要保留的元素

---

## 五、视频配方

```json
{
  "model": "auto",
  "references": [{"kind":"image","media":{"type":"artifact","artifact_id":"..."}}],
  "prompt": "按顺序逐格描述，每格约 2 秒，镜头平稳不要快速切换",
  "duration": 16,
  "resolution": "480p",
  "aspect_ratio": "4:3",
  "client_request_id": "opaque-id"
}
```

- 能力 `reference_to_video`，`auto` 首选 **wan3.0-video**：参考图上限 20 个（图片 10 / 视频 5 / 音频 5），时长 2–30 秒，支持 4:3
- 计费只有 `output_video_second`（纯图片输入不触发 input 计费）：480p 225/秒、720p 445/秒、1080p 890/秒
- **实测 8 张参考图 → 16 秒成片，镜头严格按参考图顺序出现**，没有跳格也没有乱序
- 尺寸/时长/价格**从 live model card 读**，不要硬编码

---

## 六、画外音配方

> 以上步骤已固化成 `scripts/voiceover.py`，不用手搓了。下面记的是脚本背后的坑。

**每格挑一句原文**（L0 一字不改），不要念全文。

- 全文 490 字念完约 100 秒，16 秒装不下；每格一句共 65 字 ≈ 12 秒朗读 + 4 秒停顿，刚好铺满
- 工具 `beatra.speech.synthesize`，模型 `minimax-speech-2.8-turbo`（200/1000 字），音色 `voice_preset_niannian`（念念·温柔女声·有声书旁白）
- 50 个 preset 音色**只兼容 minimax-speech-2.8-hd/turbo**
- 用 `previous_text` 串上下文保持语气连续
- **裁静音别用 `silenceremove`**：它的 `stop_periods=1` 会在句中第一个停顿处就截断（「把笔全部扫落在地」被剪成 0.16 秒）。正确做法：`silencedetect` 量出首段静音尾点与末段静音起点，再按 `-ss/-to` 显式裁
- 对齐规则：`start = max(镜头起点 + 0.08s, 上一句结束 + 0.25s)`；语音略微跨过切点完全自然，不要为了对齐剪词
- 镜头切点获取：以 0.2 秒步长抽帧，与参考图做 32×32 归一化灰度余弦相似度匹配
- 底噪：原视频自带音轨 `volume=-12dB,lowpass=f=1200` 压成听不出内容的底噪；旁白 `alimiter=limit=0.95`
- `-shortest` 会把视频截到音频长度，用 `-t` 固定时长
- **烧中文字幕**：本机 ffmpeg 未编 libass/drawtext → PIL 渲染透明 PNG（`/System/Library/Fonts/Hiragino Sans GB.ttc`，index=2 是 W6）+ `overlay` + `enable='between(t,start,end)'`

---

## 七、检图清单（每次生成后过一遍）

1. 画风与基准图是否同一档？（不是就重出，别将就）
2. 场景里有没有**不属于本格**的道具/家具/文字？
3. 出场角色跟其他格是同一张脸、同一身衣服？
4. 相邻两格摆一起是不是像同一张？
5. 作业本特写格，手写字是否清楚？

发现异常就重出，并把问题写进下一轮的排除项。

---

## 八、模型卡的几个坑（写脚本前先知道）

Beatra 的 model card 不是统一 schema，按能力有差别，硬编码字段会崩：

| 坑 | 图片能力 | 视频能力 |
|---|---|---|
| `pricing` 形态 | dict `{"options":[...]}` | 直接是 list of dict |
| 参考图上限字段 | **不写** `max_references`（是 0），要看 `inputs.public_max_count` | `max_references` + `reference_limits` |
| `controls` 元素 | 有时是字符串，有时是 `{"field": ...}` dict | 字符串 |
| `negative_prompt` | qwen 系列有；**gpt-image-2 没有**；**wan2.7 没有** | 只有部分视频模型有 |
| `edit_regions` | 只有 `wan2.7-image` / `wan2.7-image-pro` | 无 |

写工具时要兼容这几种形态。`scripts/batch_images.py` 里已经处理：
`pricing_options()`、`reference_limit()`、`control_names()` 三个兼容函数。

### 服务端幂等是真的

实测：同一个 `client_request_id` 重复提交，Beatra 返回**同一个 task_id**，
余额不变，不重复扣费。所以幂等只要保证 ID 稳定即可：

```
client_request_id = f"zuowen-{shot_id}-{sha1(canonical(payload_without_id))[:16]}"
```

参数变 → 指纹变 → ID 变（符合「新参数必须新 ID」规则）；参数不变 → ID 不变 → 命中去重。

---

## 九、常见失败与对策

| 现象 | 原因 | 对策 |
|---|---|---|
| 草坪上出现课桌 | 参考图泄漏 | 换纯背景定妆图 + 显式排除 + 检图 |
| 整片画风割裂 | 参考图不是同一档 | 统一用同一张画风基准图做参考 |
| 画面冒出京剧角色 | prefix 被理解成角色指令 | 正文写「普通现代中国小孩」+ negative 排除京剧 |
| 两格看起来是同一张 | 共用参考图 | 换参考图，或用 `edit_regions` 局部改 |
| 局部改完画风变了 | 用了整图重出 | 改用 `beatra.images.edit` + `edit_regions` |
| TTS 句子被剪掉后半截 | `silenceremove` 截到句中停顿 | 显式 `-ss/-to` 裁 |
| 字幕烧不进去 | ffmpeg 没 libass | PIL 渲染 PNG + overlay |
| 成片最后 0.4 秒被砍 | `-shortest` | 用 `-t` 指定时长 |
