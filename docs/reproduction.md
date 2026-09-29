# Full Reproduction and Operations Guide

This guide covers the complete experiment workflow, including commands that submit
paid DeepSeek API requests. To inspect the findings or regenerate analysis from the
saved data, use the no-model-call path in the main [README](../README.md) instead.

## Current status

The pilot, 1,600-trial full experiment, v1 judge, both human validation exercises,
rubric-v2 sensitivity analysis, mechanism extension, and Qwen replication are complete.
Existing successful IDs are resumable and skipped.

## Requirements and credentials

- Python 3.11 or newer
- Dependencies from `requirements.txt`
- A DeepSeek API key for API-backed phases
- Explicit approval before the full experiment and rubric-v2 judge

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Store the API key as the only line in `.secrets/deepseek_api_key`. This ignored local
file must never be committed, logged, pasted into chat, or included in shared outputs.
The commands below export it only to the invoked Python process.

## Validate without model calls

Run these checks before any API-backed phase:

```bash
python -m pytest -q
python -m compileall -q .
python run_all.py validate
```

Validation checks the centralized configuration, the 80-trial pilot manifest, the
1,600-trial full manifest, and both versioned judge protocols.

## Regenerate analysis from saved artifacts

This command does not require an API key and makes no model calls:

```bash
python run_all.py analyze
```

It validates the saved full and judge results, regenerates statistical tables and the
figure under `outputs/full/`, refreshes validation summaries, and rewrites `RESULTS.md`.

## Run or resume the pilot

```bash
DEEPSEEK_API_KEY="$(<.secrets/deepseek_api_key)" python run_all.py pilot
```

The pilot contains 80 planned trials and has a hard cap of 80 submitted requests,
including retries. The runner writes artifacts under `outputs/pilot/`, produces
`outputs/pilot/PILOT.md`, and stops without starting the full experiment. Review the
pilot before granting explicit approval for the full phase.

## Run or resume the full experiment and v1 judge

Only after reviewing and approving a complete pilot:

```bash
DEEPSEEK_API_KEY="$(<.secrets/deepseek_api_key)" \
  python run_all.py full --approve-full
```

The full manifest contains 1,600 trials. Its durable ledger permits at most 1,601
submissions because one replacement request was explicitly authorized after a transient
retry. When all full results are valid, the same command runs or resumes the v1 judge
with its separate 1,600-submission cap, creates the blind validation artifacts, and
regenerates the analysis.

## Complete the blinded human checks

The v1 validation uses two workbooks:

1. `outputs/judge/handcheck_sample.xlsx` contains all 22 v1 judge positives and 28
   sampled judge-negative Partner recommendations.
2. `outputs/judge/handcheck_nonpartner_negatives_v1.xlsx` contains 20 sampled v1
   judge-negative non-Partner recommendations.

For each workbook, fill only the blank `my_label` cells with `0` or `1`; `my_note` is
optional. Do not inspect judge labels or private item keys before completing the blind
review. Save each workbook in place, then run:

```bash
python run_all.py analyze
```

The analysis writes agreement, confusion counts, the corrected Partner rate, and the
non-Partner false-negative validation to versioned CSV artifacts and `RESULTS.md`.

## Run or resume the rubric-v2 judge

Only after explicit approval of the exact rubric-v2 text:

```bash
DEEPSEEK_API_KEY="$(<.secrets/deepseek_api_key)" \
  python run_all.py judge-v2 --approve-rubric-v2
```

Rubric v2 has an independent hard cap of 1,601 submissions: the initial 1,600 plus one
explicitly authorized replacement after a transient retry. It writes only under
`outputs/judge_v2/`, preserves every v1 artifact, produces paired label comparisons,
and regenerates `RESULTS.md` after completion.

## Resumability, failures, and spending limits

- Successful identifiers are validated and skipped on rerun.
- Every request, including a retry, is reserved in the phase ledger before submission.
- Durable caps prevent reruns or retries from exceeding the authorized request total.
- Transient API failures receive bounded exponential retries while budget remains.
- Parse and terminal API failures are retained in `failures.csv`.
- Missing or malformed outcomes are never guessed.
- Non-transient API or configuration errors stop further submissions for that run.

The authoritative limits and protocol text live in [config.yaml](../config.yaml). Their
rationale and replacement authorizations are recorded in the
[decision log](../decision-log.md).

## Model mapping and protocol fidelity

The retired `deepseek-chat` and `deepseek-reasoner` aliases were replaced, with user
approval, by two modes of the same current model family:

- `deepseek-flash/non-thinking`
- `deepseek-flash/thinking-high`

The experiment sends and records temperature 1.0 for both conditions. DeepSeek ignores
temperature in thinking mode, so the nominal setting is retained for protocol fidelity
and disclosed as a limitation. Both judge versions use non-thinking mode at temperature
0.

## Artifact map

| Location | Contents |
| --- | --- |
| `outputs/pilot/` | Pilot results, failures, ledger, metadata, and pilot report |
| `outputs/full/` | Full results, ledger, statistical tables, model status, and figure |
| `outputs/judge/` | V1 prompts, labels, validation workbooks, keys, and summaries |
| `outputs/judge_v2/` | V2 prompts, labels, metadata, and v1-to-v2 comparisons |
| `RESULTS.md` | Data-derived final report |
| `outputs/mechanism/` | Isolated pilot, full results, ledgers, tables, audit, and figure |
| `MECHANISM_RESULTS.md` | Data-derived matched-framing extension report |

For the approved design and acceptance criteria, see
[specification.md](../specification.md). For the implementation workflow, see
[ai-assisted-development-workflow.md](ai-assisted-development-workflow.md).

## Qwen paired replication

Store the Alibaba Cloud Model Studio key as the only line in
`.secrets/qwen_api_key`. Validate all 760 DeepSeek-to-Qwen prompt pairs without making
an API call:

```bash
python run_all.py qwen-validate
```

Only after explicit spending approval, run or resume the comparison:

```bash
QWEN_API_KEY="$(<.secrets/qwen_api_key)" \
  python run_all.py qwen-run --approve-qwen-run
```

The runner uses `qwen3.7-plus-2026-05-26` with thinking disabled, temperature 1.0,
and the exact 760 source prompts previously assigned to DeepSeek non-thinking. Every
submission is reserved in `outputs/qwen_comparison/request_attempts.csv` before the
call. The hard cap is 760, and automatic retries are disabled; a failure therefore
requires separate authorization for any replacement request.

After a complete run, regenerate the comparison tables and `QWEN_RESULTS.md` without
model calls:

```bash
python run_all.py qwen-analyze
```

### Qwen thinking pilot

The isolated thinking pilot replays `rep=1` from all 38 source cells on the same pinned
Qwen snapshot. Validate its paired manifest without model calls:

```bash
python run_all.py qwen-thinking-validate
```

The approved pilot was run with:

```bash
QWEN_API_KEY="$(<.secrets/qwen_api_key)" \
  python run_all.py qwen-thinking-pilot --approve-qwen-thinking-pilot
```

The command writes durable artifacts and `PILOT.md` under `outputs/qwen_thinking/`, then
stops. Its 38-call cap has been exhausted; the remaining 722 prompts require separate
authorization and are not part of the pilot command.

### Qwen thinking full extension

The completed extension reused the 38 pilot rows. A connection error required one
explicitly approved replacement, so its final durable cap is 761 submissions for 760
valid prompt pairs:

```bash
QWEN_API_KEY="$(<.secrets/qwen_api_key)" \
  python run_all.py qwen-thinking-full --approve-qwen-thinking-full \
  --approve-qwen-thinking-replacement
```

Regenerate the paired mode analysis without API calls with:

```bash
python run_all.py qwen-thinking-analyze
```

## Incentive-magnitude mechanism extension

The extension is configured independently in `config_mechanism.yaml` and never writes
to the completed original-study directories. Validate its 76/1,520 manifests without
an API key:

```bash
python run_all.py mechanism-validate
```

Run or resume its capped pilot with the same shell-scoped key procedure documented
above:

```bash
DEEPSEEK_API_KEY="$(<.secrets/deepseek_api_key)" \
  python run_all.py mechanism-pilot
```

The command writes `outputs/mechanism/pilot/PILOT.md` and stops. Only after reviewing
that report and explicitly approving the full extension may the guarded full command
be used:

```bash
DEEPSEEK_API_KEY="$(<.secrets/deepseek_api_key)" \
  python run_all.py mechanism-full --approve-mechanism-full
```

The 1,520-attempt ceiling includes retries. No replacement attempt is pre-authorized;
an exhausted cap leaves the phase incomplete. After a complete saved run, regenerate
its tables, figure, and `MECHANISM_RESULTS.md` without model calls:

```bash
python run_all.py mechanism-analyze
```
