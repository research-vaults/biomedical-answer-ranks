import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/native_key_transport'
SELECTORS={'gemini':'google/gemini-2.5-flash-lite','llama':'meta-llama/llama-3.1-8b-instruct'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def parse(text, phase, allowed=None):
    state='EXACT_JSON'
    try: obj=json.loads(text)
    except (ValueError,TypeError):
        m=re.search(r'\{.*\}',text,re.S)
        try: obj=json.loads(m.group(0)) if m else None; state='EXTRACTED_JSON'
        except ValueError: obj=None
    if not isinstance(obj,dict): return None,'INVALID_JSON'
    if phase=='generation':
        cs=obj.get('candidates')
        if not isinstance(cs,list) or len(cs)!=5: return None,'INVALID_COUNT'
        if not all(isinstance(c,dict) and c.get('option_id') in list('ABCDEFGHIJ') and isinstance(c.get('rationale'),str) and c['rationale'].strip() for c in cs): return None,'INVALID_FIELDS'
        if len({c['option_id'] for c in cs})!=5: return None,'DUPLICATE_OPTIONS'
        return {'candidates':[{'option_id':c['option_id'],'rationale':c['rationale'].strip()} for c in cs]},state
    cid=obj.get('selected_candidate_id')
    return ({'selected_candidate_id':cid},state) if set(obj)=={'selected_candidate_id'} and cid in allowed else (None,'INVALID_SELECTION')
