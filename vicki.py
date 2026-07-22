import json
import re
import urllib.error
import urllib.request

from config import LLAMA_API_URL, LLAMA_MODEL


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def ask_vicki(prompt, timeout=120, max_tokens=160):
    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": str(prompt).strip(),
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }

    request = urllib.request.Request(
        LLAMA_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"llama.cpp HTTP {exc.code}: {details[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"llama.cpp is unavailable: {exc}"
        ) from exc

    try:
        message = result["choices"][0]["message"]
        text = message.get("content", "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Invalid llama.cpp response: "
            + json.dumps(result, ensure_ascii=False)[:500]
        ) from exc

    if not text:
        raise RuntimeError("llama.cpp returned no response text")

    return text
