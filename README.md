# LLM Shopping Incentive Bias

A reproducible randomized prompt experiment testing whether platform payment structures
make an AI shopping assistant more likely to recommend a more expensive Partner product
that is stated to be equivalent—and worse for the user's budget.

**Status:** The original 80-trial pilot, 1,600-trial experiment, two judge rubrics,
blinded human validation, 1,520-trial incentive-magnitude extension, and 760-prompt
paired Qwen replication, and the 760-prompt Qwen thinking-mode extension are complete
and verified.

## Start here

| Goal | Where to go |
| --- | --- |
| Read the findings | [RESULTS.md](RESULTS.md) |
| Read the two-proposition economic model | [A simple model](docs/simple-model.md) |
| Read the mechanism findings | [MECHANISM_RESULTS.md](MECHANISM_RESULTS.md) |
| Read the Qwen comparison | [QWEN_RESULTS.md](QWEN_RESULTS.md) |
| Review the Qwen thinking pilot | [outputs/qwen_thinking/PILOT.md](outputs/qwen_thinking/PILOT.md) |
| Review the full Qwen mode comparison | [QWEN_THINKING_RESULTS.md](QWEN_THINKING_RESULTS.md) |
| Validate the Qwen replication without API calls | `python run_all.py qwen-validate` |
| Follow the mechanism extension | [Extension specification](specification.md#incentive-magnitude-mechanism-extension) |
| Understand the approved design | [specification.md](specification.md) |
| Review material methodological decisions | [decision-log.md](decision-log.md) |
| Regenerate analysis from saved data | Follow the no-model-call quickstart below |
| Rerun the API-backed workflow | [Full reproduction and operations guide](docs/reproduction.md) |

## Study at a glance

The experiment crosses five platform payment structures with two product scenarios,
two budget conditions, two nudge conditions, and two model modes. Twenty replications
per cell produce 1,600 full-run responses.

The primary outcome is whether the assistant chooses the more expensive Partner
listing. The analysis also reports incentive disclosure and post-hoc fabricated-claim
labels, including v1 and broader v2 rubrics with blinded human checks.

All prompts, raw responses, parsed outcomes, request ledgers, validation artifacts,
statistical tables, and the final report are retained under `outputs/`.

## Quickstart: reproduce the saved analysis

Python 3.11 or newer is required. Install the declared dependencies:

```bash
python -m pip install -r requirements.txt
```

Then validate the protocol and regenerate the report:

```bash
python run_all.py validate
python run_all.py analyze
```

These two commands require no API key and make no model calls. To run the automated
test and compilation checks as well:

```bash
python -m pytest -q
python -m compileall -q .
```

The isolated follow-up design can also be validated without model calls:

```bash
python run_all.py mechanism-validate
python run_all.py mechanism-analyze
```

The paired Qwen manifest can be checked without a Qwen key or model calls:

```bash
python run_all.py qwen-validate
python run_all.py qwen-thinking-validate
python run_all.py qwen-thinking-full-validate
```

## Repository map

| Path | Purpose |
| --- | --- |
| `config.yaml` | Approved design, prompts, model modes, limits, and output schemas |
| `config_mechanism.yaml` | Isolated 10%/20%/30% matched-framing extension |
| `run_all.py` | Guarded command-line entry point |
| `experiment.py` | Trial generation, API execution, validation, and durable CSV writes |
| `mechanism_experiment.py` | Extension manifest, API execution, and pilot reporting |
| `mechanism_analysis.py` | Extension trends, framing contrasts, figure, and report |
| `config_qwen.yaml` | Pinned Qwen model, source pairing, request cap, and outputs |
| `config_qwen_thinking.yaml` | Isolated 38-request Qwen thinking pilot |
| `config_qwen_thinking_full.yaml` | Approved 760-prompt Qwen thinking extension |
| `qwen_comparison.py` | Prompt-paired Qwen API execution and durable persistence |
| `qwen_analysis.py` | Qwen framing summaries and paired DeepSeek comparison |
| `qwen_thinking_analysis.py` | Paired Qwen thinking-versus-non-thinking analysis |
| `judge.py` | Versioned fabrication judges and blind validation samples |
| `analysis.py` | Statistical tables, figure, validation summaries, and report rendering |
| `MECHANISM_RESULTS.md` | Data-derived findings from the matched-framing extension |
| `tests/` | Offline regression and protocol tests |
| `outputs/` | Saved experiment, judge, validation, and analysis artifacts |

## Reproducibility and safety

API-backed phases are resumable and protected by durable request-attempt budgets.
Every submission is reserved before it is sent, retries consume the same budget, and
invalid outputs are retained rather than guessed. The full and rubric-v2 commands
require explicit approval flags and are documented separately in the
[reproduction guide](docs/reproduction.md).

The completed mechanism extension has independent 76/1,520 pilot/full ledgers under
`outputs/mechanism/`; its approval gate and exact submission caps remain enforced for
reproduction.

The experiment uses `deepseek-flash` in non-thinking and thinking-high modes. The
requested temperature 1.0 is logged for both; DeepSeek ignores it in thinking mode, so
results remain specific to the recorded run and served model version.

## Project documentation

- [Full results](RESULTS.md)
- [Mechanism-extension results](MECHANISM_RESULTS.md)
- [Qwen paired-replication results](QWEN_RESULTS.md)
- [Specification and acceptance criteria](specification.md)
- [Decision log](decision-log.md)
- [Current project status](progress.md)
- [Full reproduction and operations guide](docs/reproduction.md)
- [Coding principles](docs/coding-principles.md)
- [AI-assisted development workflow](docs/ai-assisted-development-workflow.md)

## License

This project is available under the [MIT License](LICENSE).
