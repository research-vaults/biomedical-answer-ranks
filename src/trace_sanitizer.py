"""Allowlisted projection of a provider attempt into release-relevant evidence."""
ROOT_FIELDS={'identity','attempt','phase','ok','parsed','parser_state','text','finish_reason','error_type','http_status','charged_or_reserved_usd','cost_is_estimate','failed_call_empty'}
ITEM_FIELDS={'identity','case_id','branch','model','lineage','sample_index','phase','allowed_candidate_ids','pool_id','view','condition'}
PAYLOAD_FIELDS={'model','messages','temperature','top_p','max_tokens','seed','response_format','stop','presence_penalty','frequency_penalty'}
USAGE_FIELDS={'prompt_tokens','completion_tokens','total_tokens','cost'}
def sanitize(row):
    out={k:v for k,v in row.items() if k in ROOT_FIELDS}
    item=row.get('item') or {}
    out['item']={k:v for k,v in item.items() if k in ITEM_FIELDS}
    payload=row.get('payload') or item.get('payload') or {}
    out['payload']={k:v for k,v in payload.items() if k in PAYLOAD_FIELDS}
    if isinstance(payload.get('provider'),dict):
        out['payload']['provider']={k:v for k,v in payload['provider'].items() if k in {'only','ignore','order','allow_fallbacks','require_parameters'}}
    out['usage']={k:v for k,v in (row.get('usage') or {}).items() if k in USAGE_FIELDS}
    # Preserve returned model text, not account metadata or provider envelopes.
    raw=row.get('raw_provider_payload') or {}
    if raw.get('choices'):
        choice=raw['choices'][0]
        if 'text' not in out:out['text']=choice.get('message',{}).get('content') or ''
        if 'finish_reason' not in out:out['finish_reason']=choice.get('finish_reason')
        if not out['usage']:out['usage']={k:v for k,v in (raw.get('usage') or {}).items() if k in USAGE_FIELDS}
    return out
