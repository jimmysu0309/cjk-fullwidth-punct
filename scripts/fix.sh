#!/usr/bin/env bash
# fix.sh — batch convert ASCII punctuation to full-width in CJK boundary context.
# Usage:  bash fix.sh <file> [<file>...]
#
# Safe properties:
#   - Only fires on CJK↔ASCII boundary (won't touch ASCII-only code internals)
#   - Uses \x{...} unicode escapes in perl source (avoids latin1-mojibake mishap)
#   - Verifies output: grep hits == 0, encoding stays UTF-8, no mojibake bytes

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <file> [<file>...]" >&2
  exit 1
fi

for FILE in "$@"; do
  if [ ! -f "$FILE" ]; then
    echo "✗ skip (not a file): $FILE" >&2
    continue
  fi

  perl -CSDA -i -pe '
    s/(\p{Han})\(/$1\x{ff08}/g;
    s/(\p{Han})\)/$1\x{ff09}/g;
    s/\((\p{Han})/\x{ff08}$1/g;
    s/\)(\p{Han})/\x{ff09}$1/g;
    s/(\p{Han}),/$1\x{ff0c}/g;
    s/,(\p{Han})/\x{ff0c}$1/g;
    s/(\p{Han});/$1\x{ff1b}/g;
    s/;(\p{Han})/\x{ff1b}$1/g;
    s/(\p{Han}):/$1\x{ff1a}/g;
    s/:(\p{Han})/\x{ff1a}$1/g;
    s/(\p{Han})!/$1\x{ff01}/g;
    s/!(\p{Han})/\x{ff01}$1/g;
    s/(\p{Han})\?/$1\x{ff1f}/g;
    s/\?(\p{Han})/\x{ff1f}$1/g;
  ' "$FILE"

  # Use perl for detection (BSD grep on macOS lacks -P; perl works everywhere)
  HITS=$(perl -CSDA -ne 'BEGIN{$c=0} $c++ if /[\x{4e00}-\x{9fff}][,;:!?()]|[,;:!?()][\x{4e00}-\x{9fff}]/; END{print $c}' "$FILE")
  MOJIBAKE=$(LC_ALL=C grep -c $'\xc3\xaf\xc2\xbc' "$FILE" || true)

  if [ "$MOJIBAKE" != "0" ]; then
    echo "✗ $FILE: MOJIBAKE detected ($MOJIBAKE seqs). See SKILL.md recovery section." >&2
    exit 2
  fi

  echo "✓ $FILE: remaining boundary hits=$HITS mojibake=$MOJIBAKE"
done
