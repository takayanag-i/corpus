# 文書のフォルダから、1つのコーパスを作る
# 使い方: python3 build_corpus.py <名前> <元のフォルダ> <コーパスのフォルダ> [--domain] [--ext .html,.md,.sgml,.po] [--exclude 正規表現]
#   <コーパスのフォルダ>/<名前>.txt に本文を書く。ページの区切りは改ページ文字 \f
#   <コーパスのフォルダ>/corpora.json に、種類 base か domain・ページ数・日本語の文字数・元のフォルダを記録する
#   --domain: ドメイン固有のコーパスとして登録する。corpus_count.py は --domain で名前を指定したときにカウントする
#   HTML は <main>・<article>・role="main" の要素の中を本文とし、目次やナビゲーションを除く
#   Markdown は先頭のフロントマターと {{ }} のマクロを除く
#   SGML は <!-- --> のコメントとタグを除く。翻訳の原文がコメントに入っている文書に使う
#   PO は msgstr の訳文を本文にする
import os, re, sys, json, html, argparse

JA = re.compile(r'[぀-ヿ一-鿿]')
MAIN = [re.compile(p, re.S | re.I) for p in (
    r'<main\b[^>]*>(.*?)</main>',
    r'<article\b[^>]*>(.*?)</article>',
    r'<div\b[^>]*role="main"[^>]*>(.*)',
    r'<body\b[^>]*>(.*?)</body>',
)]


def html_text(src):
    for p in MAIN:
        m = p.search(src)
        if m:
            src = m.group(1)
            break
    src = re.sub(r'(?s)<(script|style|nav)\b[^>]*>.*?</\1>', ' ', src)
    src = re.sub(r'<[^>]+>', ' ', src)
    return html.unescape(src)


def md_text(src):
    src = re.sub(r'\A---\n.*?\n---\n', '', src, flags=re.S)
    src = re.sub(r'\{\{.*?\}\}', ' ', src, flags=re.S)
    return src


def sgml_text(src):
    src = re.sub(r'(?s)<!--.*?-->', ' ', src)
    return html.unescape(re.sub(r'<[^>]+>', ' ', src))


def po_text(src):
    out, cur = [], None
    for line in src.splitlines():
        if line.startswith('msgstr '):
            cur = [line[7:]]
        elif cur is not None and line.startswith('"'):
            cur.append(line)
        else:
            if cur:
                out.append(''.join(s.strip()[1:-1] for s in cur))
            cur = None
    if cur:
        out.append(''.join(s.strip()[1:-1] for s in cur))
    return '\n'.join(s.replace('\\n', ' ').replace('\\"', '"') for s in out if s)


TEXT = {'.html': html_text, '.htm': html_text, '.sgml': sgml_text, '.po': po_text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--domain', action='store_true')
    ap.add_argument('--ext', default='.html,.md')
    ap.add_argument('--exclude', default=None)
    a = ap.parse_args()
    exts = tuple(a.ext.split(','))
    skip = re.compile(a.exclude) if a.exclude else None
    os.makedirs(a.out, exist_ok=True)
    pages, chars = 0, 0
    with open(os.path.join(a.out, a.name + '.txt'), 'w', encoding='utf-8') as o:
        for d, _, fs in sorted(os.walk(a.src)):
            for f in sorted(fs):
                path = os.path.join(d, f)
                if not f.endswith(exts) or (skip and skip.search(path)):
                    continue
                src = open(path, encoding='utf-8', errors='ignore').read()
                t = TEXT.get(os.path.splitext(f)[1], md_text)(src)
                t = re.sub(r'[ \t\r]+', ' ', t)
                t = re.sub(r'\n\s*\n+', '\n', t).replace('\f', ' ')
                n = len(JA.findall(t))
                if n == 0:
                    continue
                o.write(t + '\f')
                pages += 1; chars += n
    meta_path = os.path.join(a.out, 'corpora.json')
    meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
    meta[a.name] = {'kind': 'domain' if a.domain else 'base', 'pages': pages, 'ja_chars': chars,
                    'source': os.path.abspath(a.src)}
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{a.name}: {meta[a.name]["kind"]} {pages} ページ 日本語 {chars} 字')


if __name__ == '__main__':
    main()
