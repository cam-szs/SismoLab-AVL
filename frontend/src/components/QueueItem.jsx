export default function QueueItem({ id, station, magnitude, depth, revision, position }) {
  return (
    <div className="queue-item" aria-label={`Reporte #${id}`}>
      <strong>#{id}</strong>
      <span>{station}</span>
      <small>M {magnitude} · {depth} km</small>
      {revision != null && <small>rev {revision}{position != null ? ` · posición ${position}` : ""}</small>}
    </div>
  );
}
