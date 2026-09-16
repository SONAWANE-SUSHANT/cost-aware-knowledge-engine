import React, { useState } from "react";
import {
  Search,
  Sliders,
  Database,
  Layers,
  FileText,
  Tag,
  Cpu,
  BarChart2
} from "lucide-react";

const API_URL = "http://127.0.0.1:8000";

function SearchLab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [topK, setTopK] = useState(6);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchTerm.trim() || loading) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/queries/search?q=${encodeURIComponent(searchTerm.trim())}&top_k=${topK}`
      );

      if (!response.ok) {
        throw new Error(`Search failed: HTTP ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to execute search");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Search Input Card */}
      <div className="glass-card">
        <div className="card-title-group">
          <h3>
            <Search size={18} color="#06b6d4" />
            <span>Hybrid Retrieval Sandbox</span>
          </h3>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Inspect raw vector & lexical scores without generating an answer
          </span>
        </div>

        <form onSubmit={handleSearch}>
          <div className="query-box-wrapper">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Enter search keywords or semantic queries (e.g. 'invoice total', 'interview questions', 'PostgreSQL')..."
              style={{
                width: "100%",
                background: "transparent",
                border: "none",
                outline: "none",
                padding: "1.2rem",
                fontSize: "1rem",
                color: "var(--text-primary)"
              }}
            />

            <div className="query-controls-bar">
              <div className="query-settings">
                <div className="topk-control">
                  <Sliders size={14} />
                  <span>Retrieve Top:</span>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="topk-slider"
                  />
                  <span className="topk-val">{topK}</span>
                </div>
              </div>

              <button
                type="submit"
                className="btn-ask"
                disabled={!searchTerm.trim() || loading}
              >
                <Search size={15} />
                <span>{loading ? "Searching..." : "Execute Search"}</span>
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div className="toast error" style={{ marginTop: "1rem", position: "relative" }}>
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Search Results Display */}
      {results && (
        <div className="glass-card animate-fade-in">
          <div className="card-title-group">
            <h3>
              <Layers size={18} color="#818cf8" />
              <span>
                Retrieved Candidates ({results.results?.length || 0})
              </span>
            </h3>
            <span className="brand-badge">Hybrid Ranking</span>
          </div>

          <div className="evidence-grid">
            {results.results?.map((item, idx) => {
              const score = Number(item.score || 0);
              return (
                <div key={idx} className="evidence-card">
                  <div className="evidence-top">
                    <div className="evidence-source">
                      <span className="brand-badge" style={{ padding: "1px 6px" }}>
                        #{idx + 1}
                      </span>
                      <span>{item.document_name}</span>
                      {item.page_number && (
                        <span className="evidence-page-tag">p.{item.page_number}</span>
                      )}
                    </div>

                    <span className="evidence-score">Score: {score.toFixed(4)}</span>
                  </div>

                  {item.field && (
                    <div className="evidence-fact-badge">
                      <Tag size={12} />
                      <span>
                        {item.field}: <strong>{item.value}</strong>
                      </span>
                    </div>
                  )}

                  <p className="evidence-text">{item.text}</p>
                </div>
              );
            })}
          </div>

          {results.results?.length === 0 && (
            <div className="empty-state">
              <p>No matching chunks or facts found for this query.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchLab;
