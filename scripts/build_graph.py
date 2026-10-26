"""Build a static walking graph from the user's cached public OSM and tree data.
No network, database credentials or third-party dependencies. Run from project root.
"""
import json, math, collections, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
R=6371000
LAT0=math.radians(-33.891); LON0=151.193

def xy(lat,lon):return (R*math.radians(lon-LON0)*math.cos(LAT0),R*math.radians(lat+33.891))
def hav(a,b):
 p,q=math.radians(a['lat']),math.radians(b['lat']); dp=q-p;dl=math.radians(b['lon']-a['lon'])
 return 2*R*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p)*math.cos(q)*math.sin(dl/2)**2)))
D=json.load(open(RAW/'osm1.json'))
N={str(n['id']):n for n in D['elements'] if n['type']=='node'}
# Expand tree search only around the actual supplied network.
bounds=[min(n['lat'] for n in N.values()),min(n['lon'] for n in N.values()),max(n['lat'] for n in N.values()),max(n['lon'] for n in N.values())]
trees=[]; defaults=0; statuses=collections.Counter()
for f in json.load(open(RAW/'trees.geojson'))['features']:
 lon,lat=f['geometry']['coordinates'][:2];p=f['properties'];statuses[p.get('Tree_Status')]+=1
 if not (bounds[0]-.001 < lat < bounds[2]+.001 and bounds[1]-.001<lon<bounds[3]+.001):continue
 if str(p.get('Tree_Status','')).lower() not in ['tree','live','living']:continue
 diameter=p.get('TreeCanopyNS')
 if diameter is None:diameter=4;defaults+=1
 try: radius=float(diameter)/2
 except (ValueError,TypeError):continue
 if not 0<radius<=40:continue
 x,y=xy(lat,lon);trees.append((x,y,radius,lat,lon))
# Circle bounding boxes indexed in 25 m spatial cells.
grid=collections.defaultdict(list)
for i,(x,y,r,*_) in enumerate(trees):
 for gx in range(math.floor((x-r)/25),math.floor((x+r)/25)+1):
  for gy in range(math.floor((y-r)/25),math.floor((y+r)/25)+1):grid[gx,gy].append(i)
def shade(a,b):
 x,y=xy(a['lat'],a['lon']);X,Y=xy(b['lat'],b['lon']);dx,dy=X-x,Y-y;l=math.hypot(dx,dy)
 if not l:return 0
 # Rectangular 10 m corridor, midpoint quadrature: <=1 m along x 1 m across.
 count=max(1,math.ceil(l));covered=0
 for k in range(count):
  t=(k+.5)/count;cx=x+t*dx;cy=y+t*dy
  for j in range(10):
   off=j-4.5;px=cx-dy/l*off;py=cy+dx/l*off
   for i in grid.get((math.floor(px/25),math.floor(py/25)),[]):
    tx,ty,r,*_=trees[i]
    if (px-tx)**2+(py-ty)**2<=r*r:covered+=1;break
 return covered/(count*10)
E=[]; excluded=collections.Counter(); seen=set()
allowed={'footway','pedestrian','path','steps','living_street','residential','service','unclassified','tertiary','secondary','primary','track'}
for w in D['elements']:
 if w['type']!='way':continue
 t=w.get('tags',{});h=t.get('highway');foot=t.get('foot');access=t.get('access')
 reason=None
 if h not in allowed:reason='non-walking road class'
 elif foot in ['no','private']:reason='foot access restricted'
 elif access in ['no','private','customers','destination','permit'] and foot not in ['yes','designated','permissive']:reason='restricted access'
 elif t.get('indoor')=='yes' or h=='corridor':reason='indoor'
 elif h in ['primary','secondary','tertiary'] and t.get('sidewalk')=='no':reason='major road without sidewalk'
 if reason:excluded[reason]+=1;continue
 for u,v in zip(w['nodes'],w['nodes'][1:]):
  u,v=str(u),str(v)
  if u not in N or v not in N or u==v:continue
  if any(N[z].get('tags',{}).get('access') in ['no','private'] and N[z].get('tags',{}).get('foot') not in ['yes','designated'] for z in [u,v]):continue
  key=tuple(sorted([u,v]));
  if key in seen:continue
  a,b=N[u],N[v];length=hav(a,b)
  if length<=.01:continue
  seen.add(key)
  E.append(dict(u=u,v=v,length=length,shade=shade(a,b),name=t.get('name',{'steps':'Steps','footway':'Footpath','path':'Walking path'}.get(h,'Unnamed '+h.replace('_',' '))),highway=h,geometry=[[a['lat'],a['lon']],[b['lat'],b['lon']]],osm_way=str(w['id'])))
# Keep the largest actual connected component; do not fabricate links.
adj=collections.defaultdict(list)
for e in E:adj[e['u']].append(e['v']);adj[e['v']].append(e['u'])
unseen=set(adj);comps=[]
while unseen:
 stack=[unseen.pop()];c=set(stack)
 while stack:
  for v in adj[stack.pop()]:
   if v in unseen:unseen.remove(v);c.add(v);stack.append(v)
 comps.append(c)
main=max(comps,key=len);E=[e for e in E if e['u'] in main and e['v'] in main]
ns=[dict(id=i,lat=N[i]['lat'],lon=N[i]['lon']) for i in sorted(main)]
def nearest(lat,lon):return min(ns,key=lambda n:hav(n,dict(lat=lat,lon=lon)))
places=[]
for name,lat,lon in [('Redfern Station · Lawson Street',-33.8916059,151.1988371),('University of Sydney · Eastern Avenue',-33.8877853,151.1901403),('University of Sydney · Gate 3',-33.8889659,151.1946344),('Victoria Park · City Road',-33.886935,151.1936015),('Darlington · Abercrombie Street',-33.89093,151.1946),('University Avenue',-33.8857938,151.1900279)]:
 n=nearest(lat,lon);places.append(dict(name=name,lat=n['lat'],lon=n['lon'],nodeId=n['id']))
metadata=dict(osmDate=D['osm3s']['timestamp_osm_base'],treeSnapshot='User project snapshot, 8 April 2026; individual survey dates unknown',method='Approximate canopy overlap over a 10 m wide road corridor, sampled at <=1 m longitudinal spacing and 1 m transverse spacing. TreeCanopyNS / 2 gives circular radius. Missing diameters default to 4 m, matching original project. No time-of-day, temperature, shadows or building shade.',treeCount=len(trees),defaultDiameterCount=defaults,bounds=bounds,componentCount=len(comps),discardedNodes=sum(map(len,comps))-len(main),excludedWays=dict(excluded),coverageWarning='City asset register contains park and street trees only; campus and private trees may be absent. Zero means no mapped overlap, not proof of no shade.',sources=[dict(name='OpenStreetMap contributors',url='https://www.openstreetmap.org/copyright',license='ODbL 1.0'),dict(name='City of Sydney — Trees',url='https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::trees/about',license='CC BY 4.0',licenseEvidence='https://www.arcgis.com/sharing/rest/content/items/15c4713a688a48fcb604fc343118af05?f=json')])
out=dict(nodes=ns,edges=E,places=places,metadata=metadata)
(ROOT/'data/graph.json').write_text(json.dumps(out,separators=(',',':')))
(ROOT/'data/trees.json').write_text(json.dumps([dict(lat=t[3],lon=t[4],radius=t[2]) for t in trees],separators=(',',':')))
print(json.dumps(dict(nodes=len(ns),edges=len(E),trees=len(trees),components=sorted(map(len,comps),reverse=True),nonzeroShade=sum(e['shade']>0 for e in E),meanShade=sum(e['shade']*e['length'] for e in E)/sum(e['length'] for e in E),places=places,metadata=metadata),indent=2))
