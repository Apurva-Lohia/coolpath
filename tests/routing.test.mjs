import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { buildGraph, nearestNode, route, haversine } from '../dist/routing.mjs';

const nodes = [
  { id: 'a', lat: -33.89, lon: 151.19 },
  { id: 'b', lat: -33.89, lon: 151.191 },
  { id: 'c', lat: -33.8898, lon: 151.1905 },
  { id: 'isolated', lat: -33.9, lon: 151.2 },
];
const fixture = () => buildGraph({ nodes, edges: [
  { u: 'a', v: 'b', length: 100, shade: 0, name: 'Sunny road' },
  { u: 'a', v: 'c', length: 60, shade: 1, name: 'Tree walk' },
  { u: 'c', v: 'b', length: 60, shade: 1, name: 'Tree walk' },
] });

test('A* optimizes distance at zero penalty and canopy-adjusted cost otherwise', () => {
  const graph = fixture(), shortest = route(graph, 'a', 'b', 0), cooler = route(graph, 'a', 'b', 2);
  assert.equal(shortest.distance, 100); assert.equal(shortest.canopyFraction, 0);
  assert.equal(cooler.distance, 120); assert.equal(cooler.canopyFraction, 1);
  assert.equal(cooler.canopyDistance, 120); assert.equal(cooler.cost, 120);
  assert.deepEqual(cooler.nodes.map(node => node.id), ['a', 'c', 'b']);
});

test('reversed path has correctly oriented geometry', () => {
  const result = route(fixture(), 'b', 'a', 2);
  assert.deepEqual(result.coordinates[0], [nodes[1].lat, nodes[1].lon]);
  assert.deepEqual(result.coordinates.at(-1), [nodes[0].lat, nodes[0].lon]);
  assert.equal(result.edges[0].u, 'b'); assert.equal(result.edges[0].v, 'c');
});

test('disconnected and same-node routes are explicit', () => {
  const graph = fixture();
  assert.equal(route(graph, 'a', 'isolated'), null);
  const result = route(graph, 'a', 'a');
  assert.equal(result.distance, 0); assert.equal(result.cost, 0);
  assert.equal(result.canopyFraction, 0); assert.equal(result.edges.length, 0);
  assert.deepEqual(result.coordinates, [[nodes[0].lat, nodes[0].lon]]);
});

test('snap radius is enforced and empty graphs return null', () => {
  assert.equal(nearestNode(fixture(), nodes[0].lat, nodes[0].lon, 0).id, 'a');
  assert.equal(nearestNode(fixture(), 0, 0), null);
  assert.equal(nearestNode(buildGraph({nodes: [], edges: []}), 0, 0), null);
  assert.throws(() => nearestNode(fixture(), 100, 0), RangeError);
  assert.throws(() => nearestNode(fixture(), 0, 0, -1), RangeError);
});

test('directed edges, parallel edges and zero-length cycles', () => {
  const graph = buildGraph({nodes, edges: [
    {u: 'a', v: 'b', length: 0, shade: 0, directed: true},
    {u: 'a', v: 'b', length: 120, shade: 1},
    {u: 'a', v: 'a', length: 0, shade: 1},
  ]});
  assert.equal(graph.heuristicScale, 0);
  assert.equal(route(graph, 'a', 'b').distance, 0);
  assert.equal(route(graph, 'b', 'a').distance, 120);
  const oneWay = buildGraph({ nodes, edges: [{u:'a',v:'b',length:100,shade:0,directed:true}] });
  assert.equal(route(oneWay, 'b', 'a'), null);
});

test('equal-cost paths terminate and preserve intermediate geometry', () => {
  const graph = buildGraph({nodes,edges:[
    {u:'a',v:'b',length:120,shade:1,geometry:[[nodes[0].lat,nodes[0].lon],[-33.8899,151.1905],[nodes[1].lat,nodes[1].lon]]},
    {u:'a',v:'c',length:60,shade:1},
    {u:'c',v:'b',length:60,shade:1},
  ]});
  assert.equal(route(graph,'a','b').cost,120);
  assert.deepEqual(route(graph,'b','a').coordinates[1],[-33.8899,151.1905]);
});

test('input validation rejects malformed graph rather than inventing weights', () => {
  assert.throws(() => buildGraph({nodes, edges:[{u:'a',v:'x',length:1,shade:0}]}), RangeError);
  for (const shade of [undefined, -0.1, 1.1, NaN]) assert.throws(() => buildGraph({nodes,edges:[{u:'a',v:'b',length:1,shade}]}), RangeError);
  assert.throws(() => buildGraph({nodes:[...nodes,nodes[0]],edges:[]}), RangeError);
  assert.throws(() => buildGraph({nodes,edges:[{u:'a',v:'b',length:-1,shade:0}]}), RangeError);
  assert.throws(() => buildGraph({nodes,edges:[{u:'a',v:'b',length:1,shade:0,geometry:[[0,0],[0,1]]}]}), RangeError);
  for (const penalty of [-1, NaN, Infinity]) assert.throws(() => route(fixture(),'a','b',penalty), RangeError);
  assert.throws(() => route(fixture(),'missing','b'), RangeError);
});

test('haversine handles equal points, antimeridian, and antipodes', () => {
  assert.equal(haversine(0,0,0,0), 0);
  assert.ok(haversine(0,179.99,0,-179.99) < 2300);
  assert.ok(Number.isFinite(haversine(90,0,-90,180)));
});

function dijkstra(graph, start, end, penalty) {
  const costs = new Map([[start, 0]]), remaining = new Set(graph.nodes.keys());
  while (remaining.size) {
    let best, cost = Infinity;
    for (const id of remaining) if ((costs.get(id) ?? Infinity) < cost) { best = id; cost = costs.get(id); }
    if (best === undefined) return null;
    if (best === end) return cost;
    remaining.delete(best);
    for (const link of graph.adjacency.get(best)) {
      const candidate = cost + link.edge.length * (1 + penalty * (1 - link.edge.shade));
      if (candidate < (costs.get(link.to) ?? Infinity)) costs.set(link.to, candidate);
    }
  }
  return null;
}

test('A* matches independent Dijkstra on deterministic randomized graphs', () => {
  let seed = 47819;
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 2**32; };
  for (let trial = 0; trial < 50; trial++) {
    const sample = Array.from({length: 24}, (_, id) => ({id, lat: -33.89 + random() * .01, lon: 151.19 + random() * .01}));
    const edges = [];
    for (let i = 0; i < sample.length; i++) for (let j = i+1; j < sample.length; j++) {
      if (random() > .16) continue;
      const direct = haversine(sample[i].lat,sample[i].lon,sample[j].lat,sample[j].lon);
      edges.push({u:i,v:j,length:direct*(.9+random()),shade:random(),directed:random()<.25});
    }
    const graph = buildGraph({nodes:sample,edges});
    for (const penalty of [0,1,2,10]) {
      const actual = route(graph,0,23,penalty), expected = dijkstra(graph,0,23,penalty);
      if (expected === null) assert.equal(actual,null);
      else assert.ok(Math.abs(actual.cost-expected)<1e-7, `Trial ${trial}, penalty ${penalty}`);
    }
  }
});

test('real OSM graph validates and every preset pair is routable both ways', async () => {
  const data = JSON.parse(await readFile(new URL('../data/graph.json', import.meta.url), 'utf8'));
  const graph = buildGraph(data);
  assert.ok(graph.nodes.size > 1000);
  assert.ok(graph.edges.length > 1000);
  for (const start of data.places) for (const end of data.places) {
    const a = nearestNode(graph,start.lat,start.lon), b = nearestNode(graph,end.lat,end.lon);
    assert.ok(a && b); assert.ok(a.distance < 1 && b.distance < 1);
    const result = route(graph,a.id,b.id,2);
    assert.ok(result, `${start.name} -> ${end.name}`);
    assert.ok(result.canopyFraction >= 0 && result.canopyFraction <= 1);
    assert.deepEqual(result.coordinates[0],[a.lat,a.lon]);
    assert.deepEqual(result.coordinates.at(-1),[b.lat,b.lon]);
    for (let i=1;i<result.edges.length;i++) assert.equal(result.edges[i-1].v,result.edges[i].u);
  }
});

test('real Redfern–USyd A* agrees with zero-heuristic search', async () => {
  const data = JSON.parse(await readFile(new URL('../data/graph.json', import.meta.url), 'utf8'));
  const graph = buildGraph(data), noHeuristic = {...graph,heuristicScale:0};
  const [a,b] = data.places;
  for (const penalty of [0,1,2,5]) {
    const actual = route(graph,a.nodeId,b.nodeId,penalty), expected = route(noHeuristic,a.nodeId,b.nodeId,penalty);
    assert.ok(Math.abs(actual.cost-expected.cost)<1e-7);
  }
  const shortest = route(graph,a.nodeId,b.nodeId,0), canopy = route(graph,a.nodeId,b.nodeId,2);
  assert.ok(shortest.distance <= canopy.distance);
  assert.ok(shortest.distance > 1000 && shortest.distance < 1500);
  assert.ok(canopy.canopyFraction > shortest.canopyFraction);
});
