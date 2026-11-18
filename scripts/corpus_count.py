import os, sys, json, time, argparse, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.environ.get('CORPUS_DIR', '.')
CACHE = os.path.join(CORPUS_DIR, 'wiki_cache.json')
cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
UA = {'User-Agent': 'corpus-term-check/2.0 (corpus frequency check)'}
INTERVAL = 3.0


def api(params):
    url = 'https://ja.wikipedia.org/w/api.php?' + urllib.parse.urlencode({**params, 'format': 'json'})
    wait = 30
    for _ in range(8):
        try:
            res = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))
            time.sleep(INTERVAL)
            return res
        except urllib.error.HTTPError as e:
            after = e.headers.get('Retry-After') if e.code == 429 else None
            time.sleep(max(wait, int(after)) if after and after.isdigit() else wait)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(wait)
        wait *= 2
    raise SystemExit(f'Wikipedia API に 8 回続けて失敗した: {params}')


def save():
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


def wiki(q):
    if cache.get(q) is None:
        cache[q] = api({'action': 'query', 'list': 'search', 'srsearch': f'"{q}"', 'srinfo': 'totalhits',
                        'srprop': '', 'srlimit': 1})['query']['searchinfo']['totalhits']
        save()
    return cache[q]


def load_corpora(domains):
    meta_path = os.path.join(CORPUS_DIR, 'corpora.json')
    meta = json.load(open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
    unknown = [d for d in domains if d not in meta]
    if unknown:
        raise SystemExit(f'corpora.json に無いコーパス: {", ".join(unknown)}。build_corpus.py で作る')
    use = [n for n, m in meta.items() if m['kind'] == 'base' or n in domains]
    pages = {n: open(os.path.join(CORPUS_DIR, n + '.txt'), encoding='utf-8').read().split('\f') for n in use}
    return {n: [p for p in pages[n] if p] for n in use}


def load_weights(context, domains):
    w = {}
    for line in open(os.path.join(HERE, '..', 'references', 'weights.csv'), encoding='utf-8').read().splitlines()[1:]:
        ctx, corpus, weight = line.split(',')
        if ctx == context:
            w[corpus] = float(weight)
    if not w:
        raise SystemExit(f'weights.csv に文脈 {context} の行が無い')
    return {**w, **domains}


def count_local(q, corpora):
    parts = q.split('|')
    return {name: sum(1 for p in pages for x in parts if x in p) for name, pages in corpora.items()}


def count_wiki(q):
    return sum(wiki(x) for x in q.split('|'))


def shares(group, weights, k):
    names = list(next(iter(group.values())).keys())
    n = {c: sum(group[q][c] for q in group) for c in names}
    w = {c: weights.get(c, 0) * n[c] / (n[c] + k) for c in names if n[c] > 0}
    wsum = sum(w.values())
    return {q: round(sum(w[c] * group[q][c] / n[c] for c in w) / wsum, 3) if wsum else 0.0 for q in group}


def judge(group, sh, current, a):
    target = max((q for q in group if q != current), key=lambda q: sh[q])
    evidence = sum(sum(v.values()) for v in group.values())
    if sum(group[current].values()) == 0 and sum(group[target].values()) >= a.absent_min:
        return target, evidence, '置き換え'
    if evidence >= a.min and sh[target] >= 0.6:
        return target, evidence, '置き換え'
    if evidence >= a.min and sh[target] < 0.4:
        return target, evidence, '残す'
    return target, evidence, None


def main():
    global INTERVAL
    ap = argparse.ArgumentParser()
    ap.add_argument('phrases', nargs='*')
    ap.add_argument('--pairs')
    ap.add_argument('--context', default='prose', choices=['ui', 'web', 'prose'])
    ap.add_argument('--domain', action='append', default=[])
    ap.add_argument('--min', type=int, default=10)
    ap.add_argument('--absent-min', type=int, default=5)
    ap.add_argument('--k', type=float, default=10)
    ap.add_argument('--no-wiki', action='store_true')
    ap.add_argument('--wiki-interval', type=float, default=3.0)
    a = ap.parse_args()
    INTERVAL = a.wiki_interval
    domains = {}
    for d in a.domain:
        name, _, weight = d.partition('=')
        domains[name] = float(weight) if weight else 2.0
    corpora = load_corpora(domains)
    weights = load_weights(a.context, domains)
    if a.pairs:
        groups = []
        for line in open(a.pairs, encoding='utf-8'):
            p = [x for x in line.rstrip('\n').split('\t') if x]
            if len(p) >= 3:
                groups.append((p[0], p[1:]))
    else:
        groups = [('-', a.phrases)]
    cols = ['wiki', *corpora]
    print('\t'.join(['組', '句', '加重シェア', '根拠', '判定', '段階', *[f'{c}_件数' for c in cols]]))
    for name, qs in groups:
        current = qs[-1]
        group = {q: count_local(q, corpora) for q in qs}
        sh = shares(group, weights, a.k)
        target, evidence, verdict = judge(group, sh, current, a)
        stage = '1'
        if verdict is None and not a.no_wiki:
            group = {q: {'wiki': count_wiki(q), **group[q]} for q in qs}
            sh = shares(group, weights, a.k)
            target, evidence, verdict = judge(group, sh, current, a)
            stage = '2'
        verdict = verdict or ('割れ' if evidence >= a.min else '少ない')
        for q in qs:
            mark = verdict if q == target else ('今の語' if q == current else '')
            print('\t'.join([name, q, str(sh[q]), str(evidence), mark, stage,
                             *[str(group[q].get(c, '')) for c in cols]]), flush=True)


if __name__ == '__main__':
    main()
