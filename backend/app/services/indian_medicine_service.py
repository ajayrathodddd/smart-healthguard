
import csv
import heapq
import itertools
import json
import os
import re
import sqlite3
import tempfile
import threading

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

DB_PATH = Path(tempfile.gettempdir()) / "smart_healthguard_medicines.sqlite3"

_DB_LOCK = threading.Lock()
_DATA_FILE: Optional[Path] = None

MAX_CANDIDATES = 1000
BATCH_SIZE = 1000


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value: str) -> str:
    if value is None:
        return ""

    value = str(value).lower().strip()
    value = value.replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace("\\", " ")
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
            return str(value)

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
# SQLITE DATABASE BUILDER
# ============================================================

def _database_is_current(data_file: Path) -> bool:
    if not DB_PATH.exists():
        return False

    try:
        connection = sqlite3.connect(str(DB_PATH))

        metadata = dict(
            connection.execute(
                "SELECT key, value FROM metadata"
            ).fetchall()
        )

        connection.close()

        return (
            metadata.get("source_path") == str(data_file.resolve())
            and metadata.get("source_size") == str(data_file.stat().st_size)
            and metadata.get("source_mtime") == str(data_file.stat().st_mtime)
            and metadata.get("ready") == "1"
        )

    except Exception:
        return False


def _build_sqlite_database(data_file: Path) -> None:
    temporary_path = DB_PATH.with_name(
        f"{DB_PATH.stem}_{os.getpid()}.tmp.sqlite3"
    )

    if temporary_path.exists():
        temporary_path.unlink()

    connection = sqlite3.connect(str(temporary_path))

    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA cache_size=-8192")

        connection.execute("""
            CREATE TABLE medicines (
                id INTEGER PRIMARY KEY,
                data_json TEXT NOT NULL,
                name_norm TEXT,
                name_compact TEXT,
                composition_1 TEXT,
                composition_2 TEXT,
                searchable TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        insert_sql = """
            INSERT INTO medicines (
                data_json,
                name_norm,
                name_compact,
                composition_1,
                composition_2,
                searchable
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """

        batch = []
        total = 0

        with data_file.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for original_row in reader:
                if not original_row:
                    continue

                row = {
                    str(key).strip(): (
                        "" if value is None else str(value).strip()
                    )
                    for key, value in original_row.items()
                    if key is not None
                }

                name = _medicine_name(row)
                composition_1 = _composition_1(row)
                composition_2 = _composition_2(row)

                searchable = normalize_text(
                    f"{name} {composition_1} {composition_2}"
                )

                batch.append((
                    json.dumps(row, ensure_ascii=False),
                    normalize_text(name),
                    compact_text(name),
                    normalize_text(composition_1),
                    normalize_text(composition_2),
                    searchable,
                ))

                if len(batch) >= BATCH_SIZE:
                    connection.executemany(insert_sql, batch)
                    total += len(batch)
                    batch.clear()

            if batch:
                connection.executemany(insert_sql, batch)
                total += len(batch)

        connection.execute(
            "CREATE INDEX idx_medicine_name ON medicines(name_norm)"
        )
        connection.execute(
            "CREATE INDEX idx_medicine_compact ON medicines(name_compact)"
        )

        stat = data_file.stat()

        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [
                ("source_path", str(data_file.resolve())),
                ("source_size", str(stat.st_size)),
                ("source_mtime", str(stat.st_mtime)),
                ("ready", "1"),
                ("total_rows", str(total)),
            ],
        )

        connection.commit()
        connection.close()

        os.replace(temporary_path, DB_PATH)

        print(
            f"Indian medicine SQLite database created: {total} rows"
        )

    except Exception:
        connection.close()

        if temporary_path.exists():
            temporary_path.unlink()

        raise


def _ensure_database() -> bool:
    data_file = _find_data_file()

    if data_file is None:
        return False

    with _DB_LOCK:
        if _database_is_current(data_file):
            return True

        try:
            print("Preparing Indian medicine SQLite database...")
            _build_sqlite_database(data_file)
            return True

        except Exception as error:
            print("Failed to prepare medicine database:", error)
            return False


# ============================================================
# SQLITE SEARCH HELPERS
# ============================================================

def _candidate_query(
    connection: sqlite3.Connection,
    query: str,
):
    conditions = [
        "name_norm = ?",
        "name_compact = ?",
    ]

    parameters = [
        query,
        compact_text(query),
    ]

    requested_ingredient = _query_ingredient(query)

    for alias in _get_aliases(requested_ingredient):
        if len(alias) < 2:
            continue

        conditions.append("composition_1 LIKE ?")
        parameters.append(f"%{alias}%")

        conditions.append("composition_2 LIKE ?")
        parameters.append(f"%{alias}%")

    for token in query.split():
        if len(token) < 3:
            continue

        conditions.append("searchable LIKE ?")
        parameters.append(f"%{token}%")

    sql = """
        SELECT data_json
        FROM medicines
        WHERE
    """ + " OR ".join(conditions)

    return connection.execute(sql, parameters)


def _all_medicine_rows(connection: sqlite3.Connection):
    return connection.execute(
        "SELECT data_json FROM medicines"
    )


def _row_iterator(cursor):
    while True:
        batch = cursor.fetchmany(250)

        if not batch:
            break

        for item in batch:
            try:
                yield json.loads(item[0])
            except (TypeError, json.JSONDecodeError):
                continue


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

    composition_ingredients = (
        _extract_ingredient_names(composition_1)
        + _extract_ingredient_names(composition_2)
    )
    composition_ingredients = list(dict.fromkeys(composition_ingredients))

    score = 0

    # Exact full medicine name.
    if name == normalized_query or (
        query_compact and name_compact == query_compact
    ):
        score = 5000

    else:
        # Exact phrase in a medicine name.
        phrase_match = _contains_word(name, normalized_query)

        # Do not give combination medicines the same score
        # as a standalone medicine for a generic ingredient query.
        if phrase_match and len(composition_ingredients) <= 1:
            score = 3500

        elif len(normalized_query) >= 4 and normalized_query in name:
            score = 2200

        elif (
            query_compact
            and len(query_compact) >= 4
            and query_compact in name_compact
        ):
            score = 2000

    # Ingredient matching.
    requested_ingredient = _query_ingredient(normalized_query)
    generic_aliases = _get_aliases(requested_ingredient)

    for alias in generic_aliases:
        for ingredient in composition_ingredients:
            if ingredient == alias:
                if len(composition_ingredients) == 1:
                    score = max(score, 1500)
                else:
                    score = max(score, 1200)

    # Match requested strength.
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
# RESULT RANKING
# ============================================================

def _collect_top_results(
    rows,
    query: str,
    limit: int,
    fuzzy: bool = False,
):
    counter = itertools.count()
    top = []

    capacity = max(MAX_CANDIDATES, limit * 100)

    for row in rows:
        score = (
            _fuzzy_score(query, row)
            if fuzzy
            else _score_medicine(query, row)
        )

        if fuzzy:
            if score < 250:
                continue
        elif score < 800:
            continue

        item = (score, next(counter), row)

        if len(top) < capacity:
            heapq.heappush(top, item)
        elif score > top[0][0]:
            heapq.heapreplace(top, item)

    ranked = sorted(top, key=lambda item: item[0], reverse=True)

    results = []
    seen = set()

    for score, _, row in ranked:
        unique_key = (
            compact_text(_medicine_name(row)),
            compact_text(_composition_1(row)),
            compact_text(_composition_2(row)),
        )

        if not fuzzy:
            unique_key += (
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

    return results


# ============================================================
# SEARCH MEDICINES
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

    if not _ensure_database():
        return []

    connection = None

    try:
        connection = sqlite3.connect(str(DB_PATH))

        candidate_cursor = _candidate_query(connection, query)
        candidate_rows = _row_iterator(candidate_cursor)

        strong_results = _collect_top_results(
            candidate_rows,
            query,
            limit,
        )

        if strong_results:
            print(
                f"Indian medicine search: "
                f"{len(strong_results)} indexed result(s)"
            )
            return strong_results

        print("No strong indexed matches; trying fuzzy fallback.")

        candidate_cursor = _candidate_query(connection, query)

        fuzzy_results = _collect_top_results(
            _row_iterator(candidate_cursor),
            query,
            limit,
            fuzzy=True,
        )

        if not fuzzy_results:
            print("Trying full SQLite fuzzy search.")

            fuzzy_results = _collect_top_results(
                _row_iterator(_all_medicine_rows(connection)),
                query,
                limit,
                fuzzy=True,
            )

        print(
            f"Indian medicine search: "
            f"{len(fuzzy_results)} fuzzy result(s)"
        )

        return fuzzy_results

    except Exception as error:
        print("Indian medicine search failed:", error)
        return []

    finally:
        if connection is not None:
            connection.close()


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
        "price": _get_value(row, ["price(â‚¹)", "price", "mrp", "price_inr"]),
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
# RELOAD DATASET
# ============================================================

def reload_indian_medicine_dataset() -> None:
    global _DATA_FILE

    _DATA_FILE = None

    with _DB_LOCK:
        for path in [
            DB_PATH,
            DB_PATH.with_name(
                f"{DB_PATH.stem}_{os.getpid()}.tmp.sqlite3"
            ),
        ]:
            if path.exists():
                try:
                    path.unlink()
                except Exception as error:
                    print("Could not remove medicine database:", error)

    print("Indian medicine SQLite database cleared.")


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
