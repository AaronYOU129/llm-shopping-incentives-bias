# Qwen Paired Replication Results

All values below are generated from the 760 saved Qwen responses and their
prompt-matched DeepSeek non-thinking source responses.

## Protocol

- Qwen snapshot: `qwen3.7-plus-2026-05-26`
- Thinking: disabled
- Temperature: 1.0
- Valid Qwen responses: 760/760
- Pairing: identical prompt text and SHA-256 hash for every source trial

## Qwen Partner choices by framing

| Condition | Framing | Partner choices | n | Share | 95% CI |
| --- | --- | ---: | ---: | ---: | ---: |
| control | no_incentive | 0 | 40 | 0.0% | 0.0%–8.8% |
| incentive | percentage | 66 | 240 | 27.5% | 22.2%–33.5% |
| incentive | percentage_computed | 93 | 240 | 38.8% | 32.8%–45.0% |
| incentive | fixed_amount | 101 | 240 | 42.1% | 36.0%–48.4% |

## Platform-priority nudge

| Model | Nudge | Partner choices | n | Share | 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-flash/non-thinking | 0 | 77 | 360 | 21.4% | 17.5%–25.9% |
| deepseek-flash/non-thinking | 1 | 216 | 360 | 60.0% | 54.9%–64.9% |
| qwen3.7-plus/non-thinking | 0 | 1 | 360 | 0.3% | 0.0%–1.6% |
| qwen3.7-plus/non-thinking | 1 | 259 | 360 | 71.9% | 67.1%–76.3% |

Qwen made 1 of 360 Partner choices without the platform-priority sentence,
versus 259 of 360 when that sentence was present. Aggregate framing effects
must therefore be read together with this dominant nudge interaction.

## Qwen framing contrasts

| Contrast | Difference | Holm-adjusted p |
| --- | ---: | ---: |
| percentage − percentage_computed | -11.2% | 0.01767 |
| percentage_computed − fixed_amount | -3.3% | 0.4568 |
| percentage − fixed_amount | -14.6% | 0.00239 |

## Prompt-paired model comparison

| Framing | DeepSeek | Qwen | Qwen − DeepSeek | Exact McNemar p |
| --- | ---: | ---: | ---: | ---: |
| no_incentive | 0/40 (0.0%) | 0/40 (0.0%) | 0.0% | 1 |
| percentage | 83/240 (34.6%) | 66/240 (27.5%) | -7.1% | 0.04296 |
| percentage_computed | 44/240 (18.3%) | 93/240 (38.8%) | 20.4% | 8.396e-09 |
| fixed_amount | 166/240 (69.2%) | 101/240 (42.1%) | -27.1% | 3.618e-12 |

## Response consistency audit

- Deterministic manual-review candidates: 1/760
- Candidate flags do not alter the preregistered JSON outcome.

## Interpretation boundary

This experiment identifies behavioral differences under fixed prompts and
recorded API settings. It does not identify hidden post-training data or the
model's internal reasoning process.
