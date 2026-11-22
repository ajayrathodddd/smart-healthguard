
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Clock3,
  Search,
  RefreshCw,
  Trash2,
  FileText,
  Pill,
  ScanLine,
  ShieldCheck,
  AlertCircle,
  ChevronDown,
} from "lucide-react";

import "./AnalysisHistoryPage.css";
import { auth } from "../firebase";
const API_URL = "http://127.0.0.1:8000/api/history/";

function formatDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getTypeIcon(type) {
  switch (type) {
    case "medicine":
      return Pill;
    case "ocr":
      return ScanLine;
    case "risk":
      return ShieldCheck;
    default:
      return FileText;
  }
}

function getTypeLabel(type) {
  const labels = {
    medicine: "Medicine Analysis",
    ocr: "OCR Scan",
    risk: "Risk Detection",
  };

  return labels[type] || "Other Analysis";
}

function formatDetail(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export default function AnalysisHistoryPage() {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);

  const [search, setSearch] = useState("");
  const [analysisType, setAnalysisType] = useState("all");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState("");

  const fetchHistory = useCallback(async (signal) => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        search: search.trim(),
        analysis_type: analysisType,
        limit: "100",
        skip: "0",
      });

           const currentUser = auth.currentUser;

      if (!currentUser) {
        throw new Error("Please log in to view your analysis history.");
      }

      const token = await currentUser.getIdToken();

      const response = await fetch(`${API_URL}?${params}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal,
      });

      if (!response.ok) {
        throw new Error(
          `Unable to load history. Server returned ${response.status}.`
        );
      }

      const data = await response.json();

      setRecords(Array.isArray(data.records) ? data.records : []);
      setTotal(Number(data.total) || 0);
    } catch (err) {
      if (err.name !== "AbortError") {
        console.error("History loading failed:", err);
        setError(err.message || "Unable to load analysis history.");
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [search, analysisType]);

  useEffect(() => {
    const controller = new AbortController();

    const timeout = setTimeout(() => {
      fetchHistory(controller.signal);
    }, 300);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [fetchHistory]);

  async function handleDelete(id) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this history record?"
    );

    if (!confirmed) return;

    setDeletingId(id);
    setError("");

    try {
           const currentUser = auth.currentUser;

      if (!currentUser) {
        throw new Error("Please log in to delete history.");
      }

      const token = await currentUser.getIdToken();

      const response = await fetch(
        `${API_URL}${encodeURIComponent(id)}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new Error(
          data.detail || "Unable to delete this history record."
        );
      }

      await fetchHistory();
    } catch (err) {
      console.error("History deletion failed:", err);
      setError(err.message || "Unable to delete history.");
    } finally {
      setDeletingId("");
    }
  }

  return (
    <div className="history-page">
      <section className="history-hero">
        <div>
          <div className="history-eyebrow">
            <Activity size={15} />
            HEALTHGUARD RECORDS
          </div>

          <h2>Analysis History</h2>

          <p>
            Review your previously analyzed medicines, OCR scans,
            and educational risk assessments.
          </p>
        </div>

        <button
          type="button"
          className="history-refresh-button"
          onClick={() => fetchHistory()}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "history-spin" : ""}
          />
          Refresh
        </button>
      </section>

      <section className="history-stats">
        <div className="history-stat-card">
          <div className="history-stat-icon">
            <Clock3 size={21} />
          </div>

          <div>
            <span>Total Records</span>
            <strong>{total}</strong>
          </div>
        </div>

        <div className="history-stat-card">
          <div className="history-stat-icon">
            <Pill size={21} />
          </div>

          <div>
            <span>Medicine Records</span>
            <strong>
              {records.filter(
                (record) => record.analysis_type === "medicine"
              ).length}
            </strong>
          </div>
        </div>

        <div className="history-stat-card">
          <div className="history-stat-icon">
            <ScanLine size={21} />
          </div>

          <div>
            <span>OCR Records</span>
            <strong>
              {records.filter(
                (record) => record.analysis_type === "ocr"
              ).length}
            </strong>
          </div>
        </div>
      </section>

      <section className="history-content-panel">
        <div className="history-panel-heading">
          <div>
            <h3>Previous Analyses</h3>
            <p>Your saved analysis records from the database.</p>
          </div>

          <span className="history-record-count">
            {total} Records
          </span>
        </div>

        <div className="history-toolbar">
          <div className="history-search">
            <Search size={18} />

            <input
              type="search"
              placeholder="Search by medicine or title..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <div className="history-filter">
            <ChevronDown size={16} />

            <select
              value={analysisType}
              onChange={(event) => setAnalysisType(event.target.value)}
              aria-label="Filter analysis type"
            >
              <option value="all">All Analyses</option>
              <option value="medicine">Medicine</option>
              <option value="ocr">OCR Scanner</option>
              <option value="risk">Risk Detection</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="history-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="history-state">
            <RefreshCw size={27} className="history-spin" />
            <h3>Loading Analysis History</h3>
            <p>Retrieving saved records from MongoDB...</p>
          </div>
        ) : records.length === 0 ? (
          <div className="history-state">
            <div className="history-empty-icon">
              <FileText size={30} />
            </div>

            <h3>No History Records Found</h3>

            <p>
              {search || analysisType !== "all"
                ? "Try changing your search or filter."
                : "Your completed medicine analyses and OCR scans will appear here."}
            </p>
          </div>
        ) : (
          <div className="history-record-list">
            {records.map((record) => {
              const Icon = getTypeIcon(record.analysis_type);

              return (
                <article
                  className="history-record"
                  key={record.id}
                >
                  <div className="history-record-icon">
                    <Icon size={21} />
                  </div>

                  <div className="history-record-main">
                    <div className="history-record-top">
                      <h4>{record.title || "Untitled Analysis"}</h4>

                      <span
                        className={`history-type-badge ${record.analysis_type}`}
                      >
                        {getTypeLabel(record.analysis_type)}
                      </span>
                    </div>

                    <p className="history-record-summary">
                      {record.summary || "No summary available."}
                    </p>

                    <div className="history-record-date">
                      <Clock3 size={14} />
                      {formatDate(record.created_at)}
                    </div>

                    {record.details &&
                      Object.keys(record.details).length > 0 && (
                        <details className="history-details">
                          <summary>View Details</summary>

                          <div className="history-details-grid">
                            {Object.entries(record.details).map(
                              ([key, value]) => (
                                <div
                                  className="history-detail-item"
                                  key={key}
                                >
                                  <span>
                                    {key
                                      .replace(/_/g, " ")
                                      .replace(/\b\w/g, (char) =>
                                        char.toUpperCase()
                                      )}
                                  </span>

                                  <strong>{formatDetail(value)}</strong>
                                </div>
                              )
                            )}
                          </div>
                        </details>
                      )}
                  </div>

                  <button
                    type="button"
                    className="history-delete-button"
                    onClick={() => handleDelete(record.id)}
                    disabled={deletingId === record.id}
                    title="Delete this record"
                    aria-label={`Delete ${record.title}`}
                  >
                    {deletingId === record.id ? (
                      <RefreshCw size={17} className="history-spin" />
                    ) : (
                      <Trash2 size={17} />
                    )}
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <div className="history-disclaimer">
        <ShieldCheck size={18} />

        <p>
          History contains educational analysis summaries. It is not
          a medical record and should not replace advice from a
          qualified healthcare professional.
        </p>
      </div>
    </div>
  );
}
