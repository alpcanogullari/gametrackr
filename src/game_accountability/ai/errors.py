"""Errors raised at the AI boundary."""


class AIConfigurationError(ValueError):
    """Raised when DSPy cannot be configured safely."""


class AIOutputValidationError(ValueError):
    """Raised when an AI prediction violates the structured output contract."""
