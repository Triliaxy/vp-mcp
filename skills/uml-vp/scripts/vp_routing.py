"""Conservative native-connector proposals, without mutating Visual Paradigm."""
import copy
import math
from vp_geometry import (LEAVES, kind, validate, sequence, orthogonal, simplify,
                         segments, length, through, conflicts, shared, fingerprint, audit)


def make_plan(s, operations, mode, notes=()):
    return dict(format='uml-vp-plan-v1',mode=mode,diagramId=s.get('diagramId'),diagramName=s.get('name'),
                baseFingerprint=fingerprint(s),operations=operations,notes=list(notes))


def route(s, passes=3, limit=180, clearance=10):
    validate(s)
    if sequence(s):
        return make_plan(s,[], 'routing', ['Sequence diagram: messages, lifelines and self-calls preserved; inspect manually.'])
    edges=[e for e in s['elements'] if 'points' in e]
    by={e['viewId']:e for e in s['elements']}
    nodes={i:e for i,e in by.items() if 'points' not in e and kind(e) in LEAVES and 'bounds' in e}
    boxes={i:e['bounds'] for i,e in nodes.items()}
    captions=[e['labelBounds'] for e in nodes.values() if kind(e)=='Actor' and 'labelBounds' in e]
    paths={e['viewId']:e['points'] for e in edges};changed=set();skipped=[]

    def ports(i,j):
        x,y,w,h=boxes[i];u,v,z,t=boxes[j];typ=kind(nodes[i])
        if min(w,h)<=0:return []
        if typ=='Actor':return [((round(x+w/2),round(y+h/2)),(d,0)) for d in [-1,1]]
        if typ=='UseCase' or w<65 or h<65:
            return [((x,round(y+h/2)),(-1,0)),((x+w,round(y+h/2)),(1,0)),
                    ((round(x+w/2),y),(0,-1)),((round(x+w/2),y+h),(0,1))]
        xs={x+round(w*f) for f in [.25,.5,.75]};ys={y+round(h*f) for f in [.3,.5,.7]}
        if typ in {'Class','Interface'}:
            xs.update(range(math.ceil(x+20),math.floor(x+w-19),40))
            ys.update(range(math.ceil(y+40),math.floor(y+h-19),40))
        xs.add(round(max(x+24,min(x+w-24,u+z/2))))
        ys.add(round(max(y+32,min(y+h-24,v+t/2))))
        return ([((xx,y),(0,-1)) for xx in sorted(xs)]+[((xx,y+h),(0,1)) for xx in sorted(xs)]
                +[((x,yy),(-1,0)) for yy in sorted(ys)]+[((x+w,yy),(1,0)) for yy in sorted(ys)])

    def candidates(e):
        a,b=e['fromViewId'],e['toViewId'];cur=paths[e['viewId']];seen=set()
        for p,d in ports(a,b):
            for q,f in ports(b,a):
                options=[[p,(p[0],q[1]),q],[p,(q[0],p[1]),q]]
                if len(cur)>=4:
                    if d[0] and f[0]:
                        for t in [.25,.5,.75]:
                            xx=round(p[0]+(q[0]-p[0])*t);options.append([p,(xx,p[1]),(xx,q[1]),q])
                    if d[1] and f[1]:
                        for t in [.25,.5,.75]:
                            yy=round(p[1]+(q[1]-p[1])*t);options.append([p,(p[0],yy),(q[0],yy),q])
                for path in options:
                    path=simplify(path);key=tuple(path)
                    if len(path)<2 or key in seen:continue
                    seen.add(key)
                    if len(path)>len(simplify(cur)) or length(path)>length(cur)+1e-6:continue
                    if len(path)==len(simplify(cur)) and length(path)>=length(cur)-15:continue
                    dx,dy=path[1][0]-p[0],path[1][1]-p[1];tx,ty=path[-2][0]-q[0],path[-2][1]-q[1]
                    if dx*d[0]+dy*d[1]<=0 or dx*d[1]-dy*d[0]!=0 or tx*f[0]+ty*f[1]<=0 or tx*f[1]-ty*f[0]!=0:continue
                    if any(through(path,r,clearance if i not in [a,b] else 0) for i,r in boxes.items()
                           if not (i in [a,b] and kind(nodes[i])=='Actor')):continue
                    if any(through(path,r,5) for r in captions):continue
                    yield path

    for e in edges:
        if e.get('fromViewId') not in nodes or e.get('toViewId') not in nodes or not orthogonal(e['points']):skipped.append(e['viewId'])
    for _ in range(passes):
        count=0
        for e in sorted(edges,key=lambda e:(-len(paths[e['viewId']]),-length(paths[e['viewId']]),e['viewId'])):
            i=e['viewId'];a,b=e.get('fromViewId'),e.get('toViewId')
            if i in skipped or a==b:continue
            cur=paths[i]
            def score(p):
                values=[conflicts(p,paths[f['viewId']],shared(e,f,p,paths[f['viewId']])) for f in edges if f['viewId']!=i]
                return sum(v[0] for v in values),sum(v[1] for v in values)
            cc,co=score(cur);best=cur;rank=(cc,len(simplify(cur)),length(cur))
            for path in sorted(candidates(e),key=lambda p:(len(p),length(p),p))[:limit]:
                # Distinct endpoints avoid merged associations and colliding multiplicities.
                if any(math.dist(path[k],paths[f['viewId']][l])<20 for f in edges if f['viewId']!=i
                       for k,node in [(0,a),(-1,b)] if kind(nodes[node]) not in {'Actor','UseCase'}
                       for l,end in [(0,'fromViewId'),(-1,'toViewId')] if f.get(end)==node):continue
                c,o=score(path)
                if c>cc or o>co+1e-6:continue
                test=(c,len(path),length(path))
                if test<rank:rank=test;best=path
            if best is not cur:paths[i]=best;changed.add(i);count+=1
        if not count:break
    operations=[];predicted=copy.deepcopy(s)
    for e in edges:
        i=e['viewId']
        if i not in changed:continue
        p=paths[i]
        def pin(node,point):
            x,y,w,h=boxes[node];return [(point[0]-x)/w,(point[1]-y)/h]
        operations.append(dict(op='connector',viewId=i,points=p,orthogonal=True,
                               fromPin=pin(e['fromViewId'],p[0]),toPin=pin(e['toViewId'],p[-1])))
    for e in predicted['elements']:
        if e['viewId'] in changed:e['points']=paths[e['viewId']]
    result=make_plan(s,operations,'routing', ['Local heuristic; classes are not moved. Reposition captions and inspect native rendering after application.',
                                           'Self-relations preserved. Non-orthogonal and unsupported endpoint shapes skipped.'])
    result.update(before=audit(s),predictedAfter=audit(predicted),skippedConnectors=skipped)
    return result
