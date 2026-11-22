
import { useState } from "react";
import {
  ShieldCheck,
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  Activity,
  Database,
  PackageCheck,
  ShieldAlert,
} from "lucide-react";

import { auth } from "../firebase";
import "./RiskDetectionPage.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function getRiskClass(riskType) {
  if (riskType === "high") {
    return "risk-high";
  }

  if (riskType === "medium") {
    return "risk-medium";
  }

  return "risk-low";
}

function getRiskIcon(riskType) {
  if (riskType === "high") {
    return <XCircle size={24} />;
  }

  if (riskType === "medium") {
    return <AlertTriangle size={24} />;
  }

  return <CheckCircle2 size={24} />;
}

// ========================================================
// SAVE RISK DETECTION RESULT TO ANALYSIS HISTORY
// ========================================================

async function saveRiskHistory(medicine, riskAssessment, searchedName) {
  try {
    const medicineTitle =
      medicine.indian_brand ||
      medicine.brand_name ||
      medicine.medicine_name ||
      searchedName;

    const score = riskAssessment?.score ?? 0;
    const riskType = riskAssessment?.risk_type || "low";

    // Get the currently authenticated Firebase user.
    const currentUser = auth.currentUser;

    if (!currentUser) {
      throw new Error("Please log in to save risk analysis history.");
    }

    // Generate Firebase ID token.
    const token = await currentUser.getIdToken();

    const response = await fetch(`${API_BASE_URL}/api/history/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        analysis_type: "risk",
        title: String(medicineTitle).slice(0, 200),
        summary: `Product verification score: ${score}/100. Status: ${riskType}.`,
        details: {
          score,
          verification_status: riskType,
          manufacturer:
            medicine.indian_manufacturer ||
            medicine.manufacturer ||
            null,
          generic:
            medicine.indian_generic ||
            medicine.generic_name ||
            medicine.active_ingredient ||
            null,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(
        `Unable to save risk analysis history. Status: ${response.status}`
      );
    }

    console.log("Risk analysis saved to history.");
  } catch (error) {
    console.error("Risk history save failed:", error);
  }
}

export default function RiskDetectionPage() {
  const [medicineName, setMedicineName] = useState("");
  const [medicine, setMedicine] = useState(null);
  const [riskAssessment, setRiskAssessment] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const analyzeMedicine = async () => {
    if (!medicineName.trim()) {
      setError("Please enter a medicine name.");
      return;
    }

    setLoading(true);
    setError("");
    setMedicine(null);
    setRiskAssessment(null);

    try {
      const searchedName = medicineName.trim();

      const response = await fetch(
        `${API_BASE_URL}/api/medicines/info?name=${encodeURIComponent(
          searchedName,
        )}`,
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Unable to analyze this medicine.");
      }

      setMedicine(data);
      setRiskAssessment(data.risk_assessment || null);

      // Save successful risk analysis to MongoDB history.
      // History failure will not affect the displayed result.
      if (data.risk_assessment) {
        await saveRiskHistory(
          data,
          data.risk_assessment,
          searchedName,
        );
      }
    } catch (error) {
      setError(
        error.message || "Something went wrong while analyzing the medicine.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      analyzeMedicine();
    }
  };

  const riskType = riskAssessment?.risk_type || "low";
  const riskScore = riskAssessment?.score ?? 0;

  /*
   * IMPORTANT:
   * This wording describes PRODUCT VERIFICATION status.
   * It does not describe the medical safety of the medicine.
   */
  const displayRiskLevel =
    riskType === "high"
      ? "Verification Attention Required"
      : riskType === "medium"
        ? "Review Recommended"
        : "No Major Concerns Detected";

  const indicators = riskAssessment?.indicators || [];
  const verificationChecks = riskAssessment?.verification_checks || [];
  const safetyInformation = riskAssessment?.safety_information || [];
  const sources = medicine?.source || [];

  return (
    <div className="risk-page">
      {/* HEADER */}

      <div className="risk-page-header">
        <div className="risk-header-left">
          <div className="risk-header-icon">
            <ShieldCheck size={28} />
          </div>

          <div>
            <div className="risk-page-badge">AI + RULE BASED ANALYSIS</div>

            <h1>Medicine Risk Detection</h1>

            <p>
              Analyze available medicine information for suspicious-product risk
              indicators.
            </p>
          </div>
        </div>
      </div>

      {/* SEARCH */}

      <div className="risk-search-card">
        <div className="risk-search-header">
          <div className="risk-search-icon">
            <Search size={22} />
          </div>

          <div>
            <h2>Analyze Medicine</h2>

            <p>
              Enter a medicine name to check available verification and risk
              information.
            </p>
          </div>
        </div>

        <div className="risk-search-row">
          <div className="risk-input-wrapper">
            <Search size={19} />

            <input
              type="text"
              value={medicineName}
              onChange={(event) => setMedicineName(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter medicine name..."
            />
          </div>

          <button
            className="risk-analyze-button"
            onClick={analyzeMedicine}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Analyze Medicine"}
          </button>
        </div>

        <div className="risk-examples">
          <span>Try:</span>

          <button onClick={() => setMedicineName("Dolo 650")}>
            Dolo 650
          </button>

          <button onClick={() => setMedicineName("Azithral 500")}>
            Azithral 500
          </button>

          <button onClick={() => setMedicineName("Paracetamol")}>
            Paracetamol
          </button>
        </div>
      </div>

      {/* ERROR */}

      {error && (
        <div className="risk-error">
          <AlertTriangle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* EMPTY STATE */}

      {!medicine && !loading && !error && (
        <div className="risk-empty-state">
          <div className="risk-empty-icon">
            <ShieldCheck size={46} />
          </div>

          <h2>Ready to Analyze</h2>

          <p>
            Search for a medicine to view its verification checks, risk
            indicators, safety information, and available data sources.
          </p>
        </div>
      )}

      {/* LOADING */}

      {loading && (
        <div className="risk-loading">
          <div className="risk-loading-spinner"></div>

          <h3>Analyzing medicine information...</h3>

          <p>Checking available medicine databases and verification rules.</p>
        </div>
      )}

      {/* RESULTS */}

      {medicine && riskAssessment && (
        <div className="risk-results">
          {/* RISK SUMMARY */}

          <section className="risk-summary-card">
            <div className="risk-summary-heading">
              <div>
                <span className="risk-section-label">PRODUCT VERIFICATION</span>

                <h2>Suspicious-Product Screening</h2>
              </div>

              <Activity size={25} />
            </div>

            <div className="risk-summary-content">
              <div className={`risk-score-circle ${getRiskClass(riskType)}`}>
                <div className="risk-score-number">{riskScore}</div>

                <div className="risk-score-total">/100</div>
              </div>

              <div className="risk-summary-details">
                <div className={`risk-level-badge ${getRiskClass(riskType)}`}>
                  {getRiskIcon(riskType)}
                  {displayRiskLevel}
                </div>

                <p>
                  Screening result based on available product information and
                  predefined verification rules. This score reflects product
                  verification indicators, not medical safety.
                </p>

                <div className="risk-scale">
                  <div className="risk-scale-labels">
                    <span>Low</span>
                    <span>Moderate</span>
                    <span>High</span>
                  </div>

                  <div className="risk-scale-bar">
                    <div
                      className={`risk-scale-progress ${getRiskClass(
                        riskType,
                      )}`}
                      style={{
                        width: `${Math.min(riskScore, 100)}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* MEDICINE INFORMATION */}

          <section className="risk-section-card">
            <div className="risk-section-header">
              <div className="risk-section-icon blue">
                <PackageCheck size={21} />
              </div>

              <div>
                <h2>Medicine Information</h2>

                <p>
                  Basic information identified from available medicine sources.
                </p>
              </div>
            </div>

            <div className="risk-info-grid">
              <div className="risk-info-item">
                <span>Medicine</span>

                <strong>
                  {formatText(
                    medicine.indian_brand ||
                      medicine.brand_name ||
                      medicine.medicine_name,
                  )}
                </strong>
              </div>

              <div className="risk-info-item">
                <span>Generic / Composition</span>

                <strong>
                  {formatText(
                    medicine.indian_generic ||
                      medicine.generic_name ||
                      medicine.active_ingredient,
                  )}
                </strong>
              </div>

              <div className="risk-info-item">
                <span>Manufacturer</span>

                <strong>
                  {formatText(
                    medicine.indian_manufacturer || medicine.manufacturer,
                  )}
                </strong>
              </div>

              <div className="risk-info-item">
                <span>Medicine Type</span>

                <strong>{formatText(medicine.indian_medicine_type)}</strong>
              </div>

              <div className="risk-info-item">
                <span>Pack Size</span>

                <strong>{formatText(medicine.indian_pack_size)}</strong>
              </div>

              <div className="risk-info-item">
                <span>Discontinued Status</span>

                <strong>
                  {String(medicine.indian_discontinued).toUpperCase() === "TRUE"
                    ? "Marked discontinued"
                    : "Not marked discontinued"}
                </strong>
              </div>
            </div>
          </section>

          {/* TWO COLUMN AREA */}

          <div className="risk-two-column">
            {/* VERIFICATION CHECKS */}

            <section className="risk-section-card">
              <div className="risk-section-header">
                <div className="risk-section-icon green">
                  <CheckCircle2 size={21} />
                </div>

                <div>
                  <h2>Verification Checks</h2>

                  <p>
                    Positive information found during the screening process.
                  </p>
                </div>
              </div>

              <div className="risk-check-list">
                {verificationChecks.length > 0 ? (
                  verificationChecks.map((check, index) => (
                    <div className="risk-check-item" key={index}>
                      <div className="risk-check-icon">
                        <CheckCircle2 size={18} />
                      </div>

                      <div>
                        <strong>{check.title}</strong>
                        <p>{check.description}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="risk-muted">
                    No verification checks available.
                  </p>
                )}
              </div>
            </section>

            {/* RISK INDICATORS */}

            <section className="risk-section-card">
              <div className="risk-section-header">
                <div className="risk-section-icon orange">
                  <ShieldAlert size={21} />
                </div>

                <div>
                  <h2>Risk Indicators</h2>

                  <p>
                    Suspicious-product indicators detected from the available
                    data.
                  </p>
                </div>
              </div>

              <div className="risk-indicator-list">
                {indicators.length > 0 ? (
                  indicators.map((indicator, index) => (
                    <div
                      className={`risk-indicator-item severity-${indicator.severity}`}
                      key={index}
                    >
                      <div className="risk-indicator-icon">
                        {indicator.severity === "high" ? (
                          <XCircle size={19} />
                        ) : indicator.severity === "medium" ? (
                          <AlertTriangle size={19} />
                        ) : (
                          <Info size={19} />
                        )}
                      </div>

                      <div>
                        <div className="risk-indicator-top">
                          <strong>{indicator.title}</strong>

                          {indicator.category && (
                            <span className="risk-indicator-category">
                              {indicator.category}
                            </span>
                          )}
                        </div>

                        <p>{indicator.description}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="risk-muted">
                    No suspicious-product indicators detected.
                  </p>
                )}
              </div>
            </section>
          </div>

          {/* SAFETY INFORMATION */}

          <section className="risk-section-card">
            <div className="risk-section-header">
              <div className="risk-section-icon purple">
                <AlertTriangle size={21} />
              </div>

              <div>
                <h2>Safety Information Availability</h2>

                <p>
                  Availability of warnings, side effects, and interaction
                  information.
                </p>
              </div>
            </div>

            <div className="risk-safety-grid">
              {safetyInformation.map((item, index) => (
                <div
                  className={`risk-safety-item ${
                    item.available ? "available" : "unavailable"
                  }`}
                  key={index}
                >
                  <div className="risk-safety-icon">
                    {item.available ? (
                      <CheckCircle2 size={19} />
                    ) : (
                      <XCircle size={19} />
                    )}
                  </div>

                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* DATA SOURCES */}

          <section className="risk-section-card">
            <div className="risk-section-header">
              <div className="risk-section-icon blue">
                <Database size={21} />
              </div>

              <div>
                <h2>Data Sources</h2>

                <p>Sources used to build this screening result.</p>
              </div>
            </div>

            <div className="risk-source-list">
              {sources.length > 0 ? (
                sources.map((source, index) => (
                  <div className="risk-source-badge" key={index}>
                    <Database size={16} />
                    {source}
                  </div>
                ))
              ) : (
                <span className="risk-muted">
                  No source information available.
                </span>
              )}
            </div>
          </section>

          {/* EDUCATIONAL NOTICE */}

          <section className="risk-notice">
            <div className="risk-notice-icon">
              <Info size={22} />
            </div>

            <div>
              <h3>Important Educational Notice</h3>

              <p>{formatText(riskAssessment.assessment)}</p>

              <p>
                This feature is designed for informational and educational
                screening only. Always verify medicine packaging, batch details,
                expiry information, and other physical product information
                through appropriate official or professional channels.
              </p>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
