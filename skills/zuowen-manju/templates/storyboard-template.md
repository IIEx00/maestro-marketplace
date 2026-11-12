# 分镜表模板

## 作品信息

| 项 | 值 |
|---|---|
| 标题 | 《{{title}}》 |
| 档位 | {{level}} 原汁原味 / 轻度润色 / 改编 |
| 画风 | {{art_style_cn}} |
| 画幅 | {{aspect_ratio}} |
| 格数 | {{shot_count}} |
| 题材 | {{genre}} |
| 年级推测 | {{grade_guess}} |

## 分镜表

| 格 | 景别 | 画面（中文） | 旁白 | 对白 | 原文依据 |
|---|---|---|---|---|---|
| P01 | ECU | | | | |
| P02 | | | | | |
| P03 | | | | | |
| P04 | | | | | |
| P05 | | | | | |
| P06 | | | | | |
| P07 | | | | | |
| P08 | | | | | |

## 完整 Prompt

### 全局风格前缀

```
{{style_prefix}}
```

### P01 · {{shot_type}}

```
{{style_prefix}}, {{主体与动作}}, {{环境}}, {{景别构图}}, {{光线氛围}}, {{safety_tags}}
```

### P02 · …

（逐格）

## 使用说明

1. 打开即梦 / 可灵 / Midjourney
2. 画幅选 {{aspect_ratio}}
3. 把每格的 prompt 粘进去，一次一格
4. 想保持人物一致，先用人设描述出一张定妆图，后续每格上传为参考图

## 人设参考 prompt

### CHAR_A · {{role}}

```
{{style_prefix}}, {{appearance}}, full body, front view, neutral background,
cartoon child character, stylized animation, non-photorealistic, child-safe
```

## 调优话术

| 你说 | 我做 |
|---|---|
| 换剪纸风 | 全篇切 `shangmei-papercut` |
| 再细点 / 要 16 格 | 扩到 16 格 |
| 精简 / 6 格就够 | 缩到 6 格 |
| 竖屏 / 发抖音 | 改 9:16 |
| 要原样 | 切 L0 |
| 帮改通顺 | 切 L1 |
| 不够抓人 | 切 L2 |
