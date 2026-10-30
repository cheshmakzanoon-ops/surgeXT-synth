#!/usr/bin/env bash
#
# Launches the Surge XT standalone on a virtual X display and saves a screenshot
# of its window. Used by the "UI Screenshot" GitHub workflow and handy locally.
#
# Usage: scripts/aurora-skin/screenshot.sh <path-to-standalone> <output.png> [zoom-percent] [Category/Patch]
#
# Requires: Xvfb, xdotool, ImageMagick (import, convert)

set -euo pipefail

BINARY="$1"
OUTPUT="$2"
ZOOM="${3:-200}"
PATCH="${4:-Templates/Init Saw}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'kill "${APP_PID:-0}" "${XVFB_PID:-0}" 2>/dev/null || true; rm -rf "$SANDBOX"' EXIT

# A fresh home so no user preferences or user skins leak into the screenshot,
# with the default zoom preset so the image is crisp on high density screens
export HOME="$SANDBOX/home"
export XDG_CONFIG_HOME="$HOME/.config"
unset XDG_DOCUMENTS_DIR
mkdir -p "$HOME/Documents/Surge XT" "$XDG_CONFIG_HOME"
cat > "$HOME/Documents/Surge XT/SurgeXTUserDefaults.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<defaults version="1">
  <default key="defaultZoom" value="$ZOOM" type="2"/>
  <default key="showVirtualKeyboardStandalone" value="0" type="2"/>
  <default key="initialPatchCategory" value="${PATCH%%/*}" type="1"/>
  <default key="initialPatchName" value="${PATCH#*/}" type="1"/>
  <default key="initialPatchCategoryType" value="Factory" type="1"/>
</defaults>
EOF

# Route audio to ALSA's null device so the standalone runs as it would with a
# sound card, instead of reporting that no audio output is available
cat > "$HOME/.asoundrc" <<EOF
pcm.!default { type null }
EOF

# Factory data (patches, wavetables, skins) straight from the source tree
export SURGE_DATA_HOME="$ROOT/resources/data"

DISPLAY_NUM=":99"
Xvfb "$DISPLAY_NUM" -screen 0 2560x1600x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY="$DISPLAY_NUM"
sleep 2

"$BINARY" > "$SANDBOX/app.log" 2>&1 &
APP_PID=$!

# Wait for the window, then give the UI a moment to settle
WID=""
for _ in $(seq 1 60); do
    WID="$(xdotool search --onlyvisible --name "Surge XT" 2>/dev/null | head -n 1 || true)"
    [ -n "$WID" ] && break
    sleep 1
done

if [ -z "$WID" ]; then
    echo "Surge XT window never appeared. Application log:" >&2
    cat "$SANDBOX/app.log" >&2
    exit 1
fi

sleep 6
xdotool windowmove "$WID" 0 0 || true
xdotool mousemove 2500 1550 || true
sleep 2

import -window "$WID" "$SANDBOX/window.png"

# Keep only the synth itself: the editor sits at the bottom of the standalone
# window, below the title bar and any notification banner
EW=$((904 * ZOOM / 100))
EH=$((569 * ZOOM / 100))
WW=$(identify -format '%w' "$SANDBOX/window.png")
WH=$(identify -format '%h' "$SANDBOX/window.png")
BORDER=$(((WW - EW) / 2))
convert "$SANDBOX/window.png" -crop "${EW}x${EH}+${BORDER}+$((WH - EH - BORDER))" +repage \
    -strip "$OUTPUT"
echo "Saved $(identify -format '%wx%h' "$OUTPUT") screenshot to $OUTPUT"
