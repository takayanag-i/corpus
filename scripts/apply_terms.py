# 置き換えの決まりを、ファイル一覧の各ファイルに適用する
# 使い方: python3 apply_terms.py <ファイル一覧> <決まり.json> [--dry] [--quote-line 正規表現]
#   決まり.json: [{"from": 語, "to": 置き換え, "regex": 偽, "files": [当てるファイル], "skip_line": 当てない行の正規表現}, ...]。上から順に適用する
#   regex が真の決まりは正規表現として適用し、to に \1 などを使える。それ以外は文字列のまま置き換える
#   --quote-line に当たる行は、「」の中を変更しない。既定は人の発言を引用していそうな行
#   --dry: 書き換えずに、ファイルごとの変更する行数と合計を出力する
import re, sys, json, argparse
ap = argparse.ArgumentParser(); ap.add_argument('files'); ap.add_argument('rules'); ap.add_argument('--dry', action='store_true')
ap.add_argument('--quote-line', default=r'ユーザー|依頼|人の判断|人の指示|人の回答|の発言')
a = ap.parse_args()
rules = json.load(open(a.rules, encoding='utf-8'))
for r in rules:
    r['pat'] = re.compile(r['from']) if r.get('regex') else None
    r['skip'] = re.compile(r['skip_line']) if r.get('skip_line') else None
QUOTE = re.compile(a.quote_line)

def apply_text(text, rs):
    for r in rs:
        text = r['pat'].sub(r['to'], text) if r['pat'] else text.replace(r['from'], r['to'])
    return text

def apply_line(line, rs):
    rs = [r for r in rs if not (r['skip'] and r['skip'].search(line))]
    if not QUOTE.search(line): return apply_text(line, rs)
    parts = re.split(r'(「[^」]*」)', line)   # 「」の中の引用は変更しない
    return ''.join(s if s.startswith('「') and s.endswith('」') else apply_text(s, rs) for s in parts)

total = 0
for f in open(a.files, encoding='utf-8').read().split():
    try: src = open(f, encoding='utf-8').read()
    except (OSError, UnicodeDecodeError): continue
    rs = [r for r in rules if not r.get('files') or f in r['files']]
    lines = src.split('\n'); out = [apply_line(l, rs) for l in lines]
    n = sum(1 for x, y in zip(lines, out) if x != y)
    if n:
        total += n; print(f'{n:6d} {f}')
        if not a.dry: open(f, 'w', encoding='utf-8').write('\n'.join(out))
print('変更する行' if a.dry else '変更した行', total)
