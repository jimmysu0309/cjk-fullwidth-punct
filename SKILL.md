---
name: cjk-fullwidth-punct
description: |
  Convert half-width ASCII punctuation to full-width in Chinese (CJK) context.
  Use this skill whenever:
  - User asks to fix half-width punctuation, e.g. "修中文標點", "全形標點", "半形標點問題", "punct fix"
  - After editing source comments, docs, UI strings, or markdown reports containing
    Chinese text — run as a forcing-function check before reporting work as done
  - When CLAUDE.md §13 (or equivalent project rule) requires full-width punct in CJK
  - User mentions Taiwan/zh-TW writing convention applied to comments/docs/UI

  Strategy: detect via grep on CJK↔ASCII boundary, batch-convert via perl with unicode
  escapes (NEVER paste full-width literals into perl source — produces mojibake).
  Skips code-internal punctuation (preserves `'off'` quotes, `level === 'x'` etc.).
  Includes mojibake-recovery procedure if a previous run mis-encoded.
---

# Convert Half-Width to Full-Width Punctuation in CJK Context

When editing source code comments, documentation, or UI strings with Chinese (CJK) text,
ASCII punctuation (`,;:!?()`) often slips in. Taiwan / zh-TW convention is full-width
in CJK context. This skill detects and fixes them safely.

## Mapping Table

| ASCII | Full-width | Codepoint | Use perl escape |
|---|---|---|---|
| `,` | `,` | U+FF0C | `\x{ff0c}` |
| `;` | `;` | U+FF1B | `\x{ff1b}` |
| `:` | `:` | U+FF1A | `\x{ff1a}` |
| `(` | `(` | U+FF08 | `\x{ff08}` |
| `)` | `)` | U+FF09 | `\x{ff09}` |
| `!` | `!` | U+FF01 | `\x{ff01}` |
| `?` | `?` | U+FF1F | `\x{ff1f}` |
| `.` | `。` | U+3002 (ideographic full stop) | `\x{3002}` |

Note: full-width period is `。` (U+3002), NOT the fullwidth full stop `．` (U+FF0E).
Do NOT batch-convert `.` automatically — it conflicts with URLs, decimals, code paths
(`lib/foo.js`), and version numbers (`v1.2.3`). Handle case-by-case.

## Step 1: Detect

GNU grep (Linux, or macOS with `brew install grep` → `ggrep`):

```bash
grep -nP "[一-鿿][,;:!?()][^一-鿿]?|[^一-鿿]?[,;:!?()][一-鿿]" <file>
```

macOS default BSD grep does NOT support `-P`. Use perl instead:

```bash
perl -CSDA -ne 'print "$ARGV:$.: $_" if /[\x{4e00}-\x{9fff}][,;:!?()]|[,;:!?()][\x{4e00}-\x{9fff}]/' <file>
```

The CJK range `[一-鿿]` (or `[\x{4e00}-\x{9fff}]`) matches `U+4E00 – U+9FFF` (CJK
Unified Ideographs). The pattern catches punctuation on either side of a CJK boundary.

- 0 output → file is clean.
- Non-empty output → proceed.

For projects requiring strict §13-style enforcement, consider this a forcing function:
non-empty output blocks "task complete" until fixed.

## Step 2: Decide Scale

- **<10 hits**: Use Edit tool, fix one-by-one. Safer, more controlled, preserves git
  diff clarity. Especially preferred when only "your" newly-added sections should
  change (and inherited/legacy sections must be left alone).
- **Many hits across whole file (or batch fix is acceptable)**: Use Step 3 perl batch.
  Caveat: this will modify legacy/inherited sections too. If that's not desired, fall
  back to Edit one-by-one.

## Step 3: Batch Fix (Perl with Unicode Escapes)

**CRITICAL**: Use `\x{...}` unicode escapes in perl source code. Do NOT paste
full-width literals (`，` `（` etc.) directly. Perl source defaults to latin1; pasted
literals are byte-decoded as latin1 codepoints, then `-A` re-encodes them as UTF-8 →
**6-byte mojibake** (e.g. `（` becomes `c3 af c2 bc c2 88` instead of `ef bc 88`).

```bash
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
' <file>
```

The `-CSDA` flags enable UTF-8 for stdin / stdout / stderr / `@ARGV`. `\p{Han}`
matches Han ideographs (CJK).

Or use the bundled script: `bash ${CLAUDE_SKILL_DIR}/scripts/fix.sh <file>` — runs
the same perl + verification in one shot.

## Step 4: Verify

```bash
# 1. grep should be 0 hits
grep -nP "[一-鿿][,;:!?()][^一-鿿]?|[^一-鿿]?[,;:!?()][一-鿿]" <file>

# 2. encoding still UTF-8
file <file>

# 3. mojibake byte signature absent
LC_ALL=C grep -c $'\xc3\xaf\xc2\xbc' <file>
```

All three should return 0 / "UTF-8 text" / 0.

## Recovery: If Mojibake Already Occurred

Symptoms: file shows characters like `ï¼` followed by garbage, or `file <file>` flags
as Unicode but you see double-encoded bytes.

Reverse with byte-level substitution (perl WITHOUT `-CSDA`, operates on raw bytes):

```bash
perl -i -pe '
  s/\xc3\xaf\xc2\xbc\xc2\x88/\xef\xbc\x88/g;  # （ U+FF08
  s/\xc3\xaf\xc2\xbc\xc2\x89/\xef\xbc\x89/g;  # ） U+FF09
  s/\xc3\xaf\xc2\xbc\xc2\x8c/\xef\xbc\x8c/g;  # , U+FF0C
  s/\xc3\xaf\xc2\xbc\xc2\x9b/\xef\xbc\x9b/g;  # ; U+FF1B
  s/\xc3\xaf\xc2\xbc\xc2\x9a/\xef\xbc\x9a/g;  # : U+FF1A
  s/\xc3\xaf\xc2\xbc\xc2\x81/\xef\xbc\x81/g;  # ! U+FF01
  s/\xc3\xaf\xc2\xbc\xc2\x9f/\xef\xbc\x9f/g;  # ? U+FF1F
' <file>
```

Then re-run Step 3 with proper `\x{...}` escapes.

## Scope Boundaries

The grep + perl approach **only catches CJK↔ASCII boundary** punctuation. It will
miss:

- Half-width punctuation between two ASCII characters where the surrounding context
  is still semantically Chinese, e.g. `（LiteLLM 等）` where `(` is preceded by an
  ASCII space, not by a Han char. These need human judgment — fall back to Step 2.
- Code-internal punctuation (e.g. `level === 'off'`, `'low'/'medium'/'high'` lists,
  `extra_body.enable_thinking`) — these are ASCII-only and won't match `\p{Han}`
  patterns, so they're left alone correctly.
- The Chinese full stop `。` (U+3002) — see mapping table note. Don't batch-convert
  `.` since it conflicts with URLs / decimals / code paths.

## When NOT to Apply

- Pure ASCII source code with no Chinese.
- Files where mixed half/full-width is explicitly preserved by convention (e.g.
  inherited `v1.6.18` style comments in this codebase). If unsure, check the
  project's `CLAUDE.md` for "歷史條目不主動改寫" or similar rules.
- Inline `<code>` or fenced ` ``` ` code blocks containing punctuation that's part
  of the code being shown (e.g. example JSON with ASCII `,` separators).
- Single-character changes inside long files where the user only wants to fix
  "your newly added sections" — Step 2 (Edit) is more precise.

## Real-World Reference

Built from a 2026-05-10 session on a markdown report with ~65 cross-CJK boundary
half-width hits. First attempt at batch-replace pasted full-width chars directly
into perl source → produced mojibake. Recovery via byte-level reverse + redo with
`\x{...}` escapes worked clean. The key lesson:

> Perl source code is byte-mode by default. Full-width literals in your perl `s///`
> strings are read as latin1 bytes and double-encoded on output. Always use
> `\x{ff08}` style unicode escapes, not paste-the-character.
