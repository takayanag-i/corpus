#!/usr/bin/env bash
set -euo pipefail
OUT=${1:?出力フォルダを指定する}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT" && cd "$OUT"
if [ ! -d mdn ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/mdn/translated-content.git mdn
  (cd mdn && git sparse-checkout set files/ja/web/api files/ja/glossary files/ja/web/css files/ja/learn)
fi
if [ ! -d otel ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/open-telemetry/opentelemetry.io.git otel
  (cd otel && git sparse-checkout set content/ja)
fi
python3 -I "$HERE/build_corpus.py" mdn mdn/files/ja . --ext .md
python3 -I "$HERE/build_corpus.py" otel otel/content/ja . --ext .md
if [ ! -d pgsql ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/pgsql-jp/jpug-doc.git pgsql
  (cd pgsql && git sparse-checkout set doc/src/sgml)
fi
if [ ! -d k8s ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/kubernetes/website.git k8s
  (cd k8s && git sparse-checkout set content/ja)
fi
[ -d pydoc ] || git clone -q --depth 1 https://github.com/python/python-docs-ja.git pydoc
python3 -I "$HERE/build_corpus.py" postgresql pgsql/doc/src/sgml . --ext .sgml
python3 -I "$HERE/build_corpus.py" kubernetes k8s/content/ja . --ext .md
python3 -I "$HERE/build_corpus.py" python pydoc . --ext .po --exclude '/\.git/'
