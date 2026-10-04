export default function MapPoint({ id, left, top }) {
  return (
    <span
      className="map-point"
      style={{ left: `${left}%`, top: `${top}%` }}
      title={`Evento #${id}`}
      aria-label={`Evento #${id}`}
    />
  );
}
