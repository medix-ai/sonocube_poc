#!/usr/bin/env bash
# SonoCube macOS DMG 패키저
# 사용: ./packaging/build_dmg.sh
# 전제: pyinstaller packaging/sonocube_mac.spec 이미 실행 완료

set -e

APP_NAME="SonoCube"
VERSION="1.3.0"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_TMP="dist/${APP_NAME}_tmp.dmg"
DMG_OUT="dist/${DMG_NAME}"
VOL_SIZE="700m"   # 앱 ~495MB + 여유

if [ ! -d "$APP_PATH" ]; then
  echo "Error: ${APP_PATH} 없음 — 먼저 pyinstaller packaging/sonocube_mac.spec 실행"
  exit 1
fi

echo "▶ DMG 생성: ${DMG_OUT}"

# 1. 임시 읽기-쓰기 DMG 생성
hdiutil create \
  -srcfolder "$APP_PATH" \
  -volname "$APP_NAME" \
  -fs HFS+ \
  -fsargs "-c c=64,a=16,b=16" \
  -format UDRW \
  -size "$VOL_SIZE" \
  "$DMG_TMP"

# 2. 마운트
DEVICE=$(hdiutil attach -readwrite -noverify "$DMG_TMP" | \
         grep "/Volumes" | awk '{print $1}')
MOUNT_POINT="/Volumes/${APP_NAME}"

# 3. Applications 심볼릭 링크 추가 (드래그로 설치 가능)
ln -sf /Applications "${MOUNT_POINT}/Applications"

# 4. 언마운트
sync
hdiutil detach "$DEVICE" -quiet

# 5. 압축 DMG로 변환
hdiutil convert "$DMG_TMP" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "$DMG_OUT"

rm -f "$DMG_TMP"

echo "✓ 완료: ${DMG_OUT} ($(du -sh "$DMG_OUT" | cut -f1))"
echo ""
echo "배포 전 Gatekeeper 우회 안내를 사용자에게 공유하세요:"
echo "  sudo xattr -rd com.apple.quarantine /Applications/${APP_NAME}.app"
