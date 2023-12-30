from fastapi import FastAPI
from app.routers import openai

def create_app():
    
    app = FastAPI(
        title="AI Services",
        description="AI services are applications or software that use artificial intelligence to perform tasks, such as image recognition or natural language processing.",
        version="2.0",
        openapi_url="/api/v2/openapi.json",
    )

    app.include_router(openai.router, prefix="/open-ai")
    # app.include_router(generate_audio.router, prefix="/audio")

    return app