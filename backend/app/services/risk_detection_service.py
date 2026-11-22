from typing import Any


def _is_missing(value: Any) -> bool:
    """Return True when a field has no useful information."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, list):
        return len(value) == 0

    if isinstance(value, dict):
        return len(value) == 0

    return False


def _is_discontinued(value: Any) -> bool:
    """Check common discontinued-status values."""

    if value is None:
        return False

    value = str(value).strip().lower()

    return value in {
        "true",
        "yes",
        "1",
        "discontinued",
    }


def _add_indicator(
    indicators: list,
    category: str,
    severity: str,
    title: str,
    description: str,
):
    """Add a risk indicator."""

    indicators.append(
        {
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
        }
    )


def calculate_medicine_risk(medicine: dict) -> dict:
    """
    Medicine/product risk screening engine.

    The score represents suspicious-product / verification
    indicators found in the available data.

    Safety information such as warnings, side effects and
    drug interactions is reported separately and does not
    automatically increase the suspicious-product score.

    This system does NOT prove that a medicine is genuine
    or counterfeit.
    """

    score = 0

    indicators = []
    positive_checks = []
    safety_information = []

    # =========================================================
    # 1. MEDICINE IDENTITY
    # =========================================================

    medicine_name = (
        medicine.get("indian_brand")
        or medicine.get("brand_name")
        or medicine.get("medicine_name")
        or medicine.get("searched_name")
    )

    if _is_missing(medicine_name):
        score += 25

        _add_indicator(
            indicators,
            "Identity",
            "high",
            "Medicine identity could not be verified",
            (
                "A reliable medicine name could not be identified "
                "from the available information."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Medicine identity identified",
                "description": str(medicine_name),
            }
        )

    # =========================================================
    # 2. ACTIVE INGREDIENT / COMPOSITION
    # =========================================================

    indian_generic = medicine.get("indian_generic")

    generic_name = (
        indian_generic
        or medicine.get("generic_name")
        or medicine.get("active_ingredient")
    )

    if _is_missing(generic_name):
        score += 15

        _add_indicator(
            indicators,
            "Composition",
            "medium",
            "Active ingredient unavailable",
            (
                "The available sources did not provide a reliable "
                "active ingredient or composition."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Active ingredient identified",
                "description": str(generic_name),
            }
        )

    # =========================================================
    # 3. MANUFACTURER
    # =========================================================

    manufacturer = (
        medicine.get("indian_manufacturer")
        or medicine.get("manufacturer")
    )

    if _is_missing(manufacturer):
        score += 20

        _add_indicator(
            indicators,
            "Manufacturer",
            "high",
            "Manufacturer information unavailable",
            (
                "A manufacturer could not be identified from "
                "the available medicine information."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Manufacturer information available",
                "description": str(manufacturer),
            }
        )

    # =========================================================
    # 4. MEDICINE TYPE
    # =========================================================

    medicine_type = medicine.get("indian_medicine_type")

    if _is_missing(medicine_type):
        score += 5

        _add_indicator(
            indicators,
            "Product Information",
            "low",
            "Medicine type unavailable",
            (
                "The available dataset does not specify "
                "the medicine type."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Medicine type available",
                "description": str(medicine_type),
            }
        )

    # =========================================================
    # 5. PACK INFORMATION
    # =========================================================

    pack_size = medicine.get("indian_pack_size")

    if _is_missing(pack_size):
        score += 5

        _add_indicator(
            indicators,
            "Product Information",
            "low",
            "Pack information unavailable",
            (
                "The available medicine dataset does not "
                "provide pack-size information."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Pack information available",
                "description": str(pack_size),
            }
        )

    # =========================================================
    # 6. DISCONTINUED STATUS
    # =========================================================

    discontinued = (
        medicine.get("indian_discontinued")
        or medicine.get("is_discontinued")
    )

    if _is_discontinued(discontinued):
        score += 30

        _add_indicator(
            indicators,
            "Regulatory Status",
            "high",
            "Medicine marked as discontinued",
            (
                "The available medicine dataset indicates "
                "that this product is marked as discontinued."
            ),
        )
    else:
        positive_checks.append(
            {
                "title": "Product is not marked discontinued",
                "description": (
                    "The available medicine dataset does not "
                    "mark this product as discontinued."
                ),
            }
        )

    # =========================================================
    # 7. SOURCE VERIFICATION
    # =========================================================

    source = medicine.get("source")

    if _is_missing(source):
        score += 10

        _add_indicator(
            indicators,
            "Verification",
            "medium",
            "Source information unavailable",
            (
                "The medicine information could not be associated "
                "with a known data source."
            ),
        )
    else:
        if isinstance(source, list):
            source_text = ", ".join(
                str(item) for item in source
            )
        else:
            source_text = str(source)

        positive_checks.append(
            {
                "title": "Medicine information has known sources",
                "description": source_text,
            }
        )

    # =========================================================
    # 8. SAFETY INFORMATION
    # =========================================================

    warnings = medicine.get("warnings")

    if not _is_missing(warnings):
        safety_information.append(
            {
                "type": "warnings",
                "available": True,
                "title": "Safety warnings available",
                "description": (
                    "Safety warning information is available "
                    "from the medicine information sources."
                ),
            }
        )
    else:
        safety_information.append(
            {
                "type": "warnings",
                "available": False,
                "title": "Safety warnings unavailable",
                "description": (
                    "No safety warning information was returned "
                    "from the available sources."
                ),
            }
        )

    # =========================================================
    # 9. SIDE EFFECT INFORMATION
    # =========================================================

    side_effects = (
        medicine.get("indian_side_effects")
        or medicine.get("adverse_reactions")
    )

    if not _is_missing(side_effects):
        safety_information.append(
            {
                "type": "side_effects",
                "available": True,
                "title": "Side-effect information available",
                "description": (
                    "Side-effect information is available "
                    "from the medicine data."
                ),
            }
        )
    else:
        safety_information.append(
            {
                "type": "side_effects",
                "available": False,
                "title": "Side-effect information unavailable",
                "description": (
                    "No side-effect information was returned "
                    "from the available sources."
                ),
            }
        )

    # =========================================================
    # 10. DRUG INTERACTION INFORMATION
    # =========================================================

    interactions = (
        medicine.get("indian_drug_interactions")
        or medicine.get("drug_interactions")
    )

    if not _is_missing(interactions):
        safety_information.append(
            {
                "type": "interactions",
                "available": True,
                "title": "Drug interaction information available",
                "description": (
                    "Drug interaction information is available "
                    "from the medicine data."
                ),
            }
        )
    else:
        safety_information.append(
            {
                "type": "interactions",
                "available": False,
                "title": "Drug interaction information unavailable",
                "description": (
                    "No drug interaction information was returned "
                    "from the available sources."
                ),
            }
        )

    # =========================================================
    # 11. LIMIT SCORE
    # =========================================================

    score = min(score, 100)

    # =========================================================
    # 12. RISK LEVEL
    # =========================================================

    if score >= 60:
        risk_level = "High Risk"
        risk_type = "high"

    elif score >= 30:
        risk_level = "Moderate Risk"
        risk_type = "medium"

    else:
        risk_level = "Low Risk"
        risk_type = "low"

    # =========================================================
    # 13. DEFAULT INDICATOR
    # =========================================================

    if not indicators:
        _add_indicator(
            indicators,
            "Screening",
            "low",
            "No major suspicious-product indicators detected",
            (
                "The available medicine information did not "
                "identify major suspicious-product indicators."
            ),
        )

    # =========================================================
    # 14. FINAL ASSESSMENT
    # =========================================================

    return {
        "score": score,
        "risk_level": risk_level,
        "risk_type": risk_type,
        "indicators": indicators,
        "verification_checks": positive_checks,
        "safety_information": safety_information,
        "assessment": (
            "This is an informational screening result based "
            "on available medicine data and predefined rules. "
            "It does not prove that a medicine is genuine "
            "or counterfeit."
        ),
    }