"""Offline geometry and snapshot auditing, Python 3.10+, standard library only."""
import copy
import hashlib
import json
import math
from collections import Counter

LEAVES = {'Class', 'Interface', 'Actor', 'UseCase', 'State2', 'InitialPseudoState',
          'FinalState2', 'Choice', 'ChoicePseudoState', 'InitialState', 'FinalState'}


def kind(e):
    return e.get('modelType') or e.get('shapeType')


def validate(s):
    if not isinstance(s, dict) or not isinstance(s.get('elements'), list):
        raise ValueError('Expected a getDiagramSnapshot JSON object with elements.')
    ids = set()
    for e in s['elements']:
        if not isinstance(e.get('viewId'), str) or e['viewId'] in ids:
            raise ValueError('Missing or duplicate viewId.')
        ids.add(e['viewId'])
        for key, size in [('bounds', 4), ('labelBounds', 4)]:
            if key in e:
                r = e[key]
                if len(r) != size or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in r):
                    raise ValueError('Invalid rectangle: ' + e['viewId'])
                if min(r[2:]) < 0:
                    raise ValueError('Negative rectangle size.')
        if 'points' in e:
            if len(e['points']) < 2 or any(len(p) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in p) for p in e['points']):
                raise ValueError('Invalid connector points: ' + e['viewId'])
    return s


def fingerprint(s):
    # Ignore enumeration order, but preserve all snapshot fields and model/view identities.
    c = copy.deepcopy(s)
    c['elements'] = sorted(c['elements'], key=lambda e: e['viewId'])
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def segments(p):
    return zip(p, p[1:])


def orthogonal(p):
    return all(a[0] == b[0] or a[1] == b[1] for a, b in segments(p))


def length(p):
    return sum(math.dist(a, b) for a, b in segments(p))


def simplify(p):
    out = []
    for v in map(tuple, p):
        if out and v == out[-1]:
            continue
        while len(out) > 1:
            a, b = out[-2:]
            u = (b[0]-a[0], b[1]-a[1]); w = (v[0]-b[0], v[1]-b[1])
            if u[0]*w[1] != u[1]*w[0] or u[0]*w[0]+u[1]*w[1] <= 0:
                break  # Preserve reversals; they are not redundant collinear vertices.
            out.pop()
        out.append(v)
    return out


def overlap(a, b):
    x,y,w,h = a; u,v,z,t = b
    return max(0, min(x+w,u+z)-max(x,u))*max(0, min(y+h,v+t)-max(y,v))


def through(p, r, pad=0):
    """Open rectangle intersection, including diagonal segments; boundary contact excluded."""
    x,y,w,h = r; x-=pad; y-=pad; w+=2*pad; h+=2*pad
    if w <= 0 or h <= 0:
        return False
    for a,b in segments(p):
        lo,hi = 0.,1.
        for start, delta, low, high in [(a[0], b[0]-a[0], x, x+w), (a[1], b[1]-a[1], y, y+h)]:
            if delta == 0:
                if not low < start < high:
                    lo,hi=1.,0.; break
            else:
                t1,t2 = sorted(((low-start)/delta,(high-start)/delta))
                lo=max(lo,t1);hi=min(hi,t2)
        if lo < hi:
            return True
    return False


def conflicts(p, q, shared_endpoints=()):
    """Unique intersection points per connector pair and collinear overlap length."""
    crossings=set(); shared=set(map(tuple,shared_endpoints)); coincident=0.
    for a,b in segments(p):
        rx,ry=b[0]-a[0],b[1]-a[1]
        for c,d in segments(q):
            sx,sy=d[0]-c[0],d[1]-c[1]; den=rx*sy-ry*sx
            if den:
                t=((c[0]-a[0])*sy-(c[1]-a[1])*sx)/den
                u=((c[0]-a[0])*ry-(c[1]-a[1])*rx)/den
                if 0<=t<=1 and 0<=u<=1:
                    point=(round(a[0]+t*rx,8),round(a[1]+t*ry,8))
                    if point not in shared:crossings.add(point)
            elif rx*(c[1]-a[1])-ry*(c[0]-a[0])==0 and (rx or ry):
                axis=0 if abs(rx)>=abs(ry) else 1
                distance=max(0,min(max(a[axis],b[axis]),max(c[axis],d[axis]))-max(min(a[axis],b[axis]),min(c[axis],d[axis])))
                coincident+=distance*math.hypot(rx,ry)/abs((rx,ry)[axis])
    return len(crossings),coincident


def shared(e,f,p,q):
    return [p[i] for i,k in [(0,'fromViewId'),(-1,'toViewId')] for j,l in [(0,'fromViewId'),(-1,'toViewId')]
            if e.get(k)==f.get(l) and tuple(p[i])==tuple(q[j])]


def sequence(s):
    return s.get('type') in {'InteractionDiagram','SequenceDiagram'} or any(kind(e) in {'Message','LifeLine','Lifeline','CombinedFragment'} for e in s['elements'])


def audit(s):
    validate(s); es=[e for e in s['elements'] if 'points' in e]; by={e['viewId']:e for e in s['elements']}
    nodes=[e for e in s['elements'] if 'points' not in e and kind(e) in LEAVES and 'bounds' in e]
    crosses=0; overlaps=0.; node_hits=[]; shape_hits=[]; label_hits=[]; orphans=[]
    for i,e in enumerate(es):
        if any(e.get(k) not in by for k in ['fromViewId','toViewId']):orphans.append(e['viewId'])
        for f in es[i+1:]:
            c,o=conflicts(e['points'],f['points'],shared(e,f,e['points'],f['points']));crosses+=c;overlaps+=o
        for n in nodes:
            if n['viewId'] not in [e.get('fromViewId'),e.get('toViewId')] and through(e['points'],n['bounds']):node_hits.append([e['viewId'],n['viewId']])
        # These captions have absolute coordinates; class compartments can be local.
        for f in s['elements']:
            if f['viewId']!=e['viewId'] and ('points' in f or kind(f)=='Actor') and f.get('captionVisible',True):
                if 'labelBounds' in f and through(e['points'],f['labelBounds']):label_hits.append([e['viewId'],f['viewId']])
    for i,n in enumerate(nodes):
        for m in nodes[i+1:]:
            if overlap(n['bounds'],m['bounds'])>0:shape_hits.append([n['viewId'],m['viewId']])
    return dict(diagram=s.get('name'),connectors=len(es),bends=dict(Counter(max(0,len(simplify(e['points']))-2) for e in es)),
                totalBends=sum(max(0,len(simplify(e['points']))-2) for e in es),length=round(sum(length(e['points']) for e in es),2),
                crossings=crosses,collinearOverlapLength=round(overlaps,2),nonOrthogonal=[e['viewId'] for e in es if not orthogonal(e['points'])],
                shapeOverlaps=shape_hits,connectorThroughShapes=node_hits,connectorThroughCaptions=label_hits,orphanConnectors=orphans,
                limitations='Geometric heuristics, not visual validation. Crossings counted per pair, shared attachments excluded; collinear overlap reported separately. Container/sequence shape semantics and all text collisions are not fully covered.')


def identity(s):
    by={e['viewId']:e for e in s['elements']}
    return {e['viewId']:[e.get('modelId'),kind(e),e.get('name'),
            by.get(e.get('fromViewId'),{}).get('modelId'),by.get(e.get('toViewId'),{}).get('modelId')]
            for e in s['elements']}


def compare(before, after):
    a,b=identity(before),identity(after)
    return dict(before=audit(before),after=audit(after),
                observedIdentityPreserved=a==b,removedViews=sorted(a.keys()-b.keys()),addedViews=sorted(b.keys()-a.keys()),
                changedViews=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]),
                semanticLimit='Snapshot comparison covers view/model IDs, types, names and relation endpoint model IDs. Multiplicities, roles, attributes and guards must also be compared using relationship/model details when not exposed in the snapshot.')
