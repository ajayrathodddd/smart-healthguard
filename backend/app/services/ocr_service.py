import io
import re

from PIL import Image, ImageEnhance, ImageOps
import pytesseract


def _prepare_image(image):
    """Enlarge small images and create OCR-friendly versions."""
    image = ImageOps.grayscale(image)

    width, height = image.size
    largest = max(width, height)

    # Enlarge small uploads so tiny package text is easier to recognize.
    if largest < 1400:
        scale = 1400 / largest
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    elif largest > 2200:
        scale = 2200 / largest
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )

    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.6)
    image = ImageEnhance.Sharpness(image).enhance(2.2)

    threshold = image.point(
        lambda pixel: 255 if pixel > 160 else 0
    )

    return [image, threshold]


def _run_ocr(image, config):
    try:
        return pytesseract.image_to_string(
            image,
            config=config,
            timeout=8,
        ).strip()
    except Exception as error:
        print("[HealthGuard OCR] Pass failed:", error)
        return ""


def _text_score(text):
    if not text:
        return 0

    characters = sum(character.isalnum() for character in text)
    words = re.findall(r"[A-Za-z]{3,}", text)

    # Prefer text containing actual word-like groups, not random symbols.
    return characters + (len(words) * 4)


def _word_set(text):
    return set(re.findall(r"[a-z0-9]{2,}", text.lower()))


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Best-effort OCR for supported medicine/package images.

    Enlarges small uploads, enhances contrast, examines the full image
    and an upper package crop, and tries fallback rotations when needed.
    OCR output is not proof of medicine identity.
    """

    if not image_bytes:
        return ""

    try:
        with Image.open(io.BytesIO(image_bytes)) as uploaded:
            uploaded.load()
            image = ImageOps.exif_transpose(uploaded).convert("RGB")

        if image.width * image.height > 25000000:
            image.thumbnail((5000, 5000), Image.Resampling.LANCZOS)

    except Exception as error:
        print("[HealthGuard OCR] Image preparation failed:", error)
        return ""

    width, height = image.size

    # Keep the complete image and also inspect the upper package area.
    upper_crop = image.crop(
        (0, 0, width, max(1, int(height * 0.75)))
    )

    views = [
        ("full", image),
        ("upper_package", upper_crop),
    ]

    configurations = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 11",
    ]

    results = []
    seen = set()

    def record_result(text, label):
        if not text:
            return

        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip().lower()

        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(text)

            print(
                "[HealthGuard OCR]",
                label,
                "Characters:",
                len(text),
                "Score:",
                _text_score(text),
            )

    for view_name, view in views:
        variants = _prepare_image(view)

        for variant_index, variant in enumerate(variants, start=1):
            for config in configurations:
                text = _run_ocr(variant, config)

                record_result(
                    text,
                    f"{view_name}, variant {variant_index}, {config}",
                )

    best_score = max(
        (_text_score(text) for text in results),
        default=0,
    )

    # Try alternate orientations only when normal recognition is weak.
    if best_score < 22:
        for angle in (90, 180, 270):
            rotated = image.rotate(angle, expand=True)
            variants = _prepare_image(rotated)

            # One enhanced pass per fallback orientation.
            text = _run_ocr(
                variants[0],
                "--oem 3 --psm 6",
            )

            record_result(text, f"rotation {angle}")

            best_score = max(
                (_text_score(item) for item in results),
                default=0,
            )

            if best_score >= 22:
                break

    if not results:
        print("[HealthGuard OCR] No readable text detected.")
        return ""

    results.sort(
        key=lambda item: (
            _text_score(item),
            len(item),
        ),
        reverse=True,
    )

    best = results[0]
    combined = [best]
    best_words = _word_set(best)

    # Add another OCR result only when it contributes useful new words.
    for candidate in results[1:]:
        candidate_score = _text_score(candidate)
        candidate_words = _word_set(candidate)
        new_words = candidate_words - best_words

        if (
            candidate_score >= max(15, int(_text_score(best) * 0.55))
            and len(new_words) >= 3
        ):
            combined.append(candidate)
            best_words.update(candidate_words)

        if len(combined) >= 2:
            break

    extracted = "\n\n".join(combined).strip()

    print(
        "[HealthGuard OCR] Final extracted characters:",
        len(extracted),
    )

    return extracted
