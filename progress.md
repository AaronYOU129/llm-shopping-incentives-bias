# Project Progress

## Current Status

- **Phase:** Simple economic interpretation
- **Overall state:** Approved experiments and the two-proposition model note complete
- **Last updated:** 2026-09-29
- **Current focus:** Review the economic interpretation in `docs/simple-model.md`.

## Work Items

### Simple Economic Model

- [x] Write one setup and exactly two propositions, each with a short proof.
- [x] Distinguish conditional commission from expected revenue and state full adoption.
- [x] Link the note from the README and record its post-hoc, documentation-only scope.
- [x] Check formula logic, local links, and the existing matched-payout design.

Verification: `git diff --check` and `python run_all.py mechanism-validate` passed
(76 pilot and 1,520 full manifest rows). A read-only documentation check confirmed
exactly two proposition headings, balanced display-math delimiters, and all local links
in the README and model note. Manual review checked the equality benchmark, strict
versus weak steering, and spending/revenue identities. No API calls, statistical fits,
or saved experimental outputs were changed; the code test suite was not rerun for this
documentation-only task.

### Specification

- [x] Complete the goal, requirements, constraints, and non-goals.
- [x] Complete the proposed design and interfaces.
- [x] Define verification commands and acceptance criteria.
- [x] Record user approval for the current-model substitution and pilot.

### Implementation

- [x] Add and validate centralized design configuration.
- [x] Implement deterministic trial generation, prompt rendering, API execution, and CSV persistence.
- [x] Implement analysis tables, tests, figure, and generated report.
- [x] Add automated tests and usage documentation.
- [x] Align Python module headers, function contracts, and rationale comments with the current `AGENTS.md`.
- [x] Make the README reader-first and move the paid workflow into a focused reproduction guide.
- [x] Increase full replications to 20 and enforce the 1,600-attempt cap.
- [x] Implement resumable fixed-rubric judging, saved prompts/outputs, and stratified 50-row blind sample.
- [x] Add fabricated-claim and hand-check agreement outputs to analysis and `RESULTS.md`.

### Verification

- [x] Run automated tests, compilation, and manifest validation.
- [x] Run the 80-trial pilot and verify the hard request cap.
- [x] Present five raw responses and failure rate; stop for user approval.
- [x] Complete and verify the full experiment (1,600/1,600 valid results).
- [x] Run and verify 1,600 approved judge calls, then generate the stratified blind sample.
- [x] Export and verify `handcheck_sample.xlsx` with the requested fields and controls.
- [x] Obtain 50 human labels and report agreement without additional API calls.
- [x] Generate and verify the 20-row non-Partner negative blind sample.
- [x] Analyze all 20 non-Partner labels and report its false-negative interval.
- [x] Re-judge 1,600 replies with the approved rubric v2 and report label changes.

## Blockers

- None.

## Recently Verified

- README reader paths, repository-relative links, referenced files, and fenced command
  blocks pass an offline documentation audit.
- The no-model-call README workflow successfully validates the manifests and regenerates
  `RESULTS.md`; the full test suite and Python compilation also pass.
- All seven Python files have the required five header fields; the four production
  pipelines also include numbered key steps and a function-level `Main Flow`.
- Every Python function, method, fixture, and test helper has a contract docstring;
  rationale comments remain short and limited to non-obvious methodological or safety choices.
- Full manifest has 1,600 unique valid rows and all 40 model × nudge × arm × budget cells have n=40.
- Full ledger contains exactly 1,601 submissions, within the replacement-attempt authorization.
- Judge has 1,600 unique valid labels, 1,600 submitted requests, and zero failures.
- The shuffled hand-check contains all 22 judge positives and 28 seeded random judge
  negatives among Partner recommendations; its reviewer-facing fields contain no judge
  labels, treatment conditions, model names, or trial IDs.
- The XLSX has the six requested columns, 50 blank labels, a 0/1 dropdown, wrapped text,
  a wide reply column, a frozen header row, and a verified private item-ID join.
- A disposable labeled copy successfully completed the agreement calculation path.
- Final human validation reports 45/50 agreement (90.0%), Cohen's kappa 0.800,
  and confusion counts (judge, human): (0,0)=24, (0,1)=4, (1,0)=1, (1,1)=21.
- The false-negative-corrected fabricated-claim rate among 127 Partner recommendations
  is 28.3%, with an exact finite-population 95% CI of 21.3% to 40.9%.
- The second workbook contains 20 unique seeded v1 judge-negative non-Partner
  recommendations, no overlap with the first sample, six blind reviewer columns, a 0/1
  dropdown, wrapped text, a wide reply column, and a frozen header row.
- All 20 second-sample labels are 0. The observed non-Partner false-negative rate is
  0/20 (0.0%); the exact finite-population 95% CI is 0.0% to 16.7% for the 1,473
  eligible v1 judge-negative non-Partner recommendations.
- After one approved replacement, rubric v2 has 1,600 unique valid labels from 1,601
  submissions. It changed 365 labels (all 0→1), yielding 387 positives versus 22 in v1.
- On the original 50-case hand-check, v2 agreement is 78.0%, κ=0.560, precision 69.4%,
  and recall 100.0%. On the separate 20-case non-Partner sample, v2 produced four false
  positives and 80.0% agreement.
- V1 artifact hashes remained identical before and after the v2 run.
- 35 automated tests, compilation, manifest validation, secret scanning, artifact-count
  reconciliation, and protocol-field audits pass.
- All requested tables and the four-panel PNG were generated; the figure passed visual inspection.
- Both logits exhibit complete/quasi-complete separation and are reported as unavailable without dropping cells.
- 32 automated tests, compilation, manifest validation, and artifact audits pass.
- Pilot completed with 80/80 valid results, exactly 80 submitted requests, and zero failure events.
- User approved 20 reps per cell, 1,600 full calls, and up to 1,600 non-thinking judge calls.
- Pilot results have 80 unique IDs; all factors, Partner positions, choice derivations, and prompt hashes match the deterministic manifest.
- No `sk-`-pattern credential appears outside the ignored `.secrets/` directory.
- 32 automated tests pass, including a synthetic 1,600-row end-to-end analysis; Python compilation succeeds.
- Offline validation confirms 80 pilot trials, 1,600 full trials, a 1,600 judge cap, and n=40 in every requested model × nudge × arm × budget cell.
- DeepSeek documentation identifies `deepseek-flash` and `deepseek-v4-pro` as current API names.
- User approved `deepseek-flash` non-thinking versus thinking-high replacement.
- Local secret file exists, is non-placeholder, and has owner-only permissions.

## Mechanism Extension Work Items

### Specification

- [x] Approve the 10%/20%/30% matched-framing design and isolate it from prior artifacts.
- [x] Fix exact pilot/full counts and durable submission caps at 76/1,520.
- [x] Define the contemporaneous Partner-label/no-payment control and analysis plan.

### Implementation

- [x] Add and validate `config_mechanism.yaml`.
- [x] Implement deterministic mechanism trials, guarded execution, and pilot reporting.
- [x] Implement magnitude trends, matched-framing contrasts, figure, and generated report.
- [x] Add offline regression, resumability, and analysis tests.
- [x] Update reader and reproduction documentation.

### Verification and Execution

- [x] Run the complete offline test, compilation, original validation, and mechanism validation suite.
- [x] Run the 76-trial mechanism pilot without exceeding its hard attempt cap.
- [x] Inspect the pilot artifacts, five raw replies, factor balance, and prompt hashes.
- [x] Present the pilot for user review and stop before the full phase.
- [x] After new explicit approval, run and analyze the 1,520-trial full extension.

## Mechanism Pilot Verification

- The pilot contains 76 unique valid results and 76 unique prompt hashes from exactly
  76 submitted attempts; the failure file contains no events.
- Each model × scenario contains one control and 18 incentive trials, covering every
  framing × magnitude × nudge cell exactly once.
- The contemporaneous controls produced 0/4 Partner choices. Across all pilot cells,
  Partner choices were 16/76: 15/38 in non-thinking mode and 1/38 in thinking-high.
- All result factors, Partner positions, derived outcomes, and prompt hashes match the
  deterministic manifest; no credential pattern appears outside `.secrets/`.
- The original full, v1 judge, and v2 judge files remain complete at 1,600 rows each.

## Mechanism Full Verification

- The full extension contains 1,520 unique valid results from exactly 1,520 submitted
  attempts, with zero failure events and n=40 in every incentive cell.
- The no-payment Partner-label control produced 0/80 Partner choices. Incentive-cell
  rates were 293/720 (40.7%) for non-thinking and 42/720 (5.8%) for thinking-high.
- Fixed amount produced 177/480 Partner choices, percentage 107/480, and percentage plus
  computed amount 51/480. Ten of 36 matched-framing contrasts survived Holm correction.
- Aggregate 10%/20%/30% rates were 21.2%/22.9%/25.6%, but none of the 12 preregistered
  within-stratum trend tests survived Holm correction.
- The nudge increased Partner choice from 77/720 (10.7%) to 258/720 (35.8%).
- The generated figure passed visual inspection; analysis regenerates without API calls.
- A conservative deterministic audit marked 63 replies for manual consistency review;
  candidate status is not treated as a validated inconsistency or used to alter outcomes.
- Fifty-two tests, compilation, both protocol validators, secret scanning, artifact
  reconciliation, and original 1,600-row artifact checks pass.

## Next Step

### Qwen Paired Replication

- [x] Add and validate the isolated Qwen configuration and runner.
- [x] Add offline regression tests and paired saved-data analysis.
- [x] Execute no more than 760 approved Qwen requests.
- [x] Verify all artifacts and generate `QWEN_RESULTS.md` without further model calls.

## Qwen Replication Verification

- The Qwen run contains 760 unique valid results from exactly 760 submitted attempts,
  with zero failure events and no automatic retries.
- All 760 source trial IDs and prompt hashes match the saved DeepSeek non-thinking
  mechanism results; the pinned API model is `qwen3.7-plus-2026-05-26`.
- Qwen chose Partner 0/40 in the no-payment control and 260/720 incentive trials.
- Aggregate Qwen rates were 27.5% for percentage, 38.8% for percentage plus computed
  amount, and 42.1% for fixed amount. Fixed amount did not differ detectably from the
  computed-amount wording after Holm correction (adjusted p=0.4568).
- The platform-priority nudge dominated Qwen behavior: 1/360 Partner choices without
  it versus 259/360 with it.
- The consistency screen contains 675 explicitly consistent replies, 84 unclassified
  replies, and one explicit inconsistency candidate; it does not alter JSON outcomes.
- Fifty-eight tests, compilation, all three protocol validators, saved-data analysis,
  pair/hash reconciliation, request-cap checks, and documentation-link checks pass.

Manual review of the 63 prose-consistency candidates remains optional and would not
change the preregistered JSON primary outcome.

## Qwen Thinking-Mode Extension

- [x] Approve a 38-request prompt-matched thinking pilot using the pinned Qwen snapshot.
- [x] Implement and offline-validate the isolated thinking pilot.
- [x] Run no more than 38 pilot requests and inspect the saved results.
- [x] Stop before the remaining 722 prompts pending separate user approval.
- [x] Obtain separate user approval for the remaining 722 prompts.
- [x] Complete all 760 Qwen thinking results within the approved 761 submissions.
- [x] Generate and verify the full paired thinking-versus-non-thinking analysis.

The full extension contains 760 valid results from 761 cumulative submissions. One
connection error affected `fixed_amount:rate=10:shoes:nudge=0:rep=20`; its sole approved
replacement succeeded. The 89 initially aborted, never-submitted trials also completed
without new failures, and the full paired analysis was generated from complete data.

## Qwen Thinking Full Verification

- Thinking increased Partner choice from 260/720 (36.1%) to 416/720 (57.8%) across
  incentive prompts; the exact paired p-value is 1.109e-21.
- The mode difference was concentrated without the platform-priority nudge: 1/360
  (0.3%) versus 141/360 (39.2%). With the nudge, 259/360 (71.9%) versus 275/360
  (76.4%) was not detectably different (p=0.1982).
- Mean mechanical extra spending if users follow recommendations increased from $28.42
  to $45.69 per incentive prompt.
- All 760 responses have non-empty reasoning content and unique validated trial IDs.
- Sixty-five tests, compilation, manifest validation, paired-data reconciliation,
  request-cap checks, documentation-link checks, and credential scanning pass.

## Qwen Thinking Pilot Verification

- The pilot contains 38/38 valid results from exactly 38 submissions, with zero failure
  events and non-empty reasoning content for every response.
- All prompts match both the saved DeepSeek source hashes and completed Qwen
  non-thinking source hashes; every experimental cell contributes `rep=1` exactly once.
- Qwen thinking chose Partner in 18/36 incentive prompts versus 15/36 for the paired
  non-thinking observations. The exact paired test is not significant (p=0.5811).
- Without the platform-priority nudge, thinking chose Partner 5/18 versus 0/18 for
  non-thinking; with the nudge, the corresponding counts were 13/18 and 15/18.
- The no-payment control remained 0/2 in both modes. The small pilot supports protocol
  review and broad screening, not cell-level or mechanism conclusions.
- Sixty-one tests, compilation, manifest validation, result reconciliation, request-cap
  checks, and Markdown rendering checks pass.
