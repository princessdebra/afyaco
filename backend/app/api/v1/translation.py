from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, get_current_user
from app.schemas.translation import TranslateRequest, TranslateResponse
from app.services.translation import translate

router = APIRouter(prefix="/translate", tags=["translate"])


@router.post("", response_model=TranslateResponse)
async def translate_text(
    payload: TranslateRequest,
    current: CurrentUser = Depends(get_current_user),
) -> TranslateResponse:
    target_lang = "sw" if payload.source_lang == "en" else "en"
    translated = await translate(payload.text, payload.source_lang)
    return TranslateResponse(
        original=payload.text,
        original_lang=payload.source_lang,
        translated=translated,
        translated_lang=target_lang,
    )
