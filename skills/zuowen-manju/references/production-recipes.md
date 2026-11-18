# production.json 配方规范

`storyboard.json` 说清「每格画什么」，`production.json` 说清「每格怎么出」。
两者配套：`batch_images.py` 从 storyboard 取 prompt，从 production 取模式、模型、参考图。

## 文件位置

```
outputs/<作品名>/
├── storyboard.json      # 机读：prompt、人物、梗
├── storyboard.md        # 人读分镜表
├── source.md            # 转录稿 + 错别字/拼音登记 + 待确认清单
├── production.json      # 出图配方（本文档的格式）
└── images/              # 图片 + 定妆图 + batch_ledger.json
```

## 顶层字段

```json
{
  "_说明": "给人看的备注，脚本会忽略下划线开头的键",
  "canvas": { "type": "preset", "tier": "1K", "aspect": "4:3" },
  "shots": {
    "P01": { "mode": "generate", "model": "qwen-image-3.0", "negative_prompt": "..." },
    "P03": { "mode": "transform", "model": "qwen-image-3.0",
             "references": ["CHAR_A.png"], "negative_prompt": "..." },
    "P02": { "mode": "edit", "model": "wan2.7-image", "base": "P04.png",
             "edit_regions": [ { "image_index": 0, "x": 0.27, "y": 0.08,
                                 "width": 0.42, "height": 0.92 } ],
             "prompt": "覆盖 storyboard 里的 prompt" }
  }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `canvas` | ✅ | 全篇统一画幅。`type` 只能 `preset`；`tier` 为 `1K`/`2K`/`4K`；`aspect` 用比例（`4:3`/`9:16`）或 `source`（transform/edit 时跟随最后一张参考图） |
| `shots` | ✅ | 键是 shot_id，缺哪格就跳过哪格 |
| `shots.<id>.mode` | ✅ | `generate` / `transform` / `edit` 三选一 |
| `shots.<id>.model` | ✅ | 具体模型名，**不要写 `auto`** —— 写死才能预估价格，也才能保证全片同源 |
| `shots.<id>.references` | transform 必填 | 参考图文件名或格子号，**顺序有意义**（对应 prompt 里的 reference 1、2） |
| `shots.<id>.base` | edit 必填 | 底图文件名（当第一张参考图用） |
| `shots.<id>.edit_regions` | edit 必填 | 归一化矩形，x/y/width/height 取 0~1，每张图最多 2 个 |
| `shots.<id>.negative_prompt` | 建议 | 只有 `qwen-image-*` 系列支持；`gpt-image-2` 和 `wan2.7-image` 不支持 |
| `shots.<id>.prompt` | 可选 | 覆盖 storyboard 里的 prompt（edit 模式常用） |

## mode 怎么选

```
这一格要和其他格子同源吗？
├─ 要（同场景的另一角度 / 同人物的另一动作）
│   └─ 有合适的定稿图吗？
│       ├─ 有 → edit + edit_regions（150，最稳，画风 100% 继承）
│       └─ 没有 → transform + 参考图（190，画风靠参考图 + style_prefix）
└─ 不要（独立空镜 / 作业本特写）
    └─ generate（140，场景全靠文字）
```

**关键约束**：
- `transform` 会**继承参考图的画风**。参考图是赛璐璐就出赛璐璐，想换画风用 `edit`。
- `generate` 没有参考图，**模型会自己加人物**。如果分镜里这格不该有人，
  必须在 `negative_prompt` 里排除 `child, children, person, people, face, hand, hands`。
  （实测：大蒜篇 P04 是植物特写，模型自己加了个小女孩。）
- `edit` 的画风只由 prompt 决定，底图只提供构图。

## model 怎么选（价格随平台变，以 `beatra.models.list` 为准）

| 用途 | 模型 | 1K 单价 |
|---|---|---|
| 文生图，最省 | `gpt-image-2` | 90 |
| 文生图，支持 negative_prompt | `qwen-image-3.0` | 140 |
| 图生图，通用 | `qwen-image-3.0` | 190 |
| 图生图，要最好的服从度 | `qwen-image-3.0-pro` | 240 |
| 局部编辑（支持 edit_regions） | `wan2.7-image` | 150 |

## references 怎么指

`resolve_reference` 的查找顺序：
1. `outdir` 里的同名文件（可省略扩展名）
2. ledger 里该格子产出的文件
3. `outdir` 里以该名开头的**唯一**文件（多个匹配会报错，要写全名）

同一张图在多格里做参考图时，脚本按内容哈希缓存上传结果，**只上传一次**。

## 跑法

```bash
# 只看计划和估价，不花钱
python3 scripts/batch_images.py -s outputs/X/storyboard.json \
  -p outputs/X/production.json -o outputs/X/images --dry-run

# 确认后真跑
python3 scripts/batch_images.py -s ... -p ... -o ... --confirm

# 只补某几格（改了 prompt 或画风后重出）
python3 scripts/batch_images.py ... --shots P04,P06 --force
```

脚本自带：付费前准入检查（读 live model card）、请求指纹派生的稳定 `client_request_id`
（同参数重跑不重复扣费）、断点续跑 ledger、4 并发队列、依赖分层、失败重试、
按余额差记账。**不要用 `--force` 之外的方式改参数再重跑** —— 参数变了指纹就变，
会当成新请求重新扣费，这是对的。

## 依赖分层

参考图指向同批次的另一格时，脚本会自动分层：被依赖的格子先出，依赖它的后出。
例：P03 拿 P06 当参考 → P06 在第 0 层，P03 在第 1 层。不用手工排序。
