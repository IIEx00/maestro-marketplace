# 画风预设

全部为中国怀旧向。默认 `shangmei-ink`。

每个预设包含：中文说明、英文 `style_prefix`（写进每格 prompt 开头）、适配题材、画幅建议。

## 1. shangmei-ink（默认）· 上美影水墨

参考：《小蝌蚪找妈妈》《山水情》《牧笛》

```
1980s Shanghai Animation Film Studio ink-wash animation style, Chinese ink painting,
soft watercolor washes, minimal line work, large areas of negative space,
muted rice-paper palette of pale grey, indigo and warm ochre, hand-painted texture
```

- 适配：写景、抒情、怀念类
- 画幅：4:3（怀旧电视感）
- 注意：人物少用特写，多用中远景留白

## 2. shangmei-papercut · 上美影剪纸

参考：《葫芦兄弟》《猪八戒吃西瓜》《渔童》

```
1980s Chinese paper-cut animation style, Shanghai Animation Film Studio,
flat cut-paper characters with visible scissor edges, bold black outlines,
saturated folk-art colors of vermilion, jade green and gold,
decorative paper texture, layered silhouette composition
```

- 适配：写事、热闹、家庭日常
- 画幅：4:3
- 注意：剪纸风人物动作要「硬」，适合夸张表情

## 3. shangmei-dunhuang · 敦煌壁画

参考：《九色鹿》

```
1980s Chinese Dunhuang mural animation style, inspired by Mogao cave paintings,
earthy mineral pigments, ochre and malachite green and cinnabar red,
flowing ribbon-like drapery, aged fresco texture with subtle cracks,
decorative celestial motifs
```

- 适配：想象、神话、梦境
- 画幅：4:3 或 3:4
- 注意：适合「假如我会飞」这类题材，不适合写实家庭场景

## 4. shangmei-cel · 上美影赛璐璐

参考：《大闹天宫》《哪吒闹海》《天书奇谭》

```
classic 1980s Chinese cel animation style, Shanghai Animation Film Studio,
hand-painted cel shading, bold ink outlines, rich saturated colors,
Peking-opera-inspired character design, dramatic lighting,
visible paint texture on acetate
```

- 适配：写人、有冲突、情绪强
- 画幅：4:3
- 注意：人物造型可略夸张，但保持儿童体型比例

## 5. pencil-notebook · 铅笔作业本

参考：没有动画参考，直接还原作文本

```
pencil sketch illustration on Chinese school exercise-book paper,
grid squares visible, graphite lines with soft smudging, off-white aged paper,
red teacher pen marks as accent color, subtle paper grain and fold creases,
hand-drawn storybook aesthetic
```

- 适配：L0 原汁原味，最还原
- 画幅：3:4（竖版作业本）
- 注意：这是唯一允许画面上大量出现中文手写字的预设

## 6. picturebook-cn · 中国原创绘本

```
Chinese contemporary picture-book illustration style,
soft watercolor and colored pencil, warm nostalgic palette,
gentle line work, children's book composition,
textured cold-press paper
```

- 适配：温情家庭、低年级作文
- 画幅：3:4
- 注意：比上美影更「现代绘本」，少一点时代感

## 画风切换话术

用户说「换剪纸风」「要像葫芦娃那种」→ 切 `shangmei-papercut`。
用户说「太花了，简单点」→ 切 `shangmei-ink`。
用户说「不要动画，就要作业本」→ 切 `pencil-notebook`。

切换后全篇 `style_prefix` 统一替换，不能一格一个风格。

## style_prefix 使用规则

1. 每格 `image_prompt_en` 以 `style_prefix` 开头
2. 后面接场景描述，**不要重复风格词**
3. 结尾统一加 safety tags（见 `safety.md`）
4. 全篇 8 格必须使用同一个 `style_prefix`，校验脚本会检查
