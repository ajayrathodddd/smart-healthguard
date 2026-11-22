
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.database import database


router = APIRouter(
    prefix="/api/history",
    tags=["Analysis History"],
)

history_collection = database["analysis_history"]


class HistoryCreate(BaseModel):
    analysis_type: str
    title: str
    summary: str = ""
    details: dict = Field(default_factory=dict)


@router.post("/")
async def save_analysis_history(
    record: HistoryCreate,
    current_user: dict = Depends(get_current_user),
):
    allowed_types = {
        "medicine",
        "ocr",
        "risk",
    }

    if record.analysis_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid analysis type.",
        )

    history_record = {
        "user_id": current_user["id"],
        "analysis_type": record.analysis_type,
        "title": record.title[:200],
        "summary": record.summary[:1000],
        "details": record.details,
        "created_at": datetime.now(timezone.utc),
    }

    result = await history_collection.insert_one(history_record)

    return {
        "success": True,
        "message": "Analysis saved to history.",
        "id": str(result.inserted_id),
    }


@router.get("/")
async def get_analysis_history(
    search: str = Query("", max_length=100),
    analysis_type: str = Query("all"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    query = {
        "user_id": current_user["id"],
    }

    if analysis_type != "all":
        query["analysis_type"] = analysis_type

    if search.strip():
        query["title"] = {
            "$regex": search.strip(),
            "$options": "i",
        }

    cursor = (
        history_collection
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    records = []

    async for record in cursor:
        record["id"] = str(record.pop("_id"))
        records.append(record)

    total = await history_collection.count_documents(query)

    return {
        "success": True,
        "total": total,
        "records": records,
    }


@router.delete("/{history_id}")
async def delete_analysis_history(
    history_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(history_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid history ID.",
        )

    result = await history_collection.delete_one(
        {
            "_id": ObjectId(history_id),
            "user_id": current_user["id"],
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="History record not found.",
        )

    return {
        "success": True,
        "message": "History record deleted.",
    }
