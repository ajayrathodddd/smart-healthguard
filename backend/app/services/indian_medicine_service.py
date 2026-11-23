
import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# CONFIGURATION
# ============================================================

SERVICE_FILE = Path(__file__).resolve()

POSSIBLE_DATA_FILES = [
    SERVICE_FILE.parents[2] / "data" / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[3] / "data" / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[2] / "ml" / "data" / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[3] / "ml" / "data" / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[2] / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[3] / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[2] / "app" / "data" / "updated_indian_medicine_data.csv",
    SERVICE_FILE.parents[3] / "app" / "data" / "updated_indian_medicine_data.csv",
]

_MEDICINE_ROWS: Optional[List[Dict[str, str]]] = None
_DATA_FILE: Optional[Path] = None
_SEARCH_INDEX = None


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value: str) -> str:
    if value is None:
        return ""

    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace("\\\\", " ")
    value = value.replace(",", " ")
    value = value.replace("(", " ")
    value = value.replace(")", " ")
    value = value.replace("[", " ")
    value = value.replace("]", " ")

    value = re.sub(r"[^a-z0-9+/%.\- ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value))


def _contains_word(text: str, word: str) -> bool:
    if not text or not word:
        return False

    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
    )


# ============================================================
# MEDICINE ALIASES
# ============================================================

MEDICINE_ALIASES = {
    "dolo 650": ["dolo 650", "dolo650"],
    "dolo650": ["dolo 650", "dolo650"],
    "paracetamol": ["paracetamol", "acetaminophen"],
    "acetaminophen": ["acetaminophen", "paracetamol"],
    "metamizole": ["metamizole", "metamizol", "dipyrone"],
    "metamizol": ["metamizole", "metamizol", "dipyrone"],
    "dipyrone": ["metamizole", "metamizol", "dipyrone"],
    "calpol": ["calpol", "paracetamol"],
    "crocin": ["crocin", "paracetamol"],
}


# ============================================================
# CSV FILE FINDER
# ============================================================

def _find_data_file() -> Optional[Path]:
    global _DATA_FILE

    if _DATA_FILE is not None and _DATA_FILE.exists():
        return _DATA_FILE

    for path in POSSIBLE_DATA_FILES:
        if path.exists() and path.is_file():
            _DATA_FILE = path
            print("Indian medicine dataset found:", path)
            return path

    for root in [SERVICE_FILE.parents[3], SERVICE_FILE.parents[4]]:
        if not root.exists():
            continue

        try:
            for path in root.rglob("updated_indian_medicine_data.csv"):
                if path.is_file():
                    _DATA_FILE = path
                    print("Indian medicine dataset found:", path)
                    return path
        except Exception as error:
            print("Dataset search failed:", error)

    print("WARNING: Indian medicine dataset was not found.")
    return None


# ============================================================
# CSV COLUMN HELPERS
# ============================================================

def _get_value(row: Dict[str, str], possible_names: List[str]) -> str:
    for name in possible_names:
        value = row.get(name)
        if value:
            return value

    return ""


def _medicine_name(row: Dict[str, str]) -> str:
    return _get_value(row, [
        "name", "medicine_name", "brand_name",
        "product_name", "drug_name",
    ])


def _composition_1(row: Dict[str, str]) -> str:
    return _get_value(row, [
        "short_composition1", "short_composition_1",
        "composition", "composition1", "salt", "generic_name",
    ])


def _composition_2(row: Dict[str, str]) -> str:
    return _get_value(row, [
        "short_composition2", "short_composition_2",
        "composition2", "composition_2",
    ])


def _manufacturer(row: Dict[str, str]) -> str:
    return _get_value(row, [
        "manufacturer_name", "manufacturer",
        "company", "company_name",
    ])


# ============================================================
# INGREDIENT EXTRACTION
# ============================================================

def _extract_ingredient_names(composition: str) -> List[str]:
    if not composition:
        return []

    ingredients = []

    for part in re.split(r"\s*\+\s*", str(composition)):
        ingredient = re.sub(r"\([^)]*\)", "", part)
        ingredient = normalize_text(ingredient)

        ingredient = re.sub(
            r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu)\b",
            "",
            ingredient,
        ).strip()

        if ingredient and ingredient not in ingredients:
            ingredients.append(ingredient)

    return ingredients


def _get_aliases(query: str) -> List[str]:
    normalized = normalize_text(query)
    compact = compact_text(query)

    aliases = [normalized, compact]
    aliases.extend(MEDICINE_ALIASES.get(normalized, []))
    aliases.extend(MEDICINE_ALIASES.get(compact, []))

    unique = []

    for alias in aliases:
        alias = normalize_text(alias)

        if alias and alias not in unique:
            unique.append(alias)

    return unique


def _extract_strength(query: str) -> Optional[Tuple[str, str]]:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|μg|g|ml|iu)\b",
        str(query or ""),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    unit = match.group(2).lower()

    if unit == "μg":
        unit = "mcg"

    return match.group(1), unit


def _query_ingredient(query: str) -> str:
    value = normalize_text(query)

    value = re.sub(
        r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu)\b",
        " ",
        value,
    )

    value = re.sub(
        r"\b(tablet|tablets|tab|tabs|capsule|capsules|"
        r"cap|caps|syrup|inhaler|respules|rotacaps|"
        r"solution|suspension|injection|cream|gel|drops)\b",
        " ",
        value,
    )

    return re.sub(r"\s+", " ", value).strip()


# ============================================================
# LOAD DATASET
# ============================================================

def _load_medicine_rows() -> List[Dict[str, str]]:
    global _MEDICINE_ROWS

    if _MEDICINE_ROWS is not None:
        return _MEDICINE_ROWS

    data_file = _find_data_file()

    if data_file is None:
        _MEDICINE_ROWS = []
        return []

    rows = []

    try:
        with data_file.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                if not row:
                    continue

                rows.append({
                    str(key).strip(): (
                        "" if value is None else str(value).strip()
                    )
                    for key, value in row.items()
                    if key is not None
                })

        _MEDICINE_ROWS = rows

        print(f"Indian medicine dataset loaded: {len(rows)} rows")

        return rows

    except Exception as error:
        print("Failed to load Indian medicine dataset:", error)
        _MEDICINE_ROWS = []
        return []


# ============================================================
# BUILD SEARCH INDEX ONCE
# ============================================================

def _build_search_index(rows):
    by_name = {}
    by_ingredient = {}
    by_token = {}

    for row in rows:
        name = normalize_text(_medicine_name(row))
        compact_name = compact_text(name)

        if name:
            by_name.setdefault(name, []).append(row)

        if compact_name and compact_name != name:
            by_name.setdefault(compact_name, []).append(row)

        ingredients = (
            _extract_ingredient_names(_composition_1(row))
            + _extract_ingredient_names(_composition_2(row))
        )

        for ingredient in set(ingredients):
            by_ingredient.setdefault(ingredient, []).append(row)

        searchable = normalize_text(
            f"{_medicine_name(row)} "
            f"{_composition_1(row)} "
            f"{_composition_2(row)}"
        )

        for token in set(searchable.split()):
            if len(token) >= 3:
                by_token.setdefault(token, []).append(row)

    print("Medicine search index created.")

    return {
        "by_name": by_name,
        "by_ingredient": by_ingredient,
        "by_token": by_token,
    }


def _get_search_index():
    global _SEARCH_INDEX

    if _SEARCH_INDEX is None:
        rows = _load_medicine_rows()
        _SEARCH_INDEX = _build_search_index(rows)

    return _SEARCH_INDEX


# ============================================================
# MATCH SCORING
# ============================================================

def _score_medicine(query: str, row: Dict[str, str]) -> int:
    normalized_query = normalize_text(query)

    if not normalized_query:
        return 0

    name = normalize_text(_medicine_name(row))
    composition_1 = _composition_1(row)
    composition_2 = _composition_2(row)

    name_compact = compact_text(name)
    query_compact = compact_text(normalized_query)

    score = 0

    # Exact brand match
    if name == normalized_query or (
        query_compact and name_compact == query_compact
    ):
        score = max(score, 2500)

    # Brand phrase matching. Exact requested brand phrases outrank generic matches.
    requested_ingredient = _query_ingredient(normalized_query)
    generic_aliases = _get_aliases(requested_ingredient)

    composition_ingredients = (
        _extract_ingredient_names(composition_1)
        + _extract_ingredient_names(composition_2)
    )
    composition_ingredients = list(dict.fromkeys(composition_ingredients))

    generic_match = any(
        alias in composition_ingredients
        for alias in generic_aliases
    )

    if len(normalized_query) >= 4:
        if normalized_query in name:
            score = max(score, 2200)
        elif query_compact and query_compact in name_compact:
            score = max(score, 2100)

    # Generic ingredient matching
    for alias in generic_aliases:
        if alias not in composition_ingredients:
            continue

        if len(composition_ingredients) == 1:
            score = max(score, 1500)
        else:
            score = max(score, 1200)

    # Strength match
    requested_strength = _extract_strength(query)

    if requested_strength:
        amount, unit = requested_strength
        combined = normalize_text(
            f"{name} {composition_1} {composition_2}"
        )

        strength_pattern = (
            rf"(?<!\d){re.escape(amount)}\s*{re.escape(unit)}(?![a-z])"
        )

        if re.search(strength_pattern, combined):
            score += 150
        else:
            score = min(score, 700)

    return score


# ============================================================
# FUZZY MATCHING
# ============================================================

def _fuzzy_score(query: str, row: Dict[str, str]) -> int:
    query = normalize_text(query)

    if not query:
        return 0

    name = normalize_text(_medicine_name(row))

    if not name:
        return 0

    similarity = SequenceMatcher(None, query, name).ratio()
    return int(similarity * 500)


# ============================================================
# SEARCH MEDICINES USING INDEX
# ============================================================

def search_indian_medicines(
    medicine_name: str,
    limit: int = 10,
) -> List[Dict[str, object]]:

    query = normalize_text(medicine_name)

    print(f"Indian medicine search: '{medicine_name}'")

    if not query:
        return []

    limit = max(1, min(int(limit), 50))

    index = _get_search_index()

    if not index:
        return []

    candidate_rows = []
    seen_ids = set()

    def add_candidates(rows):
        for row in rows:
            row_id = id(row)

            if row_id not in seen_ids:
                seen_ids.add(row_id)
                candidate_rows.append(row)

    # Exact brand lookup
    compact_query = compact_text(query)

    add_candidates(index["by_name"].get(query, []))
    add_candidates(index["by_name"].get(compact_query, []))

    # Ingredient lookup
    requested_ingredient = _query_ingredient(query)

    for alias in _get_aliases(requested_ingredient):
        add_candidates(index["by_ingredient"].get(alias, []))

    # Token lookup for brand phrases and fallback matching
    query_tokens = [
        token for token in query.split()
        if len(token) >= 3
    ]

    for token in query_tokens:
        add_candidates(index["by_token"].get(token, []))

    # Only use full dataset as a last resort if no index candidates exist.
    if not candidate_rows:
        print("No indexed candidates; trying fuzzy fallback.")
        candidate_rows = index_rows = _load_medicine_rows()

    strong_results = []

    for row in candidate_rows:
        score = _score_medicine(query, row)

        if score >= 800:
            strong_results.append((score, row))

    if strong_results:
        strong_results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = []
        seen = set()

        for score, row in strong_results:
            unique_key = (
                compact_text(_medicine_name(row)),
                compact_text(_composition_1(row)),
                compact_text(_composition_2(row)),
                compact_text(_get_value(row, ["type"])),
            )

            if unique_key in seen:
                continue

            seen.add(unique_key)

            results.append({
                "score": score,
                "medicine": row,
            })

            if len(results) >= limit:
                break

        print(f"Indian medicine search: {len(results)} indexed result(s)")
        return results

    # Fuzzy fallback on indexed token candidates
    fuzzy_results = []

    for row in candidate_rows:
        score = _fuzzy_score(query, row)

        if score >= 250:
            fuzzy_results.append((score, row))

    fuzzy_results.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    results = []
    seen = set()

    for score, row in fuzzy_results:
        unique_key = (
            compact_text(_medicine_name(row)),
            compact_text(_composition_1(row)),
            compact_text(_composition_2(row)),
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        results.append({
            "score": score,
            "medicine": row,
        })

        if len(results) >= limit:
            break

    print(f"Indian medicine search: {len(results)} fuzzy result(s)")
    return results


# ============================================================
# BUILD MEDICINE PROFILE
# ============================================================

def build_indian_medicine_profile(
    row: Dict[str, str],
) -> Dict[str, object]:

    return {
        "brand_name": _medicine_name(row),
        "generic_name": _composition_1(row),
        "composition_2": _composition_2(row),
        "manufacturer": _manufacturer(row),
        "medicine_type": _get_value(row, ["type", "medicine_type", "drug_type"]),
        "pack_size": _get_value(row, ["pack_size_label", "pack_size", "packsize", "pack"]),
        "price": _get_value(row, ["price(₹)", "price", "mrp", "price_inr"]),
        "is_discontinued": _get_value(row, ["Is_discontinued", "is_discontinued", "discontinued"]),
        "medicine_description": _get_value(row, ["medicine_desc", "medicine_description", "description"]),
        "side_effects": _get_value(row, ["side_effects", "side_effect", "adverse_effects"]),
        "drug_interactions": _get_value(row, ["drug_interactions", "drug_interaction", "interactions"]),
        "source": "Indian Medicine Dataset",
    }


# ============================================================
# GET BEST MEDICINE
# ============================================================

def get_best_indian_medicine(
    medicine_name: str,
) -> Optional[Dict[str, object]]:

    results = search_indian_medicines(medicine_name, limit=10)

    if not results:
        return None

    return build_indian_medicine_profile(results[0]["medicine"])


# ============================================================
# RELOAD DATASET AND INDEX
# ============================================================

def reload_indian_medicine_dataset() -> None:
    global _MEDICINE_ROWS
    global _DATA_FILE
    global _SEARCH_INDEX

    _MEDICINE_ROWS = None
    _DATA_FILE = None
    _SEARCH_INDEX = None

    print("Indian medicine dataset and search index cleared.")


# ============================================================
# SUPPORTED CATEGORIES
# ============================================================

MEDICINE_CATEGORY_ALIASES = {
    "painkiller": ["painkiller", "analgesic", "pain relief", "pain relief medicine"],
    "fever": ["fever", "antipyretic"],
    "antibiotic": ["antibiotic", "antibacterial"],
    "cold": ["cold", "cough", "cold and cough"],
    "allergy": ["allergy", "allergic", "antihistamine"],
    "diabetes": ["diabetes", "diabetic", "blood sugar"],
    "blood pressure": ["blood pressure", "hypertension", "bp"],
    "gastric": ["gastric", "acidity", "antacid", "acid reflux"],
    "vitamin": ["vitamin", "multivitamin", "supplement"],
}


def get_supported_medicine_categories() -> Dict[str, List[str]]:
    return MEDICINE_CATEGORY_ALIASES.copy()
