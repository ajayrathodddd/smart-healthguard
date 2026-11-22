from typing import Optional

from pydantic import BaseModel, Field


class MedicineCreate(BaseModel):
    name: str = Field(..., min_length=1)
    generic_name: Optional[str] = None
    manufacturer: Optional[str] = None
    composition: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    description: Optional[str] = None


class MedicineResponse(MedicineCreate):
    id: str