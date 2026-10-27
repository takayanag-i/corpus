# 語の一覧: ファイル一覧の日本語を形態素解析し、全品詞の語と、用言を使う場面の句を出現回数の順に TSV で出す
# 使い方: python3 terms.py <ファイル一覧> [--min 2] [--pos 動詞,動詞句] [--expect 語の一覧]
#   標準出力に「出現回数<TAB>品詞<TAB>語<TAB>照合形<TAB>ファイル数<TAB>ファイル（最初の 3 つ）<TAB>最初の箇所」
#   品詞の列:
#     名詞連: 名詞・接頭辞・接尾辞の連なり。複合語
#     名詞ほか: 1 語ずつ。名詞・動詞・形容詞・形状詞・副詞・連体詞・接続詞・感動詞・代名詞・助詞・助動詞・接頭辞・接尾辞・記号
#     動詞句・形容詞句・形状詞句: 前の名詞と助詞を添えた句（例: ボタンを押す）と、後ろの名詞を添えた句（例: 太い線）
#   連用形の動詞に続く動詞は 1 語の複合動詞にする（例: 読み込み直す）
#   語は書字形の基本形。活用形の違いは 1 つにまとめる。照合形は corpus_count.py に渡す形で、用言は活用で変わらない語幹にする
#   補助記号と空白は語に入れない
#   --expect: 1 行 1 語の一覧。ファイルに語の切れ目で現れるのに、語の列にも照合形の列にも無い語を、標準エラーに「漏れ<TAB>語」で返し、終了コードを 1 にする
# 要るもの: pip install fugashi unidic-lite
import sys, re, collections, argparse, types
import fugashi

ap = argparse.ArgumentParser()
ap.add_argument('files')
ap.add_argument('--min', type=int, default=2)
ap.add_argument('--pos', help='表示する品詞をカンマで並べる。省くと全品詞')
ap.add_argument('--expect')
a = ap.parse_args()
JA = re.compile(r'[぀-ヿ一-鿿]')
SEG = re.compile(r'[぀-ヿ一-鿿０-ｚー・々ー0-9A-Za-z]+')
NOUN_RUN = ('名詞', '接尾辞', '接頭辞')
YOGEN = ('動詞', '形容詞', '形状詞')
SKIP = ('補助記号', '空白')
PARTICLE = ('格助詞', '係助詞', '副助詞')
SUBJECT = ('が', 'は', 'も')
HONORIFIC = ('くださる', '下さる', 'なさる')
tag = fugashi.Tagger()
cnt, files, first, match = collections.Counter(), collections.defaultdict(set), {}, {}
texts = []


def base(t):
    f = t.feature
    b = getattr(f, 'orthBase', None)
    return b if b and b != '*' else t.surface


def stem(t):
    b, ct = base(t), t.feature.cType or ''
    if ct.startswith(('五段', '上一段', '下一段', 'カ行変格', '形容詞')):
        s = b[:-1]
    elif ct.startswith('サ行変格'):
        s = b[:-2]
    else:
        s = b
    n = 0
    while n < min(len(s), len(t.surface)) and s[n] == t.surface[n]:
        n += 1
    return s[:n] or t.surface


def tok(surface, f):
    return types.SimpleNamespace(surface=surface, feature=f)


def merge(toks):
    out = []
    for t in toks:
        prev = out[-1] if out else None
        if prev and prev.feature.pos1 == '動詞' and t.feature.pos1 == '動詞' and base(t) not in HONORIFIC \
                and (prev.feature.cForm or '').startswith('連用形'):
            f = types.SimpleNamespace(pos1='動詞', pos2='一般', orthBase=prev.surface + base(t),
                                      cType=t.feature.cType, cForm=t.feature.cForm)
            out[-1] = tok(prev.surface + t.surface, f)
        else:
            out.append(t)
    return out


def bounds(toks):
    ends, pos = set(), 0
    starts = {0}
    for t in toks:
        pos += len(t.surface)
        ends.add(pos); starts.add(pos)
    return starts, ends


def head(run):
    return ''.join(x.surface for x in run[-2:]) if run[-1].feature.pos1 == '接尾辞' and len(run) > 1 else run[-1].surface


def add(pos, word, m, where, f):
    if not JA.search(word):
        return
    k = (pos, word)
    cnt[k] += 1
    files[k].add(f)
    first.setdefault(k, where)
    if k in match:
        a_, b_ = match[k], m
        n = 0
        while n < min(len(a_), len(b_)) and a_[n] == b_[n]:
            n += 1
        match[k] = a_[:n] or a_
    else:
        match[k] = m


def scan(toks, where, f):
    run = []

    def flush():
        w = ''.join(x.surface for x in run)
        if len(run) >= 2:
            add('名詞連', w, w, where, f)
    for i, t in enumerate(toks):
        p = t.feature.pos1
        if p in SKIP:
            flush(); run = []
            continue
        add(p, base(t), stem(t) if p in YOGEN else t.surface, where, f)
        if p in NOUN_RUN:
            run.append(t)
            continue
        flush()
        run = []
        if p not in YOGEN:
            continue
        if i >= 2 and toks[i - 1].feature.pos1 == '助詞' and toks[i - 1].feature.pos2 in PARTICLE \
                and (p == '動詞' or toks[i - 1].surface in SUBJECT):
            j = i - 2
            back = []
            while j >= 0 and toks[j].feature.pos1 in NOUN_RUN:
                back.insert(0, toks[j]); j -= 1
            if back:
                h, pa = head(back), toks[i - 1].surface
                add(p + '句', h + pa + base(t), h + pa + stem(t), where, f)
        k = i + 1
        mid = ''
        if p == '形状詞' and k < len(toks) and toks[k].surface in ('な', 'の'):
            mid = toks[k].surface; k += 1
        elif p != '形状詞' and not (t.feature.cForm or '').startswith('連体形'):
            continue
        if k < len(toks) and toks[k].feature.pos1 == '名詞':
            w = t.surface + mid + toks[k].surface
            add(p + '句', w, w, where, f)
    flush()


for f in open(a.files, encoding='utf-8').read().split():
    try:
        lines = open(f, encoding='utf-8').read().split('\n')
    except (OSError, UnicodeDecodeError):
        continue
    for ln, line in enumerate(lines, 1):
        if not JA.search(line):
            continue
        for seg in SEG.findall(line):
            raw = list(tag(seg))
            texts.append((seg, *bounds(raw)))
            scan(merge(raw), f'{f}:{ln}', f)

want = set(a.pos.split(',')) if a.pos else None
for (pos, w), c in cnt.most_common():
    if c >= a.min and (want is None or pos in want):
        fs = sorted(files[(pos, w)])
        print(f'{c}\t{pos}\t{w}\t{match[(pos, w)]}\t{len(fs)}\t{",".join(fs[:3])}\t{first[(pos, w)]}')

if a.expect:
    known = {w for _, w in cnt} | set(match.values())

    def as_word(w):
        for seg, starts, ends in texts:
            i = seg.find(w)
            while i >= 0:
                if i in starts and i + len(w) in ends:
                    return True
                i = seg.find(w, i + 1)
        return False
    missed = [w for w in dict.fromkeys(open(a.expect, encoding='utf-8').read().split()) if w not in known and as_word(w)]
    for w in missed:
        print(f'漏れ\t{w}', file=sys.stderr)
    sys.exit(1 if missed else 0)
