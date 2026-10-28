from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    source_lang: str  # 'en' or 'sw'


class TranslateResponse(BaseModel):
    original: str
    original_lang: str
    translated: str
    translated_lang: str
