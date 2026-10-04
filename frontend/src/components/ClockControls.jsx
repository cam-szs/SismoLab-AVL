export default function ClockControls({ onAdvance }) {
  return (
    <div className="clock-actions" aria-label="Controles del reloj">
      <button type="button" onClick={() => onAdvance?.(1)}>+1</button>
      <button type="button" onClick={() => onAdvance?.(5)}>+5</button>
      <button type="button" onClick={() => onAdvance?.(10)}>+10</button>
    </div>
  );
}
