function EvidenceCard({ evidence = [] }) {
  return (
    <div className="card">

      <div className="card-header">
        <h2>Evidence</h2>

        <span className="count-badge">
          {evidence.length}
        </span>
      </div>

      <div className="evidence-list">

        {evidence.length > 0 ? (
          evidence.map((item, index) => (

            <div
              className="evidence-item"
              key={`${item.document_id}-${index}`}
            >

              <div className="evidence-top">

                <div>
                  <span className="evidence-number">
                    {index + 1}
                  </span>

                  <strong>
                    {item.document_name}
                  </strong>
                </div>

                <span className="score">
                  Score: {item.score}
                </span>

              </div>

              {item.field && (
                <div className="evidence-field">

                  <strong>
                    {item.field}
                  </strong>

                  {item.value && (
                    <span>
                      {item.value}
                    </span>
                  )}

                </div>
              )}

              <p className="evidence-text">
                {item.text}
              </p>

            </div>

          ))
        ) : (
          <p className="empty">
            No evidence available.
          </p>
        )}

      </div>
    </div>
  );
}

export default EvidenceCard;