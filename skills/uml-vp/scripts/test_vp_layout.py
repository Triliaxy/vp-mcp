"""Behavioral regression tests; no VP server, project mutation or external dependency."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from vp_geometry import audit, compare, conflicts, simplify, through, fingerprint
from vp_routing import route
from vp_layout import check_plan, labels, crops, write


def node(i,x,y,w=120,h=80,typ='Class'):
    return dict(viewId=i,modelId='model-'+i,modelType=typ,name=i,bounds=[x,y,w,h])


def edge(i,a,b,pts,typ='Association'):
    return dict(viewId=i,modelId='model-'+i,modelType=typ,name=i,fromViewId=a,toViewId=b,points=pts)


def snapshot(*elements,typ='ClassDiagram'):
    return dict(diagramId='diagram-1',name='Any project name',type=typ,elements=list(elements))


class LayoutTests(unittest.TestCase):
    def sample(self):
        return snapshot(node('A',0,0),node('B',0,300),edge('link','A','B',[[120,40],[180,40],[180,340],[120,340]]))

    def test_direct_facing_ports_replace_detour_without_mutation(self):
        s=self.sample();before=copy.deepcopy(s);plan=route(s)
        self.assertEqual(s,before)
        self.assertEqual(len(plan['operations']),1)
        op=plan['operations'][0]
        self.assertEqual(len(op['points']),2)
        self.assertEqual(op['fromPin'][1],1)
        self.assertEqual(op['toPin'][1],0)
        self.assertEqual(plan['predictedAfter']['totalBends'],0)
        self.assertFalse(plan['predictedAfter']['connectorThroughShapes'])
        self.assertIn('editsJson',check_plan(plan,s))

    def test_obstacle_blocks_direct_route(self):
        s=self.sample();s['elements'].append(node('obstacle',-20,130,160,80));plan=route(s)
        self.assertFalse(plan['predictedAfter']['connectorThroughShapes'])
        for op in plan['operations']:
            self.assertFalse(through(op['points'],s['elements'][-1]['bounds']))

    def test_self_relation_is_preserved(self):
        s=snapshot(node('A',0,0),edge('self','A','A',[[120,20],[180,20],[180,60],[120,60]]))
        self.assertEqual(route(s)['operations'],[])

    def test_sequence_detected_by_type_not_name(self):
        s=self.sample();s['name']='No sequence keyword';s['type']='InteractionDiagram'
        self.assertEqual(route(s)['operations'],[])
        self.assertEqual(labels(s)['operations'],[])

    def test_diagonal_detected_and_not_rerouted(self):
        s=self.sample();s['elements'][-1]['points']=[[120,40],[0,300]]
        self.assertEqual(audit(s)['nonOrthogonal'],['link'])
        self.assertEqual(route(s)['operations'],[])

    def test_crossings_and_collinear_overlaps_are_separate(self):
        self.assertEqual(conflicts([[0,5],[10,5]],[[5,0],[5,10]]),(1,0))
        self.assertEqual(conflicts([[0,5],[10,5]],[[5,5],[15,5]]),(0,5))
        self.assertEqual(conflicts([[0,0],[10,10]],[[0,10],[10,0]]),(1,0))
        self.assertEqual(conflicts([[0,0],[10,0]],[[10,0],[10,10]],[(10,0)]),(0,0))

    def test_simplify_preserves_reversal(self):
        self.assertEqual(simplify([[0,0],[10,0],[5,0]]),[(0,0),(10,0),(5,0)])
        self.assertEqual(simplify([[0,0],[5,0],[10,0]]),[(0,0),(10,0)])

    def test_changed_endpoint_identity_detected(self):
        s=self.sample();t=copy.deepcopy(s);t['elements'][-1]['toViewId']='A'
        self.assertFalse(compare(s,t)['observedIdentityPreserved'])

    def test_stale_proposal_rejected_and_order_ignored(self):
        s=self.sample();plan=route(s);s['elements'].reverse()
        check_plan(plan,s)
        s['elements'][-1]['bounds'][0]+=20
        with self.assertRaisesRegex(ValueError,'Stale'):check_plan(plan,s)

    def test_model_mutation_operation_rejected(self):
        s=self.sample();plan=route(s)
        plan['operations']=[dict(op='renameModel',viewId='link',name='different')]
        with self.assertRaises(ValueError):check_plan(plan,s)

    def test_pin_mismatch_rejected(self):
        s=self.sample();plan=route(s);plan['operations'][0]['fromPin']=[0,0]
        with self.assertRaisesRegex(ValueError,'mismatch'):check_plan(plan,s)

    def test_labels_preserve_names_and_avoid_class(self):
        s=self.sample();e=s['elements'][-1];e['labelBounds']=[0,5,90,20];e['captionVisible']=True
        before=copy.deepcopy(s);plan=labels(s)
        self.assertEqual(s,before)
        self.assertTrue(plan['operations'])
        self.assertTrue(all(op['op'] in {'style','labels'} for op in plan['operations']))
        for op in plan['operations']:
            if 'caption' in op:self.assertNotEqual(op['caption'],e['labelBounds'])
        check_plan(plan,s)

    def test_crop_coordinates_are_scaled_clamped_and_explicit(self):
        s=self.sample();plan=route(s);r=crops(s,plan,-50,-50,2,1000,1000,300)
        self.assertTrue(r['regions'])
        self.assertTrue(all(0<=v['x']<=700 and 0<=v['y']<=700 for v in r['regions']))

    def test_output_does_not_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';write(p,{'original':True})
            with self.assertRaises(ValueError):write(p,{'original':False})
            self.assertEqual(json.loads(p.read_text()),{'original':True})


if __name__=='__main__':unittest.main()
