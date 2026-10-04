export default function ParameterGrid({ parameters = [], onChange }) {
  return (
    <div className="parameter-grid">
      {parameters.map(({ key, label, value, min = 0.1, step = 0.1 }) => (
        <label key={key}>
          {key} · {label}
          <input
            aria-label={`${key} · ${label}`}
            type="number"
            min={min}
            step={step}
            value={value ?? ""}
            onChange={(event) => onChange?.(key, event.target.value)}
          />
        </label>
      ))}
    </div>
  );
}
