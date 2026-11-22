
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_assistant_service import ask_ai_assistant


router = APIRouter(
    prefix="/api/ai-assistant",
    tags=["AI Assistant"],
)


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    try:
        answer = await ask_ai_assistant(request.question)

        return {
            "answer": answer,
            "status": "success",
        }

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        )
