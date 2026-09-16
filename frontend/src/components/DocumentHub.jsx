import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  Trash2,
  Eye,
  CheckCircle2,
  AlertCircle,
  FolderArchive,
  Layers,
  Tag,
  Hash,
  X,
  Database
} from "lucide-react";

function DocumentHub({
  documents = [],
  systemOverview = {},
  onUploadDocument,
  onDeleteDocument,
  onFetchDocumentDetails,
  uploading
}) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedDocDetails, setSelectedDocDetails] = useState(null);
  const [modalTab, setModalTab] = useState("facts");
  const [loadingDocId, setLoadingDocId] = useState(null);
  const [docToDelete, setDocToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  const confirmDelete = async () => {
    if (!docToDelete) return;
    setDeleting(true);
    try {
      await onDeleteDocument(docToDelete.id, docToDelete.filename);
      setDocToDelete(null);
    } catch (err) {
      console.error(err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    const validExtensions = [".pdf", ".docx", ".pptx", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      alert(`Unsupported file format. Please upload ${validExtensions.join(", ")}`);
      return;
    }
    onUploadDocument(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleInspect = async (docId) => {
    setLoadingDocId(docId);
    try {
      const details = await onFetchDocumentDetails(docId);
      setSelectedDocDetails(details);
      setModalTab(details.facts?.length ? "facts" : "chunks");
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDocId(null);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Knowledge Base Summary Stats */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Indexed Documents</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(99, 102, 241, 0.15)", color: "#818cf8" }}>
              <FolderArchive size={18} />
            </div>
          </div>
          <div className="kpi-val">{systemOverview.documents ?? documents.length}</div>
          <p className="kpi-subtitle">Active documents in knowledge store</p>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Extracted Chunks</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(6, 182, 212, 0.15)", color: "#06b6d4" }}>
              <Layers size={18} />
            </div>
          </div>
          <div className="kpi-val">{systemOverview.chunks ?? 0}</div>
          <p className="kpi-subtitle">Sliding-window & semantic chunks</p>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Structured Facts</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}>
              <Tag size={18} />
            </div>
          </div>
          <div className="kpi-val" style={{ color: "#34d399" }}>
            {systemOverview.facts ?? 0}
          </div>
          <p className="kpi-subtitle">Enables $0 direct deterministic lookup</p>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-title">Vector Embeddings</span>
            <div className="kpi-icon-circle" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" }}>
              <Database size={18} />
            </div>
          </div>
          <div className="kpi-val">{systemOverview.embeddings ?? 0}</div>
          <p className="kpi-subtitle">Indexed vectors for semantic search</p>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        className={`dropzone-container ${dragActive ? "drag-active" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          onChange={handleFileChange}
          className="file-input-hidden"
        />

        <div className="dropzone-icon">
          <UploadCloud size={28} />
        </div>

        <div>
          <div className="dropzone-title">
            {uploading ? "Extracting & Indexing Document..." : "Upload Document to Knowledge Engine"}
          </div>
          <div className="dropzone-subtitle">
            Drag & drop PDF, DOCX, PPTX, or TXT file here or click to browse
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.2rem" }}>
          <span className="brand-badge">PDF</span>
          <span className="brand-badge">DOCX</span>
          <span className="brand-badge">PPTX</span>
          <span className="brand-badge">TXT</span>
        </div>
      </div>

      {/* Documents Catalog Card */}
      <div className="glass-card">
        <div className="card-title-group">
          <h3>
            <FolderArchive size={18} color="#818cf8" />
            <span>Document Repository ({documents.length})</span>
          </h3>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Type</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Facts</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.length > 0 ? (
                documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <FileText size={16} color="#818cf8" />
                        <strong style={{ color: "#f8fafc" }}>{doc.filename}</strong>
                      </div>
                    </td>
                    <td>
                      <span className="brand-badge" style={{ textTransform: "uppercase" }}>
                        {doc.file_type ? doc.file_type.replace(".", "") : "TXT"}
                      </span>
                    </td>
                    <td>{doc.pages_count || 1}</td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)" }}>{doc.chunks_count || 0}</span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          color: doc.facts_count > 0 ? "#34d399" : "var(--text-muted)",
                          fontWeight: doc.facts_count > 0 ? 600 : 400
                        }}
                      >
                        {doc.facts_count || 0}
                      </span>
                    </td>
                    <td>
                      <span className="badge-method deterministic" style={{ fontSize: "0.72rem" }}>
                        <CheckCircle2 size={12} />
                        <span>Indexed</span>
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => handleInspect(doc.id)}
                          disabled={loadingDocId === doc.id}
                          title="Inspect Chunks and Extracted Facts"
                        >
                          <Eye size={13} />
                          <span>{loadingDocId === doc.id ? "Loading..." : "Inspect"}</span>
                        </button>

                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ color: "#fb7185", borderColor: "rgba(244, 63, 94, 0.2)" }}
                          onClick={() => setDocToDelete(doc)}
                          title="Delete from knowledge base"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "2.5rem" }}>
                    No documents indexed yet. Upload one above to get started!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Inspector Modal */}
      {selectedDocDetails && (
        <div className="modal-overlay" onClick={() => setSelectedDocDetails(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <FileText size={18} color="#818cf8" />
                <span>{selectedDocDetails.filename}</span>
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedDocDetails(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: "0.75rem 1.5rem", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem" }}>
              <button
                type="button"
                className={`evidence-tab-btn ${modalTab === "facts" ? "active" : ""}`}
                onClick={() => setModalTab("facts")}
              >
                Structured Facts ({selectedDocDetails.facts?.length || 0})
              </button>
              <button
                type="button"
                className={`evidence-tab-btn ${modalTab === "chunks" ? "active" : ""}`}
                onClick={() => setModalTab("chunks")}
              >
                Chunks ({selectedDocDetails.chunks?.length || 0})
              </button>
              <button
                type="button"
                className={`evidence-tab-btn ${modalTab === "pages" ? "active" : ""}`}
                onClick={() => setModalTab("pages")}
              >
                Raw Pages ({selectedDocDetails.pages?.length || 0})
              </button>
            </div>

            <div className="modal-body">
              {modalTab === "facts" && (
                <div>
                  {selectedDocDetails.facts?.length > 0 ? (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.75rem" }}>
                      {selectedDocDetails.facts.map((fact, i) => (
                        <div key={i} className="evidence-card" style={{ padding: "0.85rem" }}>
                          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                            {fact.section ? `${fact.section} &bull; ` : ""}p.{fact.page_number}
                          </div>
                          <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "#a5b4fc" }}>
                            {fact.field}
                          </div>
                          <div style={{ fontSize: "0.95rem", color: "#f8fafc", marginTop: "2px", fontWeight: 500 }}>
                            {fact.value}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <p>No structured key-value facts were extracted for this document.</p>
                    </div>
                  )}
                </div>
              )}

              {modalTab === "chunks" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {selectedDocDetails.chunks?.map((chunk, i) => (
                    <div key={i} className="evidence-card">
                      <div className="evidence-top">
                        <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "#818cf8" }}>
                          #{i + 1} &bull; {chunk.strategy} (p.{chunk.page_number})
                        </span>
                        <span className="brand-badge">{chunk.chunk_type}</span>
                      </div>
                      <p className="evidence-text" style={{ maxHeight: "120px" }}>{chunk.text}</p>
                    </div>
                  ))}
                </div>
              )}

              {modalTab === "pages" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {selectedDocDetails.pages?.map((page, i) => (
                    <div key={i} className="evidence-card">
                      <div className="evidence-top">
                        <strong>Page {page.page_number}</strong>
                      </div>
                      <p className="evidence-text" style={{ maxHeight: "200px" }}>{page.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {docToDelete && (
        <div className="modal-overlay" onClick={() => !deleting && setDocToDelete(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: "480px" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 style={{ color: "#fb7185" }}>
                <Trash2 size={18} />
                <span>Delete Document</span>
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => !deleting && setDocToDelete(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <p style={{ color: "#e2e8f0", fontSize: "0.95rem" }}>
                Are you sure you want to delete{" "}
                <strong style={{ color: "#f8fafc" }}>"{docToDelete.filename}"</strong>?
              </p>
              <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                This will permanently remove the document along with all its extracted text passages,
                sliding-window chunks, semantic chunks, vector embeddings, and structured facts.
              </p>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={deleting}
                  onClick={() => setDocToDelete(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  id="btn-confirm-delete"
                  disabled={deleting}
                  onClick={confirmDelete}
                  style={{
                    background: "linear-gradient(135deg, #e11d48 0%, #be123c 100%)",
                    color: "white",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    padding: "7px 16px",
                    fontWeight: 600,
                    fontSize: "0.86rem",
                    cursor: deleting ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem"
                  }}
                >
                  <Trash2 size={14} />
                  <span>{deleting ? "Deleting..." : "Delete Permanently"}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentHub;
