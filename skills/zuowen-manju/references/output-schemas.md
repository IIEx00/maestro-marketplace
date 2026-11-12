# 产物格式

## 一、目录

```
outputs/<作品名>/
├── storyboard.json      # 机读，含全部 prompt
├── storyboard.md        # 人读分镜表
└── source.md            # 转录稿 + 错别字登记 + 待确认清单
```

`<作品名>` 用作文标题，去掉标点。如「我的妈妈」。标题认不出时用 `zuowen-<日期>`。

## 二、source.md

见 `transcribe.md` 第五节。

## 三、storyboard.json

```json
{
  "title": "我的妈妈",
  "meta": {
    "level": "L0",
    "art_style": "shangmei-ink",
    "aspect_ratio": "4:3",
    "shot_count": 8,
    "grade_guess": "小学三年级",
    "genre": "写人",
    "generated_at": "2026-11-12"
  },
  "style_prefix": "1980s Shanghai Animation Film Studio ink-wash animation style, ...",
  "safety_tags": "cartoon child character, stylized animation, non-photorealistic, child-safe",
  "character_index": {
    "CHAR_A": {
      "role": "主角（我）",
      "appearance_cn": "8 岁男孩，黑色短发，蓝色校服",
      "appearance_en": "an 8-year-old Chinese boy with short black hair, wearing a blue school uniform"
    },
    "CHAR_B": {
      "role": "妈妈",
      "appearance_cn": "30 多岁女性，围裙，头发扎在脑后",
      "appearance_en": "a Chinese woman in her thirties wearing an apron with her hair tied back"
    }
  },
  "typos": [
    { "wrong": "辛福", "right": "幸福", "type": "typo", "gag_shot": "P01" }
  ],
  "shots": [
    {
      "shot_id": "P01",
      "shot_type": "ECU",
      "source_text": "我的妈妈很辛福，因为她有一个我。",
      "description_cn": "作业本特写，方格纸上歪斜的字迹，红笔圈住「辛福」二字",
      "image_prompt_en": "<填实际 style_prefix 原文>, close-up of a Chinese school exercise book, handwritten Chinese text \"辛福\", a red circle around it, cartoon child character, stylized animation, non-photorealistic, child-safe",
      "captions": ["我的妈妈很辛福"],
      "dialogue": [],
      "typo_gag": "辛福（原文错字，红笔圈出）",
      "characters": [],
      "duration": 4
    }
  ]
}
```

> L1/L2 档额外要求每格带 `source_text_original`（L0 不需要）。

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 作文标题 |
| `meta.level` | ✅ | `L0` / `L1` / `L2` |
| `meta.art_style` | ✅ | 画风 key，见 art-styles.md |
| `meta.aspect_ratio` | ✅ | `4:3` / `3:4` / `16:9` / `9:16` / `1:1` |
| `meta.shot_count` | ✅ | 与 `shots` 长度一致，4-16 |
| `style_prefix` | ✅ | 全篇统一 |
| `safety_tags` | ✅ | 必须含全部 4 个标签 |
| `character_index` | ✅ | 至少 1 个、最多 4 个；每个须含 `role` / `appearance_cn` / `appearance_en` |
| `character_index[].appearance_en` | ✅ | 英文外观串，≥5 词，**每格出现该角色时必须逐字内嵌** |
| `typos` | ✅ | 无错别字时给空数组；每条含 `wrong` / `type`（`typo` 或 `pinyin`） / `right` |
| `shots[].shot_id` | ✅ | `P01`…`P16`，不得重复 |
| `shots[].shot_type` | ✅ | ELS/LS/MS/CU/ECU；P01 必须是 ECU |
| `shots[].source_text` | ✅ | 原文原句（L1/L2 用改后文本） |
| `shots[].source_text_original` | L1/L2 必填 | 原文原句 |
| `shots[].description_cn` | ✅ | 中文画面描述，给人看 |
| `shots[].image_prompt_en` | ✅ | 英文 prompt；中文仅限 `handwritten Chinese text "…"` |
| `shots[].captions` | ✅ | 旁白数组；L0 下必须是 `source_text` 的原文片段 |
| `shots[].dialogue` | ✅ | 对白数组，可为空 |
| `shots[].typo_gag` | ⬜ | 该格的错别字梗说明 |
| `shots[].characters` | ✅ | `CHAR_A` 等代号数组 |
| `shots[].duration` | ⬜ | 秒数，视频出口才需要 |

## 四、storyboard.md

按 `templates/storyboard-template.md` 输出。必须包含：

1. 作品信息表（档位/画风/画幅/格数/题材/年级推测）
2. 分镜表（8 行表格）
3. 完整英文 prompt 清单（每格一段代码块，方便复制）
4. 画风 style_prefix（一次，供用户粘到工具里做全局风格）
5. 使用说明（贴到哪个工具、怎么用参考图）

## 五、命名约定

- `shot_id`：`P01`-`P16`，两位数字，不重复
- 人物：`CHAR_A`、`CHAR_B`，最多 4 个
- 文件：全小写，无空格

## 六、下游对接

用户拿去生图时：

- 即梦 / 可灵：直接贴 `image_prompt_en`，画幅按 `meta.aspect_ratio` 选
- Midjourney：`image_prompt_en --ar 4:3`
- 需要保持人物一致：先出人设图，再当参考图复用（见下节）

**注意**：不要在 prompt 里塞中文（`handwritten Chinese text "…"` 除外）。
生图模型对中文理解弱，中文只用于给人看的 `description_cn` 和 `captions`。

## 七、人物一致性三步法

本 skill 不接收任何照片，一致性全靠这三步。交付时必须把这一节一并给用户。

### 第 1 步：锁死角色块

`character_index[].appearance_en` 是一段**固定英文串**。任何一格的 prompt 里
出现该角色，就必须**逐字内嵌**这段文本，不许改写、缩写、换语序。

校验脚本会检查：凡 `characters` 里声明了某角色，其 `appearance_en` 必须原样出现在
`image_prompt_en` 中，否则报错。

同一角色在第 3 格和第 7 格的文本必须逐字节一致——这是防漂移的地基。

### 第 2 步：先出定妆图（用户自己操作）

1. 取 `character_index` 里某个角色的 `appearance_en`
2. 拼成一张正面全身图 prompt：

```
{{style_prefix}}, {{appearance_en}}, full body, front view, plain background,
neutral pose, cartoon child character, stylized animation, non-photorealistic, child-safe
```

3. 在即梦 / 可灵里生成，挑一张最满意的存下来
4. **这一步用文字描述，不需要任何照片**

### 第 3 步：以定妆图作参考图

| 工具 | 用法 | 强度建议 |
|---|---|---|
| 即梦 | 上传定妆图为「参考图」，模式下选「人物参考」 | 中等偏高，保住脸型与服装 |
| 可灵 | 参考图 + 首帧 | 高，但动作幅度会变小 |
| Midjourney | `--cref <图片URL> --cw 100` | `--cw 100` 保脸+服装；只想保脸用 `--cw 50` |
| Stability / 其他 | image-to-image，denoise 0.45-0.6 | 太低会照抄构图，太高会丢人物 |

### 第 4 步（可选）：跨格锁定种子

同一次生成里保持 `seed` 不变，能进一步稳住背景与光线基调。
在交付说明里给用户一句话提示即可，不必写进 JSON。

### 一致性自检

交付前问自己：

- 同一角色在两个不同格子里的外观描述，字面完全一样吗
- 用户手里有没有至少一张定妆图（没出的话要先提示）
- 是否明确告诉用户「参考图不是必需的，但不用会飘」

