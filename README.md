# cjk-fullwidth-punct

A [Claude Code](https://claude.com/claude-code) skill that converts half-width ASCII
punctuation (`,;:!?()`) to full-width forms in Chinese (CJK) context. Designed for
Taiwan / zh-TW writing convention, but applicable to any Chinese codebase that
prefers full-width punctuation in CJK context.

## What it does

Detects and fixes punctuation like:

```
中文,半形         →  中文，半形
中文(英文)中文     →  中文（英文）中文
參數;結尾         →  參數；結尾
```

Only fires on **CJK ↔ ASCII boundaries** — leaves code internals alone (`level === 'off'`,
`'low'/'medium'/'high'` lists, etc. are untouched).

## Install

```bash
git clone https://github.com/jimmysu0309/cjk-fullwidth-punct \
  ~/.claude/skills/cjk-fullwidth-punct
```

That's it — Claude Code auto-loads skills under `~/.claude/skills/`. Next time you
start Claude Code, the skill appears in the available skills list.

## Use from Claude Code

Just say one of these to your Claude Code session:

- "修中文標點"
- "全形標點"
- "半形標點問題"
- "fix half-width punct in this file"

Claude will invoke the skill, run detection, and either fix one-by-one (if few hits)
or batch-convert the whole file (if many).

## Use the script directly

Plain text / source comments:

```bash
bash ~/.claude/skills/cjk-fullwidth-punct/scripts/fix.sh path/to/file.txt
```

Output:

```
✓ path/to/file.txt: remaining boundary hits=0 mojibake=0
```

Markdown (skips fenced code blocks and inline `code` spans — prose only):

```bash
python3 ~/.claude/skills/cjk-fullwidth-punct/scripts/fix-md.py path/to/file.md
```

## What's included

- `SKILL.md` — full procedure (detection / batch / verify / mojibake recovery / scope notes)
- `scripts/fix.sh` — one-shot batch script (perl with unicode escapes, no mojibake risk)
- `scripts/fix-md.py` — markdown-aware variant: converts prose only, never touches
  fenced blocks / inline code spans; repairs paren pairs and flags cross-code-span
  asymmetric pairs for manual review

## Why a skill (vs. just a script)

A skill bundles the **knowledge** of when and how to apply, not just the script.
Claude Code uses the `description` in `SKILL.md` frontmatter to decide when to
auto-invoke. So in addition to a fix script, this skill carries:

- Mapping table (ASCII → full-width with codepoints + perl `\x{...}` escapes)
- Detection patterns for both GNU grep (`-P`) and macOS BSD grep (perl fallback)
- **Mojibake recovery procedure** — if you ever paste full-width literals directly
  into perl source (it defaults to latin1, double-encodes them into 6-byte garbage),
  there's a documented byte-level reverse procedure.
- Scope boundaries — when not to apply (URLs, decimals, code, inherited legacy
  comments respecting "歷史條目不主動改寫" type rules).
- **Substitution-safe snippets** — all perl in `SKILL.md` uses lookarounds / named
  captures, never dollar-digit backreferences (Claude Code substitutes positional
  argument placeholders into skill markdown when the skill is invoked with args,
  which would corrupt the documented commands).

## License

MIT — see [LICENSE](LICENSE).

## Credits

Distilled from a real Claude Code session debugging perl latin1 mojibake while
fixing a 65-hit half-width punctuation issue in a Shinkansen project doc. The
takeaway: **always use `\x{ff08}` style unicode escapes in perl source, never paste
full-width chars literally.**
