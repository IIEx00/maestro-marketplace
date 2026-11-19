#!/usr/bin/env bash
# 一把梭：分镜 → 出图 → 成片（视频 + 画外音 + 字幕）
#
# 用法：
#   bash scripts/make.sh outputs/我的家人              # 全流程
#   bash scripts/make.sh outputs/我的家人 --dry-run    # 只看计划与估价
#   bash scripts/make.sh outputs/我的家人 --no-video   # 只出图，不成片
#
# 顺序永远是：先出图（能看到图了再决定要不要花钱出视频）。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:?用法：bash scripts/make.sh <作品目录> [选项]}"
shift || true

DRY=""
NOVIDEO=""
for a in "$@"; do
  case "$a" in
    --dry-run)  DRY="--dry-run" ;;
    --no-video) NOVIDEO="1" ;;
  esac
done

SB="$WORK/storyboard.json"
PR="$WORK/production.json"
IMG="$WORK/images"
[ -f "$SB" ] || { echo "✗ 找不到 $SB"; exit 1; }

echo "═══ 1/2 出图 ═══"
if [ -n "$DRY" ]; then
  python3 "$ROOT/skills/zuowen-manju/scripts/batch_images.py" \
    -s "$SB" -p "$PR" -o "$IMG" --dry-run
  [ -n "$NOVIDEO" ] && exit 0
  echo
  echo "（加 --confirm 才会真的出图）"
  exit 0
fi

python3 "$ROOT/skills/zuowen-manju/scripts/batch_images.py" \
  -s "$SB" -p "$PR" -o "$IMG" --confirm || exit 1

[ -n "$NOVIDEO" ] && { echo "出图完成（跳过成片）"; exit 0; }

echo
echo "═══ 2/2 成片 ═══"
NAME="$(basename "$WORK")"
python3 "$ROOT/skills/zuowen-manju/scripts/voiceover.py" \
  -s "$SB" -i "$IMG" \
  --from-images --duration 16 --resolution 480p \
  -o "$WORK/${NAME}_成片.mp4" --yes

echo
echo "完成："
ls -la "$WORK"/*.mp4 "$WORK"/*.srt 2>/dev/null
