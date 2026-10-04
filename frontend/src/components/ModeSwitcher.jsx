export default function ModeSwitcher({ value, modes = [], onChange, disabled = false }) {
  return (
    <div className="mode-switcher" aria-label="Selector de modos">
      {modes.map((mode) => (
        <button
          key={mode.value}
          type="button"
          className={value === mode.value ? "active" : ""}
          onClick={() => onChange?.(mode.value)}
          disabled={disabled}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
