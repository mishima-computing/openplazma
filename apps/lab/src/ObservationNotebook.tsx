export interface ObservationNotebookProps {
  observation: string;
  hypothesis: string;
  onObservationChange: (value: string) => void;
  onHypothesisChange: (value: string) => void;
}

export function ObservationNotebook({
  observation,
  hypothesis,
  onObservationChange,
  onHypothesisChange
}: ObservationNotebookProps) {
  return (
    <section className="panel notebook-panel" aria-labelledby="notebook-heading">
      <div className="panel-heading">
        <p className="eyebrow">Observation Notebook</p>
        <h2 id="notebook-heading">Notes</h2>
      </div>
      <label>
        Observation
        <textarea
          value={observation}
          onChange={(event) => onObservationChange(event.currentTarget.value)}
          placeholder="Record what you notice in the selected signal."
          rows={5}
        />
      </label>
      <label>
        Hypothesis
        <input
          value={hypothesis}
          onChange={(event) => onHypothesisChange(event.currentTarget.value)}
          placeholder="Optional"
        />
      </label>
    </section>
  );
}
