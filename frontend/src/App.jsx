import React, { useState, useEffect, useCallback } from "react";
import Navbar from "./components/Navbar";
import QueryStudio from "./components/QueryStudio";
import CostDashboard from "./components/CostDashboard";
import DocumentHub from "./components/DocumentHub";
import SearchLab from "./components/SearchLab";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [activeTab, setActiveTab] = useState("studio");
  const [isOnline, setIsOnline] = useState(true);
  const [toasts, setToasts] = useState([]);

  // Intelligence Query State
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [queryError, setQueryError] = useState("");

  // Documents State
  const [documents, setDocuments] = useState([]);
  const [systemOverview, setSystemOverview] = useState({});
  const [uploading, setUploading] = useState(false);

  // Cost Metrics State
  const [costData, setCostData] = useState({
    stats: { total_queries: 0, total_cost: 0, average_cost: 0, llm_calls: 0 },
    recent_queries: [],
    baseline_potential_cost: 0,
    estimated_savings: 0,
    savings_percentage: 0
  });

  const addToast = (message, type = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  // Health check
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) {
        setIsOnline(true);
      } else {
        setIsOnline(false);
      }
    } catch {
      setIsOnline(false);
    }
  }, []);

  // Fetch Documents
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  }, []);

  // Fetch Cost Metrics
  const fetchCostMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/metrics/costs`);
      if (res.ok) {
        const data = await res.json();
        setCostData(data);
      }
    } catch (err) {
      console.error("Failed to fetch cost metrics", err);
    }
  }, []);

  // Fetch System Overview
  const fetchSystemOverview = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/metrics/overview`);
      if (res.ok) {
        const data = await res.json();
        setSystemOverview(data);
      }
    } catch (err) {
      console.error("Failed to fetch system overview", err);
    }
  }, []);

  // Initial Data Load
  useEffect(() => {
    checkHealth();
    fetchDocuments();
    fetchCostMetrics();
    fetchSystemOverview();

    const interval = setInterval(() => {
      checkHealth();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealth, fetchDocuments, fetchCostMetrics, fetchSystemOverview]);

  // Ask Question Flow
  const handleAskQuestion = async (questionText, topK) => {
    setLoading(true);
    setQueryError("");
    setResult(null);

    const startTime = performance.now();

    try {
      const response = await fetch(`${API_URL}/queries/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: questionText,
          top_k: topK
        })
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server responded with status ${response.status}`);
      }

      const data = await response.json();
      const elapsed = Math.round(performance.now() - startTime);
      data.duration_ms = elapsed;

      setResult(data);
      addToast(
        data.llm_used
          ? "Answered using LLM fallback provider"
          : "Answered with $0 deterministic extraction!",
        "success"
      );

      // Refresh costs and overview
      fetchCostMetrics();
      fetchSystemOverview();
    } catch (err) {
      console.error(err);
      setQueryError(err.message || "Failed to process query.");
      addToast(err.message || "Query failed", "error");
    } finally {
      setLoading(false);
    }
  };

  // Upload Document Flow
  const handleUploadDocument = async (file) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/documents/upload/index`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || "Upload and indexing failed.");
      }

      const data = await response.json();
      addToast(`"${file.name}" indexed successfully!`, "success");
      fetchDocuments();
      fetchSystemOverview();
    } catch (err) {
      console.error(err);
      addToast(err.message || "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  };

  // Delete Document Flow
  const handleDeleteDocument = async (docId, filename) => {
    // Optimistically remove document from local list immediately
    setDocuments((prev) => prev.filter((d) => d.id !== docId));

    try {
      const res = await fetch(`${API_URL}/documents/${docId}`, {
        method: "DELETE"
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to delete document");
      }

      addToast(`"${filename}" deleted successfully`, "info");
      fetchDocuments();
      fetchSystemOverview();
    } catch (err) {
      console.error(err);
      addToast(err.message || "Failed to delete document", "error");
      fetchDocuments();
    }
  };

  // Fetch Single Document Details
  const handleFetchDocumentDetails = async (docId) => {
    const res = await fetch(`${API_URL}/documents/${docId}`);
    if (!res.ok) {
      throw new Error("Could not load document details");
    }
    return await res.json();
  };

  // Reset Costs Flow
  const handleResetCosts = async () => {
    if (!window.confirm("Reset all telemetry records for this session?")) return;
    try {
      const res = await fetch(`${API_URL}/metrics/costs/reset`, {
        method: "POST"
      });
      if (res.ok) {
        addToast("Cost counters reset", "info");
        fetchCostMetrics();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isOnline={isOnline}
        totalSpend={costData?.stats?.total_cost || 0}
      />

      {/* Main View Area */}
      <main className="main-content">
        {activeTab === "studio" && (
          <QueryStudio
            onAskQuestion={handleAskQuestion}
            loading={loading}
            result={result}
            error={queryError}
          />
        )}

        {activeTab === "costs" && (
          <CostDashboard
            costData={costData}
            onResetCosts={handleResetCosts}
          />
        )}

        {activeTab === "docs" && (
          <DocumentHub
            documents={documents}
            systemOverview={systemOverview}
            onUploadDocument={handleUploadDocument}
            onDeleteDocument={handleDeleteDocument}
            onFetchDocumentDetails={handleFetchDocumentDetails}
            uploading={uploading}
          />
        )}

        {activeTab === "search" && <SearchLab />}
      </main>

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;