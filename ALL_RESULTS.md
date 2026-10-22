# Results in One Place

This is the single reading path for the completed study. An AI shopping assistant
chooses between two products described as equal in quality; the Partner product costs
more and can earn the platform money. The main outcome is whether the assistant
recommends Partner. The tables below bring together the headline results from four
completed stages. Links lead to the original reports for every cell, interval, and
test; the original reports and saved responses remain the detailed record.

## Study coverage

| Stage | Valid responses | Main comparison | Detailed report |
| --- | ---: | --- | --- |
| Original DeepSeek study | 1,600 | Five payment structures, budget, guidance, and mode | [Original results](RESULTS.md) |
| DeepSeek matched-commission extension | 1,520 | Three equivalent payout descriptions at 10%, 20%, and 30% | [Mechanism results](MECHANISM_RESULTS.md) |
| Qwen non-thinking replication | 760 | Same 760 prompts as the DeepSeek non-thinking extension | [Qwen results](QWEN_RESULTS.md) |
| Qwen thinking extension | 760 | Thinking on versus off for the same Qwen snapshot and prompts | [Qwen thinking results](QWEN_THINKING_RESULTS.md) |
| **Total** | **4,640** | Experimental responses; excludes pilots and post-hoc judging | |

The matched-commission stages use two product scenarios, 20 replications per cell,
two guidance conditions, and a control with the Partner label but no seller payment.
Each incentive-condition model/mode has 720 responses; each no-payment control has 40.
The original study also varied whether both products were within the user's budget.

## 1. Original study: budget and payment structure

When only the cheaper product fit the user's budget, Partner was never recommended
(0/800). When both products were affordable, the original payment arms gave:

| Platform payment structure | Partner choices when both affordable |
| --- | ---: |
| User subscriptions; no seller payment | 0/160 (0.0%) |
| 10% commission on Partner sales | 27/160 (16.9%) |
| Fixed amount per Partner sale | 64/160 (40.0%) |
| Payment per Partner-listing click | 28/160 (17.5%) |
| Fixed monthly seller sponsorship | 8/160 (5.0%) |

The original fixed-per-sale arm exceeded the percentage arm by 23.1 percentage points
(Holm-adjusted p=1.82e-05). Those arms did **not** hold the platform's dollar payout
constant, so this contrast alone cannot isolate the effect of wording. The later
matched-commission experiment addresses that question. Full arm-by-budget-by-guidance
results and intervals are in the [original report](RESULTS.md).

## 2. Matched payouts: wording versus incentive size

At a given displayed Partner price, “10% of the sale price,” “10%, exactly $21.90”
for the $219 headphones, and “exactly $21.90” all paid the platform the same amount
if Partner was purchased. The experiment similarly matched 20% and 30% payouts for
headphones and shoes. Percentage and fixed payments are equivalent at these displayed
prices, though they would differ if the sale price changed.

Partner recommendations across all 10%/20%/30% rates, both product scenarios, and
both guidance conditions were:

| Model and mode | Percentage only | Percentage + computed amount | Fixed amount per sale | All incentive prompts |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek non-thinking | 83/240 (34.6%) | 44/240 (18.3%) | 166/240 (69.2%) | 293/720 (40.7%) |
| DeepSeek thinking-high | 24/240 (10.0%) | 7/240 (2.9%) | 11/240 (4.6%) | 42/720 (5.8%) |
| Qwen non-thinking | 66/240 (27.5%) | 93/240 (38.8%) | 101/240 (42.1%) | 260/720 (36.1%) |
| Qwen thinking | 170/240 (70.8%) | 113/240 (47.1%) | 133/240 (55.4%) | 416/720 (57.8%) |

The DeepSeek extension found 10 of 36 matched-framing contrasts distinguishable
after Holm correction. Raising the commission from 10% to 20% to 30% produced
aggregate Partner rates of 21.2%, 22.9%, and 25.6%, but none of its 12
within-condition ordered-trend tests survived Holm correction. In Qwen non-thinking,
fixed amount exceeded percentage only (Holm-adjusted p=0.00239), while fixed amount
and percentage plus computed amount were not detectably different (Holm-adjusted
p=0.4568).
These comparisons support wording sensitivity, not a universal ranking of wordings.

The no-payment Partner-label control produced 0/80 Partner choices across the two
DeepSeek modes and 0/40 in each Qwen mode. See the [matched-commission report](MECHANISM_RESULTS.md),
[Qwen replication](QWEN_RESULTS.md), and [Qwen mode report](QWEN_THINKING_RESULTS.md)
for the cell-level results and tests.

## 3. Explicit platform guidance

The treatment sentence said the platform would like Partner products featured when
reasonable. Within incentive prompts, its presence was associated with:

| Model and mode | No guidance | Guidance present |
| --- | ---: | ---: |
| DeepSeek non-thinking | 77/360 (21.4%) | 216/360 (60.0%) |
| DeepSeek thinking-high | 0/360 (0.0%) | 42/360 (11.7%) |
| Qwen non-thinking | 1/360 (0.3%) | 259/360 (71.9%) |
| Qwen thinking | 141/360 (39.2%) | 275/360 (76.4%) |

Guidance can dominate an aggregate framing comparison: for Qwen non-thinking, almost
every Partner choice occurred when the guidance sentence was present. The detailed
[DeepSeek](MECHANISM_RESULTS.md), [Qwen non-thinking](QWEN_RESULTS.md), and
[Qwen thinking](QWEN_THINKING_RESULTS.md) reports show the framing-by-guidance cells.

## 4. Model and thinking-mode differences

DeepSeek chose Partner less often in thinking-high than non-thinking mode on matched
incentive prompts (5.8% versus 40.7%). Qwen did the opposite when thinking was enabled
on the same pinned snapshot and byte-identical prompts (57.8% versus 36.1%; exact
paired p=1.109e-21). Qwen's increase was concentrated without the guidance sentence:
0.3% non-thinking versus 39.2% thinking. With guidance, 71.9% versus 76.4% was not
detectably different (exact paired p=0.1982).

DeepSeek and Qwen also differed in *which* equivalent wording was most influential.
For example, fixed amount versus percentage plus computed amount was 69.2% versus
18.3% for DeepSeek non-thinking, but 42.1% versus 38.8% for Qwen non-thinking. The
[prompt-paired model comparison](QWEN_RESULTS.md) gives exact paired tests. These are
behavioral differences under the recorded APIs; model family, service version, and
sampling controls are not fully harmonized across providers.

## 5. Consumer spending and response quality

If users bought exactly what the assistant recommended, a Partner choice would add
$90 for headphones or $70 for shoes relative to the cheaper equal-quality product.
Under that assumption, Qwen's mean mechanical extra spending per incentive prompt
was $28.42 in non-thinking and $45.69 in thinking mode. For a fixed scenario, the
economic comparison is the price gap times the change in Partner-recommendation
probability; the [simple model](docs/simple-model.md) formalizes this. No actual
purchases or consumer welfare were measured.

In the matched DeepSeek extension, the assistant disclosed the platform relationship
in 110/335 (32.8%) Partner recommendations. In the original study, a blinded 50-reply
human check agreed with the narrow fabricated-claim judge on 45/50 (90.0%) cases.
Correcting that judge's sampled false negatives yielded an estimated 28.3% rate of
unsupported claims among original-study Partner recommendations (95% interval:
21.3%–40.9%). A broader post-hoc rubric labeled far more responses and had lower
precision on the same enriched check, so fabricated-claim rates are rubric-sensitive.
The [original report](RESULTS.md) contains both rubrics and the validation details.

## Interpretation and source of truth

The experiments measure AI responses to synthetic, equal-quality product prompts,
not real shopping behavior. The spending figures require full compliance with the
recommendation. The matched-payout comparison tests whether wording changes observed
recommendations; it does not reveal the model's internal calculations or identify a
specific post-training cause. DeepSeek thinking mode ignored the requested temperature,
and all findings are specific to the logged API runs.

This document consolidates the completed reports; it is not an additional experiment
or a newly fitted model. For exhaustive cell tables, confidence intervals, and audit
details, consult the [original](RESULTS.md), [matched-commission](MECHANISM_RESULTS.md),
[Qwen non-thinking](QWEN_RESULTS.md), and [Qwen thinking](QWEN_THINKING_RESULTS.md)
reports. The [reproduction guide](docs/reproduction.md) explains how to regenerate
those reports from saved data without API calls.
