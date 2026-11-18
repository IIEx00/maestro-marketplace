#!/usr/bin/env bash
# 安装或更新 skill 到本地 ~/.claude/skills/
# 用法：bash scripts/install.sh <skill-name> [skill-name ...]
# 不带参数则安装 marketplace.json 里登记的全部 skill
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.claude/skills"
# 备份放在 skills 目录外面，否则会被当成一个独立的 skill 注册进来
BACKUP="${HOME}/.claude/skills-backup"
mkdir -p "$DEST" "$BACKUP"

if [ $# -gt 0 ]; then
  names=("$@")
else
  names=()
  while IFS= read -r n; do
    [ -n "$n" ] && names+=("$n")
  done < <(python3 -c "
import json,os
m=json.load(open(os.path.join('$ROOT','marketplace.json'),encoding='utf-8'))
for s in m.get('skills',[]): print(s.get('name',''))
")
fi

fail=0
for name in "${names[@]}"; do
  src="$ROOT/skills/$name"
  if [ ! -d "$src" ]; then
    echo "  ✗ $name：仓库里没有这个 skill"
    fail=1
    continue
  fi
  # 整目录覆盖前先备份已装版本，便于回滚
  if [ -d "$DEST/$name" ]; then
    rm -rf "$BACKUP/$name"
    cp -R "$DEST/$name" "$BACKUP/$name"
  fi
  rm -rf "${DEST:?}/$name"
  cp -R "$src" "$DEST/$name"
  # 清掉可能残留的 pyc
  find "$DEST/$name" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null
  echo "  ✓ $name → $DEST/$name"
done

echo
echo "已装版本现在是仓库的快照。仓库改动后重跑本脚本即可同步。"
echo "旧版本备份在 $BACKUP"
echo "Claude Code 会缓存已加载的 skill，改完要重启会话才生效。"
exit $fail
