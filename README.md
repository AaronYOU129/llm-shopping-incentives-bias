# LLM Shopping Incentive Bias

A randomized prompt study of whether platform commissions steer an AI shopping assistant
toward a more expensive Partner product when a cheaper product has the same stated
quality. The completed study contains 4,640 experimental responses across the original
DeepSeek study, a matched-commission extension, and paired Qwen comparisons. The main
outcome is the assistant's recommendation, not an observed purchase.

## Results

The experiments found that the way an equal-value commission is described, explicit
platform guidance, and the model's inference mode can all change Partner
recommendations. The direction and size of those changes vary across models. Extra
consumer spending is calculated only under the assumption that shoppers follow the
recommendations; purchases were not observed.

**[Read all results in one place →](ALL_RESULTS.md)**

The integrated report covers the original experiment, matched-commission extension,
both Qwen comparisons, response quality, and interpretation limits. It links each
detailed source report for readers who want the full tables and tests.

## Reproduce the saved analysis

Python 3.11 or newer is required. The following commands use saved data and make no
model calls:

```bash
python -m pip install -r requirements.txt
python run_all.py validate
python run_all.py analyze
```

The [reproduction guide](docs/reproduction.md) covers the other saved-data analyses,
protocol checks, tests, and separately gated API runs. The experimental designs and
acceptance criteria are in the [specification](specification.md); material choices are
recorded in the [decision log](decision-log.md), with current status in
[progress](progress.md).

The entry point is `run_all.py`, configurations are in `config*.yaml`, tests are in
`tests/`, and saved prompts, responses, ledgers, and tables are in `outputs/`.

## License

This project is available under the [MIT License](LICENSE).
