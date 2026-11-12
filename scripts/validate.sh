#!/usr/bin/env bash
# 校验 skills/ 下所有 skill 的结构
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT/skills"
MARKET="$ROOT/marketplace.json"
fail=0

err() { echo "  ✗ $*"; fail=1; }
ok()  { echo "  ✓ $*"; }

for dir in "$SKILLS_DIR"/*/; do
  name="$(basename "$dir")"
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

exit "$fail"
