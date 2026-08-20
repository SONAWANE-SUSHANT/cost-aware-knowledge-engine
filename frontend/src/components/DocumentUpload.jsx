import { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

function DocumentUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    setFile(selectedFile || null);
    setMessage("");
    setError("");
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a document first.");
      return;
    }

    setUploading(true);
    setMessage("");
    setError("");

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API_URL}/documents/upload/index`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let errorMessage = "Document upload failed.";

        try {
          const errorData = await response.json();

          errorMessage =
            errorData.detail || errorMessage;
        } catch (_) {}

        throw new Error(errorMessage);
      }

      const data = await response.json();

      console.log("Upload response:", data);

      setMessage(
        `${file.name} uploaded and indexed successfully.`
      );

      setFile(null);

      document.getElementById("document-file").value = "";

    } catch (err) {
      console.error(err);

      setError(
        err.message || "Unable to upload document."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="upload-card">

      <div className="card-header">
        <div>
          <h2>Upload Document</h2>

          <p className="upload-description">
            Upload a document to add it to the knowledge engine.
          </p>
        </div>
      </div>

      <div className="upload-area">

        <input
          id="document-file"
          type="file"
          onChange={handleFileChange}
        />

        {file && (
          <div className="selected-file">
            <span>
              Selected:
            </span>

            <strong>
              {file.name}
            </strong>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="upload-button"
        >
          {uploading
            ? "Uploading..."
            : "Upload & Index"}
        </button>

      </div>

      {message && (
        <div className="success-message">
          {message}
        </div>
      )}

      {error && (
        <div className="upload-error">
          {error}
        </div>
      )}

    </section>
  );
}

export default DocumentUpload;