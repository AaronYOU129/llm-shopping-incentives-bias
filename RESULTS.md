# LLM Shopping Incentive Bias: Results

## Status

Complete v1 and rubric-v2 analyses, including the 50-reply Partner-focused and 20-reply non-Partner blinded human validations.

## Design

The full factorial crossed 5 payment arms, 2 scenarios, 2 budget conditions, 2 nudge conditions, and 2 model-mode conditions with 20 replications per cell. The analysis contains 1600 valid responses.

The two model conditions used the current `deepseek-flash` API identifier with thinking disabled or enabled at high effort. Temperature 1.0 was sent and logged, but the API ignores temperature in thinking mode.

After the experiment, every reply was coded for the post-hoc `fabricated_claim` outcome by `deepseek-flash` with thinking disabled and temperature 0 using saved rubric versions. These judge stages did not alter the experiment prompts.

## Partner-choice shares

Shares and 95% Wilson intervals are shown below.

| model | nudge | arm | budget | n | partner_choices | share | ci_lower | ci_upper | flag_n_lt_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek-flash/non-thinking | 0 | sub | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | sub | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | pct | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | pct | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | flat | both | 40 | 15 | 0.375 | 0.242 | 0.530 | no |
| deepseek-flash/non-thinking | 0 | flat | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | cpc | both | 40 | 2 | 0.050 | 0.014 | 0.165 | no |
| deepseek-flash/non-thinking | 0 | cpc | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | fixed | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 0 | fixed | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | sub | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | sub | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | pct | both | 40 | 22 | 0.550 | 0.398 | 0.693 | no |
| deepseek-flash/non-thinking | 1 | pct | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | flat | both | 40 | 39 | 0.975 | 0.871 | 0.996 | no |
| deepseek-flash/non-thinking | 1 | flat | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | cpc | both | 40 | 24 | 0.600 | 0.446 | 0.737 | no |
| deepseek-flash/non-thinking | 1 | cpc | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/non-thinking | 1 | fixed | both | 40 | 8 | 0.200 | 0.105 | 0.348 | no |
| deepseek-flash/non-thinking | 1 | fixed | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | sub | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | sub | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | pct | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | pct | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | flat | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | flat | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | cpc | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | cpc | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | fixed | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 0 | fixed | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | sub | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | sub | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | pct | both | 40 | 5 | 0.125 | 0.055 | 0.261 | no |
| deepseek-flash/thinking-high | 1 | pct | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | flat | both | 40 | 10 | 0.250 | 0.142 | 0.402 | no |
| deepseek-flash/thinking-high | 1 | flat | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | cpc | both | 40 | 2 | 0.050 | 0.014 | 0.165 | no |
| deepseek-flash/thinking-high | 1 | cpc | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | fixed | both | 40 | 0 | 0.000 | 0.000 | 0.088 | no |
| deepseek-flash/thinking-high | 1 | fixed | only | 40 | 0 | 0.000 | 0.000 | 0.088 | no |

![Partner-choice grouped bars](outputs/full/partner_choice.png)

## Prespecified contrasts

| contrast | budget | arm_1 | arm_2 | n_1 | partner_choices_1 | share_1 | ci_lower_1 | ci_upper_1 | n_2 | partner_choices_2 | share_2 | ci_lower_2 | ci_upper_2 | difference_arm1_minus_arm2 | test | statistic | p_value | ci_overlap | flag_n_lt_20 | p_value_holm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pct_vs_flat_both | both | pct | flat | 160 | 27 | 0.169 | 0.119 | 0.234 | 160 | 64 | 0.400 | 0.327 | 0.477 | -0.231 | two-sided two-proportion z-test | -4.585 | 0.000 | no | no | 0.000 |
| cpc_vs_pct_only | only | cpc | pct | 160 | 0 | 0.000 | 0.000 | 0.023 | 160 | 0 | 0.000 | 0.000 | 0.023 | 0.000 | two-sided Fisher exact test (degenerate z-test fallback) |  | 1.000 | yes | no | 1.000 |
| cpc_vs_flat_only | only | cpc | flat | 160 | 0 | 0.000 | 0.000 | 0.023 | 160 | 0 | 0.000 | 0.000 | 0.023 | 0.000 | two-sided Fisher exact test (degenerate z-test fallback) |  | 1.000 | yes | no | 1.000 |
| fixed_vs_sub | all | fixed | sub | 320 | 8 | 0.025 | 0.013 | 0.049 | 320 | 0 | 0.000 | 0.000 | 0.012 | 0.025 | two-sided two-proportion z-test | 2.846 | 0.004 | no | no | 0.013 |

### Contrast findings

- `pct_vs_flat_both`: pct minus flat = -0.231; remained statistically distinguishable after Holm correction (Holm-adjusted p=1.82e-05). The group-level 95% Wilson intervals did not overlap.
- `cpc_vs_pct_only`: cpc minus pct = 0.000; was not statistically distinguishable after Holm correction (Holm-adjusted p=1). The group-level 95% Wilson intervals overlapped.
- `cpc_vs_flat_only`: cpc minus flat = 0.000; was not statistically distinguishable after Holm correction (Holm-adjusted p=1). The group-level 95% Wilson intervals overlapped.
- `fixed_vs_sub`: fixed minus sub = 0.025; remained statistically distinguishable after Holm correction (Holm-adjusted p=0.0133). The group-level 95% Wilson intervals did not overlap.

## Primary and post-hoc outcomes by arm × budget × nudge

`chose_partner` and `fabricated_claim` use all replies in each row as their denominator. `disclosed` is conditional on recommending the Partner product; its denominator is shown explicitly. Intervals are 95% Wilson intervals.

| arm | budget | nudge | n | chose_partner_count | chose_partner_rate | chose_partner_ci_lower | chose_partner_ci_upper | disclosure_denominator_partner_recommendations | disclosed_count | disclosed_rate | disclosed_ci_lower | disclosed_ci_upper | fabricated_claim_count | fabricated_claim_rate | fabricated_claim_ci_lower | fabricated_claim_ci_upper | flag_n_lt_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sub | both | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| sub | both | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| sub | only | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| sub | only | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| pct | both | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| pct | both | 1 | 80 | 27 | 0.338 | 0.243 | 0.446 | 27 | 15 | 0.556 | 0.373 | 0.724 | 3 | 0.037 | 0.013 | 0.105 | no |
| pct | only | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| pct | only | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| flat | both | 0 | 80 | 15 | 0.188 | 0.117 | 0.287 | 15 | 8 | 0.533 | 0.301 | 0.752 | 3 | 0.037 | 0.013 | 0.105 | no |
| flat | both | 1 | 80 | 49 | 0.613 | 0.503 | 0.712 | 49 | 14 | 0.286 | 0.178 | 0.424 | 11 | 0.138 | 0.079 | 0.230 | no |
| flat | only | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| flat | only | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| cpc | both | 0 | 80 | 2 | 0.025 | 0.007 | 0.087 | 2 | 1 | 0.500 | 0.095 | 0.905 | 0 | 0.000 | 0.000 | 0.046 | no |
| cpc | both | 1 | 80 | 26 | 0.325 | 0.232 | 0.434 | 26 | 8 | 0.308 | 0.165 | 0.500 | 2 | 0.025 | 0.007 | 0.087 | no |
| cpc | only | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| cpc | only | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| fixed | both | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| fixed | both | 1 | 80 | 8 | 0.100 | 0.052 | 0.185 | 8 | 4 | 0.500 | 0.215 | 0.785 | 3 | 0.037 | 0.013 | 0.105 | no |
| fixed | only | 0 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |
| fixed | only | 1 | 80 | 0 | 0.000 | 0.000 | 0.046 | 0 | 0 |  |  |  | 0 | 0.000 | 0.000 | 0.046 | no |

## Fabricated-claim human validation

- Hand-checked replies: 50
- Raw agreement: 45/50 (90.0%)
- Cohen's kappa: 0.800
- Confusion counts (judge, human): (0,0)=24, (0,1)=4, (1,0)=1, (1,1)=21

### False-negative-corrected rate among Partner recommendations

The 22 v1 judge-positive Partner recommendations were reviewed as a census; 21 were human-positive. Among a simple random sample of 28 from the 105 judge-negative Partner recommendations, 4 were human-positive.

The stratified estimate is 28.3% (36.0 of 127 estimated claims), with an exact finite-population 95% CI of 21.3% to 40.9%.

### Non-Partner judge-negative validation

All 20 sampled v1 judge-negative non-Partner recommendations were human-negative, so the observed false-negative rate was 0.0% (0/20).

For the finite population of 1473 eligible replies, the exact 95% CI is 0.0% to 16.7%. Cohen's kappa is not estimable because both the judge and all human labels were 0.

## Rubric v2 re-judgment

- v1 positive labels: 22
- v2 positive labels: 387
- Changed 0→1: 365
- Changed 1→0: 0
- Total changed: 365/1600 (22.8%)
- Agreement on the original 50-case blind hand-check: 39/50 (78.0%), κ=0.560
- On that enriched sample, v2 precision was 69.4% and recall was 100.0% against the human labels

On the separate 20-case non-Partner hand-check, v2 agreed on 16/20 cases (80.0%) and produced 4 false positives.

The broader v2 rubric recovered every human-positive case in the original hand-check, but its lower precision and the additional non-Partner false positives mean it should be treated as a sensitivity analysis rather than an unqualified replacement for v1.

V2 labels by the product ultimately recommended:

| recommendation | n | fabricated_claim_count | fabricated_claim_rate |
| --- | --- | --- | --- |
| non-Partner | 1473 | 311 | 0.211 |
| Partner | 127 | 76 | 0.598 |

Rubric-v2 outcome rates by arm × budget × nudge are shown with the unchanged behavioral outcomes for context.

| arm | budget | nudge | n | chose_partner_rate | disclosed_rate | fabricated_claim_count | fabricated_claim_rate | fabricated_claim_ci_lower | fabricated_claim_ci_upper |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sub | both | 0 | 80 | 0.000 |  | 12 | 0.150 | 0.088 | 0.244 |
| sub | both | 1 | 80 | 0.000 |  | 12 | 0.150 | 0.088 | 0.244 |
| sub | only | 0 | 80 | 0.000 |  | 16 | 0.200 | 0.127 | 0.300 |
| sub | only | 1 | 80 | 0.000 |  | 11 | 0.138 | 0.079 | 0.230 |
| pct | both | 0 | 80 | 0.000 |  | 18 | 0.225 | 0.147 | 0.328 |
| pct | both | 1 | 80 | 0.338 | 0.556 | 34 | 0.425 | 0.323 | 0.534 |
| pct | only | 0 | 80 | 0.000 |  | 14 | 0.175 | 0.107 | 0.273 |
| pct | only | 1 | 80 | 0.000 |  | 14 | 0.175 | 0.107 | 0.273 |
| flat | both | 0 | 80 | 0.188 | 0.533 | 26 | 0.325 | 0.232 | 0.434 |
| flat | both | 1 | 80 | 0.613 | 0.286 | 39 | 0.487 | 0.381 | 0.595 |
| flat | only | 0 | 80 | 0.000 |  | 18 | 0.225 | 0.147 | 0.328 |
| flat | only | 1 | 80 | 0.000 |  | 16 | 0.200 | 0.127 | 0.300 |
| cpc | both | 0 | 80 | 0.025 | 0.500 | 24 | 0.300 | 0.211 | 0.408 |
| cpc | both | 1 | 80 | 0.325 | 0.308 | 28 | 0.350 | 0.255 | 0.459 |
| cpc | only | 0 | 80 | 0.000 |  | 24 | 0.300 | 0.211 | 0.408 |
| cpc | only | 1 | 80 | 0.000 |  | 19 | 0.237 | 0.158 | 0.341 |
| fixed | both | 0 | 80 | 0.000 |  | 14 | 0.175 | 0.107 | 0.273 |
| fixed | both | 1 | 80 | 0.100 | 0.500 | 27 | 0.338 | 0.243 | 0.446 |
| fixed | only | 0 | 80 | 0.000 |  | 6 | 0.075 | 0.035 | 0.154 |
| fixed | only | 1 | 80 | 0.000 |  | 15 | 0.188 | 0.117 | 0.287 |

## Logistic regressions

### deepseek-flash/non-thinking

Logit unavailable because complete/quasi-complete separation is present: chose_partner is constant in 6 of 10 arm × budget cells (sub/both=0, sub/only=0, pct/only=0, flat/only=0, cpc/only=0, fixed/only=0). Fit error: RuntimeError: Maximum Likelihood optimization failed to converge. Check mle_retvals

No coefficient cells were dropped; use the complete descriptive table above.

### deepseek-flash/thinking-high

Logit unavailable because complete/quasi-complete separation is present: chose_partner is constant in 7 of 10 arm × budget cells (sub/both=0, sub/only=0, pct/only=0, flat/only=0, cpc/only=0, fixed/both=0, fixed/only=0). Fit error: RuntimeError: Maximum Likelihood optimization failed to converge. Check mle_retvals

No coefficient cells were dropped; use the complete descriptive table above.

## Disclosure among Partner recommendations

| arm | n_partner_recommendations | disclosed_count | disclosure_rate | ci_lower | ci_upper | flag_n_lt_20 |
| --- | --- | --- | --- | --- | --- | --- |
| sub | 0 | 0 |  |  |  | yes |
| pct | 27 | 15 | 0.556 | 0.373 | 0.724 | no |
| flat | 64 | 22 | 0.344 | 0.239 | 0.466 | no |
| cpc | 28 | 9 | 0.321 | 0.179 | 0.507 | no |
| fixed | 8 | 4 | 0.500 | 0.215 | 0.785 | yes |

## Failures and completeness

- Valid result rows: 1600
- Submitted API requests, including retries: 1601
- Logged failure events: 1
- Valid judge result rows: 1600
- Submitted judge requests, including retries: 1600
- Logged judge failure events: 0
- Submitted judge-v2 requests, including retries: 1601
- Logged judge-v2 failure events: 1
- Partner-choice cells with n < 20: 0
- Prespecified contrasts whose group-level 95% Wilson intervals overlap: 2

## Limitations

- The experiment measures responses to synthetic prompts, not real purchasing behavior.
- The Partner product was always more expensive while stated quality was held equal; results may not generalize to richer product differences.
- Stable API names can point to updated service versions over time, so findings are specific to the logged run date and served model.
- Thinking and non-thinking modes did not have equivalent effective temperature control because thinking mode ignores the temperature setting.
- The `sub` nudge levels intentionally render identical operator text under the fixed design.
- `fabricated_claim` is post-hoc and was coded by the same model provider being studied; the blinded 50-reply hand-check quantifies, but does not eliminate, classification error.
- The corrected Partner rate treats the human labels as the reference standard; its interval covers finite-sample uncertainty in the sampled judge-negative Partner stratum, not human-coding error.
- Rubric v2 agreement reuses the v1-enriched hand-check rather than a new representative sample; it evaluates consistency on those cases, not v2 population prevalence.
- Statistical significance and non-overlapping intervals do not establish effects outside this randomized prompt experiment.
