import { useState } from "react";
import DocumentUpload from "./components/DocumentUpload";
import QueryBox from "./components/QueryBox";
import AnswerCard from "./components/AnswerCard";
import EvidenceCard from "./components/EvidenceCard";
import UsageCard from "./components/UsageCard";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const askQuestion = async () => {
    if (!query.trim()) {
      setError("Please enter a question.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API_URL}/queries/answer`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: query.trim(),
            top_k: 5,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Request failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setResult(data);

    } catch (err) {
      console.error(err);

      setError(
        "Unable to connect to the backend. Make sure the FastAPI server is running."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">

      <header className="header">
        <div className="header-content">

          <h1>
            Cost-Aware Knowledge Engine
          </h1>

          <p>
            Ask questions about your documents using
            intelligent retrieval.
          </p>

        </div>
      </header>

      <main className="main">
        
       <main className="main">

  <DocumentUpload />

  <QueryBox
    query={query}
    setQuery={setQuery}
    onAsk={askQuestion}
    loading={loading}
  />

  {/* existing result code */}

</main>

        {result && !loading && (
          <section className="results">

            <AnswerCard result={result} />

            <EvidenceCard
              evidence={result.evidence}
            />

            <UsageCard
              usage={result.usage}
            />

          </section>
        )}

      </main>

    </div>
  );
}

export default App;