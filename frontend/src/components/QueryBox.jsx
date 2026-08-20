function QueryBox({
  query,
  setQuery,
  onAsk,
  loading,
}) {
  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onAsk();
    }
  };

  return (
    <section className="query-card">
      <label htmlFor="query">
        Ask a question
      </label>

      <textarea
        id="query"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Example: What was the total amount?"
        rows={4}
      />

      <div className="query-footer">
        <span className="hint">
          Press Enter to ask
        </span>

        <button
          onClick={onAsk}
          disabled={loading}
        >
          {loading ? "Processing..." : "Ask Question"}
        </button>
      </div>
    </section>
  );
}

export default QueryBox;