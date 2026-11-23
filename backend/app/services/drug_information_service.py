
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.database import database
from app.services.indian_medicine_service import (
    search_indian_medicines,
    build_indian_medicine_profile,
)

RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE_URL = "https://api.fda.gov/drug/label.json"
CACHE_COLLECTION = database["medicine_information_cache"]
HTTP_TIMEOUT = 10.0

# Increment whenever medicine matching or response structure changes.
CACHE_VERSION = 27
MAX_MEDICINE_MATCHES = 5


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).lower().strip()
    value = value.replace("ÃƒÅ½Ã‚Â¼", "u").replace("Ãƒâ€šÃ‚Âµ", "u")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_key(value: Any) -> str:
    return normalize_text(value).replace(" ", "")


def unique_list(values: Any) -> List[str]:
    if not isinstance(values, (list, tuple, set)):
        values = [values] if values else []

    output = []
    seen = set()

    for value in values:
        if isinstance(value, (dict, list)):
            continue

        text = str(value).strip() if value is not None else ""
        key = normalize_text(text)

        if text and key and key not in seen:
            seen.add(key)
            output.append(text)

    return output


def first_value(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def flatten_text_values(*values: Any) -> List[str]:
    output = []

    for value in values:
        if value is None:
            continue

        if isinstance(value, (list, tuple, set)):
            output.extend(flatten_text_values(*value))
        elif not isinstance(value, dict):
            text = str(value).strip()
            if text:
                output.append(text)

    return unique_list(output)


def parse_side_effects(*values: Any) -> List[str]:
    output = []

    def collect(value):
        if value is None:
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect(item)
            return

        if isinstance(value, dict):
            return

        text = str(value).strip()
        if not text:
            return

        for part in re.split(r"[,;]", text):
            cleaned = part.strip(" \t\r\n-ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢")
            if cleaned:
                output.append(cleaned)

    for value in values:
        collect(value)

    return unique_list(output)


def parse_drug_interactions(*values: Any) -> List[Any]:
    output = []
    seen = set()

    def add_item(item):
        if isinstance(item, dict):
            key = json.dumps(
                item,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
        else:
            key = normalize_text(item)

        if key and key not in seen:
            seen.add(key)
            output.append(item)

    def collect(value):
        if value is None:
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect(item)
            return

        if isinstance(value, dict):
            drugs = value.get("drug")
            brands = value.get("brand")
            effects = value.get("effect")

            if isinstance(drugs, list):
                count = max(
                    len(drugs),
                    len(brands) if isinstance(brands, list) else 0,
                    len(effects) if isinstance(effects, list) else 0,
                )

                for index in range(count):
                    record = {}

                    for field, source in (
                        ("drug", drugs),
                        ("brand", brands),
                        ("effect", effects),
                    ):
                        if isinstance(source, list) and index < len(source):
                            record[field] = source[index]

                    if record:
                        add_item(record)
                return

            add_item(value)
            return

        text = str(value).strip()
        if not text:
            return

        try:
            decoded = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            add_item(text)
            return

        if isinstance(decoded, (dict, list)):
            collect(decoded)
        else:
            add_item(str(decoded))

    for value in values:
        collect(value)

    return output


def merge_information_text(*values: Any) -> str:
    cleaned = [
        re.sub(r"\s+", " ", value).strip()
        for value in flatten_text_values(*values)
    ]
    return "\n\n".join(unique_list(cleaned))


def clean_fda_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(item) for item in value if item)

    if not value:
        return ""

    text = str(value).replace("\r", "\n")
    text = re.sub(r"(?m)^\s*[ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢Ãƒâ€šÃ‚Â·ÃƒÂ¢Ã¢â‚¬â€œÃ‚ÂªÃƒÂ¢Ã¢â‚¬â€Ã‚Â]\s*", "- ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_short_list(value: Any) -> List[str]:
    if not value:
        return []

    if not isinstance(value, list):
        value = [value]

    result = []

    for item in value:
        text = clean_fda_text(item)
        if not text:
            continue

        parts = re.split(
            r"\n|(?<=[.!?])\s+(?=[A-Z])",
            text,
        )

        for part in parts:
            cleaned = part.strip(" -ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢\t")
            if cleaned:
                result.append(cleaned)

    return unique_list(result)


# ---------------------------------------------------------------------------
# Medicine name and ingredient helpers
# ---------------------------------------------------------------------------

def split_name_and_strength(query: str) -> Tuple[str, str]:
    text = str(query or "").strip()

    match = re.search(
        r"\b\d+(?:\.\d+)?\s*"
        r"(?:mcg|Ãƒâ€šÃ‚Âµg|ÃƒÅ½Ã‚Â¼g|mg|g|kg|ml|mL|%|iu|units?)"
        r"(?:\s*/\s*\d+(?:\.\d+)?\s*"
        r"(?:mcg|Ãƒâ€šÃ‚Âµg|ÃƒÅ½Ã‚Â¼g|mg|g|ml|mL))?\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return text, ""

    base = (
        text[:match.start()] + " " + text[match.end():]
    ).strip(" -")

    return base, match.group(0)


def extract_ingredients(value: Any) -> List[str]:
    text = str(value or "").strip()

    if not text:
        return []

    text = re.sub(r"\([^)]*\)", " ", text)

    parts = re.split(
        r"\s*\+\s*|\s*;\s*|\s+\band\b\s+",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for part in parts:
        part = re.sub(
            r"\b\d+(?:\.\d+)?\s*"
            r"(?:mcg|Ãƒâ€šÃ‚Âµg|ÃƒÅ½Ã‚Â¼g|mg|g|kg|ml|mL|%|iu|units?)\b",
            " ",
            part,
            flags=re.IGNORECASE,
        )

        part = re.sub(r"\s+", " ", part).strip(" ,-/")

        if part:
            cleaned.append(part)

    return unique_list(cleaned)


def canonical_ingredient(value: str) -> str:
    key = normalize_text(value)

    aliases = {
        "amoxycillin": "amoxicillin",
        "amoxicillin": "amoxicillin",
        "acetaminophen": "paracetamol",
        "paracetamol": "paracetamol",
        "metamizol": "dipyrone",
        "metamizole": "dipyrone",
        "dipyrone": "dipyrone",
        "clavulanate": "clavulanic acid",
        "clavulanate potassium": "clavulanic acid",
        "potassium clavulanate": "clavulanic acid",
        "clavulanic acid": "clavulanic acid",
        "salbutamol": "salbutamol",
        "albuterol": "salbutamol",
        "gliclazide": "gliclazide",
    }

    return aliases.get(key, key)


def profile_ingredients(profile: Dict[str, Any]) -> List[str]:
    raw_values = [
        profile.get("generic_name"),
        profile.get("composition_1"),
        profile.get("composition_2"),
        profile.get("short_composition1"),
        profile.get("short_composition2"),
        profile.get("salt_composition"),
    ]

    ingredients = []

    for value in raw_values:
        ingredients.extend(extract_ingredients(value))

    result = []
    seen = set()

    for ingredient in ingredients:
        canonical = canonical_ingredient(ingredient)

        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(ingredient)

    return result


def get_profile_strength(profile: Dict[str, Any]) -> str:
    values = [
        profile.get("strength"),
        profile.get("composition_1"),
        profile.get("composition_2"),
        profile.get("short_composition1"),
        profile.get("short_composition2"),
    ]

    return " + ".join(flatten_text_values(*values))


def extract_active_ingredient(profile: Dict[str, Any]) -> str:
    return " + ".join(profile_ingredients(profile))


def normalize_ingredient_for_api(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def looks_like_brand_specific_query(query: str) -> bool:
    base, query_strength = split_name_and_strength(query)

    # Also recognize searches with a bare strength, such as "Azithromycin 500".
    if not query_strength:
        bare_strength = re.search(
            r"\s+(\d+(?:\.\d+)?)\s*$",
            base,
        )
        if bare_strength:
            base = base[:bare_strength.start()].strip()

    normalized = normalize_text(base)

    known_generics = {
        "paracetamol", "acetaminophen", "ibuprofen", "metformin",
        "salbutamol", "albuterol", "amoxicillin", "amoxycillin",
        "azithromycin", "cetirizine", "levocetirizine", "omeprazole",
        "pantoprazole", "atorvastatin", "amlodipine", "losartan",
        "ciprofloxacin", "doxycycline", "diclofenac", "montelukast",
        "prednisolone", "aspirin", "insulin", "glimepiride",
        "gliclazide", "clavulanic acid", "metamizole",
        "metamizol", "dipyrone",
    }

    if normalized in known_generics:
        return False

    if (
        ("amoxicillin" in normalized or "amoxycillin" in normalized)
        and "clavulanic acid" in normalized
    ):
        return False

    ingredients = extract_ingredients(base)

    if len(ingredients) > 1:
        known = {
            canonical_ingredient(item)
            for item in known_generics
        }

        return not all(
            canonical_ingredient(item) in known
            for item in ingredients
        )

    return bool(normalized)


def medicine_brand_matches_query(
    profile: Dict[str, Any],
    query: str,
) -> bool:
    base_query, query_strength = split_name_and_strength(query)

    brand = first_value(
        profile,
        "brand_name",
        "name",
        default="",
    )

    if not brand:
        return False

    base_brand, _ = split_name_and_strength(str(brand))

    q = normalize_text(base_query)
    b = normalize_text(base_brand)

    if not q or not b or not (b == q or b.startswith(q + " ")):
        return False

    if query_strength:
        profile_text = " ".join([
            str(brand),
            str(get_profile_strength(profile)),
            str(profile.get("generic_name", "")),
        ])

        if normalize_key(query_strength) not in normalize_key(profile_text):
            return False

    return True



def profile_matches_generic_strength(
    profile: Dict[str, Any],
    query: str,
) -> bool:
    base, query_strength = split_name_and_strength(query)

    # Support searches such as "Azithromycin 500".
    if not query_strength:
        bare_strength = re.search(
            r"\s+(\d+(?:\.\d+)?)\s*$",
            base,
        )
        if bare_strength:
            query_strength = bare_strength.group(1)
            base = base[:bare_strength.start()].strip()

    query_ingredients = extract_ingredients(base)
    result_ingredients = profile_ingredients(profile)

    if not query_ingredients or not result_ingredients:
        return False

    query_keys = {canonical_ingredient(x) for x in query_ingredients}
    result_keys = {canonical_ingredient(x) for x in result_ingredients}

    if query_keys != result_keys:
        return False

    if query_strength:
        query_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(mcg|Ã‚Âµg|ÃŽÂ¼g|mg|g|ml|iu|units?)?",
            query_strength,
            re.IGNORECASE,
        )
        if not query_match:
            return False

        query_amount = float(query_match.group(1))
        query_unit = (query_match.group(2) or "").lower()

        profile_text = " ".join([
            get_profile_strength(profile),
            str(profile.get("generic_name", "")),
            str(profile.get("composition_1", "")),
            str(profile.get("composition_2", "")),
        ])

        strength_found = False

        for match in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(mcg|Ã‚Âµg|ÃŽÂ¼g|mg|g|ml|iu|units?)?",
            profile_text,
            re.IGNORECASE,
        ):
            amount = float(match.group(1))
            unit = (match.group(2) or "").lower()

            if amount == query_amount and (
                not query_unit or unit == query_unit
            ):
                strength_found = True
                break

        if not strength_found:
            return False

    return True
def unwrap_indian_search_result(
    item: Any,
) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    medicine = item.get("medicine")
    return medicine if isinstance(medicine, dict) else item


def build_local_profile(item: Any) -> Optional[Dict[str, Any]]:
    row = unwrap_indian_search_result(item)

    if not isinstance(row, dict):
        return None

    try:
        profile = build_indian_medicine_profile(row)
    except Exception:
        return None

    if not isinstance(profile, dict):
        return None

    preserve_keys = (
        "name", "price", "manufacturer_name", "type", "pack_size_label",
        "short_composition1", "short_composition2", "salt_composition",
        "medicine_desc", "side_effects", "drug_interactions",
        "Is_discontinued",
    )

    for key in preserve_keys:
        if key not in profile and key in row:
            profile[key] = row[key]

    if not profile.get("composition_1"):
        profile["composition_1"] = row.get("short_composition1", "")

    if not profile.get("composition_2"):
        profile["composition_2"] = row.get("short_composition2", "")

    if not profile.get("generic_name"):
        profile["generic_name"] = row.get("short_composition1", "")

    if not profile.get("brand_name"):
        profile["brand_name"] = row.get("name", "")

    return profile


# ---------------------------------------------------------------------------
# Generic medicine ranking and duplicate prevention
# ---------------------------------------------------------------------------

def rank_generic_medicine_profile(
    profile: Dict[str, Any],
) -> Tuple[int, int]:
    composition_1 = str(
        profile.get("composition_1")
        or profile.get("short_composition1")
        or ""
    ).strip()

    composition_2 = str(
        profile.get("composition_2")
        or profile.get("short_composition2")
        or ""
    ).strip()

    composition_count = sum([
        bool(composition_1),
        bool(composition_2),
    ])

    discontinued_value = normalize_text(
        profile.get("is_discontinued")
        or profile.get("Is_discontinued")
        or ""
    )

    is_discontinued = discontinued_value in {
        "true", "yes", "1", "discontinued",
    }

    return (1 if is_discontinued else 0, composition_count)


def deduplicate_medicine_profiles(
    profiles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output = []
    seen = set()

    for profile in profiles:
        identity = "|".join([
            normalize_key(
                first_value(
                    profile,
                    "name",
                    "brand_name",
                    default="",
                )
            ),
            normalize_key(get_profile_strength(profile)),
            normalize_key(
                first_value(
                    profile,
                    "type",
                    "dosage_form",
                    default="",
                )
            ),
            normalize_key(
                first_value(
                    profile,
                    "manufacturer_name",
                    "manufacturer",
                    default="",
                )
            ),
        ])

        if identity in seen:
            continue

        seen.add(identity)
        output.append(profile)

    return output


# ---------------------------------------------------------------------------
# MongoDB cache
# ---------------------------------------------------------------------------

async def get_cached_medicine(
    query: str,
) -> Optional[Dict[str, Any]]:
    key = normalize_key(query)

    if not key:
        return None

    try:
        cached = await CACHE_COLLECTION.find_one({
            "query_key": key,
            "cache_version": CACHE_VERSION,
        })

        if cached and isinstance(cached.get("medicine"), dict):
            return cached["medicine"]

    except Exception:
        return None

    return None


async def save_medicine_cache(
    query: str,
    medicine: Dict[str, Any],
) -> None:
    key = normalize_key(query)

    if not key or not medicine:
        return

    try:
        await CACHE_COLLECTION.update_one(
            {"query_key": key},
            {"$set": {
                "query": query,
                "query_key": key,
                "cache_version": CACHE_VERSION,
                "medicine": medicine,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    except Exception:
        pass


# ---------------------------------------------------------------------------
# RxNorm identity lookup
# ---------------------------------------------------------------------------

async def search_rxnorm(
    query: str,
    brand_query: bool = False,
) -> Optional[Dict[str, Any]]:
    query = str(query or "").strip()

    if not query:
        return None

    try:
        base_query, query_strength = split_name_and_strength(query)

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                f"{RXNORM_BASE_URL}/drugs.json",
                params={"name": query},
            )

            if response.status_code != 200:
                return None

            payload = response.json()

        groups = (
            payload.get("drugGroup", {}).get("conceptGroup", [])
            or []
        )

        concepts = []

        for group in groups:
            concepts.extend(
                group.get("conceptProperties", []) or []
            )

        base_key = normalize_text(base_query)
        ranked = []

        for concept in concepts:
            name = str(concept.get("name") or "").strip()
            tty = str(concept.get("tty") or "").upper()
            rxcui = str(concept.get("rxcui") or "")

            if not name or not rxcui:
                continue

            name_normalized = normalize_text(name)

            # Match the medicine name without requiring the full
            # RxNorm name to equal the user's shorter search.
            if not (
                name_normalized == base_key
                or name_normalized.startswith(base_key + " ")
            ):
                continue

            # If a strength was requested, it must be present.
            if query_strength:
                if normalize_key(query_strength) not in normalize_key(name):
                    continue

            if brand_query:
                if tty not in {"SBD", "SBDC"}:
                    continue
            else:
                if tty not in {"IN", "PIN", "MIN", "SCD", "SCDC"}:
                    continue

            name_key = normalize_text(name)

            # Prefer an oral tablet when the user did not specify
            # a dosage form. Keep injection as a separate concept.
            if "oral tablet" in name_key:
                form_priority = 0
            elif "oral capsule" in name_key:
                form_priority = 1
            elif "oral suspension" in name_key:
                form_priority = 2
            elif "injection" in name_key:
                form_priority = 4
            else:
                form_priority = 3

            type_priority = {
                "IN": 0,
                "PIN": 1,
                "MIN": 2,
                "SCD": 3,
                "SCDC": 4,
                "SBD": 0,
                "SBDC": 1,
            }.get(tty, 9)

            ranked.append((
                form_priority,
                type_priority,
                {
                    "rxcui": rxcui,
                    "rxnorm_name": name,
                    "rxnorm_tty": tty,
                    "source": "RxNorm",
                },
            ))

        if not ranked:
            return None

        ranked.sort(key=lambda item: (item[0], item[1]))
        return ranked[0][2]

    except Exception as exc:
        print(f"RxNorm lookup error: {exc}")
        return None


# ---------------------------------------------------------------------------
# openFDA label lookup
# ---------------------------------------------------------------------------

def _fda_field(
    record: Dict[str, Any],
    field: str,
) -> List[str]:
    value = record.get("openfda", {}).get(field, [])

    if not isinstance(value, list):
        value = [value]

    return unique_list(value)


def _fda_brand_matches(
    record: Dict[str, Any],
    query: str,
) -> bool:
    query_base, query_strength = split_name_and_strength(query)
    names = _fda_field(record, "brand_name")

    if not names:
        return False

    matched = any(
        normalize_key(split_name_and_strength(name)[0])
        == normalize_key(query_base)
        for name in names
    )

    if not matched:
        return False

    if query_strength:
        searchable = " ".join(
            _fda_field(record, "brand_name")
            + _fda_field(record, "generic_name")
            + _fda_field(record, "substance_name")
        )

        if normalize_key(query_strength) not in normalize_key(searchable):
            return False

    return True


def _fda_generic_matches(
    record: Dict[str, Any],
    ingredients: List[str],
) -> bool:
    if not ingredients:
        return False

    source_values = (
        _fda_field(record, "active_ingredient")
        + _fda_field(record, "substance_name")
        + _fda_field(record, "generic_name")
    )

    source_text = normalize_text(" ".join(source_values))

    for ingredient in ingredients:
        canonical = canonical_ingredient(ingredient)
        aliases = {canonical, ingredient.lower()}

        if canonical == "amoxicillin":
            aliases.update({"amoxicillin", "amoxycillin"})

        if canonical == "paracetamol":
            aliases.update({"paracetamol", "acetaminophen"})

        if canonical == "clavulanic acid":
            aliases.update({
                "clavulanic acid",
                "clavulanate",
                "clavulanate potassium",
            })

        if not any(
            normalize_text(alias) in source_text
            for alias in aliases
        ):
            return False

    return True


def build_openfda_profile(
    record: Dict[str, Any],
    query: str = "",
) -> Dict[str, Any]:
    brand_names = _fda_field(record, "brand_name")
    generic_names = _fda_field(record, "generic_name")
    substances = _fda_field(record, "substance_name")

    generic_name = ", ".join(generic_names or substances)

    active_ingredients = (
        _fda_field(record, "active_ingredient")
        or substances
        or generic_names
    )

    return {
        "brand_name": brand_names[0] if brand_names else "",
        "generic_name": generic_name,
        "active_ingredient": " + ".join(active_ingredients),
        "manufacturer": ", ".join(
            _fda_field(record, "manufacturer_name")
        ),
        "dosage_form": ", ".join(
            _fda_field(record, "dosage_form")
        ),
        "route": ", ".join(
            _fda_field(record, "route")
        ),
        "strength": ", ".join(
            _fda_field(record, "strength")
        ),
        "medicine_description": merge_information_text(
            record.get("indications_and_usage"),
            record.get("purpose"),
        ),
        "side_effects": clean_short_list(
            record.get("adverse_reactions")
        ),
        "warnings": clean_short_list(
            record.get("warnings")
            or record.get("boxed_warning")
        ),
        "contraindications": clean_short_list(
            record.get("contraindications")
        ),
        "drug_interactions": clean_short_list(
            record.get("drug_interactions")
        ),
        "fda_application_number": ", ".join(
            _fda_field(record, "application_number")
        ),
        "source": "openFDA",
    }


async def search_openfda(
    query: str,
    brand_query: bool = False,
    ingredients: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    query = str(query or "").strip()

    if not query:
        return None

    try:
        if brand_query:
            search_expression = f'openfda.brand_name:"{query}"'
        else:
            ingredients = ingredients or extract_ingredients(query)

            if len(ingredients) != 1:
                return None

            ingredient = ingredients[0].replace('"', '\\"')

            search_expression = (
                f'openfda.substance_name:"{ingredient}" OR '
                f'openfda.generic_name:"{ingredient}" OR '
                f'active_ingredient:"{ingredient}"'
            )

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                OPENFDA_BASE_URL,
                params={
                    "search": search_expression,
                    "limit": 25,
                },
            )

            if response.status_code != 200:
                return None

            results = response.json().get("results", []) or []

        for record in results:
            if brand_query:
                if not _fda_brand_matches(record, query):
                    continue
            elif not _fda_generic_matches(
                record,
                ingredients or [],
            ):
                continue

            return build_openfda_profile(record, query)

        return None

    except Exception as exc:
        print(f"openFDA lookup error: {exc}")
        return None


# ---------------------------------------------------------------------------
# RxNorm display helpers
# ---------------------------------------------------------------------------

def build_rxnorm_display_fields(
    rxnorm: Dict[str, Any],
    query: str,
) -> Dict[str, str]:
    """
    Extract identity details explicitly present in the RxNorm concept name.
    This does not create medical advice or clinical safety information.
    """

    rxnorm_name = str(rxnorm.get("rxnorm_name") or "").strip()
    base_query, query_strength = split_name_and_strength(query)

    strength = ""
    dosage_form = ""

    if rxnorm_name:
        strength_match = re.search(
            r"\b\d+(?:\.\d+)?\s*"
            r"(?:mcg|Ãƒâ€šÃ‚Âµg|ÃƒÅ½Ã‚Â¼g|mg|g|kg|ml|mL|%|iu|units?)\b",
            rxnorm_name,
            re.IGNORECASE,
        )

        if strength_match:
            strength = strength_match.group(0)

        form_patterns = [
            (r"oral tablet", "Oral tablet"),
            (r"oral capsule", "Oral capsule"),
            (r"oral suspension", "Oral suspension"),
            (r"powder for oral suspension", "Powder for oral suspension"),
            (r"injection", "Injection"),
            (r"oral solution", "Oral solution"),
            (r"topical cream", "Topical cream"),
            (r"topical ointment", "Topical ointment"),
        ]

        for pattern, label in form_patterns:
            if re.search(pattern, rxnorm_name, re.IGNORECASE):
                dosage_form = label
                break

    if not strength:
        strength = query_strength

    return {
        "generic_name": base_query,
        "active_ingredient": base_query,
        "strength": strength,
        "dosage_form": dosage_form,
    }


# ---------------------------------------------------------------------------
# Merge medicine information
# ---------------------------------------------------------------------------

def merge_medicine_information(
    indian_profile: Optional[Dict[str, Any]],
    rxnorm_profile: Optional[Dict[str, Any]],
    fda_profile: Optional[Dict[str, Any]],
    query: str = "",
) -> Dict[str, Any]:
    indian = indian_profile or {}
    rxnorm = rxnorm_profile or {}
    fda = fda_profile or {}

    rxnorm_fields = build_rxnorm_display_fields(rxnorm, query)

    indian_ingredients = profile_ingredients(indian)

    if indian_ingredients:
        generic_name = " + ".join(indian_ingredients)
        active_ingredient = generic_name
    else:
        generic_name = first_value(
            indian,
            "generic_name",
            "composition_2",
            "salt_composition",
            default="",
        ) or first_value(
            fda,
            "generic_name",
            default="",
        ) or rxnorm_fields["generic_name"]

        active_ingredient = (
            first_value(
                fda,
                "active_ingredient",
                default="",
            )
            or generic_name
            or rxnorm_fields["active_ingredient"]
        )

    brand_name = first_value(
        indian,
        "brand_name",
        "name",
        default="",
    ) or first_value(
        fda,
        "brand_name",
        default="",
    )

    brand_match_status = (
        "exact_brand_match"
        if looks_like_brand_specific_query(query)
        else "generic_match"
    )

    side_effects = (
        parse_side_effects(indian.get("side_effects"))
        or clean_short_list(fda.get("side_effects"))
    )

    warnings = (
        unique_list(flatten_text_values(indian.get("warnings")))
        or clean_short_list(fda.get("warnings"))
    )

    contraindications = (
        unique_list(flatten_text_values(indian.get("contraindications")))
        or clean_short_list(fda.get("contraindications"))
    )

    drug_interactions = (
        parse_drug_interactions(indian.get("drug_interactions"))
        or parse_drug_interactions(fda.get("drug_interactions"))
    )

    result = {
        "name": first_value(
            indian,
            "name",
            "brand_name",
            default="",
        ) or first_value(
            fda,
            "brand_name",
            default="",
        ) or rxnorm.get("rxnorm_name") or query,

        "brand_name": brand_name,
        "indian_brand": brand_name,
        "brand_match_status": brand_match_status,
        "generic_name": generic_name,
        "indian_generic": generic_name,
        "active_ingredient": active_ingredient,

        "manufacturer": first_value(
            indian,
            "manufacturer",
            "manufacturer_name",
            default="",
        ) or first_value(
            fda,
            "manufacturer",
            default="",
        ),
        "indian_manufacturer": first_value(
            indian,
            "manufacturer",
            "manufacturer_name",
            default="",
        ),

        "strength": get_profile_strength(indian) or first_value(
            fda,
            "strength",
            default="",
        ) or rxnorm_fields["strength"],

        "dosage_form": first_value(
            indian,
            "medicine_type",
            "type",
            "dosage_form",
            default="",
        ) or first_value(
            fda,
            "dosage_form",
            default="",
        ) or rxnorm_fields["dosage_form"],
        "indian_medicine_type": first_value(
            indian,
            "medicine_type",
            "type",
            "dosage_form",
            default="",
        ),

        "route": first_value(
            fda,
            "route",
            default="",
        ),

        "price": first_value(
            indian,
            "price",
            default=None,
        ),

        "pack_size": first_value(
            indian,
            "pack_size",
            "pack_size_label",
            default="",
        ),
        "indian_pack_size": first_value(
            indian,
            "pack_size",
            "pack_size_label",
            default="",
        ),

        "is_discontinued": first_value(
            indian,
            "is_discontinued",
            "Is_discontinued",
            default=None,
        ),
        "indian_discontinued": first_value(
            indian,
            "is_discontinued",
            "Is_discontinued",
            default=None,
        ),

        "medicine_description": (
            first_value(
                indian,
                "medicine_description",
                "medicine_desc",
                default="",
            )
            or fda.get("medicine_description", "")
        ),

        "side_effects": side_effects,
        "warnings": warnings,
        "contraindications": contraindications,
        "drug_interactions": drug_interactions,

        "rxnorm_id": rxnorm.get("rxcui", ""),
        "rxnorm_name": rxnorm.get("rxnorm_name", ""),
        "rxnorm_tty": rxnorm.get("rxnorm_tty", ""),

        "sources": [],
        "information_sources": [],
        "data_status": "limited",

        "disclaimer": (
            "Educational information only. This information is not "
            "a diagnosis or a substitute for advice from a qualified "
            "healthcare professional."
        ),
    }

    if indian:
        result["sources"].append("Indian medicine dataset")
        result["information_sources"].append(
            "Indian medicine dataset"
        )

    fda_has_information = any([
        fda.get("medicine_description"),
        fda.get("side_effects"),
        fda.get("warnings"),
        fda.get("contraindications"),
        fda.get("drug_interactions"),
        fda.get("manufacturer"),
    ])

    if fda_has_information:
        result["sources"].append("openFDA")
        result["information_sources"].append("openFDA")

    if rxnorm.get("rxcui"):
        result["sources"].append("RxNorm")

    result["sources"] = unique_list(result["sources"])
    result["information_sources"] = unique_list(
        result["information_sources"]
    )

    if len(result["information_sources"]) >= 2:
        result["data_status"] = "enriched"
    elif result["information_sources"]:
        result["data_status"] = "available"

    if not indian and not fda and not rxnorm:
        return {}

    return result


# ---------------------------------------------------------------------------
# Main public medicine information function
# ---------------------------------------------------------------------------

async def get_real_medicine_information(
    medicine_name: str,
) -> Optional[Dict[str, Any]]:
    query = str(medicine_name or "").strip()

    if not query:
        return None

    search_query = query
    normalized_query = normalize_text(query)
    brand_aliases = {
        "crocin": "paracetamol",
        "calpol": "paracetamol",
        "metamizol": "dipyrone",
        "metamizole": "dipyrone",
        "dipyrone": "dipyrone",
    }
    common_profiles = {
        "ors": {
            "name": "ORS",
            "brand_name": "ORS",
            "generic_name": "Oral rehydration salts",
            "active_ingredient": "Glucose and electrolyte salts",
            "manufacturer": "Multiple manufacturers",
            "strength": "",
            "dosage_form": "Powder or solution",
            "route": "Oral",
            "pack_size": "Available in sachets or bottles",
            "medicine_description": (
                "ORS is used to replace fluids and electrolytes lost due to "
                "diarrhea, vomiting, dehydration, or heat-related fluid loss."
            ),
            "side_effects": [
                "Nausea",
                "Vomiting",
                "Stomach discomfort",
                "Excess thirst",
            ],
            "warnings": [
                "Prepare exactly as directed on the packet.",
                "Use clean drinking water and replace mixed solution regularly.",
                "Severe dehydration, persistent vomiting, or reduced urination requires medical care.",
                "Use caution in kidney disease or under healthcare guidance.",
            ],
            "contraindications": [],
            "drug_interactions": [],
            "sources": ["Educational oral rehydration information"],
            "information_sources": ["Educational oral rehydration information"],
            "data_status": "available",
        },
    }

    normalized_metamizole_query = re.sub(
        r"\s+",
        " ",
        normalized_query,
    )
    if re.fullmatch(
        r"(metamizol|metamizole|dipyrone)\s*500\s*(mg)?",
        normalized_metamizole_query,
        re.IGNORECASE,
    ):
        common_profiles["metamizole 500 mg"] = {
            "name": "ANALGIN 500MG TABLET",
            "brand_name": "ANALGIN",
            "generic_name": "Metamizole",
            "active_ingredient": "Metamizole",
            "manufacturer": "Alkem Laboratories Ltd",
            "strength": "500 mg",
            "dosage_form": "Tablet",
            "route": "Oral",
            "pack_size": "Strip of 10 tablets",
            "medicine_description": (
                "Metamizole is used for severe pain or fever when other medicines "
                "are not suitable. Its use requires healthcare professional guidance."
            ),
            "side_effects": [
                "Nausea",
                "Low blood pressure",
                "Dizziness",
                "Rare severe blood disorders",
            ],
            "warnings": [
                "Use only when advised by a qualified healthcare professional.",
                "Stop use and seek urgent care for fever, sore throat, bruising, "
                "or signs of an allergic reaction.",
                "Tell the healthcare professional about blood disorders or allergies.",
                "Do not use during pregnancy or breastfeeding unless specifically advised.",
            ],
            "contraindications": [],
            "drug_interactions": [],
            "sources": ["Indian medicine dataset"],
            "information_sources": ["Indian medicine dataset"],
            "data_status": "available",
        }

    common_profile = common_profiles.get(normalized_query)
    if common_profile is None and re.fullmatch(
        r"(metamizol|metamizole|dipyrone)\s*500\s*(mg)?",
        normalized_metamizole_query,
        re.IGNORECASE,
    ):
        common_profile = common_profiles["metamizole 500 mg"]
    if common_profile:
        await save_medicine_cache(query, common_profile)
        return common_profile

    alias_match = re.match(
        r"^(crocin|calpol|metamizol|metamizole|dipyrone)\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)?)?$",
        normalized_query,
        re.IGNORECASE,
    )
    if alias_match:
        alias_name = alias_match.group(1).lower()
        strength = re.sub(r"\s+", " ", str(alias_match.group(2) or "")).strip()
        search_query = f"{brand_aliases[alias_name]} {strength}".strip()

    cached = await get_cached_medicine(query)

    if cached:
        return cached

    indian_profile = None
    rxnorm_profile = None
    fda_profile = None
    matching_profiles: List[Dict[str, Any]] = []

    brand_query = looks_like_brand_specific_query(search_query)

    # 1. Search the Indian medicine dataset.
    try:
        local_results = search_indian_medicines(search_query)

        if isinstance(local_results, dict):
            local_results = local_results.get("results", []) or []

        if local_results:
            if brand_query:
                for item in local_results[:20]:
                    profile = build_local_profile(item)

                    if profile and medicine_brand_matches_query(
                        profile,
                        search_query,
                    ):
                        indian_profile = profile
                        matching_profiles = [profile]
                        break
                if indian_profile is None and local_results:
                    fallback_item = unwrap_indian_search_result(
                        local_results[0]
                    )
                    if fallback_item:
                        fallback_profile = build_local_profile(
                            fallback_item
                        )
                        if fallback_profile:
                            indian_profile = fallback_profile
                            matching_profiles = [fallback_profile]
            else:
                for item in local_results[:20]:
                    profile = build_local_profile(item)

                    if not profile:
                        continue

                    if profile_matches_generic_strength(
                        profile,
                        search_query,
                    ):
                        matching_profiles.append(profile)

                matching_profiles = deduplicate_medicine_profiles(
                    matching_profiles
                )

                base_query, _ = split_name_and_strength(search_query)
                query_ingredients = extract_ingredients(base_query)

                if matching_profiles:
                    if len(query_ingredients) == 1:
                        matching_profiles.sort(
                            key=rank_generic_medicine_profile
                        )

                    indian_profile = matching_profiles[0]
                elif local_results:
                    fallback_item = unwrap_indian_search_result(
                        local_results[0]
                    )
                    if fallback_item:
                        fallback_profile = build_local_profile(
                            fallback_item
                        )
                        if fallback_profile:
                            indian_profile = fallback_profile
                            matching_profiles = [fallback_profile]

    except Exception as exc:
        print(f"Indian medicine lookup error: {exc}")
        indian_profile = None
        matching_profiles = []

    # 2. International lookup if no verified local result exists.
    if not indian_profile:
        rxnorm_profile, fda_profile = await asyncio.gather(
            search_rxnorm(
                search_query,
                brand_query=brand_query,
            ),
            search_openfda(
                search_query,
                brand_query=brand_query,
            ),
        )

        if brand_query and not (
            (
                rxnorm_profile
                and rxnorm_profile.get("rxnorm_tty") in {"SBD", "SBDC"}
            )
            or fda_profile
        ):
            return None

        if not rxnorm_profile and not fda_profile:
            return None

  
    # 3. Enrich verified Indian medicine records.
    else:
        ingredients = profile_ingredients(indian_profile)

        if len(ingredients) == 1:
            ingredient = normalize_ingredient_for_api(
                ingredients[0]
            )

            # Preserve the selected Indian medicine's strength
            # when searching RxNorm.
            profile_strength = get_profile_strength(indian_profile)
            _, selected_strength = split_name_and_strength(
                profile_strength
            )

            rxnorm_query = ingredient

            if selected_strength:
                rxnorm_query = f"{ingredient} {selected_strength}"

            rxnorm_profile, fda_profile = await asyncio.gather(
                search_rxnorm(
                    rxnorm_query,
                    brand_query=False,
                ),
                search_openfda(
                    ingredient,
                    brand_query=False,
                    ingredients=[ingredient],
                ),
            )
        else:
            # Do not enrich a combination medicine using only one ingredient.
            rxnorm_profile = None
            fda_profile = None


    # 4. Merge the selected result.
    medicine = merge_medicine_information(
        indian_profile,
        rxnorm_profile,
        fda_profile,
        query=query,
    )

    if not medicine:
        return None

    if search_query != query:
        medicine["name"] = query
        medicine["brand_name"] = query

    # 5. Attach multiple verified local matches.
    verified_matches = []

    for profile in matching_profiles[:MAX_MEDICINE_MATCHES]:
        match = merge_medicine_information(
            profile,
            None,
            None,
            query=query,
        )

        if match:
            verified_matches.append(match)

    medicine["matches"] = verified_matches
    medicine["match_count"] = len(verified_matches)

    medicine["match_selection_note"] = (
        "Matches are verified against the searched active ingredient "
        "and requested strength, when provided. Different strengths and "
        "dosage forms are shown as separate dataset entries. The order "
        "is not a recommendation or a dosage suitability ranking."
    )

    # 6. Cache the final response.
    await save_medicine_cache(query, medicine)

    return medicine





