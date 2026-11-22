from fastapi import APIRouter, HTTPException, Query

from app.models.medicine import MedicineCreate, MedicineResponse
from app.services.medicine_service import (
    create_medicine,
    get_all_medicines,
    get_medicine_by_id,
    search_medicine,
)
from app.services.drug_information_service import (
    get_real_medicine_information,
)

from app.services.risk_detection_service import (
    calculate_medicine_risk,
)


router = APIRouter(
    prefix="/api/medicines",
    tags=["Medicines"],
)


@router.post("/")
async def add_medicine(medicine: MedicineCreate):
    return await create_medicine(medicine)


@router.get("/")
async def list_medicines():
    return await get_all_medicines()


@router.get("/search")
async def search_medicine_endpoint(
    name: str = Query(..., min_length=1)
):
    result = await search_medicine(name)

    if not result["results"]:
        raise HTTPException(
            status_code=404,
            detail=f"No medicine information found for '{name}'.",
        )

    return result

@router.get("/info")
async def get_real_medicine_info(
    name: str = Query(..., min_length=1)
):
    medicine = await get_real_medicine_information(name)

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail=f"No reliable medicine information found for '{name}'.",
        )

    risk_assessment = calculate_medicine_risk(medicine)

    return {
        **medicine,
        "risk_assessment": risk_assessment,
    }


@router.get("/{medicine_id}")
async def get_medicine(medicine_id: str):
    medicine = await get_medicine_by_id(medicine_id)

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found",
        )

    return medicine
