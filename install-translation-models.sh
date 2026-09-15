#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten; keine root-Installation der Modelle."
  exit 1
fi

BASE_DIR="${VICKY_TRANSLATION_MODELS:-$HOME/translation-models}"
PYTHON_BIN="${VICKY_PYTHON:-$HOME/vicky8/.venv/bin/python}"
PIP_BIN="${VICKY_PIP:-$HOME/vicky8/.venv/bin/pip}"
CT2_BIN="${VICKY_CT2_TRANSFORMERS_CONVERTER:-$HOME/vicky8/.venv/bin/ct2-transformers-converter}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "FEHLER: Python-Umgebung nicht gefunden: $PYTHON_BIN"
  echo "Zuerst Vicky-Abhängigkeiten installieren."
  exit 1
fi

if [[ ! -x "$PIP_BIN" ]]; then
  echo "FEHLER: pip nicht gefunden: $PIP_BIN"
  exit 1
fi

if [[ ! -x "$CT2_BIN" ]]; then
  echo "FEHLER: CTranslate2-Konverter nicht gefunden: $CT2_BIN"
  echo "Prüfen: $PYTHON_BIN -m pip install -r ~/vicky8/requirements.txt"
  exit 1
fi

# ct2-transformers-converter benötigt PyTorch zum Laden der Hugging-Face-Modelle.
# PyTorch wird nur für den Konvertierungsschritt gebraucht; die fertigen
# CTranslate2-Modelle laufen anschließend ohne torch.
if ! "$PYTHON_BIN" -c 'import torch' >/dev/null 2>&1; then
  echo "==> Installiere PyTorch für die Modell-Konvertierung"
  "$PIP_BIN" install torch
fi

mkdir -p "$BASE_DIR"

MODELS=(
  "de-fr:Helsinki-NLP/opus-mt-de-fr"
  "en-fr:Helsinki-NLP/opus-mt-en-fr"
  "fr-de:Helsinki-NLP/opus-mt-fr-de"
  "en-de:Helsinki-NLP/opus-mt-en-de"
  "fr-en:Helsinki-NLP/opus-mt-fr-en"
  "de-en:Helsinki-NLP/opus-mt-de-en"
)

for entry in "${MODELS[@]}"; do
  pair="${entry%%:*}"
  model="${entry#*:}"
  target="$BASE_DIR/opus-mt-$pair"

  # MarianTokenizer braucht neben dem CT2-Modell auch die originalen
  # SentencePiece-Dateien und vocab.json. Fehlt eine davon, muss das Modell
  # repariert/neu konvertiert werden.
  if [[ -d "$target" \
        && -f "$target/model.bin" \
        && -f "$target/source.spm" \
        && -f "$target/target.spm" \
        && -f "$target/vocab.json" ]]; then
    echo "OK: $pair bereits vollständig vorhanden -> $target"
    continue
  fi

  echo
  echo "==> Installiere/repariere $pair aus $model"
  rm -rf "$target.tmp"
  "$CT2_BIN" \
    --model "$model" \
    --output_dir "$target.tmp" \
    --quantization int8 \
    --copy_files source.spm target.spm vocab.json \
    --force

  rm -rf "$target"
  mv "$target.tmp" "$target"
  echo "Fertig: $target"
done

echo
echo "Installierte Übersetzungsmodelle:"
find "$BASE_DIR" -maxdepth 1 -mindepth 1 -type d -name 'opus-mt-*' -printf '  %f\n' | sort

echo
echo "Hinweis: Wenn ein Modell später fehlt oder eine Übersetzung fehlschlägt,"
echo "zeigt Vicky weiterhin die Originalsprache statt die Nachricht zu unterdrücken."
