"""Opt-in bounded replay of frozen requests, independent of the offline analyses."""
import argparse,json,os,urllib.request
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('schedule');p.add_argument('--output',default='outputs/new-requests.jsonl');p.add_argument('--limit',type=int,default=1);p.add_argument('--execute',action='store_true');p.add_argument('--base-url',default='https://openrouter.ai/api/v1');p.add_argument('--key-env',default='OPENROUTER_API_KEY');p.add_argument('--model',help='Explicit endpoint mapping; recorded alongside the original model');p.add_argument('--max-input-tokens',type=int,default=20000);p.add_argument('--max-output-tokens',type=int,default=512);a=p.parse_args()
    if a.limit<1:raise SystemExit('Limit must be positive.')
    rows=[json.loads(x) for x in Path(a.schedule).read_text().splitlines() if x.strip()][:a.limit]
    print('Selected requests:',len(rows),'execution:',a.execute)
    if not a.execute:return
    out=Path(a.output)
    if out.exists():raise SystemExit('Refusing to overwrite an existing request ledger.')
    if not os.environ.get(a.key_env):raise SystemExit('Required process environment variable is absent; no request sent.')
    out.parent.mkdir(parents=True,exist_ok=True)
    for row in rows:
        payload=dict(row['payload']);original=payload['model']
        if a.model:payload['model']=a.model
        if payload.get('max_tokens',0)>a.max_output_tokens:raise SystemExit('Recorded output cap exceeds explicit limit; request not altered.')
        # A conservative UTF-8 byte bound avoids silently sending unbounded prompts.
        if len(json.dumps(payload['messages']).encode())>a.max_input_tokens:raise SystemExit('Input byte-bound exceeds limit; request not altered.')
        request=urllib.request.Request(a.base_url.rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ[a.key_env]})
        try:
            with urllib.request.urlopen(request,timeout=120) as response:result=json.load(response)
            c=result['choices'][0];record={'identity':row['identity'],'original_model':original,'payload':payload,'text':c['message'].get('content',''),'finish_reason':c.get('finish_reason'),'usage':{k:v for k,v in result.get('usage',{}).items() if k in ['prompt_tokens','completion_tokens','total_tokens','cost']}}
        except Exception as e:
            record={'identity':row['identity'],'error_type':type(e).__name__,'http_status':getattr(e,'code',None)}
        with out.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
    print('Request ledger written; no credentials or raw provider envelopes retained.')
if __name__=='__main__':main()
