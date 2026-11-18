# Maestro Marketplace

Claude Code / Agent Skill 市场仓库。每个 skill 独立目录，可单独安装、升级、发布。

## 目录结构

```
.
├── marketplace.json          # 市场索引（所有 skill 的清单）
├── skills/
│   ├── _template/            # 新建 skill 的模板，不要发布
│   │   └── SKILL.md
│   └── <skill-name>/
│       ├── SKILL.md          # 必需：入口，含 YAML frontmatter
│       ├── skill-card.md     # 可选：对外展示卡片
│       ├── .market-meta.json # 可选：安装元数据
│       ├── references/       # 可选：参考资料
│       ├── templates/        # 可选：模板文件
│       └── scripts/          # 可选：可执行脚本
└── scripts/
    └── validate.sh           # 校验所有 skill 结构
```

## 新建 skill

```bash
cp -r skills/_template skills/<skill-name>
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

检查项：目录名与 `name` 一致、frontmatter 齐全、description 非空、`marketplace.json` 登记完整。

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
