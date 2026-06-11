#!/usr/bin/env python3
"""Markdown-aware CJK boundary punctuation fixer.

Converts half-width ASCII punctuation to full-width on CJK boundaries, but ONLY
in prose — skips fenced code blocks (``` / ~~~) and inline code spans (`...`),
per the skill's Scope Boundaries. Use this for markdown / prose-mixed-with-code
files (CHANGELOG, SPEC, README); use fix.sh for plain text / source comments.

Safety rails (see SKILL.md CRITICAL #2):
- The replacement map is asserted to be in the 0xffXX family before running,
  catching the "full-width literals silently arrived half-width" failure mode.
- After converting, prints REVIEW lines for asymmetric paren pairs that span
  code spans (e.g. half-width open in prose + full-width close after a code
  span) — these cannot be auto-repaired segment-locally and need human review.
  Beware false positives: a code span containing a bare \\( between legitimate
  full-width parens will match; fix only true prose pairs.

Usage: python3 fix-md.py <file.md> [...]   (in-place)
"""
import re
import sys

MAP = {
    ',': '，',
    ';': '；',
    ':': '：',
    '(': '（',
    ')': '）',
    '!': '！',
    '?': '？',
}

HAN = r'[一-鿿]'
PUNCT_CLASS = r'[,;:!?()]'
RE_AFTER_HAN = re.compile('(?<=' + HAN + ')(' + PUNCT_CLASS + ')')
RE_BEFORE_HAN = re.compile('(' + PUNCT_CLASS + ')(?=' + HAN + ')')
FW_OPEN, FW_CLOSE = '（', '）'
# Asymmetric paren pairs within one prose segment: （...) or (...）
RE_PAIR_A = re.compile(FW_OPEN + r'([^()' + FW_OPEN + FW_CLOSE + r']*)\)')
RE_PAIR_B = re.compile(r'\(([^()' + FW_OPEN + FW_CLOSE + r']*)' + FW_CLOSE)
# Same shapes, wide window, scanned across the WHOLE line (incl. code spans)
# after conversion — candidates for manual review (cross-code-span pairs).
RE_REVIEW = re.compile(
    '(' + FW_OPEN + r'[^()' + FW_OPEN + FW_CLOSE + r']{0,200}\)'
    + r'|\([^()' + FW_OPEN + FW_CLOSE + r']{0,200}' + FW_CLOSE + ')'
)
# Inline code span: one or more backticks, content, matching backticks
RE_CODE_SPAN = re.compile(r'(`+[^`]*`+)')
RE_FENCE = re.compile(r'^\s*(```|~~~)')


def convert_prose(seg):
    seg = RE_AFTER_HAN.sub(lambda m: MAP[m.group(1)], seg)
    seg = RE_BEFORE_HAN.sub(lambda m: MAP[m.group(1)], seg)
    seg = RE_PAIR_A.sub(FW_OPEN + r'\1' + FW_CLOSE, seg)
    seg = RE_PAIR_B.sub(FW_OPEN + r'\1' + FW_CLOSE, seg)
    return seg


def convert_line(line):
    parts = RE_CODE_SPAN.split(line)
    # After split, odd indexes are code spans (kept verbatim), even are prose.
    return ''.join(p if i % 2 else convert_prose(p) for i, p in enumerate(parts))


def process(path):
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    out, changed, review, in_fence = [], 0, [], False
    for lineno, line in enumerate(lines, 1):
        if RE_FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        new = line if in_fence else convert_line(line)
        if new != line:
            changed += 1
        for m in RE_REVIEW.finditer(new):
            review.append((lineno, m.group(1)))
        out.append(new)
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(out)
    print(f'{path}: {changed} lines changed')
    for lineno, hit in review:
        print(f'  REVIEW {path}:{lineno}: {hit}')
    return changed


if __name__ == '__main__':
    cps = sorted({hex(ord(v)) for v in MAP.values()})
    assert all(c.startswith('0xff') for c in cps), (
        f'replacement map is NOT full-width ({cps}) — silently mangled, abort')
    print('replacement codepoints:', cps)
    if len(sys.argv) < 2:
        sys.exit('usage: fix-md.py <file.md> [...]')
    total = sum(process(p) for p in sys.argv[1:])
    print(f'total: {total} lines changed')
