from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.services.risk_detection_service import calculate_medicine_risk


router = APIRouter(
    prefix="/api/risk",
    tags=["Risk Detection"],
)


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            str(item)
            for item in value
            if item
        )

    if isinstance(value, dict):
        return ", ".join(
            f"{key}: {value}"
            for key, value in value.items()
            if value
        )

    return str(value).strip()


def build_risk_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert the current HealthGuard OCR/medicine response
    into the field structure expected by calculate_medicine_risk().
    """

    medicine = data.get("medicine")

    if not isinstance(medicine, dict):
        medicine = {}

    identity = data.get("ocr_identity")

    if not isinstance(identity, dict):
        identity = {}

    # ---------------------------------------------------------
    # Identity
    # ---------------------------------------------------------

    brand_name = (
        medicine.get("brand_name")
        or identity.get("brand_name")
        or data.get("medicine_name")
        or ""
    )

    generic_name = (
        medicine.get("generic_name")
        or identity.get("generic_name")
        or medicine.get("active_ingredient")
        or ""
    )

    strength = (
        medicine.get("strength")
        or identity.get("strength")
        or medicine.get("ocr_strength")
        or ""
    )

    dosage_form = (
        medicine.get("dosage_form")
        or identity.get("dosage_form")
        or medicine.get("ocr_dosage_form")
        or ""
    )

    # ---------------------------------------------------------
    # Manufacturer
    # ---------------------------------------------------------

    manufacturer = (
        medicine.get("manufacturer")
        or medicine.get("manufacturer_name")
        or ""
    )

    # ---------------------------------------------------------
    # Pack information
    # ---------------------------------------------------------

    pack_size = (
        medicine.get("pack_size")
        or medicine.get("package_size")
        or medicine.get("quantity")
        or ""
    )

    # If no separate pack size exists, preserve the
    # verified medicine strength as product information.
    if not pack_size:
        pack_size = strength

    # ---------------------------------------------------------
    # Match / verification information
    # ---------------------------------------------------------

    match_type = (
        medicine.get("ocr_match_type")
        or data.get("match_type")
        or ""
    )

    rxcui = (
        medicine.get("rxcui")
        or medicine.get("rxnorm_id")
        or ""
    )

    # ---------------------------------------------------------
    # Build the structure expected by the existing
    # calculate_medicine_risk() function.
    # ---------------------------------------------------------

    return {
        "indian_brand": brand_name,
        "brand_name": brand_name,
        "medicine_name": brand_name,

        "indian_generic": generic_name,
        "generic_name": generic_name,
        "active_ingredient": generic_name,

        "strength": strength,
        "ocr_strength": strength,

        "manufacturer": manufacturer,
        "indian_manufacturer": manufacturer,

        "indian_medicine_type": dosage_form,
        "medicine_type": dosage_form,
        "dosage_form": dosage_form,

        "indian_pack_size": pack_size,
        "pack_size": pack_size,

        "indian_discontinued": (
            medicine.get("is_discontinued")
            or medicine.get("indian_discontinued")
            or False
        ),

        "is_discontinued": (
            medicine.get("is_discontinued")
            or False
        ),

        "source": (
            medicine.get("sources")
            or medicine.get("source")
            or data.get("sources")
            or []
        ),

        "warnings": (
            medicine.get("warnings")
            or data.get("warnings")
            or []
        ),

        "indian_side_effects": (
            medicine.get("side_effects")
            or data.get("side_effects")
            or []
        ),

        "adverse_reactions": (
            medicine.get("adverse_reactions")
            or []
        ),

        "indian_drug_interactions": (
            medicine.get("interactions")
            or data.get("interactions")
            or []
        ),

        "drug_interactions": (
            medicine.get("drug_interactions")
            or []
        ),

        "rxcui": rxcui,
        "rxnorm_id": rxcui,

        "ocr_match_type": match_type,

        "extracted_text": data.get(
            "extracted_text",
            "",
        ),
    }


@router.post("/analyze")
async def analyze_medicine_risk(
    data: Dict[str, Any],
):
    """
    Analyze medicine/package verification risk.

    This endpoint does not diagnose disease and does not
    determine whether a product is definitively genuine
    or counterfeit.
    """

    try:
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid risk analysis data.",
            )

        risk_input = build_risk_input(data)

        risk_result = calculate_medicine_risk(
            risk_input
        )

        return {
            "success": True,
            "risk": risk_result,
            "medicine": {
                "brand_name": risk_input.get(
                    "brand_name",
                    "",
                ),
                "generic_name": risk_input.get(
                    "generic_name",
                    "",
                ),
                "strength": risk_input.get(
                    "strength",
                    "",
                ),
                "manufacturer": risk_input.get(
                    "manufacturer",
                    "",
                ),
                "dosage_form": risk_input.get(
                    "dosage_form",
                    "",
                ),
                "rxcui": risk_input.get(
                    "rxcui",
                    "",
                ),
            },
            "educational_notice": (
                "This is an informational screening result "
                "based on available medicine data and predefined "
                "rules. It does not prove that a medicine is "
                "genuine or counterfeit and is not medical advice."
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "[HealthGuard Risk] Analysis failed:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to calculate medicine risk.",
        )