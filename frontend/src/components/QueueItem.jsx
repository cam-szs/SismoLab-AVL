export default function QueueItem({ id, station, magnitude, depth }) {
  return (
    <div className="queue-item" aria-label={`Reporte #${id}`}>
      <strong>#{id}</strong>
      <span>{station}</span>
      <small>M {magnitude} · {depth} km</small>
    </div>
  );
}
