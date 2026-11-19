#!/usr/bin/env bash
# 校验 skills/ 下所有 skill 的结构
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT/skills"
MARKET="$ROOT/marketplace.json"
CLAUDE_MARKET="$ROOT/.claude-plugin/marketplace.json"
fail=0

err() { echo "  ✗ $*"; fail=1; }
ok()  { echo "  ✓ $*"; }

for dir in "$SKILLS_DIR"/*/; do
  name="$(basename "$dir")"
  # 模板骨架放在 templates/skill-skeleton/，不在 skills/ 下，不会被当正式 skill
  [ "$name" = "_template" ] && continue
  echo "[$name]"

  file="$dir/SKILL.md"
  if [ ! -f "$file" ]; then
    err "缺少 SKILL.md"
    continue
  fi

  # frontmatter 必须存在
  if [ "$(head -n 1 "$file")" != "---" ]; then
    err "SKILL.md 缺少 YAML frontmatter"
    continue
  fi

  fm_name="$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name:[[:space:]]*/, ""); print; exit}' "$file")"
  fm_desc="$(awk '/^---$/{n++; next} n==1 && /^description:/{found=1} found{print} /^---$/ && n==1{exit}' "$file")"

  [ -n "$fm_name" ] || err "frontmatter 缺少 name"
  [ "$fm_name" = "$name" ] || err "name ($fm_name) 与目录名 ($name) 不一致"
  [ -n "$fm_desc" ] || err "frontmatter 缺少 description"

  # marketplace.json 登记检查
  if [ -f "$MARKET" ]; then
    if ! grep -q "\"$name\"" "$MARKET"; then
      err "未在 marketplace.json 中登记"
    fi
  else
    err "缺少 marketplace.json"
  fi

  [ -f "$file" ] && [ -n "$fm_name" ] && [ "$fm_name" = "$name" ] && [ -n "$fm_desc" ] && ok "结构正常"
done

# marketplace.json 合法性
if [ -f "$MARKET" ]; then
  echo "[marketplace.json]"
  if command -v jq >/dev/null 2>&1; then
    jq empty "$MARKET" && ok "JSON 合法" || err "JSON 解析失败"
  else
    ok "跳过 JSON 校验（未安装 jq）"
  fi
fi

# ── Claude Code 官方 marketplace 清单必须存在且与仓库索引对得上 ──
echo "[.claude-plugin/marketplace.json]"
if [ ! -f "$CLAUDE_MARKET" ]; then
  err "缺少 .claude-plugin/marketplace.json（Claude Code 用 /plugin marketplace add 装的就是它）"
else
  ok "存在"
  if command -v claude >/dev/null 2>&1; then
    if claude plugin validate "$ROOT" >/dev/null 2>&1; then
      ok "claude plugin validate 通过"
    else
      err "claude plugin validate 未通过"
    fi
  fi
  # 官方清单里的 plugin 名 与 仓库索引里的 skill 名 必须一致，防止两边漂移
  a=$(python3 -c "
import json,sys
d=json.load(open('$CLAUDE_MARKET',encoding='utf-8'))
print(' '.join(sorted(p['name'] for p in d.get('plugins',[]))))
" 2>/dev/null)
  b=$(python3 -c "
import json,sys
d=json.load(open('$MARKET',encoding='utf-8'))
print(' '.join(sorted(s['name'] for s in d.get('skills',[]))))
" 2>/dev/null)
  if [ "$a" = "$b" ]; then
    ok "与 marketplace.json 登记一致：$a"
  else
    err "两边不一致：官方[$a] vs 仓库索引[$b]"
  fi
fi

exit "$fail"
