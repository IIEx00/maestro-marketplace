---
name: skill-name
description: >-
  一句话说明这个 skill 做什么。当用户提到「关键词 A」「关键词 B」「关键词 C」时使用。
disable-model-invocation: false
metadata:
  clawdbot:
    emoji: "🛠"
    requires:
      bins: []
      os: ["linux", "darwin", "win32"]
---

# Skill Name

## 何时触发

- 用户说「X」→ 执行步骤 1
- 用户说「Y」→ 执行步骤 2

不应触发的情况：……

## 快速开始

```bash
# 最短可用示例
```

## 核心流程

1. **步骤一**：做什么，用什么命令/工具
2. **步骤二**：……

关键参数说明：

| 参数 | 含义 | 默认值 |
|---|---|---|
| `--foo` | 说明 | `bar` |

## 约束与注意事项

- 需要条条可执行的约束，不要写「注意安全」这类空话
- 失败时怎么办：先查 X，再试 Y

## 常见问题

| 症状 | 排查 |
|---|---|
| 报错 A | 原因 + 处理方式 |

## 参考文件

- `references/xxx.md` — 说明
- `scripts/xxx.sh` — 说明
