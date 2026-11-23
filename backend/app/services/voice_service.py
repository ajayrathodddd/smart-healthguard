from pathlib import Path
import asyncio
import re
import uuid

from gtts import gTTS
from googletrans import Translator
import edge_tts

from app.utils.languages import SUPPORTED_LANGUAGES


AUDIO_DIR = Path("app/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


TRANSLATOR_CODES = {
    "en": "en",
    "hi": "hi",
    "kn": "kn",
    "mr": "mr",
    "bn": "bn",
    "te": "te",
    "ta": "ta",
    "ml": "ml",
    "gu": "gu",
    "pa": "pa",
    "or": "or",
    "as": "as",
    "bho": "bho",
}


# gTTS-supported languages already working in your project
GTTS_LANGUAGES = {
    "en": "en",
    "hi": "hi",
    "kn": "kn",
    "mr": "mr",
    "bn": "bn",
    "te": "te",
    "ta": "ta",
    "ml": "ml",
    "gu": "gu",
    "pa": "pa",
}


# Microsoft Edge neural voices for the languages
# that gTTS does not support.
EDGE_TTS_VOICES = {
    "or": "or-IN-SubhasiniNeural",
    "as": "as-IN-YashicaNeural",
    "bho": "bho-IN-AnanyaNeural",
}


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)

    text = re.sub(r"\s+", " ", text)

    text = re.sub(
        r"\blike\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def extract_safety_summary(
    warnings: str = "",
    description: str = "",
) -> str:

    warnings = clean_text(warnings)
    description = clean_text(description)

    if warnings:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            warnings,
        )

        important_keywords = (
            "allerg",
            "heart",
            "cardiac",
            "liver",
            "hepat",
            "pregnan",
            "breast",
            "diarrhea",
            "interaction",
            "doctor",
            "physician",
            "children",
            "kidney",
            "myasthenia",
            "pregnancy",
            "qt interval",
        )

        safety_sentences = []

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            lower_sentence = sentence.lower()

            if any(
                keyword in lower_sentence
                for keyword in important_keywords
            ):
                safety_sentences.append(sentence)

            if len(safety_sentences) >= 2:
                break

        if safety_sentences:

            return " ".join(
                safety_sentences
            )[:500].strip()

    if description:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            description,
        )

        important_keywords = (
            "inform your doctor",
            "consult your doctor",
            "allergy",
            "heart problem",
            "pregnant",
            "breastfeeding",
            "doctor",
            "physician",
        )

        safety_sentences = []

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            lower_sentence = sentence.lower()

            if any(
                keyword in lower_sentence
                for keyword in important_keywords
            ):
                safety_sentences.append(sentence)

            if len(safety_sentences) >= 2:
                break

        if safety_sentences:

            return " ".join(
                safety_sentences
            )[:500].strip()

    return (
        "Please consult a qualified healthcare professional "
        "before using this medicine, especially if you have "
        "existing medical conditions or take other medicines."
    )


def clean_side_effects(side_effects: str) -> str:

    side_effects = clean_text(side_effects)

    if not side_effects:
        return "No common side effects were available."

    parts = [
        item.strip()
        for item in side_effects.split(",")
        if item.strip()
    ]

    if not parts:
        return "No common side effects were available."

    if len(parts) == 1:
        return parts[0]

    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"

    short_parts = parts[:5]

    if len(short_parts) == 1:
        return short_parts[0]

    return (
        ", ".join(short_parts[:-1])
        + ", and "
        + short_parts[-1]
    )



def build_explanation(
    medicine_name: str,
    composition: str = "",
    description: str = "",
    side_effects: str = "",
    warnings: str = "",
) -> str:
    """Build a short, source-based educational explanation for voice playback."""

    medicine_name = clean_text(medicine_name)
    composition = clean_text(composition)
    description = clean_text(description)
    side_effects_text = clean_side_effects(side_effects)
    safety_summary = extract_safety_summary(
        warnings=warnings,
        description=description,
    )

    description_sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", description)
        if item.strip()
    ]
    short_description = " ".join(description_sentences[:2])[:350]

    warning_text = (
        clean_text(warnings)
        or safety_summary
        or "No warning information was returned by the available data source."
    )
    warning_sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", warning_text)
        if item.strip()
    ]
    short_warnings = " ".join(warning_sentences[:2])[:350]

    parts = [
        f"Medicine information: {medicine_name or 'Medicine name not verified'}.",
        f"Composition: {composition or 'Not available in the retrieved information'}.",
        "Available medicine description: "
        + (
            short_description
            or "Purpose and how the medicine works are not available in the retrieved information."
        ),
        "Reported side effects: "
        + (
            side_effects_text
            if side_effects_text
            else "No side-effect information was returned by the available data source."
        )
        + " Warnings and precautions: "
        + short_warnings,
        "Drug interactions: Ask a pharmacist or healthcare professional about possible interactions. "
        "This is educational information, not a diagnosis or prescription.",
    ]

    return " ".join(parts)

async def translate_explanation(
    explanation: str,
    language: str,
) -> str:

    if language == "en":
        return explanation

    translator_code = TRANSLATOR_CODES.get(
        language
    )

    if not translator_code:

        raise ValueError(
            f"Unsupported translation language: {language}"
        )

    last_error = None

    for attempt in range(3):
        try:
            translator = Translator()
            translated_result = await translator.translate(
                explanation,
                src="en",
                dest=translator_code,
            )
            translated_text = str(
                getattr(translated_result, "text", "")
            ).strip()

            if translated_text:
                return translated_text

            last_error = "Translation returned empty text."
        except Exception as error:
            last_error = str(error)
            await asyncio.sleep(0.4 * (attempt + 1))

    print(
        "[HealthGuard Voice] Translation fallback to English:",
        last_error,
    )
    return explanation


async def generate_edge_audio(
    text: str,
    language: str,
    filename: str,
):
    voice = EDGE_TTS_VOICES.get(language)

    if not voice:

        raise ValueError(
            f"No Edge TTS voice configured for {language}"
        )

    audio_path = AUDIO_DIR / filename

    communicate = edge_tts.Communicate(
        text,
        voice,
    )

    await communicate.save(
        str(audio_path)
    )

    if not audio_path.exists():

        raise RuntimeError(
            "Edge TTS did not create the audio file."
        )

    return audio_path


def generate_gtts_audio(
    text: str,
    language: str,
    filename: str,
):
    tts_language = GTTS_LANGUAGES.get(
        language
    )

    if not tts_language:

        raise ValueError(
            f"No gTTS language configured for {language}"
        )

    audio_path = AUDIO_DIR / filename

    speech = gTTS(
        text=text,
        lang=tts_language,
        slow=False,
    )

    speech.save(
        str(audio_path)
    )

    if not audio_path.exists():

        raise RuntimeError(
            "gTTS did not create the audio file."
        )

    return audio_path


async def create_voice_explanation(
    medicine_name: str,
    language: str,
    composition: str = "",
    description: str = "",
    side_effects: str = "",
    warnings: str = "",
):

    if language not in SUPPORTED_LANGUAGES:
        return None

    language_data = SUPPORTED_LANGUAGES[
        language
    ]

    explanation = build_explanation(
        medicine_name=medicine_name,
        composition=composition,
        description=description,
        side_effects=side_effects,
        warnings=warnings,
    )

    translated_explanation = await translate_explanation(
        explanation=explanation,
        language=language,
    )

    filename = (
        f"medicine_voice_"
        f"{language}_"
        f"{uuid.uuid4().hex}.mp3"
    )

    # Use Edge TTS for the three languages
    # that gTTS does not support.
    if language in EDGE_TTS_VOICES:

        await generate_edge_audio(
            text=translated_explanation,
            language=language,
            filename=filename,
        )

    else:

        generate_gtts_audio(
            text=translated_explanation,
            language=language,
            filename=filename,
        )

    return {
        "medicine_name": medicine_name,
        "language": language,
        "language_name": language_data["name"],
        "native_language_name": language_data["native_name"],
        "explanation": translated_explanation,
        "audio_file": f"/api/voice/audio/{filename}",
    }