# 画风预设

全部为中国怀旧向。默认 `shangmei-ink`。

每个预设包含：中文说明、英文 `style_prefix`（写进每格 prompt 开头）、适配题材、画幅建议。

## 1. shangmei-ink（默认）· 上美影水墨

参考：《小蝌蚪找妈妈》《山水情》《牧笛》《雁阵》

```
1980s Shanghai Animation Film Studio ink-wash animation style, Chinese ink painting,
soft watercolor washes bleeding into the paper, no clear outlines at all,
large areas of negative space, solid and void in balance,
muted rice-paper palette of pale grey, indigo and warm ochre, hand-painted texture
```

- 适配：写景、抒情、怀念类
- 画幅：4:3（怀旧电视感）
- 状态：✅ 已实测出图（2026-11-13）。淡雅晕染成立，但跟赛璐璐区分度不大，适合写景抒情不适合叙事
- 注意：人物少用特写，多用中远景留白

## 2. shangmei-papercut · 上美影剪纸

参考：《葫芦小金刚》《鹿女》《十二生肖奇缘记》《猪八戒吃西瓜》《渔童》

```
1980s Chinese paper-cut animation style, Shanghai Animation Film Studio,
pierced hollowed-out cut-paper figures with visible cut-out openings,
flat solid-color fills in bold separated color blocks with very little gradient,
absorbed New Year woodblock print patterns and opera face-mask motifs,
like a moving window paper-cut decoration,
dense saturated folk-art colors of vermilion, jade green and gold,
decorative paper texture, layered silhouette composition
```

- 适配：写事、热闹、家庭日常
- 画幅：4:3
- 状态：✅ 已实测出图（2026-11-13）。镂刻窗花感、红绿浓烈、人物像纸片，**七种里区分度第二高**
- 注意：剪纸风人物动作要「硬」，适合夸张表情
- 差异：葫芦**小金刚**比葫芦兄弟更装饰、更浓烈、古风更重，配色以朱红为主

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
- 状态：✅ 已实测出图（2026-11-13）。矿物色成立，但风格主要落在背景的云纹飘带上，人物还是普通小孩
- 注意：适合「假如我会飞」这类题材，不适合写实家庭场景

## 4. shangmei-cel · 上美影赛璐璐

参考：《宝莲灯》(1999)《大英雄狄青》(1996)《怪老头》(1987)《哪吒闹海》《天书奇谭》《魔方大厦》

```
classic 1980s Chinese cel animation style, Shanghai Animation Film Studio,
firm confident ink outlines with a slightly loose hand-drawn quality,
flat cel shading with hard-edged two-tone shadow and a crisp separate highlight
block, no soft gradient shading, muted warm film-graded colors softened by film
stock rather than oversaturated digital colors, rich luminous palette with
deeper light-and-shadow layering, graceful flowing character design,
Peking-opera-inspired character design, dramatic lighting,
visible paint texture on acetate
```

- 适配：写人、有冲突、情绪强
- 画幅：4:3
- 状态：✅ 已实测出图（2026-11-13），厚涂赛璐璐，七种里最好看的一张
- 注意：人物造型可略夸张，但保持儿童体型比例
- ⚠️ 参考片更正：《大闹天宫》(1961–64) 是**北京动画制片厂**作品，不属上美影，
  已从参考片单移除。国产 90 年代美影线以《宝莲灯》《大英雄狄青》《怪老头》为准。

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
- 状态：✅ 已实测出图（2026-11-13）。**七种里最有价值**：素描线稿+淡彩+纸纹，画面自带红色批改笔迹，最适合做作业本外壳
- 注意：画面上的中文一律走 `handwritten Chinese text "…"` 受控写法，与其他画风同样规则（见 `safety.md`）

## 6. picturebook-cn · 中国原创绘本

```
Chinese contemporary picture-book illustration style,
soft watercolor and colored pencil, warm nostalgic palette,
gentle line work, children's book composition,
textured cold-press paper
```

- 适配：温情家庭、低年级作文
- 画幅：3:4
- 状态：✅ 已实测出图（2026-11-13）。成立，但跟赛璐璐太接近，比较平庸
- 注意：比上美影更「现代绘本」，少一点时代感

## 画风切换话术

用户说「换剪纸风」「要像葫芦娃那种」→ 切 `shangmei-papercut`。
用户说「太花了，简单点」→ 切 `shangmei-ink`。
用户说「不要动画，就要作业本」→ 切 `pencil-notebook`。

切换后全篇 `style_prefix` 统一替换，不能一格一个风格。

## style_prefix 使用规则

1. 每格 `image_prompt_en` 以 `style_prefix` 开头
2. 后面接场景描述，**不要重复风格词**
3. 结尾统一加 4 个 safety tags（见 `safety.md`）
4. 全篇所有格必须使用同一个 `style_prefix`，校验脚本会检查

---

## 老电视质感：不要写进 prompt，用 ffmpeg（与画风无关，任何画风都能套）

扫描线、色差、显像管、低分辨率这些，AI 生图做不出来，写进 prompt 只会让模型画乱。
**正确做法是生图只管造型和配色，质感后期加**：

```bash
ffmpeg -i in.mp4 -vf "
scale=640:480:flags=bilinear,
noise=alls=6:allf=t+u,
eq=saturation=1.14:contrast=1.06:brightness=0.015,
vignette=PI/4.5,
colorbalance=rs=.03:gs=.01:bs=-.02,
geq=lum='lum(X,Y)+10*mod(Y,2)':cb='cb(X,Y)':cr='cr(X,Y)',
format=yuv420p
" -c:v libx264 -crf 20 -c:a copy out.mp4
```

0 credits，且**能套在已经做好的成片上**，不用重出图。实测有效：扫描线在平坦区域
（作业本纸面）最明显，颗粒和暗角让人一眼看出是旧电视录像。
实测产物：本地跑 `voiceover.py --crt` 生成（见 `scripts/voiceover.py`）

---

## 三条通用出图规则（与语系无关，写任何平涂风都带上）

下面三组词是从老派赛璐璐的作画规范里提炼出来的，**真正能让模型输出像那个年代的东西**，
写 `shangmei-cel` / `shangmei-papercut` 这类平涂风时都别漏：

| 规则 | 写进 prompt | 为什么 |
|---|---|---|
| 二段阴影 | `flat cel shading with hard-edged two-tone shadow and a crisp separate highlight block, no soft gradient shading` | 模型默认给柔和渐变，那是数码作画。老派平涂是硬边二分 + 单独一块高光 |
| 胶片偏灰 | `muted warm film-graded colors softened by film stock rather than oversaturated digital colors` | **模型默认输出刺眼的高饱和数字色**，这条是把它压回胶片感最有效的一句（已实测生效） |
| 硬边墨线 | `firm confident ink outlines with a slightly loose hand-drawn quality, never soft or blurry lines` | `bold ink outlines` 太泛，模型给不出"扎实墨线 + 轻微松动"的手绘感 |

**背景越简单，人物越突出、越容易跨格锁一致。** 实测：出图时把室内细节（脸谱墙、窗户）
简化掉之后，角色的辨识度反而更高，8 格之间更不容易漂。所以写 prompt 时背景别堆太多道具，
细节留给主体。

---

---

## 7. shangmei-puppet · 上美影木偶定格

参考：《大盗贼》(1989)《淘气包马小跳》(1988?)

```
1980s Chinese puppet stop-motion animation style, Shanghai Animation Film Studio,
handmade cloth and carved wooden puppet figures with visible fabric weave and
wood grain texture, rounded blunt proportions with simplified painted features,
soft natural studio lighting, miniature hand-built stage sets with painted
backdrop scenery, authentic vintage film grain, tactile fairy-tale wonder
```

- 适配：童话、寓言、奇幻、妖怪
- 画幅：4:3
- 状态：✅ 已实测出图（2026-11-13）。木偶的圆润厚重感有，但不够强
- 差异：这条线是**实体木偶拍摄**，不是画的。质感关键词是「布面肌理 / 木纹 / 定格 /
  手搭景片 / 自然柔光」，跟剪纸和赛璐璐完全不同
- 注意：`rounded blunt proportions with simplified painted features` 这半句很关键，
  写 `lifelike` 会跟 `non-photorealistic` 打架

---

## 赛璐璐叙事动画的三档（同一预设，换角色设计那半句）

上美影的赛璐璐线内部差别很大，按题材选一档当全篇基调：

| 档 | 参考 | 角色与氛围 | 适合的作文题材 |
|---|---|---|---|
| **怪诞童话** | 魔方大厦 | 造型扭曲、色调压抑、氛围诡异 | 不适合小学生作文，**不建议用** |
| **柔和童话** | 舒克和贝塔 | 造型圆润干净、配色柔和、亲切 | 童话、动物、小朋友日常 ✅ 最推荐 |
| **写实冷峻** | 特别车队 | 动物拟人、黑帮谍战、镜头偏成人向、紧张冷峻 | 不适合小学生作文，**不建议用** |

改档只改 `style_prefix` 里的角色设计那半句，其余不变：

柔和童话档的角色半句 →
`clean rounded character design with soft friendly faces, flat pastel color fills with very little gradient, warm inviting palette, painted storybook background with soft foliage and warm light`

---

## 为什么不收「先锋实验抽象短片」

《十二只蚊子和五个人》那条线是符号化极简造型、图形文字数字叙事、低饱和讽刺隐喻。
它是上美影的实验短片，不是儿童向，**对应到小学生作文几乎没有落点**。
留个记录，需要写抽象/未来/哲学向题材时再启用。

---

## 七种画风横向实测结论（2026-11-13）

同一张图（P02_v6 秋日草坪）做底，用 `beatra.images.edit` 整图重绘，构图锁死，
七种画风各出一张。产物在 `outputs/画风试片/`。

| 画风 | 效果 | 结论 |
|---|---|---|
| `shangmei-cel` 赛璐璐 | 厚涂、蓝天白云、暖色 | **最好看**，写人叙事默认选它 |
| `shangmei-papercut` 剪纸 | 镂刻窗花、红绿浓烈、人物像纸片 | **区分度第二高**，热闹题材首选 |
| `pencil-notebook` 铅笔本 | 素描淡彩+纸纹+**红色批改笔迹** | **最有商业价值**，作业本外壳就靠它 |
| `shangmei-ink` 水墨 | 淡雅晕染、留白 | 成立，但跟赛璐璐区分度不大 |
| `shangmei-dunhuang` 敦煌 | 矿物色、云纹飘带 | 成立，风格主要落在背景 |
| `shangmei-puppet` 木偶 | 圆润厚重、布景感 | 有但不够强 |
| `picturebook-cn` 绘本 | 柔水彩彩铅 | 跟赛璐璐太接近，平庸 |

**两个可以直接用的结论**：
1. 账号外壳用 `pencil-notebook` —— 它天然自带「红笔批改」，而红笔批改正是三篇素材里
   反复出现的元素（扣分、修正栏、老师的圈画）。这就是账号的第二个识别标记。
2. 写事 / 观察类题材用 `shangmei-papercut` 有实证支持，不再是纸上方案。

**方法备注**：测画风必须用 `beatra.images.edit`（整图重绘），**不能用 transform** ——
transform 会继承参考图的画风，参考图是赛璐璐就测不出别的风格。

逐张的文字结论见 `references/style-test-notes.json`。
