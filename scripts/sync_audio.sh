#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)/assets/audio/wav"
TARGET_DIR="${AST_SOUND_DIR:-/var/lib/asterisk/sounds/custom}"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Source dir not found: $SOURCE_DIR" >&2
  exit 1
fi

echo "Copying prompts to $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -f "$SOURCE_DIR"/hello.wav "$TARGET_DIR"/hello.wav
cp -f "$SOURCE_DIR"/goodby.wav "$TARGET_DIR"/goodby.wav
cp -f "$SOURCE_DIR"/second.wav "$TARGET_DIR"/second.wav
chmod 644 "$TARGET_DIR"/hello.wav "$TARGET_DIR"/goodby.wav "$TARGET_DIR"/second.wav

echo "Done. Reload Asterisk sounds if needed."
