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

**CRITICAL #1 — escapes, not literals**: Use `\x{...}` unicode escapes in perl source
code. Do NOT paste full-width literals (`，` `（` etc.) directly. Perl source defaults
to latin1; pasted literals are byte-decoded as latin1 codepoints, then `-A` re-encodes
them as UTF-8 → **6-byte mojibake** (e.g. `（` becomes `c3 af c2 bc c2 88` instead of
`ef bc 88`).

**CRITICAL #2 — this applies to ANY generated source, not just perl**: full-width
literals typed into a bash heredoc / python dict / grep pattern inside a tool call can
silently arrive as their HALF-width counterparts (observed 2026-06-11: a python
mapping dict authored as half→full came out half→half → conversion ran with ZERO
changes while detection kept reporting hits). Always build replacement maps from
escapes (`\x{ff0c}` in perl, `'\\uff0c'` in python), and before running, print the
codepoints of your replacement values and confirm they are in the `0xffXX` family:

```bash
python3 -c "M={',':'\\uff0c'}; print([hex(ord(v)) for v in M.values()])"  # expect 0xff0c
```

**CRITICAL #3 — never use `$`+digit in these snippets (skill-file corruption)**:
when this skill is invoked with arguments, Claude Code substitutes positional
argument placeholders (dollar-sign + digit, and the all-arguments placeholder) inside
SKILL.md **before rendering it** — a perl replacement like `s/(\p{Han}),/` + dollar-1
+ `\x{ff0c}/g` gets its dollar-1 replaced by the invocation arguments, corrupting the
documented command exactly when it is needed (observed 2026-06-11). Therefore every
snippet below uses **lookarounds (no capture groups)** or **named captures**
(`$+{name}` is not substituted). Files under `scripts/` are NOT substituted (they are
executed, not rendered), so shell positional parameters there are fine — but keep
their perl `$`+digit-free too, so copy-paste back into SKILL.md stays safe.

```bash
perl -CSDA -i -pe '
  s/(?<=\p{Han})\(/\x{ff08}/g;
  s/(?<=\p{Han})\)/\x{ff09}/g;
  s/\((?=\p{Han})/\x{ff08}/g;
  s/\)(?=\p{Han})/\x{ff09}/g;
  s/(?<=\p{Han}),/\x{ff0c}/g;
  s/,(?=\p{Han})/\x{ff0c}/g;
  s/(?<=\p{Han});/\x{ff1b}/g;
  s/;(?=\p{Han})/\x{ff1b}/g;
  s/(?<=\p{Han}):/\x{ff1a}/g;
  s/:(?=\p{Han})/\x{ff1a}/g;
  s/(?<=\p{Han})!/\x{ff01}/g;
  s/!(?=\p{Han})/\x{ff01}/g;
  s/(?<=\p{Han})\?/\x{ff1f}/g;
  s/\?(?=\p{Han})/\x{ff1f}/g;
' <file>
```

The `-CSDA` flags enable UTF-8 for stdin / stdout / stderr / `@ARGV`. `\p{Han}`
matches Han ideographs (CJK). Lookbehind/lookahead replace only the punctuation
itself — no capture group, no dollar-digit backreference needed.

Or use the bundled script: `bash ${CLAUDE_SKILL_DIR}/scripts/fix.sh <file>` — runs
the same perl + verification in one shot.

## Step 3b (optional): Repair Asymmetric Paren Pairs

Boundary-only conversion can leave pairs like `（...)` — full-width open (was
Han-adjacent) with half-width close (adjacent to ASCII, e.g. `（同 videoId 仍 active)`).
Repair with named captures (substitution-safe, see CRITICAL #3):

```bash
perl -CSDA -i -pe '
  s/\x{ff08}(?<inner>[^()\x{ff08}\x{ff09}]*)\)/\x{ff08}$+{inner}\x{ff09}/g;
  s/\((?<inner>[^()\x{ff08}\x{ff09}]*)\x{ff09}/\x{ff08}$+{inner}\x{ff09}/g;
' <file>
```

Skip this pass when the file legitimately mixes notation (e.g. math intervals like
`[startMs, endMs)` inside a Chinese comment) — review hits first.

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

Updated 2026-06-11 after a second real-world session surfaced two more failure modes:

1. **Skill-file argument substitution**: the skill was invoked with `args`, and Claude
   Code substituted the positional placeholders inside the rendered SKILL.md — every
   dollar-digit backreference in the documented perl became a fragment of the
   invocation arguments. The snippets were rewritten to lookarounds / named captures
   (CRITICAL #3) so they survive being rendered with arguments.
2. **Half-width mangling of full-width literals in generated source**: a python
   replacement dict authored inside a bash heredoc arrived with HALF-width values —
   the conversion ran cleanly but changed nothing, while detection kept reporting
   hits (a silent no-op, the inverse of the mojibake failure). Hence CRITICAL #2:
   build maps from escapes and codepoint-check replacement values before running.
