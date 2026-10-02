"""Versioned, outcome-hidden terminology repair; never writes frozen runs.

MeSH ConceptUI, rather than DescriptorUI, is the synonym authority. Unproved
clinical relations retain their prior value with explicit audit/sensitivity flags.
"""

from __future__ import annotations

import gzip

import hashlib

import json

import re

import shutil

import unicodedata

import xml.etree.ElementTree as ET

from collections import Counter, defaultdict

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUT = ROOT / 'data/prior_terminology'

STRICT = 'EXACT_OR_SYNONYM'

PARENT = 'ACCEPTABLE_PARENT_OR_SUBTYPE'

COMPOUND = 'COMPOUND_OR_CONTEXT_DEPENDENT'

NO = 'NOT_EQUIVALENT'

def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFKD', s).casefold() if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s.replace('&', ' and ')).split())

def readl(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def writej(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def writel(p, rows):
    p.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class Terminology:
    def __init__(self):
        self.index = defaultdict(set)
        self.records = {}
        mesh = ROOT / 'external/mesh_desc2026.xml.gz'
        with gzip.open(mesh) as f:
            for _, e in ET.iterparse(f, events=('end',)):
                if e.tag != 'DescriptorRecord':
                    continue
                descriptor = e.findtext('DescriptorUI')
                for c in e.findall('ConceptList/Concept'):
                    uid = c.findtext('ConceptUI')
                    terms = sorted({t.text for t in c.findall('TermList/Term/String') if t.text})
                    self.records[uid] = {'descriptor_id': descriptor, 'concept_id': uid,
                                         'name': c.findtext('ConceptName/String'), 'terms': terms,
                                         'locator': f'DescriptorRecord[DescriptorUI="{descriptor}"]/ConceptList/Concept[ConceptUI="{uid}"]'}
                    for term in terms:
                        self.index[norm(term)].add(uid)
                e.clear()
        labels = json.loads((ROOT / 'data/normalization/LABEL_NORMALIZATION.json').read_text())['labels']
        self.aliases = {}
        for r in labels:
            terms = {norm(r['canonical']), *(norm(t) for t in r['aliases'])}
            # Compound benchmark labels are not global synonym sets.
            if '/' not in r['canonical']:
                for t in terms:
                    self.aliases[t] = terms
        # Benchmark shorthand is a disease label; NLM D019142/M0028540
        # supplies the explicit disease synonyms. Not a lexical-prefix rule.
        self.index['ebola'].add('M0028540')
        # CDC names tuberculosis (TB); this is a verified abbreviation, not
        # acceptance of every short uppercase parenthetical.
        tb_terms = {'tuberculosis', 'tb'}
        for term in tb_terms:
            self.aliases[term] = tb_terms

    def ids(self, text):
        n = norm(text)
        return set().union(*(self.index.get(t, set()) for t in self.aliases.get(n, {n})))

    def exact(self, a, b):
        na, nb = norm(a), norm(b)
        if na == nb:
            return True
        if nb in self.aliases.get(na, set()):
            return True
        ai, bi = self.ids(a), self.ids(b)
        # Ambiguous terminology hits are not evidence of exact identity.
        return len(ai) == len(bi) == 1 and ai == bi

    def clean_parentheses(self, s):
        parts = re.findall(r'\(([^()]*)\)', s)
        main = re.sub(r'\([^()]*\)', ' ', s).strip()
        if not parts:
            return s
        initials = ''.join(w[0] for w in norm(main).split() if w not in {'of', 'the', 'and'})
        for p in parts:
            acronym = p.strip().isupper() and norm(p).replace(' ', '') == initials
            if not (acronym or self.exact(main, p)):
                return s
        return main

    def judge(self, reference, candidate):
        """Receives diagnosis text only; no outcomes, family, rank, or policy."""
        rn, cn = norm(reference), norm(candidate)
        aliases = self.aliases.get(rn, {rn})
        for alias in aliases:
            # Explicit target exclusion, not 'without shock' or non-target negation.
            if re.search(r'\b(?:non|not|excluding|without|no)\s+' + re.escape(alias) + r'\b', cn):
                return NO, 'EXPLICIT_TARGET_EXCLUSION', []
        if rn == cn:
            return STRICT, 'UNICODE_NORMALIZED_IDENTITY', []
        if self.exact(reference, candidate):
            return STRICT, 'ASSERTED_ALIAS_OR_SINGLE_MESH_CONCEPT', sorted(self.ids(reference) & self.ids(candidate))
        cleaned = self.clean_parentheses(candidate)
        if cleaned != candidate and self.exact(reference, cleaned):
            return STRICT, 'VERIFIED_EQUIVALENT_PARENTHETICAL', sorted(self.ids(reference) & self.ids(cleaned))
        return None, 'NO_NEW_DETERMINISTIC_AUTHORITY', []

    def key(self, candidate):
        """Target-independent conservative semantic key for aggregation."""
        cleaned = self.clean_parentheses(candidate)
        ids = self.ids(cleaned)
        if len(ids) == 1:
            return 'MESH_CONCEPT:' + next(iter(ids))
        n = norm(cleaned)
        return 'ALIAS:' + min(self.aliases[n]) if n in self.aliases else 'SURFACE:' + n

def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()
