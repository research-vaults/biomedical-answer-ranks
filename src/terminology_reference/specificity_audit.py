"""Source-backed relation-class repairs and explicitly separate granularity tests.

This is terminology/construct analysis of frozen model output, not clinical
case adjudication. Diagnosis text is the only input to relation rules.
"""

from __future__ import annotations

import hashlib

import json

import re

import zipfile

from collections import Counter

from pathlib import Path

from terminology import ROOT, Terminology, norm, readl, writel, writej, sha, STRICT, PARENT, COMPOUND, NO

OUT = ROOT / 'data/scoring_sensitivity'

PRIOR = ROOT / 'data/prior_terminology'

SOURCES = {
    'DDX': 'https://github.com/mila-iqia/ddxplus#pathology-description',
    'CDC_ICD': 'https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2026/icd10cm-Code%20Descriptions-2026.zip',
    'UPPER': 'https://www.cdc.gov/antibiotic-use/hcp/clinical-care/adult-outpatient.html',
    'STREP': 'https://www.cdc.gov/group-a-strep/hcp/clinical-guidance/strep-throat.html',
    'BRONCHITIS': 'https://www.cdc.gov/acute-bronchitis/about/index.html',
    'ACS': 'https://medlineplus.gov/ency/article/007639.htm',
    'ASTHMA': 'https://www.nhlbi.nih.gov/health/asthma/attacks',
    'PANIC': 'https://www.nimh.nih.gov/health/publications/panic-disorder-when-fear-overwhelms',
    'LEMS': 'https://www.ncbi.nlm.nih.gov/medgen/6005',
    'PLEURA': 'https://www.nhlbi.nih.gov/health/pleural-disorders',
    'MESH': 'https://www.nlm.nih.gov/mesh/concept_structure.html',
}

LABEL_HIERARCHIES = {
    frozenset(['URTI', 'Viral pharyngitis']),
    frozenset(['URTI', 'Acute laryngitis']),
    frozenset(['URTI', 'Acute otitis media']),
    frozenset(['URTI', 'Acute rhinosinusitis']),
}

WORDS = {
    'temporal': {'acute', 'chronic', 'recurrent', 'recurrence', 'exacerbation'},
    'etiologic': {'viral', 'bacterial'},
    'severity_or_site': {'severe', 'mild', 'left', 'right', 'bilateral'},
}

def coded_contracts():
    path = OUT / 'sources/icd10cm-Code-Descriptions-2026.zip'
    with zipfile.ZipFile(path) as z:
        order = z.read('icd10cm-order-2026.txt').decode('utf-8-sig').splitlines()
    codes = {line[6:13].strip(): {'description': line[77:].strip(), 'line': i+1} for i, line in enumerate(order)}
    definitions = json.loads((ROOT / 'data/ddxplus_english_22687585/release_conditions.json').read_text())
    # These explicit mismatches prohibit using source codes as an automatic
    # gold synonym authority. Other records retain name and code separately.
    caveats = {
        'Bronchitis': 'J40 is unspecified as acute/chronic; Acute Bronchitis is a refinement, not proved synonymous by this source.',
        'Pulmonary neoplasm': 'Name is broad, C34 denotes malignant bronchus/lung neoplasm. Code-based lung-cancer equivalence is a sensitivity, not a silent label replacement.',
        'Pancreatic neoplasm': 'Name is broad, C25 denotes malignant pancreas neoplasm. Keep source-coded sensitivity separate.',
        'Pericarditis': 'Name omits acute; I30 denotes acute pericarditis. Keep source-coded sensitivity separate.',
        'Possible NSTEMI / STEMI': 'I21 denotes acute myocardial infarction; ACS also includes unstable angina. The latter is not an MI synonym.',
        'Spontaneous rib fracture': 'S22.9 describes unspecified bony thorax fracture, broader than the named spontaneous rib target.',
        'Viral pharyngitis': 'J02.9 does not itself establish viral etiology; preserve the named viral restriction and reject strep-throat synonymy.',
        'Panic attack': 'F41 is a broader anxiety-disorder family; a panic attack does not establish panic disorder.',
        'Bronchospasm / acute asthma exacerbation': 'J45 asthma is broader than the named acute/symptomatic compound; plain Asthma is not a strict equivalent.',
        'HIV (initial infection)': 'B20 does not preserve the named initial-infection restriction.',
        'Tuberculosis': 'A15 is respiratory tuberculosis, narrower than the unqualified name; no automatic promotion of all code-neighbor terms.',
        'Anaphylaxis': 'T78.0 specifies adverse food reaction, narrower than the unqualified name.',
        'Atrial fibrillation': 'French label also mentions flutter while the English label and I48.91 specify fibrillation; keep labels distinct.',
        'Allergic sinusitis': 'French name/code refer to allergic rhinitis; English name says sinusitis. Explicit source inconsistency, not automatic equivalence.',
        'Localized edema': 'French name mentions generalized edema too; preserve the English target and record inconsistency.',
    }
    records = []
    for label, r in definitions.items():
        requested = [x.strip().upper().replace('.', '') for x in r['icd10-id'].split(',')]
        records.append({'label': label, 'released_metadata': {k: v for k,v in r.items() if k not in ['symptoms','antecedents']},
                        'descriptions': [{'code': c, **codes.get(c, {'description': 'NOT_FOUND_IN_THIS_VERSION', 'line': None})} for c in requested],
                        'source_locator': f'data/ddxplus_english_22687585/release_conditions.json/{label}',
                        'interpretation': caveats.get(label, 'Retain name and code separately; code linkage alone is not candidate equivalence.'),
                        'code_override_permitted': False})
    writej(OUT / 'RELEASED_TARGET_CONTRACT_AUDIT.json', records)
    writej(OUT / 'sources/ICD_SOURCE_MANIFEST.json', {'url': SOURCES['CDC_ICD'], 'sha256': sha(path),
        'bytes': path.stat().st_size, 'member': 'icd10cm-order-2026.txt',
        'released_conditions_sha256': sha(ROOT / 'data/ddxplus_english_22687585/release_conditions.json'),
        'version_limit': 'FY2026 code descriptions interpret released codes; the source does not declare this exact coding vintage.'})
    return records

class Audit:
    def __init__(self):
        self.t = Terminology()
        labels = json.loads((ROOT / 'data/normalization/LABEL_NORMALIZATION.json').read_text())['labels']
        self.label_names = {}
        for r in labels:
            # Compound label aliases were not verified as strict synonyms.
            for a in ([r['canonical']] if '/' in r['canonical'] else r['aliases'] + [r['canonical']]):
                self.label_names[norm(a)] = r['canonical']

    def judge(self, reference, candidate):
        rn, cn = norm(reference), norm(candidate)
        cleaned = norm(self.t.clean_parentheses(candidate))
        # Historical mention does not assert a current target diagnosis.
        terms = self.t.aliases.get(rn, {rn})
        historical = [m.span() for a in terms for m in re.finditer(r'\b(?:prior|previous|history of|resolved) ' + re.escape(a) + r'\b', cn)]
        mentions = [m.span() for a in terms for m in re.finditer(r'\b' + re.escape(a) + r'\b', cn)]
        if historical and all(any(h[0] <= m[0] and m[1] <= h[1] for h in historical) for m in mentions):
            return NO, 'HISTORICAL_MENTION_NOT_CURRENT_DIAGNOSIS', ['MESH']
        if rn == 'viral pharyngitis' and re.search(r'\b(?:strep throat|streptococcal pharyngitis|bacterial pharyngitis)\b', cn):
            return NO, 'CONTRADICTORY_ETIOLOGY', ['STREP']
        if reference == 'Bronchospasm / acute asthma exacerbation' and cleaned == 'asthma':
            return PARENT, 'ASTHMA_PARENT_WITHOUT_ACUTE_EPISODE', ['ASTHMA','CDC_ICD']
        if reference == 'Possible NSTEMI / STEMI':
            if cn.startswith('unstable angina'):
                if ' or ' in cn and 'acute coronary syndrome' in cn:
                    return COMPOUND, 'EXPLICIT_ANGINA_OR_BROADER_ACS_ALTERNATIVE', ['ACS','CDC_ICD']
                return NO, 'ANGINA_NOT_MYOCARDIAL_INFARCTION', ['ACS','CDC_ICD']
            if cn.startswith('acute coronary syndrome'):
                return COMPOUND, 'ACS_DOES_NOT_COMMIT_TO_MI', ['ACS','CDC_ICD']
        if rn == 'urti' and re.search(r'\b(?:bronchitis|bronchiolitis|pneumonia|pleuritis|pleurisy)\b', cn):
            if re.search(r'\b(?:urti|uri|upper respiratory)\b', cn):
                return COMPOUND, 'EXPLICIT_UPPER_AND_LOWER_DIAGNOSIS_COMBINATION', ['UPPER']
            return NO, 'UPPER_VERSUS_LOWER_OR_PLEURAL_DISEASE', ['UPPER', 'BRONCHITIS', 'PLEURA']
        if rn == 'urti' and cleaned in {'influenza', 'influenza flu', 'covid 19'}:
            return COMPOUND, 'LOCATION_UNSPECIFIED_SYSTEMIC_INFECTION', ['UPPER']
        if rn == 'pneumonia' and cleaned == 'covid 19':
            return COMPOUND, 'INFECTION_DOES_NOT_ASSERT_PNEUMONIA', ['UPPER']
        if rn == 'myasthenia gravis' and 'lambert eaton' in cn:
            return NO, 'DISTINCT_NEUROMUSCULAR_SYNDROME', ['LEMS', 'CDC_ICD']
        if rn == 'pancreatic neoplasm' and cleaned == 'hepatobiliary disease':
            return NO, 'ANATOMIC_ASSOCIATION_NOT_NEOPLASM_IDENTITY', ['CDC_ICD']
        # The archive's separate class names do not establish a clinical
        # hierarchy or exclusion. Only the explicit documented containment
        # above is used here; all other legacy relations remain unresolved.
        other = self.label_names.get(cleaned)
        if other and other != reference:
            if frozenset([reference, other]) in LABEL_HIERARCHIES:
                return PARENT, 'EXPLICIT_UPPER_AIRWAY_HIERARCHY', ['UPPER', 'CDC_ICD']
        return None, 'NO_NEW_DECISIVE_RELATION', []

    def refinement(self, reference, candidate):
        """Optional construct coarsening; never relabel as a proved synonym.

        Remove only a fixed whitelist of modifiers from the candidate, keeping
        the full reference specificity. No anatomy, competing diagnosis,
        compound or causal clause is erased. Applicable across the entire map.
        """
        clean = self.t.clean_parentheses(candidate)
        words = norm(clean).split()
        reference_words = set(norm(reference).split())
        removed = {w for w in words if any(w in values for values in WORDS.values()) and w not in reference_words}
        if not removed:
            return []
        residual = ' '.join(w for w in words if w not in removed)
        if not self.t.exact(reference, residual):
            # An acronym of the unmodified base disease remains an explanatory
            # parenthetical in the refinement endpoint. Verify it against that
            # base, not merely by length or uppercase spelling.
            parts = re.findall(r'\(([^()]*)\)', candidate)
            main = re.sub(r'\([^()]*\)', ' ', candidate)
            base = ' '.join(w for w in norm(main).split() if w not in removed)
            if parts and all(self.t.exact(base, p) for p in parts):
                residual = base
        if not self.t.exact(reference, residual):
            return []
        return sorted(k for k, values in WORDS.items() if values & removed)

    def source_coded(self, reference, candidate):
        # Secondary operational target interpretation, never primary synonym
        # authority. Match only explicit terms, not arbitrary code prefix hits.
        cn = norm(self.t.clean_parentheses(candidate))
        terms = {
            'Pulmonary neoplasm': {'lung cancer', 'lung carcinoma', 'bronchogenic carcinoma', 'bronchogenic lung cancer', 'primary lung cancer'},
            'Pancreatic neoplasm': {'pancreatic cancer', 'pancreatic carcinoma'},
            'Pericarditis': {'acute pericarditis'},
            'Possible NSTEMI / STEMI': {'acute myocardial infarction', 'myocardial infarction', 'heart attack', 'acute myocardial infarction ami', 'myocardial infarction mi'},
        }
        return cn in terms.get(reference, set())

def priority_dispositions(audit):
    rows = readl(PRIOR / 'PRIORITY_JUDGMENT_PACKET_BLINDED.jsonl')
    result = []
    for r in rows:
        ref, cand = r['reference_diagnosis'], r['candidate_diagnosis']
        cn = norm(cand)
        relation, basis, sources = audit.judge(ref, cand)
        if relation is None:
            if ref == 'Bronchitis':
                relation, basis, sources = PARENT, 'J40_UNSPECIFIED_VERSUS_ACUTE_REFINEMENT', ['CDC_ICD','BRONCHITIS']
            elif ref == 'URTI':
                relation, basis, sources = PARENT, 'NAMED_VIRAL_OR_COMMON_COLD_REFINEMENT; NONSPECIFIC_URI_USAGE_IS_ALSO_DOCUMENTED', ['UPPER','CDC_ICD']
            elif ref == 'GERD':
                relation, basis, sources = PARENT, 'SAME_DISEASE_WITH_EXACERBATION_STATE; NOT_EXACT_SPECIFICITY', ['CDC_ICD']
            elif ref == 'Bronchospasm / acute asthma exacerbation':
                relation, basis, sources = PARENT, 'PLAIN_ASTHMA_DOES_NOT_ASSERT_ACUTE_EXACERBATION', ['ASTHMA','CDC_ICD']
            elif ref == 'Possible NSTEMI / STEMI':
                if cn.startswith('unstable angina'):
                    relation, basis, sources = NO, 'UNSTABLE_ANGINA_IS_NOT_MYOCARDIAL_INFARCTION', ['ACS','CDC_ICD']
                else:
                    relation, basis, sources = COMPOUND, 'ACS_INCLUDES_MI_AND_NON_MI_ANGINA; DOES_NOT_COMMIT_TO_MI', ['ACS','CDC_ICD']
            elif ref == 'Unstable angina':
                relation, basis, sources = COMPOUND, 'EXPLICIT_ANGINA_OR_BROADER_ACS_ALTERNATIVE', ['ACS']
            elif ref == 'Spontaneous pneumothorax':
                relation, basis, sources = COMPOUND, 'EXPLICIT_SPONTANEOUS_OR_TRAUMATIC_ALTERNATIVE', ['PLEURA','CDC_ICD']
        assert relation is not None, r
        result.append({**r, 'strict_equivalence_supported': False, 'audited_relation': relation,
                       'basis': basis, 'source_keys': sources,
                       'clinical_case_correctness_adjudicated': False,
                       'remaining_question': 'Whether a more/less-specific answer deserves benchmark credit is a construct sensitivity, not a claim of synonymy.'})
    writel(OUT / 'PRIORITY_PACKET_SOURCE_DISPOSITIONS.jsonl', result)
