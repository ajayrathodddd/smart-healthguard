
import { useEffect, useState } from "react";
import { Volume2, Loader2, PlayCircle } from "lucide-react";

import { useVoice } from "./hooks/useVoice";

export default function MedicineVoiceSummary({
  medicineName,
  composition,
  description,
  sideEffects,
  warnings,
}) {
  const [selectedLanguage, setSelectedLanguage] = useState("en");

  const {
    languages,
    result,
    loadingLanguages,
    generating,
    error,
    loadLanguages,
    generate,
  } = useVoice();

  useEffect(() => {
    loadLanguages();
  }, []);

  const handleGenerate = () => {
    if (!medicineName || !selectedLanguage) {
      return;
    }

    generate(medicineName, selectedLanguage, {
      composition,
      description,
      sideEffects,
      warnings,
    });
  };

  return (
    <div className="medicine-voice-card">
      {/* HEADER */}
      <div className="medicine-voice-header">
        <div className="medicine-voice-icon">
          <Volume2 size={22} />
        </div>

        <div>
          <h3>Medicine Information Voice</h3>

          <p>
            Listen to a short educational summary of {medicineName}.
          </p>
        </div>
      </div>

      {/* CONTROLS */}
      <div className="medicine-voice-controls">
        <div className="medicine-voice-language">
          <label htmlFor="medicine-voice-language">
            Select Language
          </label>

          <select
            id="medicine-voice-language"
            value={selectedLanguage}
            onChange={(event) =>
              setSelectedLanguage(event.target.value)
            }
            disabled={loadingLanguages || generating}
          >
            {loadingLanguages ? (
              <option value="en">
                Loading languages...
              </option>
            ) : (
              Object.entries(languages)
                .filter(
                  ([code]) =>
                    !["or", "as", "bho"].includes(code)
                )
                .map(([code, language]) => (
                  <option
                    key={code}
                    value={code}
                  >
                    {language.name} (
                    {language.native_name})
                  </option>
                ))
            )}
          </select>
        </div>

        <button
          type="button"
          className="medicine-voice-button"
          onClick={handleGenerate}
          disabled={
            generating ||
            loadingLanguages ||
            !medicineName ||
            !selectedLanguage
          }
        >
          {generating ? (
            <>
              <Loader2
                size={18}
                className="spin"
              />
              Generating...
            </>
          ) : (
            <>
              <PlayCircle size={18} />
              Generate Voice
            </>
          )}
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div className="medicine-voice-error">
          {error}
        </div>
      )}

      {/* RESULT */}
      {result && (
        <div className="medicine-voice-result">
          <div className="medicine-voice-result-title">
            <strong>
              {result.medicine_name}
            </strong>

            <span>
              {result.language_name}
            </span>
          </div>

          <div className="medicine-voice-text">
            <p>
              {result.translated_explanation}
            </p>
          </div>

          {result.audioUrl && (
            <div className="medicine-voice-player">
              <div className="medicine-voice-player-label">
                <Volume2 size={17} />
                Listen
              </div>

              <audio
                controls
                preload="metadata"
              >
                <source
                  src={result.audioUrl}
                  type="audio/mpeg"
                />

                Your browser does not support audio
                playback.
              </audio>
            </div>
          )}

          <div className="medicine-voice-note">
            Educational information only. This voice
            summary does not provide diagnosis,
            treatment, or prescription advice.
          </div>
        </div>
      )}
    </div>
  );
}

