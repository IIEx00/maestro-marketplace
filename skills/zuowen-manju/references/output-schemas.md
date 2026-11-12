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
    "CHAR_A": { "role": "主角（我）", "appearance": "8-year-old Chinese boy, short hair, ..." },
    "CHAR_B": { "role": "妈妈", "appearance": "30s Chinese woman, apron, ..." }
  },
  "typos": [
    { "wrong": "辛福", "right": "幸福", "gag_shot": "P01" }
  ],
  "shots": [
    {
      "shot_id": "P01",
      "shot_type": "ECU",
      "source_text": "我的妈妈很辛福，因为她有一个我。",
      "description_cn": "作业本特写，方格纸上歪斜的字迹，红笔圈住「辛福」二字",
      "image_prompt_en": "<style_prefix>, close-up of a Chinese school exercise book ... , cartoon child character, stylized animation, non-photorealistic, child-safe",
      "captions": ["我的妈妈很辛福"],
      "dialogue": [],
      "typo_gag": "辛福（原文错字，红笔圈出）",
      "characters": [],
      "duration": 4
    }
  ]
}
```

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 作文标题 |
| `meta.level` | ✅ | `L0` / `L1` / `L2` |
| `meta.art_style` | ✅ | 画风 key，见 art-styles.md |
| `meta.aspect_ratio` | ✅ | `4:3` / `3:4` / `16:9` / `9:16` |
| `meta.shot_count` | ✅ | 与 `shots` 长度一致 |
| `style_prefix` | ✅ | 全篇统一 |
| `safety_tags` | ✅ | 全篇统一 |
| `character_index` | ✅ | 至少 1 个 |
| `typos` | ✅ | 无错别字时给空数组 |
| `shots[].shot_id` | ✅ | `P01`…`P08` |
| `shots[].shot_type` | ✅ | ELS/LS/MS/CU/ECU |
| `shots[].source_text` | ✅ | 原文原句 |
| `shots[].description_cn` | ✅ | 中文画面描述，给人看 |
| `shots[].image_prompt_en` | ✅ | 英文 prompt，给机器看 |
| `shots[].captions` | ✅ | 旁白数组，可为空 |
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

- `shot_id`：`P01`-`P16`，两位数字
- 人物：`CHAR_A`、`CHAR_B`，不超过 4 个
- 文件：全小写，无空格

## 六、下游对接

用户拿去生图时：

- 即梦 / 可灵：直接贴 `image_prompt_en`，画幅按 `meta.aspect_ratio` 选
- Midjourney：`image_prompt_en --ar 4:3`
- 需要保持人物一致：先用 `character_index` 里的人物描述单独出一张人设图，
  后续每格以人设图为参考图（`--cref` 或工具的参考图功能）

**注意**：不要在 prompt 里塞中文。生图模型对中文理解弱，中文只用于给人看的
`description_cn` 和 `captions`。
