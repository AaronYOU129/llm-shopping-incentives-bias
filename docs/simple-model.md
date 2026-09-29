# A Simple Model of Commission Wording and AI Recommendations

This is a post-hoc interpretive framework for the matched-payout experiments, not a
preregistered theory or an estimated structural model. It retains two propositions:
payoff equivalence as a benchmark and wording as a steering instrument.

## Setup

A platform supplies commission information to an AI shopping assistant. The assistant
recommends one of two products of identical quality: a regular product priced at
$p_0$ and a Partner product priced at $p_1$, with $\Delta p=p_1-p_0>0$. Both products
are affordable. Assume the consumer buys exactly the recommended product.

Let $y=1$ denote a Partner recommendation. The platform earns $R>0$ if the Partner
product is purchased and zero from a regular-product purchase. Thus $R$ is the
commission **conditional on a Partner sale**, not realized or expected revenue.

The platform chooses a wording $f$ from a finite set: percentage, percentage with an
explicit computed amount, or fixed amount. These wordings specify the same $R$ at the
displayed Partner price. A percentage and a fixed payment need not remain equivalent
if that price changes.

For a fixed AI model and inference mode, write the recommendation probability as

$$
q_f(R,G,k)\equiv\Pr(y=1\mid f,R,G,k)
=\Lambda\!\left(\lambda v_f(R)-\gamma\Delta p_k+\theta G+\mu_k\right),
\qquad \Lambda(z)=\frac{1}{1+e^{-z}},
$$

where $\lambda>0$, $\gamma>0$, $G\in\{0,1\}$ indicates explicit platform guidance,
and $\mu_k$ is a product-context effect. The index $v_f(R)$ represents the incentive's
behavioral weight under wording $f$; it does not measure the assistant's internal
beliefs or reasoning. Model and mode indices are suppressed, and parameters may differ
between models and modes. Other prompt features are held fixed in each comparison.

The payoff-only benchmark is $v_f(R)=R$ for every wording. We do not estimate the
parameters here; in particular, a price gap constant within product context cannot
identify $\gamma$ separately from unrestricted $\mu_k$.

## Proposition 1: Payoff-equivalent wording invariance

Under the benchmark, two wordings that specify the same commission $R$ produce the
same Partner-recommendation probability, holding guidance, product context, the AI
model, inference mode, and all other prompt features fixed:

$$
q_f(R,G,k)=q_{f'}(R,G,k).
$$

*Proof.* With $v_f(R)=v_{f'}(R)=R$, the two logistic indices are identical, so their
recommendation probabilities are identical.

This is a testable benchmark, not an assertion that the observed AI systems satisfy
it. A reliable difference at matched payouts is evidence against payoff-only wording
invariance, but does not by itself identify why the wordings have different effects.

## Proposition 2: Steering without a higher per-sale commission

Suppose changing wording is costless. Holding $R$, guidance, and all other conditions
fixed, let the platform choose

$$
f^*\in\operatorname*{arg\,max}_{f}v_f(R).
$$

Relative to any available wording $f$, this choice weakly raises the probability of a
Partner recommendation. With full consumer adoption, it increases expected consumer
spending by

$$
\mathbb{E}[p\mid f^*]-\mathbb{E}[p\mid f]
=\Delta p_k\left[q_{f^*}(R,G,k)-q_f(R,G,k)\right]\geq0.
$$

Both inequalities are strict when $v_{f^*}(R)>v_f(R)$. The commission on each Partner
sale remains $R$, while expected platform revenue increases by

$$
R\left[q_{f^*}(R,G,k)-q_f(R,G,k)\right].
$$

*Proof.* Since $\lambda>0$ and the logistic function is strictly increasing, maximizing
$v_f(R)$ maximizes $q_f$. Expected spending is $p_0+\Delta p_k q_f$ and expected
platform revenue is $Rq_f$, giving the stated differences. Under the benchmark all
wordings tie, so the platform is indifferent among them within this model.

“Without a higher per-sale commission” does not mean expected total commission
payments remain unchanged. More Partner purchases raise expected platform revenue
and the seller's expected commission payments. Nor does the model establish that
changing wording has no real-world implementation or reputational costs.

## Connection to the experiment

- The [matched-payout extension](../MECHANISM_RESULTS.md) compares wordings at the
  same displayed prices and commissions, providing the direct setting for Proposition
  1. The original payment-structure comparison alone is not a matched-payout test.
- The [Qwen replication](../QWEN_RESULTS.md) and
  [Qwen mode comparison](../QWEN_THINKING_RESULTS.md) show why comparisons should be
  reported separately by model, mode, and guidance condition. The model does not
  predict that fixed-amount wording is always the strongest steering instrument.
- Proposition 2 translates a recommendation-probability difference into expected
  extra spending under full adoption. Across product contexts, average
  $\Delta p_k(q_{f^*,k}-q_{f,k})$ using common context weights; do not generally
  multiply an average price gap by an average recommendation difference.

The experiments observe recommendations, not purchases. These spending quantities
are mechanical counterfactuals, not measured consumer losses or total social welfare.
The theoretical $f^*$ maximizes population probabilities: choosing the highest sample
rate and reporting its advantage on the same data does not validate an optimal policy.
Finally, neither proposition distinguishes arithmetic difficulty from instruction
interpretation or establishes a causal role for post-training.
