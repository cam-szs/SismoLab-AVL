import { useState } from "react";

// The simulation clock only moves forward, in whole hours typed by the user.
export default function ClockControls({ onAdvance, simulationTime, disabled = false }) {
  const [hours, setHours] = useState("");

  const submit = (event) => {
    event.preventDefault();
    const amount = Number(hours);
    if (!Number.isInteger(amount) || amount < 1) return;
    onAdvance?.(amount);
    setHours("");
  };

  return (
    <form className="clock-form" aria-label="Controles del reloj" onSubmit={submit}>
      {simulationTime && (
        <p className="clock-now">
          Reloj actual: <strong>{simulationTime.replace("T", " ").replace("Z", "")} UTC</strong>
        </p>
      )}
      <label>
        <span>Avanzar (horas)</span>
        <input
          name="hours"
          type="number"
          min="1"
          step="1"
          inputMode="numeric"
          placeholder="Ej: 80"
          value={hours}
          onChange={(event) => setHours(event.target.value)}
          required
        />
      </label>
      <button type="submit" className="action-button" disabled={disabled}>
        Avanzar reloj
      </button>
    </form>
  );
}
