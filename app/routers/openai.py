# Importing required libraries and modules
from typing import Annotated
import app.services.openai
from fastapi import APIRouter, File, UploadFile, Form
from app.schemas.openai_schemas import TextCompletion, GenerateAudio, PronunciationScoreResponse

# Creating an instance of the Router for the FASTAPI API endpoints
router = APIRouter()

# Creating an instance of the OpenAIService class from app.services.openai module
openAIService = app.services.openai.OpenAIService()

@router.post("/text_completion", tags=["Create lession"], description="Creates a completion for the provided prompt and parameters")
async def text_completion(req: TextCompletion):

    return openAIService.text_completion(req.prompt, req.template_type) 

# Defining a POST endpoint route at /generate_audio to receive and audio url based on a text prompt
@router.post("/generate_audio", tags=["Generate audio"], description="Creates an audio using openai.")
async def generate_audio(req: GenerateAudio):

    return {"audio_url": openAIService.generate_audio(req.text)}

# Defining a POST endpoint route at /transcribe to receive audio file data and transcribing it using GPT-3(openaiservice)
@router.post("/transcribe", tags=["Convert audio to text"], description="Transcribes audio into the input language.")
async def transcribe(audio_file: UploadFile = File(...)):

    transcript, _ =  openAIService.transcribe(audio_file)

    return {"transcript": transcript}


# Defining a POST endpoint route at /pronunciation_score to receive audio file and original script data then pronunciation score it using GPT-3(openaiservice)
@router.post("/pronunciation_score", tags=["Pronunciation Score"], description=".", response_model=PronunciationScoreResponse)
async def pronunciation_score(original_script: Annotated[str, Form()], audio_file: UploadFile = File(...)):

    original_script, text_transcribed, percent_diff, html_output = openAIService.pronunciation_score(original_script , audio_file)

    return {"original_script": original_script,
            "text_transcribed": text_transcribed,
            "percent_diff": percent_diff,
            "html_output": html_output
            }