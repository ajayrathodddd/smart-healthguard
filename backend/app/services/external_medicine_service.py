import httpx


RXNORM_URL = "https://rxnav.nlm.nih.gov/REST/drugs.json"


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


async def search_external_medicine(medicine_name: str):
    search_name = medicine_name.strip()

    if not search_name:
        return []

    # RxNorm uses "acetaminophen" for the medicine commonly
    # known as "paracetamol".
    aliases = {
        "paracetamol": "acetaminophen",
    }

    normalized_search = normalize_text(search_name)
    rxnorm_search = aliases.get(
        normalized_search,
        normalized_search,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                RXNORM_URL,
                params={"name": rxnorm_search},
            )

            print("RxNorm status:", response.status_code)

            response.raise_for_status()

            data = response.json()

        concept_groups = data.get("drugGroup", {}).get(
            "conceptGroup",
            [],
        )

        results = []

        for group in concept_groups:
            concepts = group.get("conceptProperties", [])

            for concept in concepts:
                name = concept.get("name") or ""
                synonym = concept.get("synonym") or ""
                term_type = concept.get("tty") or ""

                name_lower = name.lower()
                synonym_lower = synonym.lower()

                # Ignore medicine packs.
                if term_type in {"GPCK", "BPCK"}:
                    continue

                # Ignore obvious combination products.
                if "/" in name:
                    continue

                score = 0

                # Exact ingredient match gets highest priority.
                if name_lower == rxnorm_search:
                    score += 100

                if synonym_lower == rxnorm_search:
                    score += 100

                # Ingredient / precise ingredient.
                if term_type == "IN":
                    score += 50

                if term_type == "PIN":
                    score += 45

                # Clinical / branded medicine.
                if term_type == "SCD":
                    score += 20

                if term_type == "SBD":
                    score += 15

                # Partial match.
                if rxnorm_search in name_lower:
                    score += 10

                if rxnorm_search in synonym_lower:
                    score += 10

                results.append(
                    {
                        "rxcui": concept.get("rxcui"),
                        "name": name,
                        "synonym": synonym,
                        "term_type": term_type,
                        "score": score,
                    }
                )

        # Highest-quality matches first.
        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        # Remove internal score before returning to frontend.
        clean_results = []

        for result in results[:10]:
            result.pop("score", None)
            clean_results.append(result)

        return clean_results

    except Exception as error:
        print(
            "External medicine lookup failed:",
            error,
        )
        return []