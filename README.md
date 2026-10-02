# Discarding Answer Ranks Changes the Case for Mixing Biomedical LLMs

Counting every answer in a ranked list can make mixing models look better by
weakening the repeated-model baseline. This repository reproduces that
comparison from saved biomedical model outputs; it introduces no new voting rule.

[Paper PDF](manuscript/current/full-paper.pdf) ·
[Fixed paper version](https://github.com/research-vaults/biomedical-answer-ranks/blob/956426b4e3b352f21a6ef06a5cd9142b3efb7835/manuscript/current/full-paper.pdf) ·
[LaTeX source](manuscript/current/main.tex) ·
[Source ZIP](manuscript/current/manuscript-source.zip)

## Paper and findings

**Manuscript:** 1 October 2026 research draft, not the accepted workshop-upload
version. Scientific pages 1–9; references 10–12; supplement 13–38.
**Artifact:** 2 October 2026 saved-output release. The checksum manifest binds
the distributed inputs, source and PDF.

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

## Quick start

Use Python 3.11 or later on a CPU. Install dependencies once; subsequent
stored-output analyses need no network, credentials, model weights, GPU or API.
Allow several minutes and approximately 2 GB working disk for extracted inputs
and isolated replay outputs. Use a new output directory for each run. The
recorded environment uses the versions in `requirements.txt`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/verify_release.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python src/reproduce_latest.py --output outputs/latest
```

Expected completion: `PASS: all ten current capsules; no new model outputs.`
Results and per-capsule logs appear in `outputs/latest/`; `VERIFICATION.json`
records the comparisons. The runner verifies archive checksums and compares
recomputed results with frozen expectations. It does not regenerate model answers.

## Which command supports which result?

Run these from the repository root with the environment above.

| Evidence | Command | Scope |
|---|---|---|
| Main fixed-ballot contrast, selected-policy comparison and Health transfer | `.venv/bin/python src/reproduce_latest.py --output outputs/latest` | Recommended entry point; includes the eight-check representation suite |
| Rank, tie, composition, task, information and finite-budget analyses | Same `reproduce_latest.py` command | Included in its ten capsules; exploratory reuse is preserved |
| Earlier candidate-selection and support-channel controls | `.venv/bin/python src/reproduce.py --output outputs/earlier-controls` | Supporting evidence, including failed transport and scoring sensitivity |
| Text/payload consistency of the common-pool control | `.venv/bin/python src/verify_common_pool_traces.py` | Reconstructs choices and point estimates from recorded responses |

The older `reproduce_current.py` runs a superseded five-check subset and is kept
for compatibility; it is not needed in addition to `reproduce_latest.py`.
Bootstrap samples, banks, reused questions and retries are not independent cases.

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

## Reproduction boundaries and rights

The replay checks inference on saved answers, not fresh generation, clinical
adjudication, or historical provider kernels. Earlier clinical-name scoring
remains conditional on its frozen mappings. Failed calls, null results and
source-transfer failures are retained. Current figure assets are included;
the numerical replay does not regenerate every original plotting pipeline.

See [data attribution and terms](docs/DATA_AND_ATTRIBUTION.md),
[evidence and large-file handling](docs/EVIDENCE_AND_LARGE_FILES.md), and
[data transformations](docs/RELEASE_TRANSFORMATIONS.md). Scientific IDs and
seed namespaces are retained for reproducibility. Traces contain returned model
text, not inferred hidden reasoning. Large traces use checksummed gzip shards;
no Git LFS or separate storage account is needed.

**Original-code licence:** no project-wide reuse licence has yet been granted
for original code, manuscript or generated records. Public availability is not
a declaration of open-source licensing. Third-party materials retain their
stated terms; this repository does not relicense them.

Optional `src/replay_requests.py` defaults to a dry run and can execute explicitly
limited archived requests only when requested. New calls cost money and produce
new stochastic observations; they are not necessary for the numerical replay.
Never commit environment files or credentials.

## Cite this version

This title-based reference identifies the distributed research draft without
adding unverified author metadata:

```bibtex
@misc{discarding_answer_ranks_2026,
  title = {Discarding Answer Ranks Changes the Case for Mixing Biomedical LLMs},
  year = {2026},
  note = {Research draft, 1 October 2026; saved-output artifact, 2 October 2026},
  url = {https://github.com/research-vaults/biomedical-answer-ranks/blob/956426b4e3b352f21a6ef06a5cd9142b3efb7835/manuscript/current/full-paper.pdf}
}
```
