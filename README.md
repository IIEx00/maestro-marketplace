# Maestro Marketplace

Claude Code / Agent Skill 市场仓库。每个 skill 独立目录，可单独安装、升级、发布。

## 已发布的 Skill

| Skill | 版本 | 一句话 | 卡片 |
|---|---|---|---|
| [`zuowen-manju`](skills/zuowen-manju/) | 1.1.0 | 中小学生手写作文照片 → AI 漫剧分镜 prompt 包（8/16 格），默认 L0 原汁原味不改错别字，附批量出图与成片流水线 | [skill-card](skills/zuowen-manju/skill-card.md) |

## 目录结构

```
.
├── .claude-plugin/
│   └── marketplace.json      # Claude Code 官方市场清单（/plugin marketplace add 读它）
├── marketplace.json          # 仓库自有索引（skill 清单，与官方清单交叉校验不许漂移）
├── templates/
│   └── skill-skeleton/       # 新建 skill 的模板骨架（刻意不放 skills/ 下）
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md          # 必需：入口，含 YAML frontmatter
│       ├── skill-card.md     # 可选：对外展示卡片
│       ├── .market-meta.json # 可选：安装元数据
│       ├── references/       # 可选：参考资料
│       ├── templates/        # 可选：模板文件
│       └── scripts/          # 可选：可执行脚本
└── scripts/
    ├── validate.sh           # 校验所有 skill 结构
    ├── install.sh            # 安装/更新到 ~/.claude/skills/
    └── make.sh               # 分镜 → 出图 → 成片 一键跑
```

## 新建 skill

```bash
cp -r templates/skill-skeleton skills/<skill-name>
rm -rf skills/<skill-name>/scripts   # 不需要就删
```

然后修改 `skills/<skill-name>/SKILL.md`：

1. `name` 与目录名一致（小写、连字符）
2. `description` 写清「做什么 + 什么时候用」，这是模型触发 skill 的唯一依据
3. 正文写操作步骤、命令、约束，不要写成宣传文案

最后在 `marketplace.json` 的 `skills` 数组里登记。

## 校验

```bash
bash scripts/validate.sh
```

## 一把梭：分镜 → 成片

```bash
# 只看计划与估价
bash scripts/make.sh outputs/我的爷爷 --dry-run

# 全流程（先出图，再出视频 + 配音 + 字幕）
bash scripts/make.sh outputs/我的爷爷
```

前提：`outputs/<作品名>/` 下有 `storyboard.json` 和 `production.json`。
分步跑也行，见 `skills/zuowen-manju/references/production-recipes.md`。

检查项：目录名与 `name` 一致、frontmatter 齐全、description 非空、`marketplace.json` 登记完整、
两个市场清单的 skill 名单一致、`claude plugin validate` 通过。

## 发布到 Claude Code 技能市场

Claude Code 用官方 plugin marketplace 机制，认的是 `.claude-plugin/marketplace.json`。
gitee 和 GitHub 都支持（走 git clone）：

```bash
# 1. 用户添加市场
claude plugin marketplace add https://gitee.com/erosxxx/maestro-marketplace.git
claude plugin marketplace add https://github.com/IIEx00/maestro-marketplace.git

# 2. 用户安装
claude plugin install zuowen-manju@maestro-marketplace
```

本地开发用目录方式：`claude plugin marketplace add /绝对路径/maestro-marketplace`。

装完 skill 落在 `~/.claude/plugins/cache/<市场名>/<插件名>/<版本>/skills/`，
**与 `bash scripts/install.sh` 装到 `~/.claude/skills/` 是两套并行机制**：
前者是用户自己装，后者是本仓库的开发同步脚本，两边内容相同。

> 新 skill 的模板骨架在 `templates/skill-skeleton/`，**刻意不放 `skills/` 下** ——
> 放在那里会被当作一个叫 `skill-name` 的占位 skill 装进用户机器。

## 安装 / 更新到本地

```bash
# 安装或更新（不带参数则装 marketplace.json 里登记的全部）
bash scripts/install.sh <skill-name>

# 旧版本自动备份到 ~/.claude/skills-backup/
```

> Claude Code 会缓存已加载的 skill，**改完要重启会话才生效**。
> 仓库改了什么，要记得重跑本脚本同步 —— 否则本地用的还是旧版。

## SKILL.md 规范

```yaml
---
name: skill-name                 # 必需，与目录名一致
description: >-                  # 必需，一句话说明用途与触发场景
  做 X。当用户提到 Y、Z 时使用。
disable-model-invocation: false  # 可选，true 表示只能由用户显式调用
metadata:                        # 可选，运行时依赖
  clawdbot:
    emoji: "🛠"
    requires:
      bins: ["jq"]
---
```

正文建议顺序：**何时触发 → 快速开始 → 核心流程 → 常见问题 → 参考文件索引**。

---

## English

**Maestro Marketplace** — a Claude Code / Agent Skill marketplace for Chinese
creative work. Currently shipping one skill.

### Skills

| Skill | Version | What it does |
|---|---|---|
| [`zuowen-manju`](skills/zuowen-manju/) — 作文漫剧 | 1.1.0 | Turns a photo of a hand-written Chinese school essay into an 8-shot AI storyboard pack: Chinese + English image prompts, character sheet prompts, and a typo / pinyin-annotation registry. Keeps every mistake the child made and turns them into the visual gag. Ships batch image generation and a video assembly pipeline. |

### Install

As a Claude Code plugin marketplace:

```bash
claude plugin marketplace add https://github.com/IIEx00/maestro-marketplace.git
claude plugin install zuowen-manju@maestro-marketplace
```

As a plain Agent Skill:

```bash
git clone https://github.com/IIEx00/maestro-marketplace.git
cp -r maestro-marketplace/skills/zuowen-manju ~/.claude/skills/
```

### What makes it different

- **L0 by default — nothing is silently corrected.** Typos, broken sentences and
  pinyin scribbles are transcribed verbatim and registered, then placed into the
  frames with the controlled `handwritten Chinese text "…"` form. The child's
  own marks become the content, not a bug to hide.
- **7 Chinese retro art styles, every one actually rendered and compared** —
  not a wishlist. See [`references/art-styles.md`](skills/zuowen-manju/references/art-styles.md).
- **Production-grade scripts, not just prompts** — batch image generation with
  request-fingerprint idempotency, resume-from-ledger, live model-card admission
  checks and a 4-way concurrency queue; plus a video pipeline (shot-boundary
  detection → per-shot TTS → alignment → mixing → burned-in subtitles → CRT grade).
- **Child-safety built in.** Real names, schools and addresses never enter a
  prompt; a teacher's score or comment is recorded in the transcript but must
  never appear in anything published.

### Repository layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace manifest
marketplace.json                   # repo index, cross-checked against the above
skills/<skill-name>/               # the skills
templates/skill-skeleton/          # skeleton for new skills (deliberately not under skills/)
distribution/skillhub/             # prebuilt submission package for skillhub.cn
scripts/                           # validate.sh · install.sh · make.sh
```

MIT licensed.
