import React, { useState } from "react";
import {
  Sparkles,
  Send,
  Sliders,
  Copy,
  Check,
  Zap,
  Database,
  ShieldCheck,
  Cpu,
  Clock,
  Coins,
  FileText,
  Tag,
  AlertCircle,
  HelpCircle,
  Layers
} from "lucide-react";

const SUGGESTED_PROMPTS = [
  "What was the total invoice amount?",
  "What is the LR number?",
  "Summarize Sushant's backend architecture and key projects",
  "What are the database technologies used in the system?",
  "Explain the caching strategy and cost optimization logic"
];

function QueryStudio({ onAskQuestion, loading, result, error }) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [copied, setCopied] = useState(false);
  const [evidenceTab, setEvidenceTab] = useState("all");

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || loading) return;
    onAskQuestion(query.trim(), topK);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = () => {
    if (!result?.answer) return;
    navigator.clipboard.writeText(result.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatMethodName = (method) => {
    if (!method) return "Direct Extraction";
    return method
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getConfidenceLevel = (score) => {
    const s = Number(score || 0);
    if (s >= 0.8) return { label: "High", color: "#10b981", percent: Math.round(s * 100) };
    if (s >= 0.5) return { label: "Moderate", color: "#f59e0b", percent: Math.round(s * 100) };
    return { label: "Low", color: "#f43f5e", percent: Math.max(10, Math.round(s * 100)) };
  };

  const confidence = result ? getConfidenceLevel(result.confidence) : null;

  // Filter evidence based on selected tab
  const evidenceList = result?.evidence || [];
  const filteredEvidence = evidenceList.filter((item) => {
    if (evidenceTab === "facts") return Boolean(item.field);
    if (evidenceTab === "chunks") return !item.field;
    return true;
  });

  return (
    <div className="studio-grid animate-fade-in">
      {/* Query Console Card */}
      <div className="glass-card">
        {/* Quick Prompts */}
        <div className="prompts-container">
          <div className="prompts-label">
            <Sparkles size={14} color="#818cf8" />
            <span>Try sample queries:</span>
          </div>
          <div className="prompt-chips">
            {SUGGESTED_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="prompt-chip"
                onClick={() => setQuery(prompt)}
              >
                <span>{prompt}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <form onSubmit={handleSubmit}>
          <div className="query-box-wrapper">
            <textarea
              id="query-input"
              className="query-textarea"
              placeholder="Ask anything about indexed receipts, resumes, documents, or knowledge facts..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
            />

            <div className="query-controls-bar">
              <div className="query-settings">
                <div className="topk-control">
                  <Sliders size={14} />
                  <span>Top-K:</span>
                  <input
                    type="range"
                    min="1"
                    max="15"
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="topk-slider"
                  />
                  <span className="topk-val">{topK}</span>
                </div>

                <div className="keyboard-hint">
                  <kbd>Enter</kbd> to ask &bull; <kbd>Shift + Enter</kbd> newline
                </div>
              </div>

              <button
                type="submit"
                id="btn-ask-query"
                disabled={!query.trim() || loading}
                className="btn-ask"
              >
                {loading ? (
                  <>
                    <Zap size={16} className="animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    <span>Ask Engine</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Dynamic Execution Pipeline Stepper */}
        <div className="pipeline-visualizer" title="Cost-Aware Decision Pipeline Flow">
          <div className={`pipeline-step ${loading || result ? "active" : ""}`}>
            <Cpu size={13} />
            <span>1. Normalize</span>
          </div>
          <span className="pipeline-arrow">&rarr;</span>

          <div
            className={`pipeline-step ${
              result?.cache_hit ? "success" : result ? "active" : ""
            }`}
          >
            <Database size={13} />
            <span>2. Cache Check {result?.cache_hit ? "(Hit)" : ""}</span>
          </div>
          <span className="pipeline-arrow">&rarr;</span>

          <div className={`pipeline-step ${result ? "active" : ""}`}>
            <Layers size={13} />
            <span>3. Hybrid Retrieval</span>
          </div>
          <span className="pipeline-arrow">&rarr;</span>

          <div
            className={`pipeline-step ${
              result && !result.llm_used ? "success" : result ? "active" : ""
            }`}
          >
            <ShieldCheck size={13} />
            <span>4. Fact Extraction</span>
          </div>
          <span className="pipeline-arrow">&rarr;</span>

          <div
            className={`pipeline-step ${
              result?.llm_used ? "fallback" : ""
            }`}
          >
            <Zap size={13} />
            <span>
              5. LLM Fallback {result?.llm_used ? "(Engaged)" : "(Bypassed - $0)"}
            </span>
          </div>
        </div>

        {error && (
          <div className="toast error" style={{ marginTop: "1rem", position: "relative" }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Answer & Results Section */}
      {result && (
        <div className="result-container">
          {/* Answer Card */}
          <div className="answer-box">
            <div className="answer-header">
              <div className="answer-header-left">
                <span
                  className={`badge-method ${
                    result.cache_hit
                      ? "cache"
                      : result.llm_used
                      ? "llm"
                      : "deterministic"
                  }`}
                >
                  {result.cache_hit ? (
                    <Database size={13} />
                  ) : result.llm_used ? (
                    <Zap size={13} />
                  ) : (
                    <ShieldCheck size={13} />
                  )}
                  <span>
                    {result.cache_hit
                      ? "Cache Hit (0ms)"
                      : formatMethodName(result.method)}
                  </span>
                </span>

                {confidence && (
                  <div className="confidence-meter" title={`Confidence: ${confidence.percent}%`}>
                    <span>Confidence:</span>
                    <div className="confidence-bar-bg">
                      <div
                        className="confidence-bar-fill"
                        style={{
                          width: `${confidence.percent}%`,
                          backgroundColor: confidence.color
                        }}
                      />
                    </div>
                    <strong style={{ color: confidence.color }}>
                      {confidence.percent}%
                    </strong>
                  </div>
                )}
              </div>

              <button
                type="button"
                className="btn-copy"
                onClick={handleCopy}
                title="Copy answer to clipboard"
              >
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            {/* Answer Text */}
            <div className="answer-body">{result.answer}</div>

            {/* Telemetry Footer */}
            <div className="telemetry-row">
              <div className="telemetry-pill cost" title="Estimated Query Cost">
                <Coins size={14} color="#10b981" />
                <span>Cost:</span>
                <strong>${Number(result.usage?.estimated_cost || 0).toFixed(6)}</strong>
              </div>

              <div className="telemetry-pill" title="Tokens used (Prompt + Completion)">
                <Zap size={14} />
                <span>Tokens:</span>
                <strong>{result.usage?.total_tokens ?? 0}</strong>
              </div>

              <div className="telemetry-pill" title="LLM Provider invocation status">
                <Cpu size={14} />
                <span>LLM Used:</span>
                <strong style={{ color: result.llm_used ? "#fb7185" : "#34d399" }}>
                  {result.llm_used ? "Yes (Paid)" : "No (Free)"}
                </strong>
              </div>

              <div className="telemetry-pill" title="Evidence chunks retrieved">
                <FileText size={14} />
                <span>Citations:</span>
                <strong>{result.evidence?.length || 0} chunks</strong>
              </div>
            </div>
          </div>

          {/* Evidence Explorer Section */}
          <div className="glass-card evidence-section">
            <div className="evidence-header">
              <div className="card-title-group" style={{ marginBottom: 0 }}>
                <h3>
                  <FileText size={18} color="#818cf8" />
                  <span>Grounding Evidence & Citations</span>
                </h3>
              </div>

              <div className="evidence-tabs">
                <button
                  type="button"
                  className={`evidence-tab-btn ${evidenceTab === "all" ? "active" : ""}`}
                  onClick={() => setEvidenceTab("all")}
                >
                  All ({evidenceList.length})
                </button>
                <button
                  type="button"
                  className={`evidence-tab-btn ${evidenceTab === "facts" ? "active" : ""}`}
                  onClick={() => setEvidenceTab("facts")}
                >
                  Structured Facts ({evidenceList.filter((e) => e.field).length})
                </button>
                <button
                  type="button"
                  className={`evidence-tab-btn ${evidenceTab === "chunks" ? "active" : ""}`}
                  onClick={() => setEvidenceTab("chunks")}
                >
                  Passages ({evidenceList.filter((e) => !e.field).length})
                </button>
              </div>
            </div>

            {filteredEvidence.length > 0 ? (
              <div className="evidence-grid">
                {filteredEvidence.map((item, idx) => {
                  const scoreVal = Number(item.score || 0);
                  const scorePercent = Math.min(100, Math.round(scoreVal * 100));

                  return (
                    <div className="evidence-card" key={idx}>
                      <div className="evidence-top">
                        <div className="evidence-source">
                          <FileText size={15} color="#94a3b8" />
                          <span>{item.document_name || "Document"}</span>
                          {item.page_number && (
                            <span className="evidence-page-tag">
                              p.{item.page_number}
                            </span>
                          )}
                        </div>

                        <span className="evidence-score" title="Relevance Score">
                          Score: {scoreVal.toFixed(3)}
                        </span>
                      </div>

                      {item.field && (
                        <div className="evidence-fact-badge">
                          <Tag size={12} />
                          <span>
                            {item.field}: <strong>{item.value || ""}</strong>
                          </span>
                        </div>
                      )}

                      <p className="evidence-text">{item.text}</p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <p>No citations match the selected filter.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default QueryStudio;
