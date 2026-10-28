import json

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

LANG_NAME = {"en": "English", "sw": "Swahili"}


async def translate(text: str, source_lang: str) -> str:
    """Translate `text` from `source_lang` ('en' or 'sw') to the other
    language, via a self-hosted Qwen model on the devserver's Ollama
    instance. CPU-only (num_gpu=0) — see config.py's comment on why.
    """
    if source_lang not in LANG_NAME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "source_lang must be 'en' or 'sw'")
    target_lang = "sw" if source_lang == "en" else "en"

    prompt = (
        f"Translate the following {LANG_NAME[source_lang]} text to {LANG_NAME[target_lang]}. "
        f"Reply with ONLY the translation, no explanation, no quotes.\n\n{text}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_translate_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_gpu": 0, "temperature": 0.1},
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Translation is temporarily unavailable"
        ) from exc

    translated = data.get("response", "").strip()
    if not translated:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Translation is temporarily unavailable")
    return translated
