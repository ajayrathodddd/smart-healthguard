import { useState } from "react";

import {
  getSupportedLanguages,
  generateVoiceExplanation,
  getAudioUrl,
} from "../services/voiceApi";

export function useVoice() {
  const [languages, setLanguages] = useState({});
  const [result, setResult] = useState(null);

  const [loadingLanguages, setLoadingLanguages] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [error, setError] = useState("");

  async function loadLanguages() {
    try {
      setLoadingLanguages(true);
      setError("");

      const data = await getSupportedLanguages();

      setLanguages(data.languages || {});
    } catch (err) {
      setError(
        err.message || "Failed to load languages."
      );
    } finally {
      setLoadingLanguages(false);
    }
  }

  async function generate(
    medicineName,
    language,
    medicineData = {}
  ) {
    try {
      setGenerating(true);
      setError("");
      setResult(null);

      const data =
        await generateVoiceExplanation(
          medicineName,
          language,
          medicineData
        );

      setResult({
        ...data,
        audioUrl: getAudioUrl(
          data.audio_file
        ),
      });

      return data;
    } catch (err) {
      setError(
        err.message ||
          "Failed to generate voice explanation."
      );

      return null;
    } finally {
      setGenerating(false);
    }
  }

  function clearResult() {
    setResult(null);
    setError("");
  }

  return {
    languages,
    result,
    loadingLanguages,
    generating,
    error,
    loadLanguages,
    generate,
    clearResult,
  };
}