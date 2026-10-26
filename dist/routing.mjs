/** Real A* over a bounded, preprocessed pedestrian graph. No network services required. */
const R = 6371008.8;
const radians = value => value * Math.PI / 180;

function coordinate(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
    throw new RangeError('Coordinates must be finite latitude/longitude values.');
  }
}

export function haversine(lat1, lon1, lat2, lon2) {
  coordinate(lat1, lon1); coordinate(lat2, lon2);
  const a = Math.sin(radians(lat2 - lat1) / 2) ** 2 +
    Math.cos(radians(lat1)) * Math.cos(radians(lat2)) * Math.sin(radians(lon2 - lon1) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(Math.max(0, Math.min(1, a))));
}

class MinHeap {
  constructor() { this.items = []; }
  push(value) {
    const a = this.items; a.push(value); let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (a[p].priority <= value.priority) break;
      a[i] = a[p]; i = p;
    }
    a[i] = value;
  }
  pop() {
    const a = this.items;
    if (!a.length) return undefined;
    const first = a[0], last = a.pop();
    if (a.length) {
      let i = 0;
      while (2 * i + 1 < a.length) {
        let child = 2 * i + 1;
        if (child + 1 < a.length && a[child + 1].priority < a[child].priority) child++;
        if (last.priority <= a[child].priority) break;
        a[i] = a[child]; i = child;
      }
      a[i] = last;
    }
    return first;
  }
  get size() { return this.items.length; }
}

export function buildGraph(data) {
  if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) throw new TypeError('Graph requires nodes and edges arrays.');
  const nodes = new Map(), adjacency = new Map(), edges = [];
  for (const item of data.nodes) {
    if (!item || !['string', 'number'].includes(typeof item.id) || (typeof item.id === 'number' && !Number.isFinite(item.id))) throw new TypeError('Every node needs a string or finite numeric ID.');
    if (nodes.has(item.id)) throw new RangeError(`Duplicate node ID: ${item.id}`);
    coordinate(item.lat, item.lon);
    nodes.set(item.id, { ...item }); adjacency.set(item.id, []);
  }
  let heuristicScale = 1;
  for (const [index, item] of data.edges.entries()) {
    if (!item || !nodes.has(item.u) || !nodes.has(item.v)) throw new RangeError(`Edge ${index} references an unknown node.`);
    if (!Number.isFinite(item.length) || item.length < 0) throw new RangeError(`Edge ${index} has an invalid length.`);
    if (!Number.isFinite(item.shade) || item.shade < 0 || item.shade > 1) throw new RangeError(`Edge ${index} needs shade in [0, 1].`);
    const from = nodes.get(item.u), to = nodes.get(item.v);
    const direct = haversine(from.lat, from.lon, to.lat, to.lon);
    if (direct > 0) heuristicScale = Math.min(heuristicScale, item.length / direct);
    const geometry = item.geometry ?? [[from.lat, from.lon], [to.lat, to.lon]];
    if (!Array.isArray(geometry) || geometry.length < 2) throw new RangeError(`Edge ${index} needs at least two geometry coordinates.`);
    for (const point of geometry) {
      if (!Array.isArray(point) || point.length !== 2) throw new TypeError(`Edge ${index} has invalid geometry.`);
      coordinate(point[0], point[1]);
    }
    // Each edge geometry is expected in u -> v order; reject reversed or detached lines.
    if (haversine(from.lat, from.lon, ...geometry[0]) > 2 || haversine(to.lat, to.lon, ...geometry.at(-1)) > 2) throw new RangeError(`Edge ${index} geometry does not match its endpoints.`);
    const edge = { ...item, index, name: typeof item.name === 'string' ? item.name : 'Walking path', geometry: geometry.map(point => [...point]) };
    edges.push(edge);
    adjacency.get(edge.u).push({ to: edge.v, edge, reverse: false });
    if (edge.directed !== true && edge.u !== edge.v) adjacency.get(edge.v).push({ to: edge.u, edge, reverse: true });
  }
  // This scale guarantees h(u) <= cost(u,v) + h(v), including rounded/zero lengths.
  return { nodes, adjacency, edges, heuristicScale };
}

export function nearestNode(graph, lat, lon, maxDistanceMeters = 150) {
  coordinate(lat, lon);
  if (typeof maxDistanceMeters !== 'number' || Number.isNaN(maxDistanceMeters) || maxDistanceMeters < 0) throw new RangeError('Maximum snap distance must be nonnegative.');
  let nearest = null, distance = maxDistanceMeters;
  for (const node of graph.nodes.values()) {
    const candidate = haversine(lat, lon, node.lat, node.lon);
    if (candidate <= distance) { distance = candidate; nearest = { ...node, distance }; }
  }
  return nearest;
}

export function route(graph, startId, endId, penalty = 2) {
  if (!graph.nodes.has(startId) || !graph.nodes.has(endId)) throw new RangeError('Start and destination must be graph nodes.');
  if (!Number.isFinite(penalty) || penalty < 0) throw new RangeError('Canopy preference must be finite and nonnegative.');
  const end = graph.nodes.get(endId);
  const heuristic = id => {
    const node = graph.nodes.get(id);
    return graph.heuristicScale * haversine(node.lat, node.lon, end.lat, end.lon);
  };
  const queue = new MinHeap(), distances = new Map([[startId, 0]]), previous = new Map();
  queue.push({ id: startId, cost: 0, priority: heuristic(startId) });
  let visited = 0;
  while (queue.size) {
    const current = queue.pop();
    if (current.cost !== distances.get(current.id)) continue;
    visited++;
    if (current.id === endId) {
      const pathEdges = [], pathNodes = [end];
      let id = endId;
      while (id !== startId) {
        const step = previous.get(id);
        const geometry = step.reverse ? [...step.edge.geometry].reverse() : step.edge.geometry;
        pathEdges.push({ ...step.edge, u: step.from, v: id, geometry: geometry.map(point => [...point]) });
        id = step.from; pathNodes.push(graph.nodes.get(id));
      }
      pathNodes.reverse(); pathEdges.reverse();
      const distance = pathEdges.reduce((sum, edge) => sum + edge.length, 0);
      const canopyDistance = pathEdges.reduce((sum, edge) => sum + edge.length * edge.shade, 0);
      const coordinates = pathEdges.length ? pathEdges.flatMap((edge, i) => i ? edge.geometry.slice(1) : edge.geometry) : [[end.lat, end.lon]];
      return { nodes: pathNodes, edges: pathEdges, distance, canopyDistance, canopyFraction: distance > 0 ? canopyDistance / distance : 0, cost: current.cost, coordinates, visited };
    }
    for (const link of graph.adjacency.get(current.id)) {
      const weight = link.edge.length * (1 + penalty * (1 - link.edge.shade));
      if (!Number.isFinite(weight)) throw new RangeError('Routing cost overflow; reduce canopy preference.');
      const cost = current.cost + weight;
      if (!Number.isFinite(cost)) throw new RangeError('Route cost exceeds numeric limits.');
      if (cost < (distances.get(link.to) ?? Infinity)) {
        distances.set(link.to, cost); previous.set(link.to, { ...link, from: current.id });
        queue.push({ id: link.to, cost, priority: cost + heuristic(link.to) });
      }
    }
  }
  return null;
}
