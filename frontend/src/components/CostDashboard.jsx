import React, { useState } from "react";
import {
  DollarSign,
  TrendingDown,
  Cpu,
  Database,
  RotateCcw,
  Sparkles,
  PieChart as PieIcon,
  BarChart3,
  Activity
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from "recharts";

const METHOD_COLORS = {
  deterministic_fact: "#10b981",
  deterministic_table: "#06b6d4",
  llm_fallback: "#8b5cf6",
  unknown: "#f43f5e",
  cached: "#3b82f6"
};

function CostDashboard({ costData, onResetCosts }) {
  const [filterMethod, setFilterMethod] = useState("all");

  const stats = costData?.stats || {};
  const recentQueries = costData?.recent_queries || [];
  const baselineCost = costData?.baseline_potential_cost || 0;
  const estimatedSavings = costData?.estimated_savings || 0;
  const savingsPct = costData?.savings_percentage || 0;

  const totalQueries = stats.total_queries || 0;
  const totalCost = stats.total_cost || 0;
  const llmCalls = stats.llm_calls || 0;
  const deterministicCalls = Math.max(0, totalQueries - llmCalls);
  const deterministicWinRate = totalQueries > 0 ? Math.round((deterministicCalls / totalQueries) * 100) : 100;

  // Prepare chart data for query history
  const historyData = recentQueries.map((q, idx) => ({
    name: `#${idx + 1}`,
    cost: Number(q.total_cost || 0),
    tokens: Number(q.total_tokens || 0),
    duration: Number(q.duration_ms || 0),
    method: q.method || "unknown"
  })).reverse();

  // Method distribution for pie chart
  const methodCounts = recentQueries.reduce((acc, q) => {
    const m = q.method || "unknown";
    acc[m] = (acc[m] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.keys(methodCounts).map((key) => ({
    name: key.replace(/_/g, " "),
    value: methodCounts[key],
    rawKey: key
  }));

  // Filtered queries for ledger
  const filteredQueries = recentQueries.filter((q) => {
    if (filterMethod === "all") return true;
    if (filterMethod === "llm") return q.llm_used;
    if (filterMethod === "deterministic") return !q.llm_used;
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* KPI Cards Row */}
      <div className="kpi-grid">
        {/* Total Spend */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Total Spend</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}>
              <DollarSign size={18} />
            </div>
          </div>
          <div className="kpi-val" style={{ color: "#34d399" }}>
            ${Number(totalCost).toFixed(6)}
          </div>
          <p className="kpi-subtitle">Actual expenditure across all retrieval & LLM calls</p>
        </div>

        {/* Estimated Savings */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Cost Saved</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(99, 102, 241, 0.15)", color: "#818cf8" }}>
              <TrendingDown size={18} />
            </div>
          </div>
          <div className="kpi-val" style={{ color: "#818cf8" }}>
            ${Number(estimatedSavings).toFixed(4)}
          </div>
          <p className="kpi-subtitle">
            <strong style={{ color: "#34d399" }}>{savingsPct}% saved</strong> vs brute-force LLM routing
          </p>
        </div>

        {/* Deterministic Win Rate */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Deterministic Win Rate</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(6, 182, 212, 0.15)", color: "#06b6d4" }}>
              <Cpu size={18} />
            </div>
          </div>
          <div className="kpi-val" style={{ color: "#38bdf8" }}>
            {deterministicWinRate}%
          </div>
          <p className="kpi-subtitle">
            {deterministicCalls} of {totalQueries} queries answered without LLM fees
          </p>
        </div>

        {/* Queries Count */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Queries Processed</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" }}>
              <Activity size={18} />
            </div>
          </div>
          <div className="kpi-val">{totalQueries}</div>
          <p className="kpi-subtitle">
            Avg query cost: ${Number(stats.average_cost || 0).toFixed(6)}
          </p>
        </div>
      </div>

      {/* Visual Analytics Charts */}
      <div className="charts-grid">
        {/* Cost & Latency History Chart */}
        <div className="glass-card chart-card">
          <div className="card-title-group">
            <h3>
              <BarChart3 size={18} color="#818cf8" />
              <span>Query Cost Progression ($)</span>
            </h3>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Recent executions</span>
          </div>

          {historyData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={historyData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" stroke="#475569" fontSize={12} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={12} tickLine={false} tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#111827",
                      borderColor: "rgba(255,255,255,0.1)",
                      borderRadius: 8,
                      fontSize: 12
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cost"
                    name="Cost ($)"
                    stroke="#818cf8"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#costGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state">
              <p>Run queries in the Intelligence Studio to view live cost progression.</p>
            </div>
          )}
        </div>

        {/* Method Distribution Pie Chart */}
        <div className="glass-card chart-card">
          <div className="card-title-group">
            <h3>
              <PieIcon size={18} color="#06b6d4" />
              <span>Extraction Method Distribution</span>
            </h3>
          </div>

          {pieData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={METHOD_COLORS[entry.rawKey] || "#64748b"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#111827",
                      borderColor: "rgba(255,255,255,0.1)",
                      borderRadius: 8,
                      fontSize: 12
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    formatter={(val) => (
                      <span style={{ color: "#94a3b8", fontSize: "0.78rem" }}>{val}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state">
              <p>No query executions recorded yet.</p>
            </div>
          )}
        </div>
      </div>

      {/* Query Audit Ledger */}
      <div className="glass-card">
        <div className="card-title-group">
          <h3>
            <Database size={18} color="#10b981" />
            <span>Query Audit & Telemetry Ledger</span>
          </h3>

          <div className="ledger-header-controls">
            <select
              value={filterMethod}
              onChange={(e) => setFilterMethod(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Queries</option>
              <option value="deterministic">Deterministic ($0 LLM)</option>
              <option value="llm">LLM Invocations</option>
            </select>

            <button
              type="button"
              className="btn-secondary"
              onClick={onResetCosts}
              title="Reset cost session counters"
            >
              <RotateCcw size={14} />
              <span>Reset Counters</span>
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Query</th>
                <th>Routing Method</th>
                <th>LLM Invoked</th>
                <th>Tokens</th>
                <th>Latency</th>
                <th>Query Cost</th>
              </tr>
            </thead>
            <tbody>
              {filteredQueries.length > 0 ? (
                filteredQueries.map((item, idx) => (
                  <tr key={idx}>
                    <td className="query-cell" title={item.query}>
                      {item.query}
                    </td>
                    <td>
                      <span
                        className={`badge-method ${
                          item.llm_used ? "llm" : "deterministic"
                        }`}
                        style={{ fontSize: "0.72rem" }}
                      >
                        {item.method ? item.method.replace(/_/g, " ") : "Direct"}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: item.llm_used ? "#fb7185" : "#34d399", fontWeight: 600 }}>
                        {item.llm_used ? "Yes" : "No ($0)"}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
                        {item.total_tokens || 0}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
                        {Number(item.duration_ms || 0).toFixed(1)} ms
                      </span>
                    </td>
                    <td>
                      <strong style={{ color: "#34d399", fontFamily: "var(--font-mono)" }}>
                        ${Number(item.total_cost || 0).toFixed(6)}
                      </strong>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                    No queries logged in this session yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default CostDashboard;
