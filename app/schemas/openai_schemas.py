from typing import Optional
from pydantic import BaseModel

class TextCompletion(BaseModel):
    prompt: str
    template_type: Optional[int] = None

class GenerateAudio(BaseModel):
    text: str

class PronunciationScore(BaseModel):
    orginal_script: str

class PronunciationScoreResponse(BaseModel):
    original_script: str
    text_transcribed: str
    percent_diff: float
    html_output: str