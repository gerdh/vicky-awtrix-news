# Optional local AI importance sorter

Vicky can ask a local OpenAI-compatible model to reorder already-finished news
messages by importance. The model receives numbered, final display texts and
may return only a permutation of those numbers. It cannot rewrite, merge, add
or remove headlines. Invalid output or an unavailable endpoint leaves the
existing order unchanged.

The feature is opt-in. Without `VICKY_AI_IMPORTANCE_SORT=1`, Vicky performs no
AI request and keeps its deterministic source-diversified order.

## Tested Moon setup

The Davanod Raspberry Pi 5 Moon setup was validated with:

- 8 GB RAM
- `llama-server` bound only to `127.0.0.1:8080`
- Qwen2.5 1.5B Instruct GGUF, `Q4_K_M`
- one inference slot, 2,048-token context and four CPU threads

Build `llama-server` from the official llama.cpp repository and place the
local GGUF model at a Moon-local path. Do not copy model or service paths from
Montpellier.

The helper expects these defaults:

```text
$HOME/llama.cpp/build/bin/llama-server
$HOME/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

Override them when needed:

```bash
VICKY_LLAMA_SERVER=/local/path/llama-server \
VICKY_AI_MODEL_PATH=/local/path/model.gguf \
bash scripts/install-local-ai-sorter-service.sh
```

With the default paths:

```bash
bash scripts/install-local-ai-sorter-service.sh
sudo systemctl enable --now vicky-llama-sorter.service
curl -fsS http://127.0.0.1:8080/health
sudo systemctl restart awtrix-news.service
```

Expected health response:

```json
{"status":"ok"}
```

Verify a bulletin after pressing the left refresh button:

```bash
journalctl -u awtrix-news --since "3 minutes ago" --no-pager |
grep -E "AI importance|button bulletin|publish vicky_news"
```

`AI importance sort changed order` or `priority/order unchanged` confirms that
the sorter is active. The right button continues to cycle the Vicky output
language; the left button refreshes without changing it.
