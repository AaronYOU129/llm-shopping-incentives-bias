# Qwen Thinking-Mode Results

All comparisons use the same pinned Qwen snapshot and byte-identical prompts.

## Protocol

- Model snapshot: `qwen3.7-plus-2026-05-26`
- Thinking comparison: enabled versus disabled
- Temperature: 1.0
- Valid paired responses: 760/760
- Submitted requests: 761/761

## Overall incentive result

- Non-thinking: 260/720 (36.1%)
- Thinking: 416/720 (57.8%)
- Difference: 21.7%
- Exact paired p-value: 1.109e-21
- Mean extra user spending if recommendations are followed: $28.42 versus $45.69 per incentive prompt

## By framing

| Condition | Framing | Non-thinking | Thinking | Difference | Exact p (raw) |
| --- | --- | ---: | ---: | ---: | ---: |
| incentive | percentage | 66/240 (27.5%) | 170/240 (70.8%) | 43.3% | 7.547e-26 |
| control | no_incentive | 0/40 (0.0%) | 0/40 (0.0%) | 0.0% | 1 |
| incentive | percentage_computed | 93/240 (38.8%) | 113/240 (47.1%) | 8.3% | 0.02446 |
| incentive | fixed_amount | 101/240 (42.1%) | 133/240 (55.4%) | 13.3% | 0.0009728 |

## By platform-priority nudge

| Nudge | Non-thinking | Thinking | Difference | Exact p (raw) |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1/360 (0.3%) | 141/360 (39.2%) | 38.9% | 5.13e-41 |
| 1 | 259/360 (71.9%) | 275/360 (76.4%) | 4.4% | 0.1982 |

## Framing × nudge

| Framing | Nudge | Non-thinking | Thinking | Difference | Exact p (raw) |
| --- | ---: | ---: | ---: | ---: | ---: |
| percentage | 0 | 0/120 (0.0%) | 67/120 (55.8%) | 55.8% | 1.355e-20 |
| percentage | 1 | 66/120 (55.0%) | 103/120 (85.8%) | 30.8% | 5.728e-08 |
| percentage_computed | 1 | 93/120 (77.5%) | 87/120 (72.5%) | -5.0% | 0.4614 |
| percentage_computed | 0 | 0/120 (0.0%) | 26/120 (21.7%) | 21.7% | 2.98e-08 |
| fixed_amount | 0 | 1/120 (0.8%) | 48/120 (40.0%) | 39.2% | 1.776e-13 |
| fixed_amount | 1 | 100/120 (83.3%) | 85/120 (70.8%) | -12.5% | 0.02753 |
