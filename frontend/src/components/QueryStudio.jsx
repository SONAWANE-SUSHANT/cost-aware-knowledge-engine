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
  FileText,
  Tag,
  AlertCircle,
  Layers,
  ArrowRight,
  TrendingUp,
  FileCode,
  FileCheck,
  CheckCircle2,
  HelpCircle
} from "lucide-react";

const SUGGESTED_PROMPTS = [
  { text: "What was the total invoice amount?", category: "Billing", icon: "receipt" },
  { text: "What is the LR number and vehicle number?", category: "Logistics", icon: "truck" },
  { text: "Summarize Sushant's backend architecture and key projects", category: "Technical", icon: "cpu" },
  { text: "What are the database technologies used in the system?", category: "Architecture", icon: "database" },
  { text: "Explain the caching strategy and cost optimization logic", category: "Strategy", icon: "sparkles" }
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
    if (s >= 0.8) return { label: "High Confidence", color: "#10b981", percent: Math.round(s * 100), bg: "rgba(16, 185, 129, 0.15)" };
    if (s >= 0.5) return { label: "Moderate Confidence", color: "#f59e0b", percent: Math.round(s * 100), bg: "rgba(245, 158, 11, 0.15)" };
    return { label: "Low Confidence", color: "#f43f5e", percent: Math.max(10, Math.round(s * 100)), bg: "rgba(244, 63, 94, 0.15)" };
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
      <div className="glass-card query-console-card">
        {/* Quick Prompts */}
        <div className="prompts-container">
          <div className="prompts-label">
            <Sparkles size={14} color="#818cf8" />
            <span>Interactive Prompts</span>
          </div>
          <div className="prompt-chips">
            {SUGGESTED_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="prompt-chip"
                onClick={() => setQuery(prompt.text)}
              >
                <span className="prompt-chip-cat">{prompt.category}</span>
                <span className="prompt-chip-text">{prompt.text}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <form onSubmit={handleSubmit}>
          <div className={`query-box-wrapper ${loading ? "is-loading" : ""}`}>
            <textarea
              id="query-input"
              className="query-textarea"
              placeholder="Ask anything about indexed receipts, invoices, technical docs, or knowledge facts..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
            />

            <div className="query-controls-bar">
              <div className="query-settings">
                <div className="topk-control">
                  <Sliders size={14} color="#818cf8" />
                  <span>Citations Top-K:</span>
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
                className={`btn-ask ${loading ? "loading-active" : ""}`}
              >
                {loading ? (
                  <>
                    <Zap size={16} className="animate-spin" />
                    <span>Routing Query...</span>
                  </>
                ) : (
                  <>
                    <Send size={15} />
                    <span>Run Query</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Dynamic Execution Pipeline Stepper */}
        <div className="pipeline-wrapper">
          <div className="pipeline-title">Execution Pipeline Route</div>
          <div className="pipeline-visualizer" title="Cost-Aware Decision Pipeline Flow">
            <div className={`pipeline-step ${loading || result ? "active" : ""}`}>
              <Cpu size={14} />
              <div className="step-content">
                <span className="step-num">01</span>
                <span className="step-name">Query Normalizer</span>
              </div>
            </div>
            
            <div className={`pipeline-track ${result ? "completed" : loading ? "pulsing" : ""}`} />

            <div
              className={`pipeline-step ${
                result?.cache_hit ? "success" : result ? "active" : ""
              }`}
            >
              <Database size={14} />
              <div className="step-content">
                <span className="step-num">02</span>
                <span className="step-name">
                  Cache {result?.cache_hit ? "(Hit)" : ""}
                </span>
              </div>
            </div>

            <div className={`pipeline-track ${result ? "completed" : loading ? "pulsing" : ""}`} />

            <div className={`pipeline-step ${result ? "active" : ""}`}>
              <Layers size={14} />
              <div className="step-content">
                <span className="step-num">03</span>
                <span className="step-name">Hybrid RAG</span>
              </div>
            </div>

            <div className={`pipeline-track ${result ? "completed" : loading ? "pulsing" : ""}`} />

            <div
              className={`pipeline-step ${
                result && !result.llm_used ? "success" : result ? "active" : ""
              }`}
            >
              <ShieldCheck size={14} />
              <div className="step-content">
                <span className="step-num">04</span>
                <span className="step-name">Fact Extraction</span>
              </div>
            </div>

            <div className={`pipeline-track ${result?.llm_used ? "fallback" : ""}`} />

            <div
              className={`pipeline-step ${
                result?.llm_used ? "fallback" : result ? "bypassed" : ""
              }`}
            >
              <Zap size={14} />
              <div className="step-content">
                <span className="step-num">05</span>
                <span className="step-name">
                  {result?.llm_used ? "LLM Invoked" : "LLM Bypassed"}
                </span>
              </div>
            </div>
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
            <div className="answer-glow-backdrop" />
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
                    <Database size={14} />
                  ) : result.llm_used ? (
                    <Zap size={14} />
                  ) : (
                    <ShieldCheck size={14} />
                  )}
                  <span>
                    {result.cache_hit
                      ? "Cache Hit (Instant)"
                      : formatMethodName(result.method)}
                  </span>
                </span>

                {confidence && (
                  <div
                    className="confidence-meter"
                    title={`Model Grounding Confidence: ${confidence.percent}%`}
                    style={{ background: confidence.bg }}
                  >
                    <CheckCircle2 size={13} color={confidence.color} />
                    <span>{confidence.label}:</span>
                    <strong style={{ color: confidence.color }}>
                      {confidence.percent}%
                    </strong>
                  </div>
                )}
              </div>

              <button
                type="button"
                className={`btn-copy ${copied ? "copied" : ""}`}
                onClick={handleCopy}
                title="Copy answer to clipboard"
              >
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? "Copied to Clipboard" : "Copy Answer"}</span>
              </button>
            </div>

            {/* Answer Text */}
            <div className="answer-body">{result.answer}</div>

            {/* Telemetry Footer */}
            <div className="telemetry-row">
              <div className="telemetry-pill cost" title="Estimated Query Execution Cost">
                <TrendingUp size={14} color="#10b981" />
                <span>Engine Cost:</span>
                <strong>{Number(result.usage?.estimated_cost || 0).toFixed(6)}</strong>
              </div>

              <div className="telemetry-pill" title="Tokens used (Prompt + Completion)">
                <Zap size={14} color="#818cf8" />
                <span>Tokens:</span>
                <strong>{result.usage?.total_tokens ?? 0}</strong>
              </div>

              <div className="telemetry-pill" title="Execution latency">
                <Clock size={14} color="#38bdf8" />
                <span>Latency:</span>
                <strong>{result.duration_ms || 12} ms</strong>
              </div>

              <div className="telemetry-pill" title="LLM Provider invocation status">
                <Cpu size={14} color={result.llm_used ? "#fb7185" : "#34d399"} />
                <span>LLM Used:</span>
                <strong style={{ color: result.llm_used ? "#fb7185" : "#34d399" }}>
                  {result.llm_used ? "Yes (Synthesis)" : "No (Direct Lookup)"}
                </strong>
              </div>

              <div className="telemetry-pill" title="Retrieved grounding citations">
                <FileText size={14} color="#c084fc" />
                <span>Citations:</span>
                <strong>{result.evidence?.length || 0} retrieved</strong>
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
                  All Sources ({evidenceList.length})
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
                  const isPdf = item.document_name?.toLowerCase().endsWith(".pdf");
                  const isDocx = item.document_name?.toLowerCase().endsWith(".docx");

                  return (
                    <div className="evidence-card" key={idx}>
                      <div className="evidence-top">
                        <div className="evidence-source">
                          <span className={`file-badge ${isPdf ? "pdf" : isDocx ? "docx" : "txt"}`}>
                            {isPdf ? "PDF" : isDocx ? "DOCX" : "TXT"}
                          </span>
                          <span className="source-name" title={item.document_name}>
                            {item.document_name || "Document"}
                          </span>
                          {item.page_number && (
                            <span className="evidence-page-tag">
                              p.{item.page_number}
                            </span>
                          )}
                        </div>

                        <div className="evidence-score-pill" title="Similarity / Hybrid Relevance Score">
                          <span className="score-label">Score</span>
                          <strong className="score-val">{scoreVal.toFixed(3)}</strong>
                        </div>
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
