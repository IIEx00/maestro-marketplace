---
name: zuowen-manju
description: >-
  把中小学生应试作文照片（小学/初中/高中，学校或培训机构写的）转成 AI 漫剧分镜，
  输出可直接粘贴到即梦/可灵/Midjourney 的中英文生图 prompt 包（默认 8 格，可扩 16 格）。
  默认 L0 原汁原味：不改错别字、不改病句，错别字直接当画面梗。
  默认画风为 8090 年代上海美术电影制片厂风格（水墨/剪纸/敦煌/赛璐璐/木偶/作业本/绘本），可按题材切换。只用中国怀旧画风。
  当用户发作文图片并说「做成漫剧」「做成分镜」「改动画」「转成动画短片」「作文漫剧」
  「小学生作文改动画」「怀旧作文」时使用。
disable-model-invocation: false
metadata:
  clawdbot:
    emoji: "📝"
    requires:
      bins: ["python3"]
      os: ["linux", "darwin", "win32"]
---

# 作文漫剧（zuowen-manju）

把一张作文照片变成一套漫剧分镜 prompt 包。**只出 prompt，不生成图**。

## 何时触发

- 用户发来作文图片（手写/印刷/拍照/扫描都行），要求做成漫剧、动画、分镜、短片
- 用户说「把这篇作文改成 AI 动画」「孩子写的作文能做成动画吗」
- 用户要批量做系列（但仍按「一篇一次」执行，每篇独立产出）

不应触发：纯文字散文/小说改写 → 用 `xiaoshuojubenzhuanfenjing`；短视频推文带货 → 用 `xiaoshuozhuantuiwenfenjing`。

## 第 0 步：准入判定（必做）

**先确认来稿确实是中小学生手写的应试作文**，再往下走。判定错了后面全白做。

按 `references/eligibility.md`，用「强信号 / 弱信号 / 反证」三类证据判定：

| 判定 | 条件 | 动作 |
|---|---|---|
| `student_essay` | ≥2 条强信号且无反证 | 继续 |
| `user_confirmed` | 存疑，问用户后确认 | 继续，记 `用户确认` |
| `rejected` | 命中任一反证 | 停下，说明原因 + 指去处 |

**强信号**：方格作文纸 / 老师红笔批改 / 手写稚嫩有涂改 / 铅笔书写
**反证**：印刷体或电子文档 / 出版排版 / 成人化思辨 / AI 生成痕迹 / 网络小说格式

反证一票否决，且**内容优先于笔迹**——字像小孩但内容是成人议论的，判 `rejected`。

判定结果必须写进 `meta.source_verdict` 与 `meta.source_signals`，校验脚本会拦。

## 三条硬规则（每次必守）

1. **图像 prompt 必须包含四个安全标签**：
   `cartoon child character, stylized animation, non-photorealistic, child-safe`；
   禁止 `photorealistic` / `realistic photo` / `real person` / `hyperrealistic` / 明星姓名。
2. **脱敏**。作文里的真实姓名、学校名、具体地址**不进 prompt**，人物统一用
   `CHAR_A` / `CHAR_B` 代号；原文旁白/对白里可以保留（那是原文）。
3. **不编造原文**。图片模糊、手写字认不出时，用 `？` 占位并在「待确认清单」列出，
   禁止猜写。所有分镜的 `source_text` 必须能对回转录稿的原文。

### 中文书写规则

`image_prompt_en` 默认全英文，**唯一例外**是错别字梗：

```
handwritten Chinese text "辛福"
```

- 只能出现在需要展示手写字的格子（P01 特写、对应句所在格）
- 单块不超过 40 字
- 块内同样做隐私检查（手机号、学校全称会被拦）
- 其余任何中文都会被校验脚本拒绝

## 快速路径

```
0. 准入判定：强信号 ≥2 条且无反证，否则问一句或拒绝
1. 读图 → 逐字转录原文（含错别字、拼音、涂改痕迹）
2. 按默认跑：档位 L0 ｜ 画风按题材推荐（写景/抒情→水墨，写事→剪纸…），
   不额外提问；产出后再说明可调项
3. 拆 8 格分镜 → 写 prompt
4. 产出 storyboard.json + storyboard.md + source.md，并跑校验脚本
```

**唯一需要中途停下问用户的情况**：待确认清单里有关键内容认不出，
或题材触碰 `references/safety.md` 第三节红线。其余一律先按默认产出。

## 流程

### 第 1 步：转录

按 `references/transcribe.md`。要点：

- 逐行转录，保留换行与分段
- 错别字**照抄**，在 `typos` 里登记正确写法（供后面做梗）
- 拼音、涂抹、老师红笔批注、家长签字，都单独标注
- 判断年级（看字迹/字数/用词）与题材（写人/写事/写景/状物/想象/议论/诗歌）
- 无法辨认的字写 `？`，收进待确认清单
- 卷面若印了题面，顺手识别「题目 / 文体限制 / 字数 / 禁忌」四要素，
  判读依据见 `references/exam-requirements.md`

### 第 2 步：确认档位与画风

档位见 `references/adapt-levels.md`：

| 档位 | 做什么 | 默认 |
|---|---|---|
| L0 原汁原味 | 一字不改，错别字当梗 | ✅ |
| L1 轻度润色 | 只修错别字与标点，情节不动（须补 `source_text_original`） | |
| L2 改编 | 补冲突、加反转，为传播服务（须补 `source_text_original`） | |

> 字数与体裁以**卷面题面**为准，不要预设地区规则——各省差异明显
> （中考 40/50/54 分制并存，字数 500 与 600 都有），详见 `references/exam-requirements.md`。

画风见 `references/art-styles.md`，共 7 种，默认 `shangmei-ink`。按题材自动推荐，用户不表态就用默认：

| 题材 | 推荐画风 | 实测 |
|---|---|---|
| 写景 / 抒情 | `shangmei-ink` 水墨（默认） | 待验证 |
| 写事 / 热闹 | `shangmei-papercut` 剪纸 | 待验证 |
| 想象 / 神话 | `shangmei-dunhuang` 敦煌 | 待验证 |
| 写人 / 冲突 | `shangmei-cel` 赛璐璐 | ✅ 已出图 |
| 纯还原作业本 | `pencil-notebook` 铅笔+纸纹 | 待验证 |
| 温情家庭 / 低年级 | `picturebook-cn` 原创绘本 | 待验证 |
| 童话 / 寓言 / 奇幻 / 妖怪 | `shangmei-puppet` 木偶定格 | 待验证 |

**只有 `shangmei-cel` 真正出过图**，其余六种都标了「待验证」。

**只用中国怀旧画风**（上美影系 + 作业本 + 原创绘本），不设日系 / 美系。
**用户明确要求某个画风时，先出一张试片（140 credits）再往下做**，不要直接批量出 8 格。

出片后必检两件事：
1. 阴影是不是硬边二分、有没有单独一块高光（软渐变就是没生效）
2. 颜色是不是被胶片压过（刺眼的高饱和就是没生效）

### 第 3 步：拆分镜

按 `references/storyboard-rules.md`。默认 8 格，用户说「详细点」扩到 16 格。

- 开头 1 格必须是**作业本特写**（作文纸、方格、红笔批改），这是怀旧钩子
- 中间按作文的起承转合切，一段一个画面，不要旁白配空镜
- 结尾 1 格回到作业本 / 老师批语，形成闭环
- 每格必须写 `source_text`，指向原文哪一句

**诗歌例外**：`genre` 判定为 `诗歌` 时走 4 格意象分镜（P01 作业本 → P02 核心意象 →
P03 意象转折 → P04 落点），按意象切不按行切，详见 `storyboard-rules.md` 第十一节。
考试题面通常写「诗歌除外」，但用户主动发来诗时照样要能做。

### 第 4 步：写 prompt

模板见 `templates/storyboard-template.md`。每格 prompt 结构：

```
[style_prefix] + [主体与动作] + [环境] + [景别/构图] + [光线氛围] + [safety_tags]
```

- `style_prefix` 来自画风预设，全篇统一
- 首尾「作业本特写」若要换成 `pencil-notebook`（自带红笔批改，做账号外壳用），
  在该格加 `style_prefix_override`，该格改用覆盖值校验，其余格不变
- 中文描述给用户看，英文 prompt 给机器看，两者内容必须一致
- 错别字梗：在 `typo_gag` 里写清「画面上出现的原文错字」，prompt 中用
  `handwritten Chinese text "XXX"` 表达（这是唯一允许出现中文的位置）
- **人物一致性**：`character_index[].appearance_en` 是固定英文串，
  该角色出场的每格必须**逐字内嵌**，不许改写或缩写（校验脚本会检查）

### 第 5 步：校验与产出

```bash
python3 ~/.claude/skills/zuowen-manju/scripts/validate_storyboard.py \
  outputs/<作品名>/storyboard.json
```

校验不过就修，别直接交付。产出结构见 `references/output-schemas.md`。

## 输出

```
outputs/<作品名>/
├── storyboard.json      # 机读，含全部 prompt
├── storyboard.md        # 人读分镜表
├── source.md            # 转录稿 + 错别字/拼音登记 + 待确认清单
├── production.json      # 出图配方（模式/模型/参考图/排除项），要真出图才需要
└── images/              # 图片 + 定妆图 + batch_ledger.json
```

`production.json` 和 `images/` 只有在用户要真出图时才产生，格式见
`references/production-recipes.md`。

交付时在对话里给出：

1. 转录稿（带错别字标注）
2. 分镜表（Markdown 表格，8 行）
3. 完整的英文 prompt 清单（每格一段，可直接复制）
4. 人设定妆图 prompt（每个角色一段）+ 参考图用法一句话
5. 待确认清单（如有）

## 多篇做成系列时

「一篇一次」是产出单位，几篇合成一个账号是发布单位。
**共用视觉模板，不共用人物设定** —— 定妆图、作业本外壳、画风家族跨篇统一；
人物的年龄、性别、身份各篇各写，不越界。详见 `references/series.md`。

## 人物一致性

不接收照片，只靠文字锁人物。交付时必须附「先出定妆图 → 再当参考图」的三步法
（详见 `references/output-schemas.md` 第七节）。不提示用户这一点，8 格人物会长得不一样。

## 输入边界

**只处理**：中小学生手写应试作文（小学/初中/高中，学校或培训机构写的），
体裁为记叙、议论、说明、散文、诗歌。

**不处理**（判 `rejected`，指给其他 skill）：

| 来稿 | 去处 |
|---|---|
| 网络小说、长篇连载 | `xiaoshuojubenzhuanfenjing` |
| 成人散文、随笔 | `xiaoshuojubenzhuanfenjing` |
| 已发表/印刷排版的文章 | 指出不是手写稿 |
| 纯文字小说改短视频推文 | `xiaoshuozhuantuiwenfenjing` |

判定方法见 `references/eligibility.md`。

## 需要真出图时

本 skill 不生成图片，也不接收用户上传的照片作为参考图。
用户要出图时，把 `image_prompt_en` 交给 `gpt-image-2-5-studio`（文生图）。
人物一致性靠「先出定妆图 → 再当参考图」的三步法，全流程只用文字。
不要把生图调用的结果混进分镜 JSON。

### 要批量出图并出片时

用 Beatra 批量出图（有脚本，已端到端验证）：

```bash
# 1. 按每格写一份配方（模式 / 模型 / 参考图 / 排除项），模板见 templates/production-template.json
# 2. 先看计划与估价，不花钱
python3 scripts/batch_images.py -s <storyboard.json> -p <production.json> -o <images/> --dry-run
# 3. 确认余额后再跑
python3 scripts/batch_images.py -s ... -p ... -o ... --confirm
```

脚本自带：付费前准入检查（读 live model card 校验模型/画幅/排除项/参考图数量）、
请求指纹派生的稳定 `client_request_id`（同参数重跑不重复扣费）、
断点续跑 ledger、4 并发队列、依赖分层（参考图指向同批次另一格时自动等上游产出）、
失败重试、余额差记账。

**模式怎么选**：`generate` 无参考（作业本特写、独立空镜）；`transform` 拿参考图锁人物/画风，
场景靠 prompt 文字控制；`edit` 以某张定稿图为底局部改，画风 100% 继承、最省。
详细配方与踩坑见 `references/production-lessons.md`，配方文件字段规范见
`references/production-recipes.md`。

## 要做成片时

分镜只是中间产物。要成片按这个顺序，每一步都有脚本：

```bash
# 1. 出图（幂等 + 断点续跑，先 --dry-run 看估价）
python3 scripts/batch_images.py -s outputs/X/storyboard.json \
    -p outputs/X/production.json -o outputs/X/images --dry-run
python3 scripts/batch_images.py ... --confirm

# 2. 出片 + 配音 + 字幕（视频也会一并生成）
python3 scripts/voiceover.py -s outputs/X/storyboard.json -i outputs/X/images \
    --from-images --duration 16 --resolution 480p -o outputs/X/成片.mp4 --yes
```

`voiceover.py` 会自动：切镜头切点 → 逐格 TTS 念原文旁白 → 裁首尾静音 →
按镜头对位 → 混音（原音轨压低当底噪）→ 烧中文字幕 → 可选加老电视质感。
旁白塞不进视频时自动压速（零成本，不重新合成）。配音缓存在
`outputs/X/_voiceover_cache/tts/`，中断后用 `--audio-dir` 指它就能跳过 TTS 不重复扣费。

**注意**：脚本读 storyboard 里的 `captions` 念原文（L0 下必须是原文片段）。
每格挑**较短**的那句，16 秒塞 7 句才不会压速。

## 参考文件

- `references/eligibility.md` — 准入判定：强信号 / 弱信号 / 反证
- `references/transcribe.md` — 读图与原文转录规则（含诗歌分行转录）
- `references/exam-requirements.md` — 小升初/中考/高考的题面、字数与评分规范（含出处）
- `references/adapt-levels.md` — L0/L1/L2 三档处理细则
- `references/art-styles.md` — 7 种中国怀旧画风预设与英文 style prefix（上美影六线：剪纸/木偶/赛璐璐/水墨/敦煌/作业本 + 原创绘本）
- `references/storyboard-rules.md` — 8/16 格拆解规则、景别用法、诗歌 4 格分支
- `references/safety.md` — 儿童形象、隐私、平台合规
- `references/output-schemas.md` — 产物字段定义
- `references/production-lessons.md` — 实测踩坑与出片配方（要真做成片时才读）
- `references/production-recipes.md` — production.json 字段规范与模式选择（要真出图时才读）
- `references/series.md` — 多篇做成一个账号时的共用/不共用规则
- `templates/storyboard-template.md` — 分镜表与 prompt 书写模板
- `templates/production-template.json` — 批量出图配方模板（模式 / 模型 / 参考图 / 排除项）
- `scripts/validate_storyboard.py` — JSON 结构 + 安全检查
- `scripts/batch_images.py` — 批量出图（幂等 + 断点续跑 + 付费前准入检查）
- `scripts/voiceover.py` — 成片流水线：视频 + 画外音 + 混音 + 字幕 + 老电视质感
- `examples/storyboard.example.json` — 常规 8 格样例（可跑通校验）
- `examples/poem.example.json` — 诗歌 4 格样例（可跑通校验）
- `examples/worked-example-我的爷爷/` — 一篇虚构成品示例（storyboard / source / production 全套），
  演示错别字当梗、拼音注音、首尾闭环、外壳换画风、人物一致性
- `examples/style-test-notes.json` — 七种画风横向实测的文字结论
