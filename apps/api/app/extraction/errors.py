class ExtractionError(Exception):
    """Base class for safe, provider-independent extraction failures."""


class ExtractionTimeoutError(ExtractionError):
    """The provider did not respond before the configured timeout."""


class ExtractionProviderError(ExtractionError):
    """The provider could not complete a request."""


class ExtractionResponseError(ExtractionError):
    """The provider response cannot be used as a valid Liflow result."""
