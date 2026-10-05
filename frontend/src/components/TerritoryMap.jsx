// Geographic plane of the scenario (0..1000 km on both axes). North (larger
// y) is drawn at the top. Fill colour = priority, a dashed ring = expensive
// access, a hollow point = archived event, a line = chosen reference link.
const SIZE = 1000;
const flipY = (y) => SIZE - y;

export default function TerritoryMap({ zones = [], points = [], associations = [], onSelect }) {
  const byId = new Map(points.map((point) => [point.id, point]));
  const links = associations
    .filter((item) => item.is_reference && byId.has(item.source_id) && byId.has(item.reference_id))
    .map((item) => ({ from: byId.get(item.source_id), to: byId.get(item.reference_id) }));

  return (
    <div className="territory">
      <svg
        className="territory-map"
        viewBox={`-80 -10 ${SIZE + 90} ${SIZE + 50}`}
        role="img"
        aria-label="Mapa del territorio con zonas y epicentros"
      >
        <rect className="territory-frame" x="0" y="0" width={SIZE} height={SIZE} />
        {[250, 500, 750].map((tick) => (
          <g key={tick} className="territory-grid">
            <line x1={tick} y1="0" x2={tick} y2={SIZE} />
            <line x1="0" y1={tick} x2={SIZE} y2={tick} />
            <text x={tick} y={SIZE + 24} textAnchor="middle">{tick}</text>
            <text x="-6" y={flipY(tick) + 8} textAnchor="end">{tick}</text>
          </g>
        ))}
        {zones.map((zone) => (
          <g key={zone.name} className={`territory-zone ${zone.populated ? "populated" : "unpopulated"}`}>
            <rect
              x={zone.x_min}
              y={flipY(zone.y_max)}
              width={zone.x_max - zone.x_min}
              height={zone.y_max - zone.y_min}
            />
            <text x={zone.x_min + 10} y={flipY(zone.y_max) + 30}>{zone.name}</text>
          </g>
        ))}
        {links.map(({ from, to }) => (
          <line
            key={`${from.id}-${to.id}`}
            className="territory-link"
            x1={from.x}
            y1={flipY(from.y)}
            x2={to.x}
            y2={flipY(to.y)}
          />
        ))}
        {points.map((point) => (
          <g
            key={point.id}
            className={`territory-point prio-${point.priority}${point.archived ? " archived" : ""}`}
            transform={`translate(${point.x} ${flipY(point.y)})`}
            onClick={() => onSelect?.(point.id)}
          >
            <title>
              {`#${point.id} · P${point.priority} · M ${Number(point.magnitude).toFixed(1)} · (${point.x}, ${point.y}) km` +
                `${point.archived ? " · archivado" : ""}${point.expensive ? " · acceso costoso" : ""}`}
            </title>
            {point.expensive && <circle className="territory-expensive" r="26" />}
            <circle r={8 + Math.max(0, Number(point.magnitude)) * 2} />
            <text y="-22" textAnchor="middle">{point.id}</text>
          </g>
        ))}
      </svg>
      <div className="territory-legend">
        <span><i className="swatch zone-populated" /> Zona poblada</span>
        <span><i className="swatch zone-unpopulated" /> Zona no poblada</span>
        <span><i className="dot prio-3" /> Prioridad alta</span>
        <span><i className="dot prio-2" /> Media</span>
        <span><i className="dot prio-1" /> Baja</span>
        <span><i className="dot hollow" /> Archivado</span>
        <span><i className="ring" /> Acceso costoso</span>
        <span><i className="link" /> Referencia elegida</span>
      </div>
    </div>
  );
}
