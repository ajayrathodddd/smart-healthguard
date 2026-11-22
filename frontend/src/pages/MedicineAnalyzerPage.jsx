
import { useState } from "react";
import { auth } from "../firebase";
import {
  Search,
  ShieldCheck,
  Pill,
  Building2,
  FlaskConical,
  Scale,
  Package,
  FileText,
  AlertCircle,
  Loader2,
  Globe,
  AlertTriangle,
  Stethoscope,
  Database,
  CheckCircle2,
  Info,
} from "lucide-react";

import MedicineVoiceSummary from "../voice/MedicineVoiceSummary";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function MedicineAnalyzerPage() {
  const [medicineName, setMedicineName] = useState("");
  const [medicine, setMedicine] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* =========================================================
     ANALYZE MEDICINE
  ========================================================= */

  const handleAnalyze = async () => {
    if (!medicineName.trim()) {
      setError("Please enter a medicine name.");
      return;
    }

    setLoading(true);
    setError("");
    setMedicine(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/medicines/info?name=${encodeURIComponent(
          medicineName.trim(),
        )}`,
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Medicine information not found.",
        );
      }

      setMedicine(data);

      /* =====================================================
         SAVE SUCCESSFUL ANALYSIS TO USER HISTORY
      ===================================================== */

      try {
        const currentUser = auth.currentUser;

        if (!currentUser) {
          throw new Error(
            "Please log in to save analysis history.",
          );
        }

        const token = await currentUser.getIdToken();

        const historyTitle =
          data.indian_brand ||
          data.brand_name ||
          data.medicine_name ||
          data.searched_name ||
          medicineName.trim();

        const historySummary =
          data.indian_generic ||
          data.generic_name ||
          data.active_ingredient ||
          "Medicine information analyzed successfully.";

        const historyResponse = await fetch(
          `${API_BASE_URL}/api/history/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              analysis_type: "medicine",
              title: String(historyTitle),
              summary: String(historySummary),
              details: {
                manufacturer:
                  data.indian_manufacturer ||
                  data.manufacturer ||
                  "Not available",

                strength:
                  data.strength ||
                  "Not available",

                route:
                  data.route ||
                  "Not available",
              },
            }),
          },
        );

        if (!historyResponse.ok) {
          console.error(
            "History save failed:",
            await historyResponse.text(),
          );
        } else {
          console.log(
            "Medicine analysis saved to history.",
          );
        }
      } catch (historyError) {
        console.error(
          "Unable to save medicine history:",
          historyError,
        );
      }
    } catch (error) {
      console.error("Medicine analysis error:", error);

      setError(
        error.message ||
          "Unable to connect to the Smart HealthGuard backend.",
      );
    } finally {
      setLoading(false);
    }
  };

  /* =========================================================
     BASIC MEDICINE DATA
  ========================================================= */

  const displayName =
    medicine?.indian_brand ||
    medicine?.brand_name ||
    medicine?.medicine_name ||
    medicine?.searched_name ||
    "Medicine";

  const genericName =
    medicine?.indian_generic ||
    medicine?.generic_name ||
    medicine?.active_ingredient ||
    "Generic information unavailable";

  const manufacturer =
    medicine?.indian_manufacturer ||
    medicine?.manufacturer ||
    "Not available";

  const composition =
    medicine?.indian_generic ||
    medicine?.active_ingredient ||
    "Not available";

  const medicineType =
    medicine?.indian_medicine_type || "Not available";

  const packSize =
    medicine?.indian_pack_size || "Not available";

  const description =
    medicine?.indian_description ||
    medicine?.indications ||
    medicine?.purpose ||
    "No description is available for this medicine.";

  const sideEffects =
    medicine?.indian_side_effects ||
    medicine?.adverse_reactions ||
    "Information not available.";

  /* =========================================================
     SAFETY INFORMATION
  ========================================================= */

  const rawWarnings =
    medicine?.warnings ||
    medicine?.contraindications ||
    "Warning information not available.";

  /* =========================================================
     DRUG INTERACTIONS
  ========================================================= */

  const rawInteractions =
    medicine?.indian_drug_interactions ||
    medicine?.drug_interactions ||
    "";

  let interactions = rawInteractions;

  if (typeof rawInteractions === "string") {
    try {
      const parsedInteractions = JSON.parse(rawInteractions);

      if (
        parsedInteractions &&
        typeof parsedInteractions === "object"
      ) {
        interactions = parsedInteractions;
      }
    } catch {
      interactions = rawInteractions;
    }
  }

  /* =========================================================
     DATA SOURCES
  ========================================================= */

  const sources = Array.isArray(medicine?.source)
    ? medicine.source
    : [];

  /* =========================================================
     PRODUCT STATUS
  ========================================================= */

  const discontinuedStatus =
    medicine?.indian_discontinued === "FALSE"
      ? "Active"
      : medicine?.indian_discontinued === "TRUE"
        ? "Discontinued"
        : "Not available";

  /* =========================================================
     GENERAL TEXT FORMATTER
  ========================================================= */

  const formatText = (value) => {
    if (!value) {
      return "Information not available.";
    }

    if (typeof value === "string") {
      return value.trim();
    }

    if (Array.isArray(value)) {
      return value
        .map((item) => String(item).trim())
        .filter(Boolean)
        .join(", ");
    }

    if (typeof value === "object") {
      return JSON.stringify(value, null, 2);
    }

    return String(value);
  };

  /* =========================================================
     SIDE EFFECT FORMATTER
  ========================================================= */

  const getSideEffectList = (value) => {
    if (!value) {
      return [];
    }

    if (Array.isArray(value)) {
      return value
        .map((item) => String(item).trim())
        .filter(Boolean);
    }

    if (typeof value === "string") {
      return value
        .split(/[,;|]+/)
        .map((item) => item.trim())
        .filter(Boolean);
    }

    return [String(value)];
  };

  /* =========================================================
     MEDICINE DESCRIPTION FORMATTER
  ========================================================= */

  const getDescriptionParagraphs = (value) => {
    if (!value) {
      return [];
    }

    const text = String(value)
      .replace(/\s+/g, " ")
      .trim();

    if (!text) {
      return [];
    }

    const sentences = text
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter(Boolean);

    if (sentences.length <= 2) {
      return [text];
    }

    const paragraphs = [];
    let currentParagraph = [];

    sentences.forEach((sentence, index) => {
      currentParagraph.push(sentence);

      if (
        currentParagraph.length >= 2 ||
        index === sentences.length - 1
      ) {
        paragraphs.push(
          currentParagraph.join(" "),
        );

        currentParagraph = [];
      }
    });

    return paragraphs;
  };

  /* =========================================================
     SAFETY SECTION PARSER
  ========================================================= */

  const getSafetySections = (value) => {
    if (!value) {
      return {
        contraindications: [],
        warnings: [],
      };
    }

    let text = String(value)
      .replace(/\r?\n/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (!text) {
      return {
        contraindications: [],
        warnings: [],
      };
    }

    text = text
      .replace(/\(\s*\)/g, " ")
      .replace(/\[\s*\]/g, " ")
      .replace(/\{\s*\}/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    const sectionTitles = {
      "4": "Contraindications",
      "4.1": "Hypersensitivity",
      "4.2": "Hepatic Dysfunction",
      "4.3": "Important Contraindication",

      "5": "Warnings & Precautions",
      "5.1": "Serious Allergic Reactions",
      "5.2": "Liver Problems",
      "5.3": "Infantile Hypertrophic Pyloric Stenosis",
      "5.4": "Heart Rhythm Changes",
      "5.5": "Cardiovascular Risk",
      "5.6": "Clostridioides difficile-Associated Diarrhea",
      "5.7": "Myasthenia Gravis",
      "5.8": "Use in Sexually Transmitted Infections",
      "5.9": "Antibiotic Resistance",
    };

    text = text.replace(
      /^\s*(?:4|5)\s+(?:CONTRAINDICATIONS?|WARNINGS?\s+AND\s+PRECAUTIONS?)\s*/i,
      "",
    );

    const subsectionRegex =
      /(?:^|\s)(4\.\d+|5\.\d+)\s+/g;

    const matches = [];
    let match;

    while (
      (match = subsectionRegex.exec(text)) !== null
    ) {
      matches.push({
        number: match[1],
        index: match.index,
        contentStart: subsectionRegex.lastIndex,
      });
    }

    const contraindications = [];
    const warnings = [];

    if (matches.length > 0) {
      matches.forEach((item, index) => {
        const start = item.contentStart;

        const end =
          index < matches.length - 1
            ? matches[index + 1].index
            : text.length;

        let content = text
          .substring(start, end)
          .trim();

        if (!content) {
          return;
        }

        content = content
          .replace(/^[-•:)\s]+/, "")
          .trim();

        const title =
          sectionTitles[item.number] ||
          "Important Safety Information";

        const headingPattern = new RegExp(
          `^${title.replace(
            /[.*+?^${}()|[\]\\]/g,
            "\\$&",
          )}\\s*`,
          "i",
        );

        content = content
          .replace(headingPattern, "")
          .trim();

        content = content
          .replace(/\(\s*\)/g, "")
          .replace(/\[\s*\]/g, "")
          .replace(/\{\s*\}/g, "")
          .replace(/\s+/g, " ")
          .trim();

        if (!content) {
          return;
        }

        const section = {
          number: item.number,
          title,
          content,
        };

        if (item.number.startsWith("4.")) {
          contraindications.push(section);
        } else if (item.number.startsWith("5.")) {
          warnings.push(section);
        }
      });

      return {
        contraindications,
        warnings,
      };
    }

    const contraindicationMatch = text.match(
      /^\s*(?:4\s+)?CONTRAINDICATIONS?\s*[:\-]?\s*(.*)$/i,
    );

    if (contraindicationMatch) {
      const content = contraindicationMatch[1]
        .replace(/\(\s*\)/g, "")
        .trim();

      if (content) {
        contraindications.push({
          number: "4",
          title: "Contraindications",
          content,
        });
      }
    }

    const warningMatch = text.match(
      /^\s*(?:5\s+)?WARNINGS?\s*(?:AND\s+PRECAUTIONS?)?\s*[:\-]?\s*(.*)$/i,
    );

    if (warningMatch) {
      const content = warningMatch[1]
        .replace(/\(\s*\)/g, "")
        .trim();

      if (content) {
        warnings.push({
          number: "5",
          title: "Warnings & Precautions",
          content,
        });
      }
    }

    if (
      contraindications.length === 0 &&
      warnings.length === 0
    ) {
      const fallbackParagraphs = text
        .split(/(?<=[.!?])\s+(?=[A-Z])/)
        .map((item) =>
          item.replace(/\(\s*\)/g, "").trim(),
        )
        .filter((item) => item.length > 20);

      if (fallbackParagraphs.length > 0) {
        warnings.push(
          ...fallbackParagraphs.map((content, index) => ({
            number: String(index + 1),
            title: "Important Safety Information",
            content,
          })),
        );
      } else {
        warnings.push({
          number: "1",
          title: "Important Safety Information",
          content: text,
        });
      }
    }

    return {
      contraindications,
      warnings,
    };
  };

  const safetySections = getSafetySections(rawWarnings);

  const contraindications =
    safetySections.contraindications;

  const warnings = safetySections.warnings;

  /* =========================================================
     DRUG INTERACTION RENDERER
  ========================================================= */

  const renderInteractionContent = () => {
    if (!interactions) {
      return (
        <p className="medicine-muted-text">
          No interaction information available.
        </p>
      );
    }

    if (
      typeof interactions === "object" &&
      !Array.isArray(interactions) &&
      Array.isArray(interactions.drug)
    ) {
      const drugs = interactions.drug || [];

      const brands = Array.isArray(interactions.brand)
        ? interactions.brand
        : [];

      return (
        <div className="interaction-list">
          {drugs.map((drug, index) => (
            <div
              className="interaction-item"
              key={`${drug}-${index}`}
            >
              <div className="interaction-number">
                {index + 1}
              </div>

              <div className="interaction-details">
                <strong className="interaction-drug">
                  {drug}
                </strong>

                {brands[index] && (
                  <p className="interaction-brands">
                    <strong>Related brands:</strong>{" "}
                    {String(brands[index]).trim()}
                  </p>
                )}

                <span className="interaction-effect">
                  Important interaction
                </span>
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (Array.isArray(interactions)) {
      return (
        <div className="interaction-list">
          {interactions.map((item, index) => (
            <div
              className="interaction-item"
              key={index}
            >
              <div className="interaction-number">
                {index + 1}
              </div>

              <div className="interaction-details">
                <p>{formatText(item)}</p>
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (typeof interactions === "object") {
      return (
        <div className="interaction-list">
          {Object.entries(interactions).map(
            ([key, value], index) => (
              <div
                className="interaction-item"
                key={index}
              >
                <div className="interaction-number">
                  {index + 1}
                </div>

                <div className="interaction-details">
                  <strong className="interaction-drug">
                    {key}
                  </strong>

                  <p>{formatText(value)}</p>
                </div>
              </div>
            ),
          )}
        </div>
      );
    }

    return (
      <div className="medicine-text-box">
        <p>{formatText(interactions)}</p>
      </div>
    );
  };

  /* =========================================================
     PAGE
  ========================================================= */

  return (
    <div className="medicine-page">
      {/* HEADER */}

      <div className="medicine-page-header">
        <div>
          <div className="page-badge">
            <ShieldCheck size={15} />
            AI-POWERED ANALYSIS
          </div>

          <h2>Medicine Analyzer</h2>

          <p>
            Search and understand medicine information using
            Smart HealthGuard&apos;s connected medicine data
            sources.
          </p>
        </div>

        <div className="medicine-header-icon">
          <Pill size={42} />
        </div>
      </div>

      {/* SEARCH */}

      <div className="medicine-search-card">
        <div className="search-card-header">
          <div className="search-icon">
            <Search size={22} />
          </div>

          <div>
            <h3>Search Medicine</h3>

            <p>
              Enter the medicine name you want to analyze.
            </p>
          </div>
        </div>

        <div className="medicine-search-box">
          <Search size={20} />

          <input
            type="text"
            placeholder="Example: Dolo 650"
            value={medicineName}
            onChange={(e) => setMedicineName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleAnalyze();
              }
            }}
          />

          <button
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search size={18} />
                Analyze
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="medicine-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* EMPTY STATE */}

      {!medicine && !loading && !error && (
        <div className="medicine-empty-state">
          <div className="empty-pill-icon">
            <Pill size={40} />
          </div>

          <h3>Ready to analyze a medicine</h3>

          <p>
            Search for an Indian or generic medicine above to
            view available information from multiple medicine
            data sources.
          </p>

          <div className="example-search">
            <span>Try:</span>

            <button onClick={() => setMedicineName("Dolo 650")}>
              Dolo 650
            </button>

            <button
              onClick={() => setMedicineName("Azithral 500")}
            >
              Azithral 500
            </button>
          </div>
        </div>
      )}

      {/* LOADING */}

      {loading && (
        <div className="medicine-empty-state">
          <Loader2 size={40} className="spin" />

          <h3>Analyzing medicine...</h3>

          <p>
            Smart HealthGuard is checking Indian medicine data
            and connected medicine information sources.
          </p>
        </div>
      )}

      {/* RESULT */}

      {medicine && !loading && (
        <div className="medicine-result-container">
          {/* RESULT HEADER */}

          <div className="result-title-row">
            <div>
              <span>ANALYSIS RESULT</span>
              <h3>{displayName}</h3>
            </div>

            <div className="database-badge">
              <ShieldCheck size={17} />
              Information Sources
            </div>
          </div>

          {/* MAIN MEDICINE INFORMATION */}

          <div className="medicine-main-card">
            <div className="medicine-main-header">
              <div className="medicine-big-icon">
                <Pill size={32} />
              </div>

              <div className="medicine-main-title">
                <div className="medicine-title-line">
                  <h3>{displayName}</h3>

                  {discontinuedStatus === "Active" && (
                    <span className="medicine-status-active">
                      <CheckCircle2 size={14} />
                      Active
                    </span>
                  )}
                </div>

                <p>{genericName}</p>
              </div>
            </div>

            <div className="medicine-section-heading">
              <Database size={18} />
              <span>Basic Medicine Information</span>
            </div>

            <div className="medicine-info-grid">
              <div className="medicine-info-item">
                <div className="info-icon blue">
                  <Building2 size={20} />
                </div>

                <div>
                  <span>Manufacturer</span>
                  <strong>{manufacturer}</strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon purple">
                  <FlaskConical size={20} />
                </div>

                <div>
                  <span>Composition</span>
                  <strong>{composition}</strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon green">
                  <Scale size={20} />
                </div>

                <div>
                  <span>Medicine Type</span>
                  <strong>{medicineType}</strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon orange">
                  <Package size={20} />
                </div>

                <div>
                  <span>Pack Size</span>
                  <strong>{packSize}</strong>
                </div>
              </div>
            </div>

            {/* MEDICINE DESCRIPTION */}

            <div className="medicine-description">
              <div className="description-icon">
                <FileText size={20} />
              </div>

              <div className="medicine-description-content">
                <span>WHAT THIS MEDICINE IS USED FOR</span>

                <div className="medicine-description-paragraphs">
                  {getDescriptionParagraphs(description).map(
                    (paragraph, index) => (
                      <p key={index}>{paragraph}</p>
                    ),
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* SIDE EFFECTS */}

          <div className="medicine-main-card medicine-side-effects">
            <div className="medicine-section-top">
              <div className="section-icon warning-icon">
                <AlertTriangle size={21} />
              </div>

              <div>
                <h3>Side Effects</h3>

                <p>
                  Reported or documented adverse reactions
                  associated with this medicine.
                </p>
              </div>
            </div>

            <div className="medicine-content-box side-effects-box">
              <div className="side-effects-list">
                {getSideEffectList(sideEffects).map(
                  (effect, index) => (
                    <div
                      className="side-effect-item"
                      key={`${effect}-${index}`}
                    >
                      <CheckCircle2 size={17} />
                      <span>{effect}</span>
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>

          {/* CONTRAINDICATIONS */}

          {contraindications.length > 0 && (
            <div className="medicine-main-card medicine-warning-section">
              <div className="medicine-section-top">
                <div className="section-icon danger-icon">
                  <AlertCircle size={21} />
                </div>

                <div>
                  <h3>Contraindications</h3>

                  <p>
                    Situations in which the medicine should not
                    be used according to the available medicine
                    information.
                  </p>
                </div>
              </div>

              <div className="warning-sections">
                {contraindications.map(
                  (contraindication, index) => (
                    <div
                      className="warning-item"
                      key={`${contraindication.number}-${index}`}
                    >
                      <div className="warning-item-header">
                        <div className="warning-number">
                          {contraindication.number}
                        </div>

                        <div>
                          <h4>{contraindication.title}</h4>
                        </div>
                      </div>

                      <p>{contraindication.content}</p>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {/* WARNINGS AND PRECAUTIONS */}

          {warnings.length > 0 && (
            <div className="medicine-main-card medicine-warning-section">
              <div className="medicine-section-top">
                <div className="section-icon danger-icon">
                  <AlertTriangle size={21} />
                </div>

                <div>
                  <h3>Warnings &amp; Precautions</h3>

                  <p>
                    Important safety information available from
                    the connected medicine sources.
                  </p>
                </div>
              </div>

              <div className="warning-sections">
                {warnings.map((warning, index) => (
                  <div
                    className="warning-item"
                    key={`${warning.number}-${index}`}
                  >
                    <div className="warning-item-header">
                      <div className="warning-number">
                        {warning.number}
                      </div>

                      <div>
                        <h4>{warning.title}</h4>
                      </div>
                    </div>

                    <p>{warning.content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* DRUG INTERACTIONS */}

          <div className="medicine-main-card medicine-interactions-section">
            <div className="medicine-section-top">
              <div className="section-icon interaction-icon">
                <Stethoscope size={21} />
              </div>

              <div>
                <h3>Drug Interactions</h3>

                <p>
                  Important interaction information available
                  for the analyzed medicine.
                </p>
              </div>
            </div>

            {renderInteractionContent()}
          </div>

          {/* ADDITIONAL INFORMATION */}

          <div className="medicine-main-card">
            <div className="medicine-section-heading">
              <Globe size={18} />
              <span>Additional Information</span>
            </div>

            <div className="medicine-info-grid">
              <div className="medicine-info-item">
                <div className="info-icon blue">
                  <Globe size={20} />
                </div>

                <div>
                  <span>Route</span>
                  <strong>
                    {medicine.route || "Not available"}
                  </strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon purple">
                  <ShieldCheck size={20} />
                </div>

                <div>
                  <span>RxNorm ID</span>
                  <strong>
                    {medicine.rxcui || "Not available"}
                  </strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon green">
                  <FileText size={20} />
                </div>

                <div>
                  <span>Data Sources</span>
                  <strong>
                    {sources.length > 0
                      ? `${sources.length} source${
                          sources.length > 1 ? "s" : ""
                        } available`
                      : "Not available"}
                  </strong>
                </div>
              </div>

              <div className="medicine-info-item">
                <div className="info-icon orange">
                  <Package size={20} />
                </div>

                <div>
                  <span>Indian Product Status</span>
                  <strong>{discontinuedStatus}</strong>
                </div>
              </div>
            </div>

            {/* DATA SOURCES */}

            {sources.length > 0 && (
              <div className="medicine-data-sources">
                <div className="source-heading">
                  <Database size={17} />
                  <span>Information Sources</span>
                </div>

                <div className="source-badges">
                  {sources.map((source, index) => (
                    <span
                      className="source-badge"
                      key={index}
                    >
                      <ShieldCheck size={14} />
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* MEDICINE INFORMATION VOICE */}

          <MedicineVoiceSummary
            medicineName={displayName}
            composition={composition}
            description={description}
            sideEffects={sideEffects}
            warnings={rawWarnings}
          />

          {/* EDUCATIONAL NOTICE */}

          <div className="medicine-notice">
            <ShieldCheck size={20} />

            <div>
              <strong>Educational information only</strong>

              <p>
                Smart HealthGuard provides medicine information
                for educational purposes. It does not provide
                diagnosis, treatment, or prescription advice.
                Always consult a qualified healthcare
                professional for medical decisions.
              </p>
            </div>
          </div>

          {/* SMALL INFORMATION NOTE */}

          <div className="medicine-data-note">
            <Info size={16} />

            <span>
              Information shown may vary by medicine, source,
              and available labeling data.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MedicineAnalyzerPage;
