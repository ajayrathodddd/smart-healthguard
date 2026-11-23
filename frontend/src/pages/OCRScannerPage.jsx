import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Camera,
  CheckCircle2,
  CircleAlert,
  FileImage,
  Info,
  Loader2,
  Pill,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Upload,
  Volume2,
  X,
} from "lucide-react";

import "./OCRScannerPage.css";
import { auth } from "../firebase";
import {
  generateVoiceExplanation,
  getAudioUrl,
} from "../voice/services/voiceApi";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "kn", label: "Kannada" },
  { code: "mr", label: "Marathi" },
  { code: "bn", label: "Bengali" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "ml", label: "Malayalam" },
  { code: "gu", label: "Gujarati" },
  { code: "pa", label: "Punjabi" },
  { code: "or", label: "Odia" },
  { code: "as", label: "Assamese" },
  { code: "bho", label: "Bhojpuri" },
];

function formatText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          return (
            item.text || item.description || item.name || JSON.stringify(item)
          );
        }

        return String(item);
      })
      .filter(Boolean)
      .join("\n");
  }

  if (typeof value === "object") {
    return (
      value.text ||
      value.description ||
      value.name ||
      JSON.stringify(value, null, 2)
    );
  }

  return String(value);
}

function normalizeResult(data) {
  if (!data || typeof data !== "object") {
    return {};
  }

  if (data.data && typeof data.data === "object") {
    return {
      ...data,
      ...data.data,
    };
  }

  return data;
}

function getMedicineName(medicine) {
  if (!medicine || typeof medicine !== "object") {
    return "";
  }

  return (
    medicine.name ||
    medicine.medicine_name ||
    medicine.brand_name ||
    medicine.generic_name ||
    medicine.active_ingredient ||
    medicine.matched_name ||
    medicine.product_name ||
    ""
  );
}

function getMedicineField(medicine, keys) {
  if (!medicine || typeof medicine !== "object") {
    return "";
  }

  for (const key of keys) {
    if (
      medicine[key] !== undefined &&
      medicine[key] !== null &&
      String(medicine[key]).trim() !== ""
    ) {
      return formatText(medicine[key]);
    }
  }

  return "";
}

function splitList(value) {
  const text = formatText(value);

  if (!text) {
    return [];
  }

  return text
    .split(/\n|[Ã¢â‚¬Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢]|;/)
    .map((item) => item.replace(/^[-*]\s*/, "").trim())
    .filter(Boolean);
}

function getSpeechLanguage(language) {
  const mapping = {
    en: "en-IN",
    hi: "hi-IN",
    kn: "kn-IN",
    mr: "mr-IN",
    bn: "bn-IN",
    ta: "ta-IN",
    te: "te-IN",
    ml: "ml-IN",
    gu: "gu-IN",
    pa: "pa-IN",
    or: "or-IN",
    as: "as-IN",
    bho: "bho-IN",
  };

  return mapping[language] || "en-IN";
}

function getErrorMessage(error) {
  if (!error) {
    return "Something went wrong while processing the image.";
  }

  if (error.name === "AbortError") {
    return "Medicine analysis is taking longer than expected. Please try again.";
  }

  return error.message || "Unable to process the medicine image.";
}

export default function OCRScannerPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const streamRef = useRef(null);
  const previewUrlRef = useRef(null);

  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const [language, setLanguage] = useState("en");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState("");

  // Only trust medicine-specific information when the backend explicitly
  // reports medicine_found: true.
  const medicineVerified = result?.medicine_found === true;
  const medicine = medicineVerified
    ? result?.medicine || result?.matched_medicine || null
    : null;

  const brandVerified =
    medicineVerified &&
    (result?.match_type === "verified_brand" ||
      medicine?.ocr_match_type === "verified_brand");

  const genericStrengthVerified =
    medicineVerified &&
    (result?.match_type === "verified_generic_strength_brand_unverified" ||
      medicine?.data_status === "generic_strength_verified_brand_unverified");

  const extractedText =
    formatText(
      result?.extracted_text ||
        result?.ocr_text ||
        result?.text ||
        result?.raw_text,
    ) || "No readable text was detected.";

  // OCR-detected identity is display-only until independently verified.
  const ocrIdentity = result?.ocr_identity || result?.identity || {};
  const ocrDetectedBrand = formatText(
    ocrIdentity.brand_name || result?.ocr_brand_name || "",
  );
  const ocrDetectedGeneric = formatText(
    ocrIdentity.generic_name ||
      ocrIdentity.generic ||
      result?.ocr_generic_name ||
      "",
  );
  const ocrDetectedStrength = formatText(
    ocrIdentity.strength ||
      result?.ocr_strength ||
      result?.detected_strength ||
      "",
  );
  const ocrDetectedForm = formatText(
    ocrIdentity.dosage_form ||
      ocrIdentity.medicine_type ||
      result?.ocr_dosage_form ||
      "",
  );
  const hasOcrIdentity = Boolean(
    ocrDetectedBrand ||
    ocrDetectedGeneric ||
    ocrDetectedStrength ||
    ocrDetectedForm,
  );
  const medicineName = medicineVerified ? getMedicineName(medicine) : "";

  const manufacturer = medicineVerified
    ? getMedicineField(medicine, [
        "manufacturer",
        "manufacturer_name",
        "company",
        "brand_owner",
      ])
    : "";

  const composition = medicineVerified
    ? getMedicineField(medicine, [
        "composition",
        "active_ingredients",
        "ingredients",
        "salt",
        "active_ingredient",
        "generic_name",
      ])
    : "";

  const medicineType = medicineVerified
    ? getMedicineField(medicine, [
        "medicine_type",
        "type",
        "dosage_form",
        "form",
      ])
    : "";

  const ocrStrengthMatch = extractedText.match(
    /\b(1000|750|650|500|325|250|200|100|50)\s*(mg|mcg|g)\b/i,
  );

  const verifiedStrength =
    result?.ocr_strength || result?.detected_strength || result?.strength || "";

  const packSize = medicineVerified
    ? getMedicineField(medicine, [
        "pack_size",
        "package_size",
        "quantity",
        "strength",
        "indian_pack_size",
        "ocr_strength",
      ]) ||
      formatText(verifiedStrength) ||
      (ocrStrengthMatch ? `${ocrStrengthMatch[1]} ${ocrStrengthMatch[2]}` : "")
    : "";

  const route = medicineVerified
    ? getMedicineField(medicine, ["route", "administration_route"])
    : "";

  const rxnormId = medicineVerified
    ? getMedicineField(medicine, ["rxnorm_id", "rx_norm_id", "rxcui"]) ||
      formatText(result?.rxcui || result?.rxnorm_id || result?.rx_norm_id || "")
    : "";

  const medicineInformation = medicineVerified
    ? formatText(
        result?.medicine_information ||
          medicine?.information ||
          medicine?.medicine_description ||
          medicine?.description ||
          medicine?.indications ||
          medicine?.purpose,
      )
    : "";

  const sideEffects = medicineVerified
    ? splitList(
        result?.side_effects ||
          result?.side_effect ||
          medicine?.side_effects ||
          medicine?.adverse_reactions,
      )
    : [];

  const warnings = medicineVerified
    ? splitList(
        result?.warnings ||
          result?.warning ||
          result?.precautions ||
          medicine?.warnings ||
          medicine?.precautions,
      )
    : [];

  const interactions = medicineVerified
    ? splitList(
        result?.drug_interactions ||
          result?.interactions ||
          medicine?.drug_interactions ||
          medicine?.interactions,
      )
    : [];

  const contraindications = medicineVerified
    ? splitList(result?.contraindications || medicine?.contraindications)
    : [];

  const sources = medicineVerified
    ? Array.isArray(result?.sources)
      ? result.sources
      : Array.isArray(medicine?.sources)
        ? medicine.sources
        : []
    : [];

  const informationSources =
    medicineVerified &&
    medicine?.information_sources &&
    typeof medicine.information_sources === "object"
      ? medicine.information_sources
      : {};

  function getSectionSourceCaption(section) {
    const sectionSources = informationSources?.[section];

    if (!Array.isArray(sectionSources) || sectionSources.length === 0) {
      return "";
    }

    return `Source${sectionSources.length > 1 ? "s" : ""}: ${sectionSources.join(", ")}`;
  }

  useEffect(() => {
    if (cameraOpen && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [cameraOpen]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }

      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOpen(false);
  }

  async function startCamera() {
    setCameraError("");
    setError("");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError("Camera access is not supported by this browser.");
      return;
    }

    try {
      stopCamera();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: {
            ideal: "environment",
          },
          width: {
            ideal: 1920,
          },
          height: {
            ideal: 1080,
          },
        },
        audio: false,
      });

      streamRef.current = stream;
      setCameraOpen(true);
    } catch (cameraErr) {
      console.error(cameraErr);

      setCameraError(
        "Camera permission was denied or the camera is unavailable. Allow camera access in your browser and try again.",
      );
    }
  }

  function createPreview(file) {
    if (!file) {
      return;
    }

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
    }

    const url = URL.createObjectURL(file);

    previewUrlRef.current = url;

    setPreviewUrl(url);
    setSelectedImage(file);
  }

  function handleImageSelect(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setError("");
    setCameraError("");
    setResult(null);

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("Image size is too large. Please select an image below 10 MB.");
      return;
    }

    stopCamera();
    createPreview(file);
  }

  function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      return;
    }

    if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      setCameraError(
        "Camera is still starting. Please wait a moment and try again.",
      );
      return;
    }

    const width = video.videoWidth;
    const height = video.videoHeight;

    if (!width || !height) {
      setCameraError("Unable to capture the camera frame. Please try again.");
      return;
    }

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");

    if (!context) {
      setCameraError("Unable to capture the image.");
      return;
    }

    context.drawImage(video, 0, 0, width, height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError("Unable to create the captured image.");
          return;
        }

        const file = new File([blob], `healthguard-scan-${Date.now()}.jpg`, {
          type: "image/jpeg",
        });

        createPreview(file);
        stopCamera();
      },
      "image/jpeg",
      0.92,
    );
  }

  async function analyzeImage() {
    if (!selectedImage) {
      setError("Please select or capture a medicine package image first.");
      return;
    }

    setIsAnalyzing(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", selectedImage);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000);

    try {
      const response = await fetch(`${API_BASE_URL}/api/ocr/analyze`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      const contentType = response.headers.get("content-type") || "";

      let data;

      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();

        data = {
          success: response.ok,
          extracted_text: text,
        };
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            `OCR request failed with status ${response.status}.`,
        );
      }

      const normalizedResult = normalizeResult(data);

      // Display OCR results even if history saving fails.
      setResult(normalizedResult);

      // Save only a compact OCR summary, never the uploaded image
      // or raw extracted OCR text.
      try {
        const verified = normalizedResult?.medicine_found === true;

        const matchedMedicine = verified
          ? normalizedResult?.medicine ||
            normalizedResult?.matched_medicine ||
            null
          : null;

        const detectedMedicineName = verified
          ? getMedicineName(matchedMedicine)
          : "";

        const historyTitle = detectedMedicineName || "Unverified OCR Scan";

        const historySummary = verified
          ? "OCR scan completed and medicine identity verified."
          : "OCR scan completed. Medicine identity was not verified.";

        const historyDetails = {
          medicine_verified: verified,
        };

        if (verified && matchedMedicine) {
          historyDetails.manufacturer =
            getMedicineField(matchedMedicine, [
              "manufacturer",
              "manufacturer_name",
              "company",
              "brand_owner",
            ]) || "Not available";

          historyDetails.composition =
            getMedicineField(matchedMedicine, [
              "composition",
              "active_ingredients",
              "ingredients",
              "salt",
              "active_ingredient",
              "generic_name",
            ]) || "Not available";

          historyDetails.strength =
            getMedicineField(matchedMedicine, [
              "strength",
              "pack_size",
              "package_size",
              "quantity",
            ]) || "Not available";
        }

        // Get the currently authenticated Firebase user.
        const currentUser = auth.currentUser;

        if (!currentUser) {
          throw new Error("Please log in to save OCR history.");
        }

        // Generate a Firebase ID token for backend authentication.
        const token = await currentUser.getIdToken();

        const historyResponse = await fetch(`${API_BASE_URL}/api/history/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            analysis_type: "ocr",
            title: historyTitle,
            summary: historySummary,
            details: historyDetails,
          }),
        });

        if (!historyResponse.ok) {
          console.warn(
            "OCR history save failed:",
            await historyResponse.text(),
          );
        } else {
          console.log("OCR analysis saved to history.");
        }
      } catch (historyError) {
        console.error("Unable to save OCR history:", historyError);
      }
    } catch (analyzeError) {
      console.error("OCR analysis failed:", analyzeError);
      setError(getErrorMessage(analyzeError));
    } finally {
      clearTimeout(timeoutId);
      setIsAnalyzing(false);
    }
  }

  function clearScan() {
    stopCamera();

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }

    setSelectedImage(null);
    setPreviewUrl("");
    setResult(null);
    setError("");
    setCameraError("");
    setVoiceAudioUrl("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function speakText() {
    if (isSpeaking) {
      const audio = document.getElementById("ocr-voice-audio");
      if (audio) {
        audio.pause();
      } else if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsSpeaking(false);
      return;
    }

    try {
      setIsTranslating(true);
      setError("");

      const voiceName = medicineVerified
        ? (medicineName || composition || "Verified medicine")
        : "Unverified OCR medicine package";

      const voiceDescription = medicineVerified
        ? medicineInformation
        : "Medicine identity could not be verified. The following OCR text was extracted. " +
          extractedText.slice(0, 350);

      const data = await generateVoiceExplanation(
        voiceName,
        language,
        {
          composition,
          description: voiceDescription,
          sideEffects: sideEffects,
          warnings: warnings,
        },
      );

      const audioUrl = getAudioUrl(data.audio_file);
      setVoiceAudioUrl(audioUrl);

      setTimeout(() => {
        const audio = document.getElementById("ocr-voice-audio");
        if (!audio) {
          setError("Unable to play the generated voice.");
          return;
        }

        audio.onended = () => setIsSpeaking(false);
        audio.onerror = () => {
          setIsSpeaking(false);
          setError("Unable to play the generated voice.");
        };

        audio.play()
          .then(() => setIsSpeaking(true))
          .catch(() => {
            setIsSpeaking(false);
            setError("The browser blocked audio playback.");
          });
      }, 100);
    } catch (speechError) {
      console.error("Voice error:", speechError);
      setIsTranslating(false);
      setIsSpeaking(false);

      if (
        typeof window !== "undefined" &&
        window.speechSynthesis &&
        typeof window.SpeechSynthesisUtterance !== "undefined"
      ) {
        const fallbackText = medicineVerified
          ? [
              medicineName ? `Medicine: ${medicineName}.` : "",
              medicineInformation
                ? `Information: ${medicineInformation}.`
                : "",
              sideEffects.length
                ? `Side effects: ${sideEffects.join(", ")}.`
                : "",
              warnings.length
                ? `Warnings: ${warnings.join(". ")}.`
                : "",
            ].filter(Boolean).join(" ")
          : `Medicine identity could not be verified. ${extractedText.slice(0, 350)}`;

        const utterance = new SpeechSynthesisUtterance(fallbackText);
        utterance.lang = getSpeechLanguage(language);
        utterance.rate = 0.9;
        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => {
          setIsSpeaking(false);
          setError("Voice playback is unavailable for this language.");
        };
        window.speechSynthesis.speak(utterance);
        setError("");
      } else {
        setError(
          speechError.message ||
          "Unable to generate voice in this language.",
        );
      }
    } finally {
      setIsTranslating(false);
    }
  }

  return (
    <div className="ocr-page">
      <main className="ocr-page-container">
        {/* HERO */}

        <section className="ocr-hero">
          <div className="ocr-badge-row">
            <span className="ocr-badge ocr-badge-primary">
              <ScanLine size={14} />
              AI OCR Scanner
            </span>

            <span className="ocr-badge ocr-badge-success">
              <span className="ocr-online-dot" />
              System Online
            </span>
          </div>

          <h1 className="ocr-hero-title">
            Scan a medicine package
            <span> with AI</span>
          </h1>

          <p className="ocr-hero-description">
            Upload any medicine package image or use your camera. Smart
            HealthGuard will attempt to extract whatever text is readable. Smart
            HealthGuard extracts readable information and organizes the
            available medicine details.
          </p>

          <div className="ocr-feature-pills">
            <span className="ocr-feature-pill">OCR extraction</span>
            <span className="ocr-feature-pill">Medicine matching</span>
            <span className="ocr-feature-pill">Voice assistance</span>
          </div>
        </section>

        {/* ERROR */}

        {error && (
          <div className="ocr-error ocr-section">
            <AlertCircle size={18} />

            <div>
              <strong>OCR processing error</strong>
              <div>{error}</div>
            </div>

            <button
              type="button"
              className="ocr-close-button"
              onClick={() => setError("")}
            >
              <X size={15} />
            </button>
          </div>
        )}

        {/* CAMERA */}

        {cameraOpen && (
          <section className="ocr-camera ocr-section">
            <div className="ocr-panel-header">
              <div>
                <div className="ocr-panel-title">Camera Scanner</div>
                <div className="ocr-panel-subtitle">
                  Position the medicine package inside the camera frame.
                </div>
              </div>

              <button
                type="button"
                className="ocr-secondary-button"
                onClick={stopCamera}
              >
                <X size={14} />
                Close Camera
              </button>
            </div>

            <div className="ocr-camera-stage">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="ocr-camera-video"
              />

              <div className="ocr-camera-overlay">
                <div className="ocr-camera-frame" />
              </div>
            </div>

            <div className="ocr-camera-footer">
              <button
                type="button"
                className="ocr-primary-button"
                onClick={capturePhoto}
              >
                <Camera size={18} />
                Capture Package
              </button>
            </div>
          </section>
        )}

        <canvas ref={canvasRef} className="ocr-hidden" />

        {/* CAMERA ERROR */}

        {cameraError && (
          <div className="ocr-error ocr-section">
            <CircleAlert size={18} />

            <div>
              <strong>Camera unavailable</strong>
              <div>{cameraError}</div>
            </div>
          </div>
        )}

        {/* SCAN OPTIONS */}

        {!cameraOpen && !result && !selectedImage && (
          <section className="ocr-section">
            <div className="ocr-section-header">
              <h2 className="ocr-section-title">Scan Medicine Package</h2>
              <p className="ocr-section-description">
                Choose how you want to scan the medicine package.
              </p>
            </div>

            <div className="ocr-scan-grid">
              <button
                type="button"
                className="ocr-scan-card"
                onClick={startCamera}
              >
                <div className="ocr-scan-card-content">
                  <div className="ocr-scan-icon">
                    <Camera size={23} />
                  </div>

                  <div>
                    <div className="ocr-scan-card-title">Scan with Camera</div>
                    <div className="ocr-scan-card-description">
                      Capture the medicine package directly using your device
                      camera.
                    </div>

                    <span className="ocr-scan-card-link">
                      Open Camera
                      <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              </button>

              <button
                type="button"
                className="ocr-scan-card"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="ocr-scan-card-content">
                  <div className="ocr-scan-icon green">
                    <Upload size={23} />
                  </div>

                  <div>
                    <div className="ocr-scan-card-title">Upload Image</div>
                    <div className="ocr-scan-card-description">
                      Upload any medicine package image. OCR will attempt to
                      read blurry, dark, tilted, and partially visible images
                      too.
                    </div>

                    <span className="ocr-scan-card-link green-link">
                      Choose Image
                      <ArrowRight size={13} />
                    </span>
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="ocr-hidden"
                  onChange={handleImageSelect}
                />
              </button>
            </div>

            <div className="ocr-info-strip">
              <Info size={16} />
              <span>
                All supported image qualities are accepted. Smart HealthGuard
                attempts to extract readable text from blurry, dark, tilted, and
                partially visible images.
              </span>
            </div>

            <div className="ocr-feature-grid">
              <div className="ocr-feature-card">
                <div className="ocr-feature-card-inner">
                  <div className="ocr-feature-icon">
                    <ScanLine size={17} />
                  </div>

                  <div>
                    <div className="ocr-feature-title">OCR Extraction</div>
                    <div className="ocr-feature-description">
                      Extract readable package text.
                    </div>
                  </div>
                </div>
              </div>

              <div className="ocr-feature-card">
                <div className="ocr-feature-card-inner">
                  <div className="ocr-feature-icon green-feature">
                    <Pill size={17} />
                  </div>

                  <div>
                    <div className="ocr-feature-title">
                      Medicine Information
                    </div>
                    <div className="ocr-feature-description">
                      Organize available medicine data.
                    </div>
                  </div>
                </div>
              </div>

              <div className="ocr-feature-card">
                <div className="ocr-feature-card-inner">
                  <div className="ocr-feature-icon purple-feature">
                    <Volume2 size={17} />
                  </div>

                  <div>
                    <div className="ocr-feature-title">Voice Assistance</div>
                    <div className="ocr-feature-description">
                      {medicineVerified ? "Listen to verified medicine information." : "Medicine identity is unverified. Voice playback will read only the text extracted from the package."}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* SELECTED IMAGE */}

        {selectedImage && !result && (
          <section className="ocr-panel ocr-section">
            <div className="ocr-panel-header">
              <div>
                <div className="ocr-panel-title">Selected Medicine Package</div>
                <div className="ocr-panel-subtitle">
                  Review the image before starting OCR analysis.
                </div>
              </div>

              <button
                type="button"
                className="ocr-secondary-button danger-button"
                onClick={clearScan}
              >
                <X size={14} />
                Remove
              </button>
            </div>

            <div className="ocr-selected-grid">
              <div className="ocr-image-preview">
                {previewUrl ? (
                  <img src={previewUrl} alt="Selected medicine package" />
                ) : (
                  <div className="ocr-empty-image">
                    <FileImage size={42} />
                  </div>
                )}
              </div>

              <div className="ocr-selected-info">
                <div className="ocr-file-card">
                  <div className="ocr-file-icon">
                    <FileImage size={19} />
                  </div>

                  <div className="ocr-file-details">
                    <div className="ocr-file-name">{selectedImage.name}</div>
                    <div className="ocr-file-meta">
                      {(selectedImage.size / (1024 * 1024)).toFixed(2)} MB
                      {" ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ "}
                      {selectedImage.type || "image"}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  className="ocr-primary-button ocr-analyze-button"
                  onClick={analyzeImage}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 size={18} className="ocr-spin" />
                      Analyzing Package...
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      Analyze Medicine
                    </>
                  )}
                </button>

                <div className="ocr-small-note">
                  Your image is processed through the Smart HealthGuard OCR
                  service.
                </div>
              </div>
            </div>
          </section>
        )}

        {/* LOADING */}

        {isAnalyzing && (
          <section className="ocr-loading ocr-section">
            <div className="ocr-loading-icon">
              <ScanLine size={27} className="ocr-loading-scan" />
            </div>

            <h2 className="ocr-loading-title">Analyzing medicine package</h2>

            <p className="ocr-loading-description">
              Smart HealthGuard is extracting readable text from the image and
              organizing the available information.
            </p>

            <div className="ocr-loading-bar">
              <span />
            </div>
          </section>
        )}

        {/* RESULTS */}

        {result && !isAnalyzing && (
          <section className="ocr-section">
            <div className="ocr-result-header">
              <div className="ocr-result-left">
                <div className="ocr-result-icon">
                  <CheckCircle2 size={23} />
                </div>

                <div>
                  <div className="ocr-result-label">OCR ANALYSIS RESULT</div>

                  <h2 className="ocr-result-title">
                    Text extracted successfully
                  </h2>

                  <p className="ocr-result-description">
                    Review the information detected from your medicine package.
                  </p>
                </div>
              </div>

              <div className="ocr-result-actions">
                <button
                  type="button"
                  className="ocr-secondary-button"
                  onClick={analyzeImage}
                  disabled={isAnalyzing}
                >
                  <RefreshCw size={14} />
                  Analyze Again
                </button>

                <button
                  type="button"
                  className="ocr-secondary-button danger-button"
                  onClick={clearScan}
                >
                  <X size={14} />
                  Clear Scan
                </button>
              </div>
            </div>

            {/* PACKAGE PREVIEW + EXTRACTED TEXT */}

            <div
              className="ocr-result-grid"
              style={{ gridTemplateColumns: "minmax(0, 1fr)" }}
            >
              <div className="ocr-panel">
                <div className="ocr-panel-header">
                  <div>
                    <div className="ocr-panel-title">Package Preview</div>
                    <div className="ocr-panel-subtitle">
                      Scanned medicine package
                    </div>
                  </div>

                  <ShieldCheck size={19} className="ocr-cyan-icon" />
                </div>

                <div className="ocr-panel-body">
                  <div className="ocr-image-preview">
                    {previewUrl ? (
                      <img src={previewUrl} alt="Scanned medicine package" />
                    ) : (
                      <div className="ocr-empty-image">
                        <FileImage size={42} />
                      </div>
                    )}
                  </div>

                  <div className="ocr-image-meta">
                    <div className="ocr-image-meta-name">
                      {selectedImage?.name || "Medicine package"}
                    </div>
                    <div className="ocr-image-meta-sub">
                      Image scanned by Smart HealthGuard
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {hasOcrIdentity && !medicineVerified && (
              <div className="ocr-panel" style={{ marginBottom: "18px" }}>
                <div className="ocr-panel-body">
                  <div className="ocr-result-label">
                    SCANNER-DETECTED PACKAGE DETAILS
                  </div>
                  <p style={{ margin: "8px 0 14px", color: "#b7791f" }}>
                    Unverified OCR text - these details have not been confirmed
                    against a trusted medicine source.
                  </p>
                  {[
                    ["Brand detected", ocrDetectedBrand],
                    ["Ingredient detected", ocrDetectedGeneric],
                    ["Strength detected", ocrDetectedStrength],
                    ["Dosage form detected", ocrDetectedForm],
                  ]
                    .filter(([, value]) => value)
                    .map(([label, value]) => (
                      <div
                        key={label}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          padding: "8px 0",
                          borderBottom: "1px solid rgba(128,128,128,0.2)",
                        }}
                      >
                        <span>{label}</span>
                        <strong style={{ textAlign: "right" }}>{value}</strong>
                      </div>
                    ))}
                </div>
              </div>
            )}
            {/* MEDICINE MATCH */}

            <div className="ocr-panel ocr-result-panel">
              <div className="ocr-panel-body">
                <div className="ocr-result-section-header">
                  <div className="ocr-result-section-icon green">
                    <Pill size={19} />
                  </div>

                  <div>
                    <div className="ocr-result-label green-label">
                      {brandVerified
                        ? "BRAND VERIFIED"
                        : genericStrengthVerified
                          ? "INGREDIENT + STRENGTH VERIFIED"
                          : "MEDICINE NOT VERIFIED"}
                    </div>

                    <h3 className="ocr-medicine-name">
                      {medicineVerified && medicineName
                        ? medicineName
                        : result?.verification_message
                              ?.toLowerCase()
                              .includes(
                                "generic medicine and strength were verified",
                              )
                          ? "Generic medicine verified ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â brand unverified"
                          : "Medicine identity could not be verified"}
                    </h3>
                    <p className="ocr-panel-subtitle">
                      {medicineVerified
                        ? result?.verification_message ||
                          "Medicine information was verified by the backend."
                        : "Only extracted package text is available. No medicine record is confirmed."}
                    </p>
                  </div>
                </div>

                {medicineVerified && medicineName && (
                  <div className="ocr-data-grid">
                    <DataCard label="Manufacturer" value={manufacturer} />
                    <DataCard label="Composition" value={composition} />
                    <DataCard label="Medicine Type" value={medicineType} />
                    <DataCard label="Pack / Strength" value={packSize} />
                    <DataCard label="Route" value={route} />
                    <DataCard label="RxNorm ID" value={rxnormId} />
                  </div>
                )}
              </div>
            </div>

            {/* INFORMATION + VOICE */}

            <div className="ocr-two-column">
              <div className="ocr-info-card">
                <div className="ocr-info-card-header">
                  <div className="ocr-info-icon">
                    <Info size={19} />
                  </div>

                  <div>
                    <div className="ocr-card-title">Medicine Information</div>

                    <div className="ocr-card-subtitle">
                      {medicineVerified
                        ? [
                            "Available information from the backend.",
                            getSectionSourceCaption("medicine_information"),
                          ]
                            .filter(Boolean)
                            .join(" ")
                        : "Medicine-specific information is hidden until identity is verified."}
                    </div>
                  </div>
                </div>

                <div className="ocr-text-box ocr-information-box">
                  {medicineVerified && medicineInformation ? (
                    <div className="ocr-text">{medicineInformation}</div>
                  ) : (
                    <div className="ocr-empty-text">
                      {medicineVerified
                        ? "No medicine information was returned for this scan."
                        : "No verified medicine information is available. Review the extracted text and confirm the package with a pharmacist."}
                    </div>
                  )}
                </div>
              </div>

              <div className="ocr-voice-panel">
                <div className="ocr-info-card-header">
                  <div className="ocr-info-icon purple">
                    <Volume2 size={19} />
                  </div>

                  <div>
                    <div className="ocr-card-title">Voice Assistance</div>
                    <div className="ocr-card-subtitle">
                      {medicineVerified ? "Listen to verified medicine information." : "Medicine identity is unverified. Voice playback will read only the text extracted from the package."}
                    </div>
                  </div>
                </div>

                <label className="ocr-field-label">Language</label>

                <select
                  value={language}
                  onChange={(event) => {
                    setLanguage(event.target.value);
                    setVoiceAudioUrl("");
                    setIsSpeaking(false);
                  }}
                  className="ocr-language-select"
                >
                  {LANGUAGES.map((item) => (
                    <option key={item.code} value={item.code}>
                      {item.label}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  className="ocr-voice-button"
                  onClick={speakText}
                  disabled={isTranslating}
                >
                  {isTranslating ? (
                    <>
                      <Loader2 size={16} className="ocr-spin" />
                      Translating...
                    </>
                  ) : isSpeaking ? (
                    <>
                      <X size={16} />
                      Stop Voice
                    </>
                  ) : (
                    <>
                      <Volume2 size={16} />
                      Read Information
                    </>
                  )}
                </button>

                {voiceAudioUrl && (
                  <audio
                    id="ocr-voice-audio"
                    controls
                    preload="metadata"
                    className="ocr-voice-audio"
                  >
                    <source src={voiceAudioUrl} type="audio/mpeg" />
                  </audio>
                )}

                <p className="ocr-small-note">
                  Voice playback uses your browser's speech synthesis support.
                </p>
              </div>
            </div>

            {/* SIDE EFFECTS */}

            <ResultListSection
              title="Side Effects"
              subtitle={[
                "Side-effect information is shown only when it can be matched to a verified medicine.",
                getSectionSourceCaption("side_effects"),
              ]
                .filter(Boolean)
                .join(" ")}
              icon={<CircleAlert size={19} />}
              iconClass="orange"
              items={sideEffects}
              emptyText={
                medicineVerified
                  ? "No side-effect information was returned for this scan."
                  : "Medicine identity could not be verified. Side-effect information is withheld because it cannot safely be linked to this package."
              }
            />

            {/* WARNINGS */}

            <div className="ocr-info-card ocr-warning-section">
              <div className="ocr-info-card-header">
                <div className="ocr-info-icon red">
                  <AlertCircle size={19} />
                </div>

                <div>
                  <div className="ocr-card-title">Warnings & Precautions</div>
                  <div className="ocr-card-subtitle">
                    Safety information is displayed only when the medicine identity is verified.
                    {getSectionSourceCaption("warnings") &&
                      ` ${getSectionSourceCaption("warnings")}`}
                  </div>
                </div>
              </div>

              <div className="ocr-warning-list">
                {warnings.length > 0 ? (
                  warnings.map((warning, index) => (
                    <div key={`${warning}-${index}`} className="ocr-warning">
                      <div className="ocr-warning-title">
                        Safety Information
                      </div>
                      <div className="ocr-warning-text">{warning}</div>
                    </div>
                  ))
                ) : (
                  <div className="ocr-empty-box">
                    {medicineVerified
                      ? "No warning or precaution information was returned for this scan."
                      : "Medicine identity could not be verified. Product-specific warnings and precautions are withheld to avoid displaying potentially incorrect safety information."}
                  </div>
                )}
              </div>
            </div>

            {/* CONTRAINDICATIONS */}

            <ResultListSection
              title="Contraindications"
              subtitle={[
                "Contraindications can only be displayed after the medicine identity is verified against a trusted source.",
                getSectionSourceCaption("contraindications"),
              ]
                .filter(Boolean)
                .join(" ")}
              icon={<AlertCircle size={19} />}
              iconClass="red"
              items={contraindications}
              emptyText={
                medicineVerified
                  ? "No contraindication information was returned for this scan."
                  : "Medicine identity could not be verified. Product-specific contraindications cannot safely be confirmed."
              }
            />

            {/* INTERACTIONS */}

            <ResultListSection
              title="Drug Interactions"
              subtitle={[
                "Drug interaction information requires a verified medicine identity.",
                getSectionSourceCaption("drug_interactions"),
              ]
                .filter(Boolean)
                .join(" ")}
              icon={<ShieldCheck size={19} />}
              iconClass="orange"
              items={interactions}
              emptyText={
                medicineVerified
                  ? "No interaction information was returned for this scan."
                  : "Medicine identity could not be verified. Drug interactions cannot safely be confirmed for this package."
              }
              interaction
            />

            {/* SOURCES */}

            {sources.length > 0 && (
              <div className="ocr-info-card">
                <div className="ocr-info-card-header">
                  <div className="ocr-info-icon">
                    <FileImage size={19} />
                  </div>

                  <div>
                    <div className="ocr-card-title">Information Sources</div>
                    <div className="ocr-card-subtitle">
                      Sources returned by the backend.
                    </div>
                  </div>
                </div>

                <div className="ocr-source-list">
                  {sources.map((source, index) => {
                    const label =
                      typeof source === "string"
                        ? source
                        : source?.name ||
                          source?.title ||
                          source?.source ||
                          source?.url ||
                          `Source ${index + 1}`;

                    const url = typeof source === "object" ? source?.url : null;

                    return (
                      <div key={`${label}-${index}`} className="ocr-source">
                        {url ? (
                          <a
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="ocr-source-link"
                          >
                            {label}
                          </a>
                        ) : (
                          <span>{label}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* SAFETY NOTICE */}

            <div className="ocr-safety">
              <ShieldCheck size={19} className="ocr-safety-icon" />

              <div>
                <div className="ocr-safety-title">
                  Educational Information Notice
                </div>

                <div className="ocr-safety-text">
                  Smart HealthGuard provides educational information extracted
                  from medicine packaging and available data sources. OCR
                  results may contain mistakes. This information should not be
                  used as a diagnosis, prescription, or replacement for advice
                  from a qualified healthcare professional.
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

/* =========================================================
   SMALL REUSABLE COMPONENTS
   ========================================================= */

function DataCard({ label, value }) {
  return (
    <div className="ocr-data-card">
      <div className="ocr-data-label">{label}</div>

      <div className="ocr-data-value">
        {value || <span className="ocr-not-available">Not available</span>}
      </div>
    </div>
  );
}

function ResultListSection({
  title,
  subtitle,
  icon,
  iconClass,
  items,
  emptyText,
  interaction = false,
}) {
  return (
    <div className="ocr-info-card">
      <div className="ocr-info-card-header">
        <div className={`ocr-info-icon ${iconClass}`}>{icon}</div>

        <div>
          <div className="ocr-card-title">{title}</div>
          <div className="ocr-card-subtitle">{subtitle}</div>
        </div>
      </div>

      {items.length > 0 ? (
        <div className={interaction ? "ocr-interaction-grid" : "ocr-list"}>
          {items.map((item, index) => (
            <div
              key={`${item}-${index}`}
              className={interaction ? "ocr-interaction" : "ocr-list-item"}
            >
              {!interaction && <span className="ocr-list-dot" />}
              <span>{item}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="ocr-empty-box">{emptyText}</div>
      )}
    </div>
  );
}
