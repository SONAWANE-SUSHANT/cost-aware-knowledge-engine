function UsageCard({ usage = {} }) {
  return (
    <div className="card">

      <div className="card-header">
        <h2>Usage</h2>
      </div>

      <div className="usage-grid">

        <div className="usage-item">
          <span>Prompt Tokens</span>

          <strong>
            {usage.prompt_tokens ?? 0}
          </strong>
        </div>

        <div className="usage-item">
          <span>Completion Tokens</span>

          <strong>
            {usage.completion_tokens ?? 0}
          </strong>
        </div>

        <div className="usage-item">
          <span>Total Tokens</span>

          <strong>
            {usage.total_tokens ?? 0}
          </strong>
        </div>

        <div className="usage-item">
          <span>Estimated Cost</span>

          <strong>
            ${usage.estimated_cost ?? 0}
          </strong>
        </div>

      </div>
    </div>
  );
}

export default UsageCard;