# Model outputs, execution traces, claim-supporting logs and large files

## What is included

These experiments use recorded model requests and responses, not tool-using laboratory agents. Their execution traces consist of scheduled scientific identities, request payloads, returned answer/rationale text, parsed choices, attempts/failures, completion reasons and token usage where originally available. No private chain of thought is inferred or manufactured; only text actually returned and recorded is retained.

| Claim or diagnostic | Model outputs and execution trace | Supporting records and reproducible check |
| --- | --- | --- |
| Current fixed-ballot representation contrast and selected-policy comparison | Stripped ranked option IDs in `data/current/supplementary-material.zip`; generation attempts in `evidence/current/` | `src/reproduce_latest.py`; ten capsules including the eight-check representation suite, Native720 and Health256 |
| Rank information, ties, composition and finite-budget boundaries | The same capsules preserve source/task IDs, paired banks, empty failures and candidate ranks | Rank, tie, composition, task-strata and donor replay capsules; exploratory reuse, not new cases |
| Diagnostic-specificity and early access/selection effects | `data/development_observations/GENERATOR_CANONICAL.jsonl`, `NATURAL_CALLS.jsonl`, pools; `data/interface_screen/CALLS.jsonl` | `data/scoring_sensitivity/`, `data/development_replay/`; `src/replay_development.py` |
| Selector and support-channel extension | `data/selector_extension/CALLS.jsonl`, `data/joint_reference/CALLS.jsonl`, their schedules and scored rows | `src/analyze_development_selectors.py`, `src/analyze_support_channel.py` |
| Fresh paired support-use contrast | `data/fresh_confirmation/GENERATOR_CANONICAL.jsonl`, `SELECTOR_CALLS.jsonl`, exact schedules, maps and pools | `src/analyze_fresh_confirmation.py`; branch and order scripts; `data/order_challenge/` |
| Native-key transport, including non-confirmation | `data/native_key_transport/GENERATOR_CANONICAL.jsonl`, `SELECTION_CALLS.jsonl`, schedules, official keys and pools | `src/analyze_native_key_transport.py`, `src/plot_source_comparison.py` |
| Common-pool support interface | `data/common_pool/CALLS.jsonl` (6,409 attempts for 6,400 valid choices), `SCHEDULE.jsonl`, `UNITS.json` | `src/analyze_common_pool_support.py`, independent `src/verify_common_pool_traces.py`; intervention checks and case vectors |
| Failed attempts, retry history and earlier full-ranking failure | All records in the explicitly listed compressed banks under `evidence/attempts/` | `evidence/TRACE_INDEX.json`: exact counts, source-record fingerprints, output availability, logical and storage hashes |

Canonical generation files contain the records selected for the analysis, including explicit empty failed slots. The added attempt banks preserve the full retained hosted/local-serving attempts for development, fresh confirmation and native-key generation, plus development difficulty and the failed full-ranking predecessor. Do not count retries as new independent cases or pool this predecessor into the repaired single-choice experiment. The index reports `ok_missing` separately from failure, rather than inventing missing statuses. Record order is the preserved order within each source ledger; hosted and local-serving ledgers are concatenated with route labels, not misrepresented as a recovered global wall-clock timeline.

`evidence/logs/` contains the stdout/stderr of a fresh, successful **offline** replay of the 12 analysis/plot programs, a numerical verification summary, automated test output and the independent common-pool text/payload/token check. These logs support numerical reproduction; they are not original provider runtime logs or new model generations. `evidence/historical_checks/` separately preserves sanitized historical verification reports and clearly labels their original-record scope. A passing log is corroborating evidence, not a substitute for inspectable inputs and executable analysis.

## Privacy boundary

`src/trace_sanitizer.py` uses a field allowlist. It preserves scientific text/settings/attempt information and removes provider envelopes, authorization fields, account/request identifiers, infrastructure addresses, provisioning details and arbitrary error/traceback strings. Available failure type and HTTP status remain. New exports are checked against the original returned text so sanitization does not silently rewrite a model's answer. Public benchmark text remains subject to the attribution and rights statement in `DATA_AND_ATTRIBUTION.md`.

Claim-supporting `.log` files are explicitly allowed under `evidence/logs/`; generic runtime/build `.log` files remain ignored elsewhere. New evidence is scanned in decompressed form as well as stored form. Original opaque scientific request IDs, reproducible seed namespaces, published citations, public model identifiers and necessary third-party attribution are retained; none is an account credential. No private keys, environment files, private patient data, hidden provider reasoning, operational account logs or internal reviews are included.

## Large-file policy and commands

- **Project policy:** every individual Git-tracked file must be at most **50 MiB**. This is our conservative project limit, not a statement of GitHub's platform limits. `src/verify_release.py` enforces it.
- Existing analysis inputs remain ordinary files so the standard replay commands work unchanged. No existing input is replaced by an LFS pointer or a missing download.
- New large attempt ledgers use deterministic gzip shards. Each shard compresses at most **4 MiB of logical input**. `mtime=0` avoids recording a local creation time; gzip contains no source pathname. A manifest records the hash and byte count of every stored shard and of the reconstructed logical file.
- A shard can split a JSON line. **Do not treat each shard as a standalone JSONL dataset.** Use `unpack` to reconstruct the byte-identical original logical file before reading lines.
- Everything needed is committed to this release repository. **No Git LFS, paid external storage, expiring links or external account is required.** Future oversized data require equivalent durable access, hashes and retrieval instructions.

Example using the fresh-generation attempt history, from the repository root:

```bash
python src/large_files.py verify evidence/attempts/fresh_generation/manifest.json
python src/large_files.py unpack evidence/attempts/fresh_generation/manifest.json outputs/fresh-generation-attempts.jsonl
python src/verify_release.py
python -m unittest discover -s tests -v
```

To pack a future **already sanitized and reviewed** ledger into a new bundle:

```bash
python src/large_files.py pack outputs/sanitized-attempts.jsonl evidence/attempts/new-study
```

Packing is not anonymization. Review the decompressed content before adding it, update the trace index, stage the intended files, regenerate `SHA256SUMS` with `python src/verify_release.py --write-manifest`, and run verification again before committing. Never force-push or rewrite old history to conceal an accidentally committed secret; stop publication and handle the exposure explicitly. Packing and unpacking refuse to overwrite existing destinations; a tampered bundle fails verification before the final reconstructed file is published.

## Reproducing the independent execution check

```bash
python src/verify_common_pool_traces.py
python src/reproduce.py --output outputs/new-replay
```

The independent common-pool check parses retained response text afresh, verifies payload correspondence, reconstructs all eight scoring/selector point estimates, and reports matched candidate/order/rank groups, actual prompt-token ranges, completion reasons and attempt counts. Main replay preserves case-cluster bootstrap uncertainty. Neither check converts frozen semantic labels into clinically adjudicated truth.
