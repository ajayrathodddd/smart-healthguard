from pydantic import BaseModel


class VoiceExplanationRequest(BaseModel):
    medicine_name: str
    language: str

    composition: str = ""
    description: str = ""
    side_effects: str = ""
    warnings: str = ""