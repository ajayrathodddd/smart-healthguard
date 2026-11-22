export default function VoiceMedicineForm({
  medicineName,
  setMedicineName,
  selectedLanguage,
  setSelectedLanguage,
  languages,
  onGenerate,
  loadingLanguages,
  generating,
}) {
  function handleSubmit(event) {
    event.preventDefault();

    if (!medicineName.trim() || !selectedLanguage) {
      return;
    }

    onGenerate(medicineName.trim(), selectedLanguage);
  }

  return (
    <form className="voice-form" onSubmit={handleSubmit}>
      <div className="voice-field">
        <label htmlFor="medicine-name">
          Medicine Name
        </label>

        <input
          id="medicine-name"
          type="text"
          value={medicineName}
          onChange={(event) => setMedicineName(event.target.value)}
          placeholder="Example: Dolo 650"
          disabled={generating}
        />
      </div>

      <div className="voice-field">
        <label htmlFor="voice-language">
          Select Language
        </label>

        <select
          id="voice-language"
          value={selectedLanguage}
          onChange={(event) => setSelectedLanguage(event.target.value)}
          disabled={loadingLanguages || generating}
        >
          <option value="">
            {loadingLanguages
              ? "Loading languages..."
              : "Choose a language"}
          </option>

          {Object.entries(languages).map(([code, language]) => (
            <option key={code} value={code}>
              {language.name} ({language.native_name})
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        className="voice-generate-button"
        disabled={
          generating ||
          loadingLanguages ||
          !medicineName.trim() ||
          !selectedLanguage
        }
      >
        {generating ? "Generating..." : "Generate Voice Explanation"}
      </button>
    </form>
  );
}