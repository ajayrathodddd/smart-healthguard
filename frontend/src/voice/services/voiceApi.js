const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function getSupportedLanguages() {
  const response = await fetch(
    `${API_BASE_URL}/api/voice/languages`
  );

  if (!response.ok) {
    throw new Error("Failed to load supported languages.");
  }

  return response.json();
}

function normalizeMedicineField(value) {
  if (value === null || value === undefined) return "";

  if (typeof value === "string") return value.trim();

  if (Array.isArray(value)) {
    return value
      .map(normalizeMedicineField)
      .filter(Boolean)
      .join(". ");
  }

  if (typeof value === "object") {
    return Object.values(value)
      .map(normalizeMedicineField)
      .filter(Boolean)
      .join(". ");
  }

  return String(value);
}
export async function generateVoiceExplanation(
  medicineName,
  language,
  medicineData = {}
) {
  const response = await fetch(
    `${API_BASE_URL}/api/voice/explain`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        medicine_name: medicineName,
        language: language,

        composition:
          normalizeMedicineField(medicineData.composition),

        description:
          normalizeMedicineField(medicineData.description),

        side_effects:
          normalizeMedicineField(medicineData.sideEffects),

        warnings:
          normalizeMedicineField(medicineData.warnings),
      }),
    }
  );

  if (!response.ok) {
    const errorData =
      await response.json().catch(() => null);

    throw new Error(
      errorData?.detail ||
        "Failed to generate voice explanation."
    );
  }

  return response.json();
}

export function getAudioUrl(audioFile) {
  if (!audioFile) {
    return null;
  }

  return `${API_BASE_URL}${audioFile}`;
}


