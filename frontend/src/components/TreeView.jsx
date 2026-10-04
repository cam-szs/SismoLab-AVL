const NODE_RADIUS = 22;
const COLUMN_GAP = 58;
const LEVEL_GAP = 78;

export function layoutTree(root) {
  if (!root) return { nodes: [], edges: [], width: 0, height: 0 };
  const positions = new Map();
  const nodes = [];
  let index = 0;
  let maxDepth = 0;

  const visit = (node, depth) => {
    if (!node) return;
    visit(node.izquierdo, depth + 1);
    const position = { node, x: index, y: depth };
    positions.set(node, position);
    nodes.push(position);
    index += 1;
    maxDepth = Math.max(maxDepth, depth);
    visit(node.derecho, depth + 1);
  };
  visit(root, 0);

  const edges = [];
  nodes.forEach((position) => {
    if (position.node.izquierdo) edges.push([position, positions.get(position.node.izquierdo)]);
    if (position.node.derecho) edges.push([position, positions.get(position.node.derecho)]);
  });

  return {
    nodes,
    edges,
    width: index * COLUMN_GAP + NODE_RADIUS * 2,
    height: (maxDepth + 1) * LEVEL_GAP + NODE_RADIUS * 2 + 12,
  };
}

export function findTreeNode(root, eventId) {
  if (!root) return null;
  if (root.key.event_id === eventId) return root;
  return findTreeNode(root.izquierdo, eventId) ?? findTreeNode(root.derecho, eventId);
}

export default function TreeView({ root, tone = "avl", onSelect }) {
  const { nodes, edges, width, height } = layoutTree(root);
  if (nodes.length === 0) {
    return <div className="empty-state compact">Sin nodos</div>;
  }

  const center = (position) => ({
    x: NODE_RADIUS + position.x * COLUMN_GAP,
    y: NODE_RADIUS + 12 + position.y * LEVEL_GAP,
  });

  return (
    <svg
      className={`tree-svg tree-${tone}`}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
    >
      {edges.map(([from, to], index) => {
        const start = center(from);
        const end = center(to);
        return (
          <line
            key={`edge-${index}`}
            className="tree-edge"
            x1={start.x}
            y1={start.y}
            x2={end.x}
            y2={end.y}
          />
        );
      })}
      {nodes.map((position) => {
        const point = center(position);
        const node = position.node;
        const factor = node.factor_balanceo ?? 0;
        const reviewed = node.event?.status === "reviewed";
        const magnitude = (node.key.magnitude_tenths / 10).toFixed(1);
        const interactive = Boolean(onSelect);
        return (
          <g
            key={node.key.event_id}
            className={`tree-node-group prio-${node.key.priority}${Math.abs(factor) > 1 ? " is-unbalanced" : ""}${reviewed ? " is-reviewed" : ""}${interactive ? " is-clickable" : ""}`}
            onClick={interactive ? () => onSelect(node) : undefined}
            onKeyDown={interactive
              ? (event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(node);
                  }
                }
              : undefined}
            role={interactive ? "button" : undefined}
            tabIndex={interactive ? 0 : undefined}
          >
            <circle className="tree-circle" cx={point.x} cy={point.y} r={NODE_RADIUS} />
            <text className="tree-label-id" x={point.x} y={point.y - 2} textAnchor="middle">
              #{node.key.event_id}
            </text>
            <text className="tree-label-meta" x={point.x} y={point.y + 11} textAnchor="middle">
              P{node.key.priority} M{magnitude}
            </text>
            <text
              className="tree-factor"
              x={point.x}
              y={point.y - NODE_RADIUS - 5}
              textAnchor="middle"
            >
              b{factor > 0 ? `+${factor}` : factor}
            </text>
            <text
              className={`tree-status ${reviewed ? "reviewed" : "pending"}`}
              x={point.x + NODE_RADIUS - 2}
              y={point.y - NODE_RADIUS + 4}
              textAnchor="middle"
            >
              {reviewed ? "✓" : "•"}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
