import { useEffect, useState } from "react";

import VoiceHeader from "./VoiceHeader";
import VoiceMedicineForm from "./VoiceMedicineForm";
import VoiceResult from "./VoiceResult";
import { useVoice } from "./hooks/useVoice";
import "./voice.css";
export default function InformationVoicePage() {
  const [medicineName, setMedicineName] = useState("");
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

  return (
    <div className="voice-page">
      <VoiceHeader />

      <div className="voice-card">
        <VoiceMedicineForm
          medicineName={medicineName}
          setMedicineName={setMedicineName}
          selectedLanguage={selectedLanguage}
          setSelectedLanguage={setSelectedLanguage}
          languages={languages}
          onGenerate={generate}
          loadingLanguages={loadingLanguages}
          generating={generating}
        />
      </div>

      {error && (
        <div className="voice-error">
          {error}
        </div>
      )}

      <VoiceResult result={result} />
    </div>
  );
}