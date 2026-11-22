export default function VoiceResult({ result }) {
  if (!result) {
    return null;
  }

  return (
    <div className="voice-result">
      <div className="voice-result-header">
        <div>
          <h2>Voice Explanation Ready</h2>

          <p>
            {result.medicine_name} · {result.language_name}
          </p>
        </div>

        <span className="voice-status">
          {result.status}
        </span>
      </div>

      <div className="voice-explanation">
        <h3>Explanation</h3>

        <p>{result.translated_explanation}</p>
      </div>

      {result.audioUrl && (
        <div className="voice-player">
          <h3>Listen</h3>

          <audio controls preload="metadata">
            <source
              src={result.audioUrl}
              type="audio/mpeg"
            />

            Your browser does not support audio playback.
          </audio>
        </div>
      )}

      <div className="voice-disclaimer">
        <strong>Educational information only:</strong>

        <p>
          This information is provided for educational purposes.
          Always follow the instructions of a qualified healthcare
          professional.
        </p>
      </div>
    </div>
  );
}