# DSPy integration

The DSPy integration supports AI-assisted interpretation during Discovery Mode. It does not monitor files, compute diffs, or make routine accountability decisions.

## Implemented modules

- `GameClassifier`: proposes game structure and session strategy.
- `ProgressionSignalRanker`: ranks structured changes by likely progression relevance.
- Pydantic schemas: bound all inputs and validate confidence, provenance references, and outputs.
- Safe configuration: disables DSPy persistence/history and requires explicit remote-provider opt-in.

Both modules receive serialized `StructuredObservation` values. Their schema has no raw-file-content field and rejects extra inputs.

## Configuration

Copy `.env.example` to `.env` for local development and set a model supported by DSPy/LiteLLM.

For a local provider:

```dotenv
GAME_ACCOUNTABILITY_AI_MODEL=ollama_chat/qwen3
GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE=false
```

For a remote provider, opt in explicitly and provide credentials through environment variables:

```dotenv
GAME_ACCOUNTABILITY_AI_MODEL=openai/gpt-5-mini
GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE=true
OPENAI_API_KEY=replace-me
```

`OPENAI_API_KEY` is the standard OpenAI environment variable. The loader also accepts `GAME_ACCOUNTABILITY_AI_API_KEY` as a compatibility override for other providers or older local configuration. `.env` is ignored by Git. Do not put secrets in source, profiles, observations, tests, or logs.

## Usage

```python
from game_accountability.ai import (
    ClassificationRequest,
    GameClassifier,
    configure_dspy,
    load_dspy_settings,
)

settings = load_dspy_settings()
configure_dspy(settings)

request = ClassificationRequest(observations=[...])
classification = GameClassifier()(request=request).result
```

An application service must persist the returned confidence and provenance before using the output to build a candidate profile. AI output must not directly enable contextual Runtime Mode.

Tests inject predictors and make no network or model calls.
