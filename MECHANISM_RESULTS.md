# Incentive Magnitude and Framing: Results

## Status

Complete analysis of 1520 valid randomized responses.

## Design

The extension crossed 10%, 20%, and 30% incentive magnitudes with percentage, percentage-plus-computed-amount, and fixed-amount framings. It retained both model modes, both nudge levels, and both product scenarios, while restricting budgets to the condition where both products were affordable. A contemporaneous Partner-label control stated that the platform received no seller payment.

## Key findings

- The no-payment Partner-label control produced 0/80 Partner choices.
- Across incentive cells, non-thinking chose Partner in 293/720 (40.7%), versus 42/720 (5.8%) for thinking-high.
- Matched framing mattered more than magnitude: fixed amount produced 177/480 (36.9%), percentage 107/480 (22.3%), and percentage plus computed amount 51/480 (10.6%).
- The nudge raised Partner choice from 77/720 (10.7%) to 258/720 (35.8%).
- Aggregate rates at 10%, 20%, and 30% were 102/480 (21.2%), 110/480 (22.9%), and 123/480 (25.6%); 0/12 preregistered within-stratum trend tests survived Holm correction.
- 10/36 matched-framing contrasts survived Holm correction.
- Among Partner recommendations, the platform relationship was disclosed in 110/335 (32.8%).
- The deterministic prose scan marked 63/1520 responses as manual-review candidates; this is not a validated inconsistency rate.

## Partner-choice shares

| condition | model | framing | incentive_rate | nudge | n | partner_choices | share | ci_lower | ci_upper |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control | deepseek-flash/non-thinking | no_incentive | <NA> | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/non-thinking | percentage | 10 | 0 | 40 | 5 | 0.125 | 0.0546 | 0.2611 |
| incentive | deepseek-flash/non-thinking | percentage | 10 | 1 | 40 | 25 | 0.625 | 0.4703 | 0.7578 |
| incentive | deepseek-flash/non-thinking | percentage | 20 | 0 | 40 | 2 | 0.05 | 0.01382 | 0.165 |
| incentive | deepseek-flash/non-thinking | percentage | 20 | 1 | 40 | 21 | 0.525 | 0.375 | 0.6706 |
| incentive | deepseek-flash/non-thinking | percentage | 30 | 0 | 40 | 6 | 0.15 | 0.07061 | 0.2907 |
| incentive | deepseek-flash/non-thinking | percentage | 30 | 1 | 40 | 24 | 0.6 | 0.446 | 0.7365 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 10 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 10 | 1 | 40 | 14 | 0.35 | 0.2213 | 0.5049 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 20 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 20 | 1 | 40 | 11 | 0.275 | 0.1611 | 0.4283 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 30 | 0 | 40 | 3 | 0.075 | 0.02584 | 0.1986 |
| incentive | deepseek-flash/non-thinking | percentage_computed | 30 | 1 | 40 | 16 | 0.4 | 0.2635 | 0.554 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 10 | 0 | 40 | 15 | 0.375 | 0.2422 | 0.5297 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 10 | 1 | 40 | 30 | 0.75 | 0.5981 | 0.8581 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 20 | 0 | 40 | 25 | 0.625 | 0.4703 | 0.7578 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 20 | 1 | 40 | 38 | 0.95 | 0.835 | 0.9862 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 30 | 0 | 40 | 21 | 0.525 | 0.375 | 0.6706 |
| incentive | deepseek-flash/non-thinking | fixed_amount | 30 | 1 | 40 | 37 | 0.925 | 0.8014 | 0.9742 |
| control | deepseek-flash/thinking-high | no_incentive | <NA> | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage | 10 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage | 10 | 1 | 40 | 7 | 0.175 | 0.08745 | 0.3195 |
| incentive | deepseek-flash/thinking-high | percentage | 20 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage | 20 | 1 | 40 | 7 | 0.175 | 0.08745 | 0.3195 |
| incentive | deepseek-flash/thinking-high | percentage | 30 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage | 30 | 1 | 40 | 10 | 0.25 | 0.1419 | 0.4019 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 10 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 10 | 1 | 40 | 3 | 0.075 | 0.02584 | 0.1986 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 20 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 20 | 1 | 40 | 3 | 0.075 | 0.02584 | 0.1986 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 30 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | percentage_computed | 30 | 1 | 40 | 1 | 0.025 | 0.004427 | 0.1288 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 10 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 10 | 1 | 40 | 3 | 0.075 | 0.02584 | 0.1986 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 20 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 20 | 1 | 40 | 3 | 0.075 | 0.02584 | 0.1986 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 30 | 0 | 40 | 0 | 0 | 0 | 0.08762 |
| incentive | deepseek-flash/thinking-high | fixed_amount | 30 | 1 | 40 | 5 | 0.125 | 0.0546 | 0.2611 |

## Ordered magnitude trends

| model | framing | nudge | n | partner_choices_10 | partner_choices_20 | partner_choices_30 | trend_statistic | p_value | p_value_holm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek-flash/non-thinking | percentage | 0 | 120 | 5 | 2 | 6 | 0.3597 | 0.7191 | 1 |
| deepseek-flash/non-thinking | percentage | 1 | 120 | 25 | 21 | 24 | -0.2268 | 0.8206 | 1 |
| deepseek-flash/non-thinking | percentage_computed | 0 | 120 | 0 | 0 | 3 | 2.148 | 0.03169 | 0.3486 |
| deepseek-flash/non-thinking | percentage_computed | 1 | 120 | 14 | 11 | 16 | 0.4715 | 0.6373 | 1 |
| deepseek-flash/non-thinking | fixed_amount | 0 | 120 | 15 | 25 | 21 | 1.342 | 0.1797 | 1 |
| deepseek-flash/non-thinking | fixed_amount | 1 | 120 | 30 | 38 | 37 | 2.366 | 0.01796 | 0.2155 |
| deepseek-flash/thinking-high | percentage | 0 | 120 | 0 | 0 | 0 |  | 1 | 1 |
| deepseek-flash/thinking-high | percentage | 1 | 120 | 7 | 7 | 10 | 0.8385 | 0.4017 | 1 |
| deepseek-flash/thinking-high | percentage_computed | 0 | 120 | 0 | 0 | 0 |  | 1 | 1 |
| deepseek-flash/thinking-high | percentage_computed | 1 | 120 | 3 | 3 | 1 | -0.9541 | 0.3401 | 1 |
| deepseek-flash/thinking-high | fixed_amount | 0 | 120 | 0 | 0 | 0 |  | 1 | 1 |
| deepseek-flash/thinking-high | fixed_amount | 1 | 120 | 3 | 3 | 5 | 0.7749 | 0.4384 | 1 |

## Matched-payout framing contrasts

| model | nudge | incentive_rate | framing_1 | framing_2 | n_1 | partner_choices_1 | share_1 | n_2 | partner_choices_2 | share_2 | difference_1_minus_2 | test | statistic | p_value | p_value_holm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek-flash/non-thinking | 0 | 10 | percentage | percentage_computed | 40 | 5 | 0.125 | 40 | 0 | 0 | 0.125 | two-sided two-proportion z-test | 2.309 | 0.02092 | 0.4812 |
| deepseek-flash/non-thinking | 0 | 10 | percentage_computed | fixed_amount | 40 | 0 | 0 | 40 | 15 | 0.375 | -0.375 | two-sided two-proportion z-test | -4.297 | 1.734e-05 | 0.0005201 |
| deepseek-flash/non-thinking | 0 | 10 | percentage | fixed_amount | 40 | 5 | 0.125 | 40 | 15 | 0.375 | -0.25 | two-sided two-proportion z-test | -2.582 | 0.009823 | 0.2456 |
| deepseek-flash/non-thinking | 0 | 20 | percentage | percentage_computed | 40 | 2 | 0.05 | 40 | 0 | 0 | 0.05 | two-sided two-proportion z-test | 1.432 | 0.1521 | 1 |
| deepseek-flash/non-thinking | 0 | 20 | percentage_computed | fixed_amount | 40 | 0 | 0 | 40 | 25 | 0.625 | -0.625 | two-sided two-proportion z-test | -6.03 | 1.637e-09 | 5.731e-08 |
| deepseek-flash/non-thinking | 0 | 20 | percentage | fixed_amount | 40 | 2 | 0.05 | 40 | 25 | 0.625 | -0.575 | two-sided two-proportion z-test | -5.438 | 5.383e-08 | 1.83e-06 |
| deepseek-flash/non-thinking | 0 | 30 | percentage | percentage_computed | 40 | 6 | 0.15 | 40 | 3 | 0.075 | 0.075 | two-sided two-proportion z-test | 1.061 | 0.2885 | 1 |
| deepseek-flash/non-thinking | 0 | 30 | percentage_computed | fixed_amount | 40 | 3 | 0.075 | 40 | 21 | 0.525 | -0.45 | two-sided two-proportion z-test | -4.392 | 1.125e-05 | 0.0003601 |
| deepseek-flash/non-thinking | 0 | 30 | percentage | fixed_amount | 40 | 6 | 0.15 | 40 | 21 | 0.525 | -0.375 | two-sided two-proportion z-test | -3.547 | 0.0003902 | 0.01093 |
| deepseek-flash/non-thinking | 1 | 10 | percentage | percentage_computed | 40 | 25 | 0.625 | 40 | 14 | 0.35 | 0.275 | two-sided two-proportion z-test | 2.46 | 0.01388 | 0.333 |
| deepseek-flash/non-thinking | 1 | 10 | percentage_computed | fixed_amount | 40 | 14 | 0.35 | 40 | 30 | 0.75 | -0.4 | two-sided two-proportion z-test | -3.596 | 0.0003235 | 0.009381 |
| deepseek-flash/non-thinking | 1 | 10 | percentage | fixed_amount | 40 | 25 | 0.625 | 40 | 30 | 0.75 | -0.125 | two-sided two-proportion z-test | -1.206 | 0.2278 | 1 |
| deepseek-flash/non-thinking | 1 | 20 | percentage | percentage_computed | 40 | 21 | 0.525 | 40 | 11 | 0.275 | 0.25 | two-sided two-proportion z-test | 2.282 | 0.02248 | 0.4945 |
| deepseek-flash/non-thinking | 1 | 20 | percentage_computed | fixed_amount | 40 | 11 | 0.275 | 40 | 38 | 0.95 | -0.675 | two-sided two-proportion z-test | -6.196 | 5.782e-10 | 2.081e-08 |
| deepseek-flash/non-thinking | 1 | 20 | percentage | fixed_amount | 40 | 21 | 0.525 | 40 | 38 | 0.95 | -0.425 | two-sided two-proportion z-test | -4.32 | 1.562e-05 | 0.0004842 |
| deepseek-flash/non-thinking | 1 | 30 | percentage | percentage_computed | 40 | 24 | 0.6 | 40 | 16 | 0.4 | 0.2 | two-sided two-proportion z-test | 1.789 | 0.07364 | 1 |
| deepseek-flash/non-thinking | 1 | 30 | percentage_computed | fixed_amount | 40 | 16 | 0.4 | 40 | 37 | 0.925 | -0.525 | two-sided two-proportion z-test | -4.965 | 6.86e-07 | 2.264e-05 |
| deepseek-flash/non-thinking | 1 | 30 | percentage | fixed_amount | 40 | 24 | 0.6 | 40 | 37 | 0.925 | -0.325 | two-sided two-proportion z-test | -3.415 | 0.0006368 | 0.01719 |
| deepseek-flash/thinking-high | 0 | 10 | percentage | percentage_computed | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 10 | percentage_computed | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 10 | percentage | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 20 | percentage | percentage_computed | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 20 | percentage_computed | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 20 | percentage | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 30 | percentage | percentage_computed | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 30 | percentage_computed | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 0 | 30 | percentage | fixed_amount | 40 | 0 | 0 | 40 | 0 | 0 | 0 | two-sided Fisher exact test |  | 1 | 1 |
| deepseek-flash/thinking-high | 1 | 10 | percentage | percentage_computed | 40 | 7 | 0.175 | 40 | 3 | 0.075 | 0.1 | two-sided two-proportion z-test | 1.352 | 0.1763 | 1 |
| deepseek-flash/thinking-high | 1 | 10 | percentage_computed | fixed_amount | 40 | 3 | 0.075 | 40 | 3 | 0.075 | 0 | two-sided two-proportion z-test | 0 | 1 | 1 |
| deepseek-flash/thinking-high | 1 | 10 | percentage | fixed_amount | 40 | 7 | 0.175 | 40 | 3 | 0.075 | 0.1 | two-sided two-proportion z-test | 1.352 | 0.1763 | 1 |
| deepseek-flash/thinking-high | 1 | 20 | percentage | percentage_computed | 40 | 7 | 0.175 | 40 | 3 | 0.075 | 0.1 | two-sided two-proportion z-test | 1.352 | 0.1763 | 1 |
| deepseek-flash/thinking-high | 1 | 20 | percentage_computed | fixed_amount | 40 | 3 | 0.075 | 40 | 3 | 0.075 | 0 | two-sided two-proportion z-test | 0 | 1 | 1 |
| deepseek-flash/thinking-high | 1 | 20 | percentage | fixed_amount | 40 | 7 | 0.175 | 40 | 3 | 0.075 | 0.1 | two-sided two-proportion z-test | 1.352 | 0.1763 | 1 |
| deepseek-flash/thinking-high | 1 | 30 | percentage | percentage_computed | 40 | 10 | 0.25 | 40 | 1 | 0.025 | 0.225 | two-sided two-proportion z-test | 2.922 | 0.003479 | 0.09045 |
| deepseek-flash/thinking-high | 1 | 30 | percentage_computed | fixed_amount | 40 | 1 | 0.025 | 40 | 5 | 0.125 | -0.1 | two-sided two-proportion z-test | -1.698 | 0.08953 | 1 |
| deepseek-flash/thinking-high | 1 | 30 | percentage | fixed_amount | 40 | 10 | 0.25 | 40 | 5 | 0.125 | 0.125 | two-sided two-proportion z-test | 1.432 | 0.1521 | 1 |

## JSON-to-prose consistency audit

The JSON `recommended` field remains the preregistered primary outcome. A conservative deterministic text scan flags explicit clauses that name the other listing or both listings for manual review; unclassified prose is not assumed consistent.

| consistency_status | n |
| --- | --- |
| explicit_consistent | 1281 |
| unclassified | 176 |
| explicit_inconsistent_candidate | 49 |
| ambiguous_candidate | 14 |

![Mechanism response curves](outputs/mechanism/full/mechanism_partner_choice.png)

## Completeness

- Valid responses: 1520
- Submitted attempts: 1520
- Logged failure events: 0

## Interpretation constraints

- Results identify effects of the randomized prompt representations, not internal cognition.
- The control has no nudge because duplicating identical control text would add no information.
- The served model behind a stable API name may change over time; this run is time-specific.
- Thinking mode ignores the nominal temperature, so effective sampling controls differ by mode.
