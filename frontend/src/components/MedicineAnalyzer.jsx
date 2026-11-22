import { useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function MedicineAnalyzer() {
  const [medicineName, setMedicineName] = useState("");
  const [medicineData, setMedicineData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const analyzeMedicine = async () => {
    if (!medicineName.trim()) {
      setError("Please enter a medicine name.");
      return;
    }

    setLoading(true);
    setError("");
    setMedicineData(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/medicines/info?name=${encodeURIComponent(
          medicineName.trim()
        )}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Medicine information not found."
        );
      }

      setMedicineData(data);
    } catch (error) {
      console.error("Medicine analysis error:", error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="medicine-analyzer">
      <div className="analyzer-card">
        <h2>Medicine Analyzer</h2>

        <p>
          Search and understand medicine information using
          Smart HealthGuard's verified medicine sources.
        </p>

        <div className="search-section">
          <label>Search Medicine</label>

          <p>
            Enter the medicine name you want to analyze.
          </p>

          <div className="medicine-search">
            <input
              type="text"
              value={medicineName}
              onChange={(event) =>
                setMedicineName(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  analyzeMedicine();
                }
              }}
              placeholder="Example: Dolo 650"
            />

            <button
              onClick={analyzeMedicine}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {medicineData && (
          <div className="medicine-result">

            <h2>
              {medicineData.indian_brand ||
                medicineData.brand_name ||
                medicineData.medicine_name}
            </h2>

            <p>
              <strong>Generic Name:</strong>{" "}
              {medicineData.indian_generic ||
                medicineData.generic_name ||
                "Not available"}
            </p>

            <p>
              <strong>Manufacturer:</strong>{" "}
              {medicineData.indian_manufacturer ||
                medicineData.manufacturer ||
                "Not available"}
            </p>

            <p>
              <strong>Medicine Type:</strong>{" "}
              {medicineData.indian_medicine_type ||
                "Not available"}
            </p>

            <p>
              <strong>Pack Size:</strong>{" "}
              {medicineData.indian_pack_size ||
                "Not available"}
            </p>

            <p>
              <strong>Active Ingredient:</strong>{" "}
              {medicineData.active_ingredient ||
                "Not available"}
            </p>

            <p>
              <strong>Route:</strong>{" "}
              {medicineData.route ||
                "Not available"}
            </p>

            <hr />

            <h3>Medicine Information</h3>

            <p>
              {medicineData.indian_description ||
                medicineData.indications ||
                "Information not available."}
            </p>

            <h3>Side Effects</h3>

            <p>
              {medicineData.indian_side_effects ||
                medicineData.adverse_reactions ||
                "Information not available."}
            </p>

            <h3>Warnings</h3>

            <p>
              {medicineData.warnings ||
                "Warning information not available."}
            </p>

            <h3>Drug Interactions</h3>

            <p>
              {medicineData.indian_drug_interactions ||
                medicineData.drug_interactions ||
                "Information not available."}
            </p>

            <hr />

            <p>
              <strong>Data Sources:</strong>{" "}
              {medicineData.source?.join(", ") ||
                "Not available"}
            </p>

            <p>
              <strong>RxNorm ID:</strong>{" "}
              {medicineData.rxcui || "Not available"}
            </p>

            <div className="healthguard-disclaimer">
              <strong>Educational Information</strong>
              <br />
              Smart HealthGuard provides medicine information
              for educational purposes only. It is not a
              substitute for advice from a qualified doctor
              or pharmacist.
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

export default MedicineAnalyzer;