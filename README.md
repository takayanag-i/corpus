# corpus

## 使用技術一覧

- Python
- Bash
- Git
- fugashi
- unidic-lite
- MediaWiki API
- Claude Code

## 目次

1. [プロジェクトについて](#プロジェクトについて)
2. [環境](#環境)
3. [ディレクトリ構成](#ディレクトリ構成)
4. [開発環境構築](#開発環境構築)
5. [トラブルシューティング](#トラブルシューティング)

## プロジェクト名

corpus

## プロジェクトについて

日本語の文書とコードで、カタカナ語が一般に使われる箇所を和語・漢語の造語で書いた語を見つけ、コーパスで一般的な言い方を確認してから置き換える Claude Code のスキルである。例: 画素→ピクセル、道具→ツール、つまみ→スライダー。

手順と判定の基準は `SKILL.md` を参照。決めた語の一覧は `references/terms.csv`、文脈ごとのコーパスの重みは `references/weights.csv` を参照。

## 環境

| 言語・ライブラリ | バージョン |
| --- | --- |
| Python | 3.10 以上 |
| fugashi | 指定なし |
| unidic-lite | 指定なし |

Python のバージョンは `SKILL.md` の記載である。このリポジトリはロックファイル、ビルド定義、Dockerfile を含まず、fugashi と unidic-lite のバージョンは固定していない。動作を確認した環境は Python 3.13.18、fugashi 1.5.2、unidic-lite 1.0.8 である。

## ディレクトリ構成

```
.
├── README.md
├── SKILL.md
├── references
│   ├── terms.csv
│   └── weights.csv
└── scripts
    ├── apply_terms.py
    ├── build_corpus.py
    ├── corpus_count.py
    ├── fetch_corpora.sh
    └── terms.py
```

## 開発環境構築

### 起動

corpus はアプリケーションを起動しない。このリポジトリの中身を `.claude/skills/corpus/` に配置すると、Claude Code から `/corpus` で呼び出せる。

`terms.py` が使う形態素解析器を仮想環境にインストールし、基本のコーパスを作成する。コーパスのダウンロードは約 400MB で、所要時間は数分である。

```bash
python3 -m venv .venv
.venv/bin/pip install fugashi unidic-lite
bash scripts/fetch_corpora.sh <コーパスのフォルダ>
```

### 動作確認

Wikipedia への問い合わせを省いて 1 組をカウントし、列名が `組`・`句`・`加重シェア`・`根拠`・`判定`・`段階` で始まる TSV が表示されることを確認する。

```bash
CORPUS_DIR=<コーパスのフォルダ> python3 scripts/corpus_count.py --no-wiki ピクセル数 画素数
```

### 停止

常駐するプロセスは無い。`fetch_corpora.sh` と `corpus_count.py` の実行を中断するときは、実行した端末で Ctrl+C を入力する。

### 環境変数の一覧

| 変数名 | 役割 | 既定値 |
| --- | --- | --- |
| CORPUS_DIR | `corpus_count.py` が参照するコーパスのフォルダ。`corpora.json`、各コーパスの `.txt`、`wiki_cache.json` を置く | `.` |

### コマンド一覧

スクリプトは直接実行する。元のコマンドの列は、スクリプトが内部で実行するコマンドである。

| コマンド | 実行する処理 | 元のコマンド |
| --- | --- | --- |
| `bash scripts/fetch_corpora.sh <出力フォルダ>` | MDN・OpenTelemetry・PostgreSQL・Kubernetes・Python の日本語版を取得し、基本のコーパスを作成する | `git clone --depth 1` と `python3 scripts/build_corpus.py` |
| `python3 scripts/build_corpus.py <名前> <元のフォルダ> <コーパスのフォルダ> [--domain] [--ext .html,.md] [--exclude 正規表現]` | 文書のフォルダから 1 つのコーパスを作成し、`corpora.json` に登録する。`--domain` でドメイン固有のコーパスにする | − |
| `python3 scripts/terms.py <ファイル一覧> [--min 2] [--pos 品詞,...] [--expect 語の一覧]` | ファイル一覧の日本語を形態素解析し、全品詞の語と用言の句を出現回数の順に TSV で出力する | − |
| `python3 scripts/corpus_count.py [--context ui\|web\|prose] [--domain 名前=重み] [--min 10] [--absent-min 5] [--k 10] [--no-wiki] [--wiki-interval 3] 句 [句 ...]` | 句ごとに各コーパスの件数と加重シェアと判定を TSV で出力する | − |
| `python3 scripts/corpus_count.py --pairs pairs.tsv [同じオプション]` | TSV に並べた組をまとめてカウントする | − |
| `python3 scripts/apply_terms.py <ファイル一覧> <決まり.json> [--dry] [--quote-line 正規表現]` | 置き換えの決まりを上から順に適用する。`--dry` はファイルを書き換えず、変更する行数を出力する | − |

## トラブルシューティング

| 表示されるエラー | 原因 | 対処 |
| --- | --- | --- |
| `1: 出力フォルダを指定する` | `fetch_corpora.sh` の引数に出力フォルダが無い | 出力フォルダを引数に指定する |
| `corpora.json に無いコーパス: <名前>。build_corpus.py で作る` | `--domain` に指定したコーパスが `CORPUS_DIR` の `corpora.json` に無い | `build_corpus.py` に `--domain` を付けて登録するか、`CORPUS_DIR` の値を確認する |
| `weights.csv に文脈 <文脈> の行が無い` | `references/weights.csv` に `--context` の文脈の行が無い | `weights.csv` にその文脈の行を追加する |
| `Wikipedia API に 8 回続けて失敗した: <パラメータ>` | Wikipedia API が 429 か通信の失敗を 8 回続けて返した | 時間をおいて再実行するか、`--wiki-interval` を大きくする。`--no-wiki` を指定すると Wikipedia に問い合わせない |
| `漏れ<TAB><語>` と終了コード 1 | `--expect` の語がファイルに語として現れるのに、`terms.py` の一覧に無い | 一覧に目を通す前に `terms.py` の抽出を直す |
| `ModuleNotFoundError: No module named 'fugashi'` | `terms.py` を実行した Python に fugashi が無い | 仮想環境に `pip install fugashi unidic-lite` でインストールし、その Python で実行する |
