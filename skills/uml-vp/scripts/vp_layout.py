"""Offline UML VP helpers. No network, no VP mutation, no third-party packages."""
import argparse
import json
import math
import sys
from pathlib import Path
from vp_geometry import (validate, fingerprint, audit, compare, kind, LEAVES,
                         sequence, overlap, through, segments, orthogonal, length)
from vp_routing import make_plan, route


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    p=Path(path)
    if p.exists():raise ValueError('Output already exists; choose a new path: '+str(p))
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def labels(s):
    validate(s)
    if sequence(s):return make_plan(s,[],'labels',['Sequence message captions require manual placement; skipped.'])
    edges=[e for e in s['elements'] if 'points' in e]
    shapes=[e['bounds'] for e in s['elements'] if 'points' not in e and kind(e) in LEAVES and 'bounds' in e]
    reserved=shapes+[e['labelBounds'] for e in s['elements'] if kind(e)=='Actor' and 'labelBounds' in e]
    # Work with existing label rectangles; preserve text and native font settings.
    tasks=[]
    for e in edges:
        for source,key in [('labelBounds','caption'),('multA','multA'),('multB','multB')]:
            if source not in e or min(e[source][2:])<=0:continue
            if key=='caption' and (not e.get('name') or not e.get('captionVisible',True)):continue
            tasks.append((e,key,e[source]))
    remaining=[r for _,_,r in tasks];placed=[];ops=[]
    for e,key,old in tasks:
        remaining.remove(old);w,h=old[2:];candidates=[old];path=e['points']
        if key=='caption':
            for a,b in sorted(segments(path),key=lambda pair:-math.dist(*pair)):
                if a[0]!=b[0] and a[1]!=b[1]:continue
                for t in [.5,.3,.7]:
                    x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
                    for gap in [10,25,45]:
                        if a[1]==b[1]:candidates.extend([[round(x-w/2),round(y-h-gap),w,h],[round(x-w/2),round(y+gap),w,h]])
                        else:candidates.extend([[round(x+gap),round(y-h/2),w,h],[round(x-w-gap),round(y-h/2),w,h]])
        else:
            p,q=(path[0],path[1]) if key=='multA' else (path[-1],path[-2])
            d=math.dist(p,q)
            if d:
                ux,uy=(q[0]-p[0])/d,(q[1]-p[1])/d
                for along in [22,42,62]:
                    for side in [-1,1]:
                        x=p[0]+ux*along-uy*side*(w/2+8);y=p[1]+uy*along+ux*side*(h/2+8)
                        candidates.append([round(x-w/2),round(y-h/2),w,h])
        def score(r):
            return (sum(overlap(r,b) for b in reserved)*200+sum(overlap(r,b) for b in placed+remaining)*100
                    +sum(through(f['points'],r) for f in edges)*150)
        best=min(enumerate(candidates),key=lambda pair:(score(pair[1]),pair[0]))[1]
        placed.append(best)
        if best!=old:
            if key=='caption':ops.append(dict(op='style',viewId=e['viewId'],captionSide=12))
            ops.append(dict(op='labels',viewId=e['viewId'],**{key:best}))
    return make_plan(s,ops,'labels',['Existing rectangle sizes reused; text, names, font and model properties are not rewritten.',
                                   'Greedy collision reduction only. Caption bounds can be stale; visually inspect results.'])


def check_plan(plan, current):
    validate(current)
    if plan.get('format')!='uml-vp-plan-v1':raise ValueError('Unknown plan format.')
    if plan.get('baseFingerprint')!=fingerprint(current):raise ValueError('Stale plan: snapshot changed. Generate a new proposal.')
    if plan.get('diagramId')!=current.get('diagramId') or plan.get('diagramName')!=current.get('name'):raise ValueError('Different diagram.')
    by={e['viewId']:e for e in current['elements']}
    allowed={'connector':{'op','viewId','points','orthogonal','fromPin','toPin'},
             'labels':{'op','viewId','caption','multA','multB'},'style':{'op','viewId','captionSide'}}
    for op in plan.get('operations',[]):
        typ=op.get('op');e=by.get(op.get('viewId'))
        if typ not in allowed or set(op)-allowed[typ] or not e or 'points' not in e:raise ValueError('Unsupported operation or target.')
        if typ=='connector':
            p=op.get('points',[])
            if len(p)<2 or any(len(v)!=2 or any(not isinstance(n,(int,float)) or not math.isfinite(n) for n in v) for v in p):raise ValueError('Invalid points.')
            if not op.get('orthogonal') or not orthogonal(p):raise ValueError('Connector is not orthogonal.')
            for key,endpoint,index in [('fromPin','fromViewId',0),('toPin','toViewId',-1)]:
                pin=op.get(key,[])
                if len(pin)!=2 or any(not isinstance(n,(int,float)) or not math.isfinite(n) or not 0<=n<=1 for n in pin):raise ValueError('Invalid pin.')
                shape=by.get(e.get(endpoint))
                if not shape or 'bounds' not in shape:raise ValueError('Missing endpoint.')
                x,y,w,h=shape['bounds']
                if math.dist(p[index],[x+pin[0]*w,y+pin[1]*h])>1.01:raise ValueError('Pin and path endpoint mismatch.')
        elif typ=='style' and op.get('captionSide')!=12:raise ValueError('Unsupported caption style.')
        elif typ=='labels':
            for key,r in op.items():
                if key in {'op','viewId'}:continue
                if len(r)!=4 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in r) or min(r[2:])<=0:raise ValueError('Invalid caption rectangle.')
    return dict(diagramName=current['name'],editsJson=json.dumps(plan['operations'],ensure_ascii=False))


def crops(s, plan, ox, oy, scale, width, height, size):
    validate(s)
    if scale<=0 or min(width,height,size)<=0:raise ValueError('Positive scale and image dimensions required.')
    # Intentionally supports the post-edit snapshot: target stable IDs, not the old fingerprint.
    if plan.get('diagramId')!=s.get('diagramId'):raise ValueError('Different diagram for inspection.')
    by={e['viewId']:e for e in s['elements']};regions=[];seen=set()
    for op in plan.get('operations',[]):
        e=by.get(op.get('viewId'))
        if not e:continue
        for i in [e.get('fromViewId'),e.get('toViewId')]:
            n=by.get(i)
            if not n or i in seen:continue
            seen.add(i);x,y,w,h=n['bounds'];cx=(x+w/2-ox)*scale;cy=(y+h/2-oy)*scale
            cw=min(size,width);ch=min(size,height);px=round(max(0,min(width-cw,cx-cw/2)));py=round(max(0,min(height-ch,cy-ch/2)))
            if any(abs(px-r['x'])<cw/3 and abs(py-r['y'])<ch/3 for r in regions):continue
            regions.append(dict(diagramName=s['name'],x=px,y=py,width=cw,height=ch,scale=scale,maxDimension=min(2400,size)))
    return dict(regions=regions,note='Export-pixel coordinates computed using the explicit verified canvas origin and render scale. Call inspectDiagramImage, then open/view every returned image. No visual validation is performed by this script.')


def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    for name in ['audit','simplify','labels']:
        c=subs.add_parser(name);c.add_argument('snapshot');c.add_argument('--output',required=True)
        if name=='audit':c.add_argument('--after')
        if name=='simplify':
            c.add_argument('--passes',type=int,default=3);c.add_argument('--candidate-limit',type=int,default=180);c.add_argument('--clearance',type=float,default=10)
    c=subs.add_parser('check-plan');c.add_argument('plan');c.add_argument('--current',required=True);c.add_argument('--output',required=True)
    c=subs.add_parser('inspection-plan');c.add_argument('snapshot');c.add_argument('--plan',required=True);c.add_argument('--output',required=True)
    for flag in ['origin-x','origin-y','scale']:c.add_argument('--'+flag,type=float,required=True)
    for flag in ['image-width','image-height']:c.add_argument('--'+flag,type=int,required=True)
    c.add_argument('--size',type=int,default=1200)
    args=p.parse_args()
    if args.command=='check-plan':result=check_plan(read(args.plan),read(args.current))
    else:
        s=validate(read(args.snapshot))
        if args.command=='audit':result=compare(s,read(args.after)) if args.after else audit(s)
        elif args.command=='simplify':
            if not 1<=args.passes<=10 or not 1<=args.candidate_limit<=2000 or not 0<=args.clearance<=100:raise ValueError('Invalid optimization limits.')
            result=route(s,args.passes,args.candidate_limit,args.clearance)
        elif args.command=='labels':result=labels(s)
        else:result=crops(s,read(args.plan),args.origin_x,args.origin_y,args.scale,args.image_width,args.image_height,args.size)
    write(args.output,result);print(args.output)
    if args.command=='audit' and args.after and not result['observedIdentityPreserved']:return 2
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Error: '+str(exc),file=sys.stderr);sys.exit(1)
