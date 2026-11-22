import React from "react";
import {
  BrainCircuit,
  BarChart3,
  FolderArchive,
  Search,
  Zap
} from "lucide-react";

function Navbar({ activeTab, setActiveTab, isOnline }) {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand section */}
        <div className="brand-section">
          <div className="brand-icon-wrapper">
            <BrainCircuit size={22} className="brand-icon" />
          </div>
          <div className="brand-info">
            <h1>KnowledgeEngine</h1>
            <p>Cost-Aware Hybrid Retrieval & Grounded Intelligence</p>
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
            <span>Query Studio</span>
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
          {/* Engine Status indicator */}
          <div className="status-indicator">
            <div className="status-dot-wrapper">
              <span
                className={`status-dot ${isOnline ? "" : "disconnected"}`}
                title={isOnline ? "Knowledge Engine Online" : "Engine Backend Offline"}
              />
              {isOnline && <span className="status-dot-pulse" />}
            </div>
            <span className="status-label">{isOnline ? "Engine Ready" : "Offline"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
