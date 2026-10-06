// Geographic plane of the scenario (0..1000 km on both axes), drawn as an
// SVG where 1 unit = 1 km. North (larger y) is at the top, so every y is
// flipped. The coast, river and relief are decoration only: zones, stations
// and epicenters are the data. Fill colour = priority, size = magnitude,
// hollow = archived, dashed ring = expensive access, line = chosen reference.
const SIZE = 1000;
const flipY = (y) => SIZE - y;
const curve = (points) => {
  // Smooth decorative line through world points (quadratic midpoints).
  const [first, ...rest] = points.map(([x, y]) => [x, flipY(y)]);
  let d = `M${first[0]} ${first[1]}`;
  for (let index = 0; index < rest.length - 1; index += 1) {
    const [x, y] = rest[index];
    const [nx, ny] = rest[index + 1];
    d += ` Q${x} ${y} ${(x + nx) / 2} ${(y + ny) / 2}`;
  }
  const [lx, ly] = rest[rest.length - 1];
  return `${d} T${lx} ${ly}`;
};

const COAST = [[540, 1000], [610, 985], [700, 972], [800, 968], [905, 958], [940, 900],
  [955, 820], [975, 740], [1000, 690]];
const RIVER = [[600, 430], [625, 520], [660, 600], [700, 655], [745, 700], [790, 760], [850, 830], [925, 905]];
const TICKS = [0, 250, 500, 750, 1000];

function zonePattern(zone) {
  if (zone.populated) return "url(#terrain-urban)";
  const name = zone.name.toLowerCase();
  if (name.includes("sierra") || name.includes("monta")) return "url(#terrain-mountain)";
  if (name.includes("desierto") || name.includes("arena")) return "url(#terrain-sand)";
  return "url(#terrain-field)";
}

export default function TerritoryMap({ zones = [], points = [], stations = [], associations = [], onSelect }) {
  const byId = new Map(points.map((point) => [point.id, point]));
  const links = associations
    .filter((item) => item.is_reference && byId.has(item.source_id) && byId.has(item.reference_id))
    .map((item) => ({ from: byId.get(item.source_id), to: byId.get(item.reference_id) }));

  return (
    <div className="territory">
      <svg
        className="terrain-map"
        viewBox="-70 -20 1120 1080"
        role="img"
        aria-label="Mapa del territorio con zonas, estaciones y epicentros"
      >
        <defs>
          <linearGradient id="terrain-land" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor="#e9e2c9" />
            <stop offset="0.55" stopColor="#dfe8cf" />
            <stop offset="1" stopColor="#cfe0c4" />
          </linearGradient>
          <linearGradient id="terrain-sea" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#bcd9e6" />
            <stop offset="1" stopColor="#8fbfd6" />
          </linearGradient>
          <pattern id="terrain-urban" width="26" height="26" patternUnits="userSpaceOnUse">
            <rect width="26" height="26" fill="#f1dcd3" />
            <rect x="3" y="3" width="9" height="8" fill="#e3b8a8" />
            <rect x="15" y="3" width="8" height="10" fill="#dcae9c" />
            <rect x="3" y="15" width="10" height="8" fill="#dcae9c" />
            <rect x="16" y="16" width="7" height="7" fill="#e3b8a8" />
          </pattern>
          <pattern id="terrain-mountain" width="44" height="34" patternUnits="userSpaceOnUse">
            <rect width="44" height="34" fill="#d9d2bd" />
            <path d="M4 28 L14 12 L24 28 M20 28 L31 8 L42 28" fill="none" stroke="#9b8e6e" strokeWidth="2" />
          </pattern>
          <pattern id="terrain-sand" width="60" height="24" patternUnits="userSpaceOnUse">
            <rect width="60" height="24" fill="#efe1b8" />
            <path d="M0 16 Q15 8 30 16 T60 16" fill="none" stroke="#d6c08a" strokeWidth="2" />
          </pattern>
          <pattern id="terrain-field" width="20" height="20" patternUnits="userSpaceOnUse">
            <rect width="20" height="20" fill="#d6e5c8" />
            <circle cx="10" cy="10" r="2" fill="#a9c49a" />
          </pattern>
          <pattern id="terrain-waves" width="40" height="18" patternUnits="userSpaceOnUse">
            <path d="M0 10 Q10 4 20 10 T40 10" fill="none" stroke="#ffffff" strokeOpacity="0.45" strokeWidth="2" />
          </pattern>
        </defs>

        {/* Land, sea and relief (decoration). */}
        <rect x="0" y="0" width={SIZE} height={SIZE} fill="url(#terrain-land)" />
        <path className="terrain-sea" d={`${curve(COAST)} L${SIZE} ${flipY(SIZE)} Z`} />
        <path className="terrain-sea-waves" d={`${curve(COAST)} L${SIZE} ${flipY(SIZE)} Z`} />
        <path className="terrain-coast" d={curve(COAST)} />
        {[[160, 110], [115, 80], [70, 50]].map(([rx, ry]) => (
          <ellipse key={rx} className="terrain-contour" cx="610" cy={flipY(400)} rx={rx} ry={ry} />
        ))}
        <path className="terrain-river" d={curve(RIVER)} />

        {/* Coordinate grid. */}
        {TICKS.map((tick) => (
          <g key={tick} className="terrain-grid">
            {tick > 0 && tick < SIZE && (
              <>
                <line x1={tick} y1="0" x2={tick} y2={SIZE} />
                <line x1="0" y1={flipY(tick)} x2={SIZE} y2={flipY(tick)} />
              </>
            )}
            <text x={tick} y={SIZE + 34} textAnchor="middle">{tick}</text>
            <text x="-12" y={flipY(tick) + 8} textAnchor="end">{tick}</text>
          </g>
        ))}
        <text className="terrain-axis" x={SIZE / 2} y={SIZE + 58} textAnchor="middle">x (km)</text>

        {/* Zones (data). */}
        {zones.map((zone) => (
          <g key={zone.name} className={`terrain-zone ${zone.populated ? "populated" : "unpopulated"}`}>
            <rect
              x={zone.x_min}
              y={flipY(zone.y_max)}
              width={zone.x_max - zone.x_min}
              height={zone.y_max - zone.y_min}
              fill={zonePattern(zone)}
            />
            <rect
              className="terrain-zone-border"
              x={zone.x_min}
              y={flipY(zone.y_max)}
              width={zone.x_max - zone.x_min}
              height={zone.y_max - zone.y_min}
            />
            <text className="terrain-zone-name" x={zone.x_min + 12} y={flipY(zone.y_max) + 30}>
              {zone.name}
            </text>
            <text className="terrain-zone-kind" x={zone.x_min + 12} y={flipY(zone.y_max) + 54}>
              {zone.populated ? "zona poblada" : "zona no poblada"}
            </text>
          </g>
        ))}

        {/* Stations (data). */}
        {stations.map((station) => (
          <g
            key={station.code}
            className="terrain-station"
            transform={`translate(${station.x_km} ${flipY(station.y_km)})`}
          >
            <title>{`Estación ${station.code} (${station.x_km}, ${station.y_km}) km`}</title>
            <path d="M0 -16 L14 10 L-14 10 Z" />
            <text y="34" textAnchor="middle">{station.code}</text>
          </g>
        ))}

        {/* Association links and epicenters (data). */}
        {links.map(({ from, to }) => (
          <line
            key={`${from.id}-${to.id}`}
            className="terrain-link"
            x1={from.x}
            y1={flipY(from.y)}
            x2={to.x}
            y2={flipY(to.y)}
          />
        ))}
        {points.map((point) => {
          const radius = 9 + Math.max(0, Number(point.magnitude)) * 2.2;
          return (
            <g
              key={point.id}
              className={`terrain-point prio-${point.priority}${point.archived ? " archived" : ""}`}
              transform={`translate(${point.x} ${flipY(point.y)})`}
              onClick={() => onSelect?.(point.id)}
            >
              <title>
                {`#${point.id} · prioridad ${point.priority} · M ${Number(point.magnitude).toFixed(1)} · (${point.x}, ${point.y}) km` +
                  `${point.archived ? " · archivado" : ""}${point.expensive ? " · acceso costoso" : ""}`}
              </title>
              {!point.archived && <circle className="terrain-halo" r={radius * 1.9} />}
              {!point.archived && <circle className="terrain-halo inner" r={radius * 1.4} />}
              {point.expensive && <circle className="terrain-expensive" r={radius + 10} />}
              <circle className="terrain-epicenter" r={radius} />
              <text y={-radius - 8} textAnchor="middle">{point.id}</text>
            </g>
          );
        })}

        {/* Map furniture: frame, north arrow and scale bar. */}
        <rect className="terrain-frame" x="0" y="0" width={SIZE} height={SIZE} />
        <g className="terrain-north" transform="translate(60 70)">
          <circle r="34" />
          <path d="M0 -26 L10 6 L0 0 L-10 6 Z" className="needle" />
          <path d="M0 26 L10 -6 L0 0 L-10 -6 Z" className="needle-south" />
          <text y="-40" textAnchor="middle">N</text>
        </g>
        <g className="terrain-scale" transform={`translate(30 ${SIZE - 60})`}>
          <rect x="-12" y="-6" width="260" height="52" rx="6" className="plate" />
          <rect x="0" y="0" width="100" height="10" className="dark" />
          <rect x="100" y="0" width="100" height="10" className="light" />
          <text x="0" y="36" textAnchor="middle">0</text>
          <text x="100" y="36" textAnchor="middle">100</text>
          <text x="200" y="36" textAnchor="start">200 km</text>
        </g>
      </svg>
      <div className="territory-legend">
        <span><i className="swatch zone-populated" /> Zona poblada</span>
        <span><i className="swatch zone-unpopulated" /> Zona no poblada</span>
        <span><i className="station" /> Estación</span>
        <span><i className="dot prio-3" /> Prioridad alta</span>
        <span><i className="dot prio-2" /> Media</span>
        <span><i className="dot prio-1" /> Baja</span>
        <span><i className="dot hollow" /> Archivado</span>
        <span><i className="ring" /> Acceso costoso</span>
        <span><i className="link" /> Referencia elegida</span>
        <span>Tamaño = magnitud</span>
      </div>
    </div>
  );
}
