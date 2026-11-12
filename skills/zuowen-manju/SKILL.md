---
name: zuowen-manju
description: >-
  把中小学生应试作文照片（小学/初中/高中，学校或培训机构写的）转成 AI 漫剧分镜，
  输出可直接粘贴到即梦/可灵/Midjourney 的中英文生图 prompt 包（默认 8 格，可扩 16 格）。
  默认 L0 原汁原味：不改错别字、不改病句，错别字直接当画面梗。
  默认画风为 8090 年代上海美术电影制片厂风格（水墨/剪纸/敦煌/赛璐璐），可按题材切换。
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

画风见 `references/art-styles.md`，共 6 种，默认 `shangmei-ink`。按题材自动推荐，用户不表态就用默认：

| 题材 | 推荐画风 |
|---|---|
| 写景 / 抒情 | `shangmei-ink` 水墨（默认） |
| 写事 / 热闹 | `shangmei-papercut` 剪纸 |
| 想象 / 神话 | `shangmei-dunhuang` 敦煌 |
| 写人 / 冲突 | `shangmei-cel` 赛璐璐 |
| 纯还原作业本 | `pencil-notebook` 铅笔+纸纹 |
| 温情家庭 / 低年级 | `picturebook-cn` 原创绘本 |

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
└── source.md            # 转录稿 + 错别字登记 + 待确认清单
```

交付时在对话里给出：

1. 转录稿（带错别字标注）
2. 分镜表（Markdown 表格，8 行）
3. 完整的英文 prompt 清单（每格一段，可直接复制）
4. 人设定妆图 prompt（每个角色一段）+ 参考图用法一句话
5. 待确认清单（如有）

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

## 参考文件

- `references/eligibility.md` — 准入判定：强信号 / 弱信号 / 反证
- `references/transcribe.md` — 读图与原文转录规则（含诗歌分行转录）
- `references/exam-requirements.md` — 小升初/中考/高考的题面、字数与评分规范（含出处）
- `references/adapt-levels.md` — L0/L1/L2 三档处理细则
- `references/art-styles.md` — 6 种中国怀旧画风预设与英文 style prefix
- `references/storyboard-rules.md` — 8/16 格拆解规则、景别用法、诗歌 4 格分支
- `references/safety.md` — 儿童形象、隐私、平台合规
- `references/output-schemas.md` — 产物字段定义
- `templates/storyboard-template.md` — 分镜表与 prompt 书写模板
- `scripts/validate_storyboard.py` — JSON 结构 + 安全检查
- `examples/storyboard.example.json` — 常规 8 格样例（可跑通校验）
- `examples/poem.example.json` — 诗歌 4 格样例（可跑通校验）
