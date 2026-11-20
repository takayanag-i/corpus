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

### コマンドとエラー

コマンドの一覧と、表示されるエラーと対処は [SKILL.md](SKILL.md) の「コマンド一覧」と「トラブルシューティング」を参照。
