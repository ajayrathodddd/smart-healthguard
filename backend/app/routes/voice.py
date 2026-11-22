from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.voice import VoiceExplanationRequest
from app.services.voice_service import create_voice_explanation
from app.utils.languages import get_supported_languages


router = APIRouter(
    prefix="/api/voice",
    tags=["Voice Assistant"],
)


@router.get("/languages")
async def get_languages():
    return {
        "languages": get_supported_languages()
    }


@router.post("/explain")
async def explain_medicine(request: VoiceExplanationRequest):

    try:
        result = await create_voice_explanation(
            medicine_name=request.medicine_name,
            language=request.language,
            composition=request.composition,
            description=request.description,
            side_effects=request.side_effects,
            warnings=request.warnings,
        )

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Unsupported language.",
            )

        return result

    except HTTPException:
        raise

    except Exception as error:
        import traceback

        print("========== VOICE ERROR ==========")
        print("Error type:", type(error).__name__)
        print("Error:", repr(error))
        traceback.print_exc()
        print("=================================")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate the medicine voice explanation.",
        )


@router.get("/audio/{filename}")
async def get_audio(filename: str):

    audio_path = Path("app/audio") / filename

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found.",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )