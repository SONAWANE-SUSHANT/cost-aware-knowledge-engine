function AnswerCard({ result }) {
  const formatMethod = (method) => {
    if (!method) {
      return "Unknown";
    }

    return method
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  return (
    <div className="card answer-card">

      <div className="card-header">
        <h2>Answer</h2>

        <span className="method-badge">
          {formatMethod(result.method)}
        </span>
      </div>

      <div className="answer">
        {result.answer}
      </div>

      <div className="metadata">

        <div className="metadata-item">
          <span>Confidence</span>

          <strong>
            {Number(result.confidence ?? 0).toFixed(2)}
          </strong>
        </div>

        <div className="metadata-item">
          <span>LLM Used</span>

          <strong>
            {result.llm_used ? "Yes" : "No"}
          </strong>
        </div>

        <div className="metadata-item">
          <span>Cache</span>

          <strong>
            {result.cache_hit ? "Hit" : "Miss"}
          </strong>
        </div>

      </div>

    </div>
  );
}

export default AnswerCard;