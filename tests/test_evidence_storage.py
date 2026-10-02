import json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from large_files import pack,unpack,chunks
from trace_sanitizer import sanitize
class EvidenceStorageTests(unittest.TestCase):
    def test_roundtrip_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/'trace.jsonl';source.write_bytes(b'{"text":"example response"}\n'*170000)
            a=pack(source,p/'a');b=pack(source,p/'b');self.assertEqual(a,b);self.assertGreater(len(a['parts']),1)
            unpack(p/'a/manifest.json',p/'restored.jsonl');self.assertEqual(source.read_bytes(),(p/'restored.jsonl').read_bytes())
            with self.assertRaises(FileExistsError):unpack(p/'a/manifest.json',p/'restored.jsonl')
    def test_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'input').write_bytes(b'example');pack(p/'input',p/'bundle');part=p/'bundle/part-000000.gz';part.write_bytes(part.read_bytes()+b'changed')
            with self.assertRaises(AssertionError):unpack(p/'bundle/manifest.json',p/'output')
            self.assertFalse((p/'output').exists())
    def test_sanitizer_keeps_science_not_provider_envelope(self):
        r={'identity':'trial-1','text':'example answer','ok':False,'attempt':2,'http_status':429,'account_id':'not-a-real-account','raw_provider_payload':{'id':'not-a-real-request'},'payload':{'model':'example','messages':[],'authorization':'dummy'},'usage':{'prompt_tokens':12,'account_id':'dummy'}}
        s=sanitize(r);self.assertEqual(s['text'],r['text']);self.assertEqual(s['attempt'],2);self.assertEqual(s['http_status'],429)
        self.assertNotIn('raw_provider_payload',s);self.assertNotIn('account_id',s);self.assertNotIn('authorization',s['payload']);self.assertEqual(s['usage'],{'prompt_tokens':12})
