import base64
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import capability_scan as cap

CATALOG = json.loads((ROOT / 'data/capabilities.json').read_text())


def mock_api(path, params=None, missing_ok=False):
    if '/git/trees/' in path:
        return {'truncated': False, 'tree': [
            {'type':'blob','path':'src/gpu/shader.cpp'},
            {'type':'blob','path':'src/audio/audio.cpp'},
            {'type':'blob','path':'src/runtime/xex_loader.rs'},
            {'type':'blob','path':'third_party/lib/shader.cpp'},
            {'type':'blob','path':'tests/test_shader.cpp'},
            {'type':'blob','path':'README.md'},
        ]}, ''
    if path.endswith('/readme'):
        body = '# Roadmap\n- [x] Loader\n- [ ] GPU mapping\n- [X] Audio\n'
        return {'encoding':'base64','content':base64.b64encode(body.encode()).decode(),'path':'README.md'}, ''
    raise AssertionError('unexpected call: '+path)


class CapabilityScanTests(unittest.TestCase):
    def test_catalog_is_valid(self):
        cap.validate_catalog(CATALOG)
        self.assertEqual(len(CATALOG['features']), 20)

    def test_source_hits_are_never_implementations(self):
        result = cap.enrich_project('owner/repo','main',CATALOG,mock_api)
        self.assertNotIn('reviewed', result)
        self.assertNotIn('verified_implemented', result)
        self.assertEqual(result['inventory']['source_files'], 3)
        self.assertEqual(result['inventory']['status'], 'ok')
        self.assertEqual(result['checklist']['implemented'], 2)
        self.assertEqual(result['checklist']['total'], 3)
        self.assertTrue(any(x['id']=='shaders' for x in result['inventory']['features']))

    def test_enrichment_needs_no_manual_evidence_file(self):
        output = cap.enrich_project('owner/repo', 'main', CATALOG, mock_api)
        self.assertIn('inventory', output)
        self.assertIn('checklist', output)
        self.assertNotIn('forecast', output)
        self.assertNotIn('reviewed', output)

    def test_overlap_excludes_missing_scans(self):
        items = [
            {'repo':'a/a','name':'A','coverage':{'inventory':{'status':'ok','features':[{'id':'shaders','matching_files':4}]}}},
            {'repo':'b/b','name':'B','coverage':{'inventory':{'status':'ok','features':[{'id':'shaders','matching_files':3}]}}},
            {'repo':'c/c','name':'C','coverage':{'inventory':{'status':'error','features':[{'id':'shaders','matching_files':4}]}}}
        ]
        overlap = cap.build_overlap(items,CATALOG)
        self.assertEqual(next(x for x in overlap if x['id']=='shaders')['project_count'], 2)

if __name__=='__main__':
    unittest.main()

class DeclaredMetricTests(unittest.TestCase):
    def test_known_upstream_patterns(self):
        rules = json.loads((ROOT / 'data/declared_metrics.json').read_text())['rules']
        examples = [
            ('Freminet/ScarlettX', '(281 of 422 tracked functions)', 281, 422),
            ('ItsNotRexed/Leonida', 'All 26,503 translated', 26503, 26503),
            ('R0Y00/Xbox2Windows', '851 of 12,101 PS records compiled', 851, 12101),
            ('ivall/xcl', '26 698 / 26 698 programs of the retail pack', 26698, 26698),
            ('sammwyy/xvalkyrie', '37 of the 40 public GDK samples', 37, 40),
            ('californiaAlmonds/OpenScarlett', '**RDNA2 Opcodes Decoded:** `774/779`', 774, 779),
        ]
        for repo, text, expected_done, expected_total in examples:
            with self.subTest(repo=repo):
                vals = cap.parse_published_metrics(text, rules[repo], 'https://github.com/example/repo/blob/main/README.md')
                self.assertTrue(vals)
                self.assertEqual((vals[0]['implemented'],vals[0]['total']), (expected_done, expected_total))
                self.assertEqual(vals[0]['status'],'upstream_reported')

    def test_invalid_ratio_ignored(self):
        vals = cap.parse_published_metrics('99 of 3 tracked functions', [{'id':'a','label':'test','pattern':r'(\d+) of (\d+) tracked functions'}], 'https://github.com/a/b')
        self.assertEqual(vals, [])

class UpstreamForecastTests(unittest.TestCase):
    def test_upstream_forecast_needs_history(self):
        now=dt.datetime(2026,11,22,tzinfo=dt.timezone.utc)
        self.assertEqual(cap.estimate_reported_metric_eta('a/b','functions',50,100,[],now)['status'],'insufficient_data')
        self.assertEqual(cap.estimate_reported_metric_eta('a/b','functions',100,100,[],now)['status'],'scope_complete')

    def test_scope_eta_with_stable_denominator(self):
        now=dt.datetime(2026,11,22,tzinfo=dt.timezone.utc)
        history=[]
        for k, val in enumerate([50,60,70,80]):
            day=dt.date(2026,10,1)+dt.timedelta(days=k*10)
            history.append({'generated_at':day.isoformat()+'T00:00:00Z','projects':[{'repo':'a/b','coverage':{'reported_metrics':[{'id':'functions','implemented':val,'total':100}]}}]})
        estimate=cap.estimate_reported_metric_eta('a/b','functions',90,100,history,now)
        self.assertEqual(estimate['status'],'experimental')
        self.assertIn('not a full-emulator',estimate['scope'])
