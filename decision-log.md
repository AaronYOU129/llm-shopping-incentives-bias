# Decision Log

## DEC-001 — Preserve the original model-mode contrast on the current API

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** User and implementing agent
- **Related specification sections:** Functional Requirements; Constraints; Risks

### Context

The requested `deepseek-chat` and `deepseek-reasoner` aliases were retired on
2026-07-24. Current models expose thinking as a mode. Using Flash versus Pro would
change model family and reasoning simultaneously.

### Options Considered

1. **Same-family mode comparison:** Use `deepseek-flash` with thinking disabled versus enabled-high.
2. **Different current models:** Compare Flash and Pro, confounding model family with reasoning.
3. **Stop permanently:** Do not run because the legacy identifiers are unavailable.

### Decision

Use `deepseek-flash` in non-thinking and thinking-high modes, with explicit labels in
the experimental `model` column. Continue sending/logging temperature 1.0 and disclose
that DeepSeek ignores it in thinking mode.

### Rationale

This most closely preserves the original non-reasoning versus reasoning factor while
holding model family constant. The user explicitly approved it.

### Consequences

- **Positive:** The two levels remain interpretable as a reasoning-mode comparison.
- **Negative:** Results do not reproduce legacy model versions and thinking has no effective temperature control.
- **Follow-up:** Record exact mode and API identifier in metadata and limitations.

## DEC-002 — Enforce the call authorization as a durable request-attempt budget

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** Implementing agent
- **Related specification sections:** Reliability; Constraints; Error Handling

### Context

The original design required retries but forbade calls beyond 80 pilot plus 800 full.
Retries are still submitted API requests and therefore can increase cost.

### Options Considered

1. **Unbounded phase completion:** Retry every trial independently, potentially exceeding authorization.
2. **Durable attempt budget:** Count every initial request and retry against the phase cap.
3. **No retries:** Preserve the call cap but violate the reliability requirement.

### Decision

Record every request reservation durably before submission and cap total reservations
at the then-approved 80 for pilot and 800 for full. Retries consume the same cap. DEC-004
later raises only the full cap to 1,600; the same reservation mechanism remains in force.

### Rationale

This satisfies both requirements without silently increasing cost. If failures consume
the budget, the run reports incomplete cells rather than making unauthorized calls.

### Consequences

- **Positive:** Reruns and crashes cannot exceed the authorized request total.
- **Negative:** Transient failures can leave the phase incomplete at the cap.
- **Follow-up:** Report submitted attempts, incomplete trials, and failures in pilot/final reports.

## DEC-003 — Keep credentials outside Python and versioned project files

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** User and implementing agent
- **Related specification sections:** Inputs; Security and privacy

### Context

The user prefers a local file for entering the DeepSeek key, while the experiment
requires Python to obtain it from `DEEPSEEK_API_KEY`.

### Options Considered

1. **Read the secret file in Python:** Convenient but violates the explicit environment-variable interface.
2. **Shell-scoped export:** Load the ignored local file into the child process environment only.
3. **Commit a configuration key:** Unsafe and prohibited.

### Decision

Keep the owner-readable key at `.secrets/deepseek_api_key`. The invoking shell exports
its value as `DEEPSEEK_API_KEY`; Python reads only that variable.

### Rationale

This supports the requested local workflow without hardcoding, logging, or committing a secret.

### Consequences

- **Positive:** Secret handling is local, ignored, and compatible with the required interface.
- **Negative:** Users must load the variable before invoking Python directly.
- **Follow-up:** Document a safe command and validate only presence, never value.

## DEC-004 — Increase full-run precision to twenty replications per cell

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** User
- **Related specification sections:** Functional Requirements; Constraints; Acceptance Criteria

### Context

The pilot passed, and the user requested n=40 for each arm × budget cell within each
model × nudge combination after pooling the two scenarios.

### Decision

Increase full replications from 10 to 20, producing 1,600 experiment trials and a
durable 1,600-request submission cap.

### Rationale

Two scenarios times twenty replications yields the requested n=40 per reported cell.

### Consequences

- **Positive:** Narrower descriptive uncertainty and requested cell sizes.
- **Negative:** Doubles full-run API usage.
- **Follow-up:** Validate all 1,600 manifest IDs before and after execution.

## DEC-005 — Add a fixed-rubric post-hoc fabrication judge and blind validation

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** User and implementing agent
- **Related specification sections:** Functional Requirements; Outputs; Risks

### Context

One pilot response invented stronger build/support despite explicit product equivalence.
The user approved a post-hoc outcome without changing experimental prompts.

### Decision

Judge every full-run reply with `deepseek-flash`, thinking disabled, temperature 0,
using one fixed rubric. Save prompts and raw/parsed outputs, cap submissions at 1,600,
and initially draw a seeded simple random sample of 50 for human coding. Blind the sample
to the judge labels until human labels are complete. DEC-007 supersedes only the sampling
design after the completed judge results showed 22 positives.

### Rationale

The fixed prompt makes the post-hoc measure auditable; same-size automated coding covers
all replies, while blinded human review estimates classification reliability.

### Consequences

- **Positive:** Captures an unanticipated failure mode with explicit validation.
- **Negative:** Post-hoc status and same-provider judging limit interpretation.
- **Follow-up:** Use the DEC-007 stratified sample and report rates as post-hoc, plus
  agreement, Cohen's kappa, and confusion counts.

## DEC-006 — Authorize one replacement experiment request

- **Status:** Accepted
- **Date:** 2026-09-22
- **Decision makers:** User
- **Related specification sections:** Constraints; Error Handling; Acceptance Criteria

### Context

One transient error during the full phase was retried successfully, consuming one of
the 1,600 authorized submissions and leaving the final planned trial unsubmitted.

### Decision

Raise the full-stage durable attempt cap from 1,600 to exactly 1,601. Use the sole new
reservation to submit the missing trial; do not authorize any further replacement calls.

### Rationale

This completes the approved 1,600-trial factorial design without guessing the missing
outcome and keeps the cost expansion to one explicit request.

### Consequences

- **Positive:** All planned factorial cells can reach their approved sample size.
- **Negative:** Total experiment request submissions can be 1,601 because of the recovered retry.
- **Follow-up:** Verify 1,600 unique valid results and exactly 1,601 or fewer ledger entries.

## DEC-007 — Enrich the blinded hand-check for judge-positive cases

- **Status:** Accepted
- **Date:** 2026-09-23
- **Decision makers:** User
- **Related specification sections:** Human validation; Outputs; Risks

### Context

A simple random sample contained too few judge-positive cases to assess errors on the
post-hoc outcome efficiently. The completed judge stage produced 22 positive labels.

### Decision

Replace the simple random hand-check with all 22 judge-positive replies plus a seeded
random sample of 28 judge-negative replies among responses that recommended the Partner
product. Shuffle the combined 50 rows and expose only opaque item IDs, reconstructed A/B
listings, replies, and blank human-label/note fields in the reviewer workbook.

### Rationale

Including every observed positive makes false-positive review possible for the full set,
while the eligible negative stratum provides a targeted check for false negatives among
the behavior of greatest substantive interest. Opaque IDs and omitted treatment fields
preserve reviewer blinding.

### Consequences

- **Positive:** The validation set contains 22 positive and 28 relevant negative cases.
- **Negative:** The enriched sample is not representative of the 1,600-reply prevalence;
  use it for agreement and confusion counts, not prevalence estimation.
- **Follow-up:** After all 50 `my_label` cells are filled, join through the private key
  and report raw agreement, Cohen's kappa, and the confusion matrix.

## DEC-008 — Correct the Partner rate and extend validation to non-Partner recommendations

- **Status:** Accepted
- **Date:** 2026-09-23
- **Decision makers:** User
- **Related specification sections:** Human validation; Outputs; Constraints; Risks

### Context

The completed stratified hand-check found one false positive among all 22 v1 judge
positives and four false negatives in the random sample of 28 judge-negative Partner
recommendations. The first validation sample did not cover non-Partner recommendations.

### Decision

Estimate the human-corrected fabricated-claim rate among Partner recommendations using
the census of judge positives and design weights for the sampled judge-negative stratum.
Invert the finite-population hypergeometric distribution for an exact 95% interval.
Separately draw 20 seeded random v1 judge-negative non-Partner recommendations for a
second blinded hand-check. Preserve v1 when the user later supplies rubric v2.

### Rationale

The estimator reflects unequal inclusion probabilities and the interval accounts for
sampling without replacement. The second sample checks a substantively distinct stratum
that the first design omitted.

### Consequences

- **Positive:** The corrected Partner estimate and its uncertainty match the actual
  validation design; non-Partner false negatives can be assessed separately.
- **Negative:** The correction treats human labels as the reference standard. The
  20-case non-Partner sample leaves a broad upper confidence bound even when no false
  negatives are observed.
- **Follow-up:** Do not start v2 calls until the exact revised rubric is received.

### Validation outcome

All 20 second-sample labels were human-negative. The observed false-negative rate in
the 1,473-case v1 judge-negative non-Partner stratum is 0/20, with an exact
finite-population 95% interval of 0.0% to 16.7%.

## DEC-009 — Approve a broader rubric v2 with isolated artifacts and budget

- **Status:** Accepted
- **Date:** 2026-09-24
- **Decision makers:** User
- **Related specification sections:** Functional Requirements; Outputs; Constraints

### Context

The v1 judge missed several human-coded claims expressed through vague superiority,
trust, service, support, fit, and value language. The user approved the proposed exact
rubric v2 after reviewing its inclusion and exclusion rules.

### Decision

Re-judge all 1,600 saved replies using `deepseek-flash`, thinking disabled, temperature
0, and the approved v2 prompt. Use an independent 1,600-submission hard cap, including
retries. Store every v2 artifact under `outputs/judge_v2/`, retain v1 unchanged, and
produce a complete paired label comparison.

### Rationale

The revised rubric directly covers the observed v1 error modes while preserving the
original experiment responses and making the classification change auditable.

### Consequences

- **Positive:** V1 and v2 can be reproduced, compared item by item, and evaluated on the
  existing blinded human labels.
- **Negative:** With no spare submissions beyond 1,600, any retry can leave an item
  unresolved and require new explicit authorization to complete it.
- **Follow-up:** Completed. The cap, prompt hashes, metadata, label changes, preserved v1
  hashes, and report were verified.

### Replacement authorization

One transient retry consumed an authorized submission and left the final planned reply
unsubmitted at 1,599 valid labels. On 2026-09-24, the user approved exactly one
replacement request, raising only the v2 cap from 1,600 to 1,601.

## DEC-010 — Run an isolated matched-framing incentive-magnitude extension

- **Status:** Accepted
- **Date:** 2026-09-28
- **Decision makers:** User and implementing agent
- **Related specification sections:** Incentive-Magnitude Mechanism Extension

### Context

The original experiment found substantially more Partner choices under a fixed
per-purchase amount than under a nearly equal 10% payment. That arm comparison changed
the numerical representation, wording, and exact payout at once, so it cannot identify
whether the difference came from incentive magnitude, arithmetic burden, or framing.

### Decision

Run a separate randomized extension crossing 10%, 20%, and 30% incentive magnitudes
with percentage-only, percentage-plus-computed-amount, and fixed-amount representations.
Match exact dollar payouts within scenario and rate, retain the two model modes and
nudge conditions, and use only the both-affordable budget. Add a contemporaneous control
that retains the Partner label but explicitly provides no platform payment. Use 76 pilot
and 1,520 full trials with no pre-authorized replacement attempts, store all outputs
under `outputs/mechanism/`, and require pilot review before the full phase.

### Rationale

The computed-amount condition directly tests whether making percentage arithmetic
explicit closes the framing gap. Exact matching prevents payout size from contaminating
the comparison, while the label-preserving control separates economic incentives from
the Partner designation. Rerunning all conditions contemporaneously avoids treating a
potentially updated API model as equivalent to the earlier served version.

### Consequences

- **Positive:** Magnitude trends and framing effects become separately testable.
- **Positive:** Existing results and judge artifacts remain unchanged and auditable.
- **Negative:** The extension requires up to 76 pilot and, after approval, 1,520 full calls.
- **Negative:** It identifies prompt effects, not the model's inaccessible internal reasoning.
- **Follow-up:** Verify offline, run the capped pilot, present it, and stop for approval.

### Pilot review and full authorization

The pilot completed with 76/76 valid results, exactly 76 submissions, and no failures.
After reviewing the protocol summary and the observed JSON-to-prose inconsistency risk,
the user approved the 1,520-trial full phase on 2026-09-28. The JSON `recommended` field
remains the primary outcome. A separate deterministic audit flags explicit prose choices
for manual review without changing or guessing the primary outcome.

### Completion outcome

The full phase completed with 1,520 valid results from exactly 1,520 submissions and no
failures. No preregistered within-stratum magnitude trend survived Holm correction. Ten
of 36 matched-framing contrasts survived correction, all in non-thinking cells and all
involving higher Partner-choice rates for fixed-amount wording. The consistency audit
remains a candidate screen rather than a substitute outcome.

## DEC-011 — Replay the mechanism prompts on a fixed Qwen snapshot

- **Status:** Accepted
- **Date:** 2026-09-28
- **Decision makers:** User and implementing agent
- **Related specification sections:** Qwen Paired Replication

### Context

The mechanism extension found a strong fixed-amount framing effect in DeepSeek's
non-thinking mode. A second model family can distinguish a DeepSeek-specific response
from a framing pattern that transfers across independently post-trained systems.

### Decision

Replay the exact 760 prompts assigned to DeepSeek non-thinking using
`qwen3.7-plus-2026-05-26` with thinking disabled and temperature 1.0. Pair observations
by the saved DeepSeek source trial ID, isolate all artifacts, and enforce a durable
760-submission cap with no automatic retries.

### Rationale

Exact prompt pairing holds products, positions, brands, incentive wording, magnitudes,
nudges, and replication IDs constant. A pinned snapshot prevents later alias updates
from silently changing the tested model. Disabling retries keeps the approved spending
boundary equal to the planned sample size.

### Consequences

- **Positive:** The comparison directly tests whether the observed framing pattern
  transfers to a second model family.
- **Positive:** Prompt-hash checks and separate artifacts preserve auditability.
- **Negative:** Any failed request leaves the dataset incomplete unless the user later
  approves a replacement attempt.
- **Follow-up:** Implement offline checks, execute the capped run, and report paired
  model differences without making claims about hidden training procedures.

### Completion outcome

The run completed with 760 valid results from exactly 760 submissions and no failures.
Qwen reproduced the ordering of fixed amount above percentage, but its computed-amount
rate was statistically indistinguishable from fixed amount. Qwen was also far more
conditional on the explicit platform-priority nudge: 1/360 Partner choices without it
and 259/360 with it. These results support prompt sensitivity across model families but
not a universal fixed-amount-specific mechanism.
