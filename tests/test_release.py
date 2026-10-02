import json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from transport_io import parse
from analyze_common_pool_support import contrast
def readl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
class ReleaseTests(unittest.TestCase):
    def test_pool_construction_from_generation(self):
        from pool_construction import fresh_pools
        folder=R/'data/fresh_confirmation'
        cfg=json.loads((folder/'CONFIG.json').read_text())
        lookup=json.loads((R/'data/normalization/LABEL_NORMALIZATION.json').read_text())['lookup']
        rebuilt=fresh_pools(cfg,readl(folder/'GENERATOR_CANONICAL.jsonl'),lookup)
        self.assertEqual(rebuilt,json.loads((folder/'NATURAL_POOL_MANIFEST.json').read_text())['pools'])
    def test_parser_valid(self):
        p,_=parse('{"selected_candidate_id":"C001"}','selection',['C001','C002']);self.assertEqual(p,{'selected_candidate_id':'C001'})
    def test_parser_rejects_outside_pool(self):
        p,_=parse('{"selected_candidate_id":"C999"}','selection',['C001']);self.assertIsNone(p)
    def test_contrast_sign(self):
        self.assertEqual(contrast({'M_forward':1,'M_reverse':0,'H_forward':0,'H_reverse':1}),2)
    def test_contrast_invariance(self):
        self.assertEqual(contrast(dict.fromkeys(['M_forward','M_reverse','H_forward','H_reverse'],.5)),0)
    def test_case_and_sample_counts(self):
        for folder,gen,sel,call in [('fresh_confirmation',2688,1536,'SELECTOR_CALLS.jsonl'),('native_key_transport',1792,1024,'SELECTION_CALLS.jsonl')]:
            root=R/'data'/folder;self.assertEqual(len(readl(root/'GENERATOR_CANONICAL.jsonl')),gen)
            self.assertEqual(len({x['identity'] for x in readl(root/call) if x.get('ok')}),sel)
    def test_common_pool_completed_choices(self):
        rows=readl(R/'data/common_pool/CALLS.jsonl');good={x['identity']:x for x in rows if x.get('ok')}
        self.assertEqual(len(good),6400)
        for row in good.values():self.assertEqual(row['finish_reason'],'stop')
    def test_schedule_matches_retained_responses(self):
        pairs=[('common_pool','SCHEDULE.jsonl','CALLS.jsonl'),('fresh_confirmation','SELECTOR_SCHEDULE.jsonl','SELECTOR_CALLS.jsonl'),('native_key_transport','SELECTOR_SCHEDULE.jsonl','SELECTION_CALLS.jsonl')]
        for folder,s,c in pairs:
            root=R/'data'/folder;schedule={x['identity']:x for x in readl(root/s)}
            for row in readl(root/c):
                self.assertEqual(row['payload'],schedule[row['identity']]['payload'])
                self.assertNotIn('raw_provider_payload',row)
    def test_common_pool_matched_rank_dose(self):
        units=json.loads((R/'data/common_pool/UNITS.json').read_text());self.assertEqual(len(units),320)
        for u in units:
            n=len(u['candidates']);a=u['ordinal'];self.assertEqual(sorted(a['H'].values()),list(range(1,n+1)));self.assertEqual(sorted(a['M'].values()),list(range(1,n+1)))
            self.assertEqual(sorted(abs(r-(n+1-r)) for r in a['H'].values()),sorted(abs(r-(n+1-r)) for r in a['M'].values()))
    def test_no_false_transport_confirmation(self):
        r=json.loads((R/'expected/native_key_transport.json').read_text())
        for v in r.values():self.assertLess(v['J']['ci97_5'][0],0);self.assertGreater(v['J']['ci97_5'][1],0)
if __name__=='__main__':unittest.main()
