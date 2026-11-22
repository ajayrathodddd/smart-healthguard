from datetime import datetime, timezone

from bson import ObjectId

from app.database import database
from app.models.medicine import MedicineCreate
from app.services.external_medicine_service import search_external_medicine


medicine_collection = database["medicines"]


async def create_medicine(medicine: MedicineCreate):
    medicine_data = medicine.model_dump()

    medicine_data["created_at"] = datetime.now(timezone.utc)
    medicine_data["updated_at"] = datetime.now(timezone.utc)

    result = await medicine_collection.insert_one(medicine_data)

    return {
        "id": str(result.inserted_id),
        **medicine_data,
    }


async def get_medicine_by_id(medicine_id: str):
    if not ObjectId.is_valid(medicine_id):
        return None

    medicine = await medicine_collection.find_one(
        {"_id": ObjectId(medicine_id)}
    )

    if medicine is None:
        return None

    medicine["id"] = str(medicine["_id"])
    del medicine["_id"]

    return medicine


async def get_all_medicines():
    medicines = []

    cursor = medicine_collection.find().sort("created_at", -1)

    async for medicine in cursor:
        medicine["id"] = str(medicine["_id"])
        del medicine["_id"]
        medicines.append(medicine)

    return medicines


async def search_medicine(medicine_name: str):
    """
    Search medicine in MongoDB first.

    If the medicine is not available locally,
    search the external RxNorm medicine database.
    """

    search_name = medicine_name.strip()

    if not search_name:
        return {
            "source": "none",
            "results": [],
        }

    # 1. Search MongoDB
    medicines = await medicine_collection.find(
        {
            "$or": [
                {
                    "name": {
                        "$regex": search_name,
                        "$options": "i",
                    }
                },
                {
                    "generic_name": {
                        "$regex": search_name,
                        "$options": "i",
                    }
                },
            ]
        }
    ).to_list(length=20)

    if medicines:
        results = []

        for medicine in medicines:
            medicine["id"] = str(medicine["_id"])
            del medicine["_id"]
            results.append(medicine)

        return {
            "source": "mongodb",
            "results": results,
        }

    # 2. MongoDB did not find it → external lookup
    external_results = await search_external_medicine(search_name)

    if external_results:
        return {
            "source": "rxnorm",
            "results": external_results,
        }

    # 3. Nothing found
    return {
        "source": "none",
        "results": [],
    }