# Discarding Answer Ranks Changes the Case for Mixing Biomedical LLMs

Public research release of recorded biomedical model outputs, analysis code,
claim-supporting traces, and a complete manuscript. This is a method-analysis
study, not a new voting method or a clinical decision system.

## Paper and findings

[Full manuscript](manuscript/current/full-paper.pdf): **1 October 2026 research
draft**, with nine scientific pages, references on pages 10–12, and supplement
on pages 13–38. This is not a claim that these bytes were submitted or accepted.
[LaTeX source](manuscript/current/main.tex), all figures and style files, and a
[self-contained source ZIP](manuscript/current/manuscript-source.zip) are included.
PDF SHA-256: `1707638557abe487c73d3a513b2e0b3731e70fba62a2422b367928f972e51be1`.

Holding ranked answers fixed, counting every listed answer rather than just the
first can weaken repeated-model sampling more than mixed-model sampling. On 288
MedXpertQA questions, the resulting shift in the mixed-minus-Gemma accuracy gap
is 9.72 percentage points [5.29, 14.21]. A relative shift is not a better policy:
on a separate 720-question test, mixing loses 8.95 points [−11.16, −6.75] against
the development-selected Gemma first-choice policy. Health data provide a
different boundary: mixing helps inclusion voting without outperforming the
selected first-choice policy. The intervals are the manuscript's 95% intervals.
Model quality is not matched; these results do not isolate an intrinsic effect
of lineage diversity or establish clinical validity.

## Setup and reproduction

Use Python 3.11 or later on a CPU. Install dependencies once; subsequent
stored-output analyses need no network, credentials, model weights, GPU or API.
Allow several minutes and approximately 2 GB working disk for extracted inputs
and isolated replay outputs. Use a new output directory for each run.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/verify_release.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python src/reproduce_latest.py --output outputs/latest
```

The latest replay runs ten supplementary capsules, including the eight-check
representation suite, exact allocation/budget analyses, rank destruction,
task and composition sensitivities, information controls, tie policies and the
equal-budget donor screen. It verifies archive checksums and compares generated
results with the supplied expected outputs. The experiments are **not rerun**:
the scripts recompute inference on already recorded outputs. Bootstrap samples,
banks, reused questions and retries do not create additional independent cases.

Earlier scientifically relevant controls are also reproducible:

```bash
.venv/bin/python src/reproduce.py --output outputs/earlier-controls
.venv/bin/python src/verify_common_pool_traces.py
```

These earlier analyses include failed transport and scoring-sensitive findings;
they are not substituted for the paper's native-answer-key results. The older
five-check entry point `src/reproduce_current.py` is retained for compatibility;
use `reproduce_latest.py` for the complete present suite.

## Rebuild the paper

Install a TeX distribution with `latexmk`, pdfLaTeX, BibTeX and the packages used
in the source. No shell escape is required.

```bash
.venv/bin/python src/build_manuscript.py --output outputs/paper-build
```

The command builds the main paper, references and supplement in isolation and
checks for unresolved references. The committed PDF is the version identified
above; timestamps can make rebuilt PDF bytes differ without changing content.

## Contents and provenance

| Location | Purpose |
|---|---|
| `data/current/supplementary-material.zip` | Latest ten replay capsules: stripped ranked answers, native keys, protocols, analysis programs and expected results |
| `data/` | Earlier generation/selection observations, schedules, frozen scoring maps and numerical targets |
| `evidence/current/` | Four sanitized generation-attempt banks: output text, completion/failure states and usage where recorded; prompt hashes replace question text |
| `evidence/attempts/` | Relevant earlier retained attempt histories, including failures, as checksummed gzip shards |
| `evidence/logs/` | Historical successful replay logs, not new inference or provider invoices |
| `src/`, `tests/`, `expected/` | Portable analyses, tests and regression targets |
| `manuscript/current/` | One complete research draft and its self-contained source |
| `docs/` | Scientific provenance, rights, evidence map and reproduction boundaries |

Across the program, generators include Gemma-4-26B-A4B, Llama-3.1-8B,
Ministral-14B, Qwen2.5-14B and Llama-3.3-70B. The central 720-question and Health
tests use Gemma and Llama-3.3-70B; the latter is not a small model. See the
manuscript and schedules for model identifiers and per-study participation.

Only recorded returned model text is included; no hidden reasoning is inferred.
Provider envelopes, account IDs, credentials, private patient data, internal
reviews, planning files and obsolete manuscript drafts are excluded. Historical
capsule filenames, experimental IDs and hash-seed namespaces remain where they
are scientific provenance or affect numerical reproduction. Capsule statements
about their original internal creation are historical, not this release's status.

See [data attribution](docs/DATA_AND_ATTRIBUTION.md) and
[evidence and large files](docs/EVIDENCE_AND_LARGE_FILES.md). Files are limited
to 50 MiB; large traces use deterministic gzip shards. No Git LFS or separately
authenticated storage is needed. Third-party licenses and citation attribution
are preserved; this release does not relicense third-party material.

Optional `src/replay_requests.py` defaults to a dry run and can execute explicitly
limited archived requests only when requested. New calls cost money and produce
new stochastic observations; they are not necessary for the numerical replay.
Never commit environment files or credentials.

This public repository may be associated with its authors through external
links. It is **not certified anonymous for conference review**; a separate
reviewer-facing snapshot must be used when required. No conference submission
was changed to create this release. Numerical reproduction is not independent
clinical adjudication or a guarantee of future model behavior.
