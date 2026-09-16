import React from "react";
import {
  BrainCircuit,
  BarChart3,
  FolderArchive,
  Search,
  Zap,
  Activity,
  DollarSign
} from "lucide-react";

function Navbar({ activeTab, setActiveTab, isOnline, totalSpend = 0, modelName = "openai/gpt-4o-mini" }) {
  const formatCost = (val) => {
    const num = Number(val || 0);
    return `$${num.toFixed(6)}`;
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand section */}
        <div className="brand-section">
          <div className="brand-icon-wrapper">
            <BrainCircuit size={22} />
          </div>
          <div className="brand-info">
            <h1>
              KnowledgeEngine
              <span className="brand-badge">Cost-Aware</span>
            </h1>
            <p>Hybrid Retrieval & Intelligent Extraction</p>
          </div>
        </div>

        {/* View switcher tabs */}
        <nav className="nav-tabs" aria-label="Main Navigation">
          <button
            id="tab-studio"
            className={`nav-tab-btn ${activeTab === "studio" ? "active" : ""}`}
            onClick={() => setActiveTab("studio")}
          >
            <Zap size={16} />
            <span>Intelligence Studio</span>
          </button>

          <button
            id="tab-costs"
            className={`nav-tab-btn ${activeTab === "costs" ? "active" : ""}`}
            onClick={() => setActiveTab("costs")}
          >
            <BarChart3 size={16} />
            <span>Cost Analytics</span>
          </button>

          <button
            id="tab-docs"
            className={`nav-tab-btn ${activeTab === "docs" ? "active" : ""}`}
            onClick={() => setActiveTab("docs")}
          >
            <FolderArchive size={16} />
            <span>Document Hub</span>
          </button>

          <button
            id="tab-search"
            className={`nav-tab-btn ${activeTab === "search" ? "active" : ""}`}
            onClick={() => setActiveTab("search")}
          >
            <Search size={16} />
            <span>Retrieval Lab</span>
          </button>
        </nav>

        {/* Status & Live Telemetry */}
        <div className="nav-telemetry">
          <div className="model-pill" title="Active configured LLM fallback model">
            <Zap size={12} />
            <span>{modelName.replace("openai/", "")}</span>
          </div>

          <div className="cost-ticker" title="Cumulative estimated engine spend">
            <DollarSign size={13} />
            <span>{formatCost(totalSpend)}</span>
          </div>

          <div className="status-indicator">
            <span
              className={`status-dot ${isOnline ? "" : "disconnected"}`}
              title={isOnline ? "Engine API Connected" : "Engine API Offline"}
            />
            <span>{isOnline ? "Live" : "Offline"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
