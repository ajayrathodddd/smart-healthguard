import re

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services.ocr_service import extract_text_from_image
from app.services.medicine_service import search_medicine


router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR Scanner"],
)


# ============================================================
# OCR CLEANING
# ============================================================

def clean_ocr_line(line: str) -> str:
    """
    Clean one OCR line while preserving useful medicine text.
    """

    line = line.strip()

    # Remove obvious OCR junk from beginning/end
    line = re.sub(
        r"^[^A-Za-z0-9]+",
        "",
        line,
    )

    line = re.sub(
        r"[^A-Za-z0-9)%/.\- ]+$",
        "",
        line,
    )

    # Normalize spaces
    line = re.sub(
        r"\s+",
        " ",
        line,
    ).strip()

    return line


# ============================================================
# GENERIC MEDICINE NAMES
# ============================================================

KNOWN_GENERIC_NAMES = [
    "paracetamol",
    "acetaminophen",
    "ibuprofen",
    "azithromycin",
    "amoxicillin",
    "cetirizine",
    "metformin",
    "omeprazole",
]


# ============================================================
# EXTRACT GENERIC NAME
# ============================================================

def extract_generic_name(
    ocr_text: str,
) -> str:
    """
    Find a known generic medicine name in OCR text.
    """

    if not ocr_text:
        return ""

    for generic_name in KNOWN_GENERIC_NAMES:

        if re.search(
            rf"\b{re.escape(generic_name)}\b",
            ocr_text,
            re.IGNORECASE,
        ):
            return generic_name.capitalize()

    return ""


# ============================================================
# EXTRACT STRENGTH
# ============================================================

def extract_strength(
    ocr_text: str,
) -> str:
    """
    Extract medicine strength such as:
    650 mg
    500 mg
    10 mg
    5 ml
    """

    if not ocr_text:
        return ""

    # Normal form:
    # 650 mg
    # 500mg
    # 10 MG
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|ml|g)\b",
        ocr_text,
        re.IGNORECASE,
    )

    if match:

        value = match.group(1)
        unit = match.group(2).lower()

        return f"{value} {unit}"

    # Handle OCR where unit may be missing:
    # Dolo-650
    # Waypee-650
    # Paracetamol 650
    match = re.search(
        r"\b[A-Za-z][A-Za-z0-9\-]*[- ](\d{2,4})\b",
        ocr_text,
        re.IGNORECASE,
    )

    if match:

        return f"{match.group(1)} mg"

    return ""


# ============================================================
# EXTRACT BRAND NAME
# ============================================================

def extract_brand_name(
    ocr_text: str,
    generic_name: str,
) -> str:
    """
    Extract a likely brand/product name.

    Examples:
    Dolo-650
    Waypee-650
    """

    if not ocr_text:
        return ""

    lines = [
        clean_ocr_line(line)
        for line in ocr_text.splitlines()
        if clean_ocr_line(line)
    ]

    candidates = []

    for line in lines:

        # ----------------------------------------------------
        # Brand + strength
        #
        # Dolo-650
        # Waypee-650
        # ----------------------------------------------------

        match = re.search(
            r"\b([A-Za-z][A-Za-z0-9]*)\s*[-]\s*(\d{2,4})\b",
            line,
            re.IGNORECASE,
        )

        if match:

            brand = match.group(1)
            strength = match.group(2)

            candidates.append(
                f"{brand}-{strength}"
            )

            continue

        # ----------------------------------------------------
        # Brand + space + strength
        #
        # Dolo 650
        # Waypee 650
        # ----------------------------------------------------

        match = re.search(
            r"\b([A-Za-z][A-Za-z0-9]*)\s+(\d{2,4})\b",
            line,
            re.IGNORECASE,
        )

        if match:

            brand = match.group(1)
            strength = match.group(2)

            candidates.append(
                f"{brand}-{strength}"
            )

    # --------------------------------------------------------
    # Remove generic medicine names from brand candidates
    # --------------------------------------------------------

    filtered_candidates = []

    for candidate in candidates:

        candidate_lower = candidate.lower()

        if generic_name:
            if candidate_lower.startswith(
                generic_name.lower()
            ):
                continue

        if candidate not in filtered_candidates:
            filtered_candidates.append(
                candidate
            )

    if filtered_candidates:
        return filtered_candidates[0]

    return ""


# ============================================================
# BUILD MEDICINE INFORMATION
# ============================================================

def extract_medicine_details(
    ocr_text: str,
) -> dict:
    """
    Extract brand name, generic name and strength
    independently from OCR text.
    """

    generic_name = extract_generic_name(
        ocr_text
    )

    strength = extract_strength(
        ocr_text
    )

    brand_name = extract_brand_name(
        ocr_text,
        generic_name,
    )

    return {
        "brand_name": brand_name,
        "generic_name": generic_name,
        "strength": strength,
    }


# ============================================================
# MEDICINE MATCHING
# ============================================================

async def find_medicine_from_ocr(
    generic_name: str,
    brand_name: str,
    strength: str,
):
    """
    Search the existing medicine service.

    Priority:
    1. Generic + strength
    2. Generic
    3. Brand
    """

    candidates = []

    # --------------------------------------------------------
    # Generic + strength
    # --------------------------------------------------------

    if generic_name and strength:

        candidates.append(
            f"{generic_name} {strength}"
        )

    # --------------------------------------------------------
    # Generic only
    # --------------------------------------------------------

    if generic_name:

        candidates.append(
            generic_name
        )

    # --------------------------------------------------------
    # Brand
    # --------------------------------------------------------

    if brand_name:

        candidates.append(
            brand_name
        )

    # Remove duplicates
    candidates = list(
        dict.fromkeys(candidates)
    )

    print(
        "OCR medicine search candidates:",
        candidates,
    )

    for candidate in candidates:

        try:

            result = await search_medicine(
                candidate
            )

            if (
                result
                and result.get("results")
            ):

                print(
                    "Medicine matched using:",
                    candidate,
                )

                return {
                    "medicine_source": result.get(
                        "source",
                        "unknown",
                    ),
                    "medicine_match": result[
                        "results"
                    ][0],
                    "matched_query": candidate,
                }

        except Exception as error:

            print(
                f"Medicine search failed for "
                f"'{candidate}':",
                error,
            )

    return {
        "medicine_source": "none",
        "medicine_match": None,
        "matched_query": "",
    }


# ============================================================
# OCR SCAN ENDPOINT
# ============================================================

@router.post("/scan")
async def scan_medicine_image(
    file: UploadFile = File(...),
):

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file.content_type:

        raise HTTPException(
            status_code=400,
            detail="Invalid file type.",
        )

    if not file.content_type.startswith(
        "image/"
    ):

        raise HTTPException(
            status_code=400,
            detail="Please upload an image file.",
        )

    image_bytes = await file.read()

    if not image_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    try:

        # ====================================================
        # 1. OCR
        # ====================================================

        extracted_text = (
            extract_text_from_image(
                image_bytes
            )
        )

        print(
            "OCR extracted text:",
            extracted_text,
        )

        # ====================================================
        # 2. Extract medicine details
        # ====================================================

        medicine_details = (
            extract_medicine_details(
                extracted_text
            )
        )

        brand_name = medicine_details[
            "brand_name"
        ]

        generic_name = medicine_details[
            "generic_name"
        ]

        strength = medicine_details[
            "strength"
        ]

        print(
            "OCR brand name:",
            brand_name,
        )

        print(
            "OCR generic name:",
            generic_name,
        )

        print(
            "OCR strength:",
            strength,
        )

        # ====================================================
        # 3. Search existing medicine service
        # ====================================================

        medicine_result = (
            await find_medicine_from_ocr(
                generic_name=generic_name,
                brand_name=brand_name,
                strength=strength,
            )
        )

        medicine_match = (
            medicine_result.get(
                "medicine_match"
            )
        )

        medicine_source = (
            medicine_result.get(
                "medicine_source",
                "none",
            )
        )

        matched_query = (
            medicine_result.get(
                "matched_query",
                "",
            )
        )

        # ====================================================
        # 4. Display name
        #
        # Brand takes priority.
        # Generic is fallback.
        # ====================================================

        medicine_name = (
            brand_name
            or generic_name
        )

        # ====================================================
        # 5. Return response
        # ====================================================

        return {

            "success": True,

            "filename": file.filename,

            # -----------------------------------------------
            # OCR
            # -----------------------------------------------

            "extracted_text": (
                extracted_text
            ),

            # -----------------------------------------------
            # Separate medicine identification
            # -----------------------------------------------

            "medicine_name": (
                medicine_name
            ),

            "brand_name": (
                brand_name
            ),

            "generic_name": (
                generic_name
            ),

            "strength": (
                strength
            ),

            # -----------------------------------------------
            # Existing medicine service result
            # -----------------------------------------------

            "medicine_match": (
                medicine_match
            ),

            "medicine_source": (
                medicine_source
            ),

            "matched_query": (
                matched_query
            ),

            "medicine_info": (
                medicine_match
            ),

            # -----------------------------------------------
            # Additional information
            # -----------------------------------------------

            "side_effects": (
                medicine_match.get(
                    "side_effects",
                    [],
                )
                if isinstance(
                    medicine_match,
                    dict,
                )
                else []
            ),

            "warnings": (
                medicine_match.get(
                    "warnings",
                    [],
                )
                if isinstance(
                    medicine_match,
                    dict,
                )
                else []
            ),

            "interactions": (
                medicine_match.get(
                    "interactions",
                    [],
                )
                if isinstance(
                    medicine_match,
                    dict,
                )
                else []
            ),

            "sources": (
                medicine_match.get(
                    "sources",
                    [],
                )
                if isinstance(
                    medicine_match,
                    dict,
                )
                else []
            ),
        }

    except Exception as error:

        print(
            "OCR processing failed:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process the image.",
        )