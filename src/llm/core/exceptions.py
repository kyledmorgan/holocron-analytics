"""
Custom exceptions for the LLM-Derived Data module.
"""


class LLMError(Exception):
    """Base exception for all LLM module errors."""
    pass


class LLMProviderError(LLMError):
    """
    Error communicating with an LLM provider.
    
    Raised when:
    - Provider is unreachable
    - Request times out
    - Provider returns an error response
    - Model is not available
    """
    
    def __init__(self, message: str, provider: str = None, status_code: int = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class LLMValidationError(LLMError):
    """
    Error validating LLM output against schema.
    
    Raised when:
    - LLM response is not valid JSON
    - JSON does not conform to expected schema
    - Required fields are missing
    """
    
    def __init__(self, message: str, validation_errors: list = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class LLMConfigError(LLMError):
    """
    Error in LLM configuration.
    
    Raised when:
    - Configuration file is missing or invalid
    - Required configuration values are not set
    - Configuration values are out of valid range
    """
    pass


class LLMStorageError(LLMError):
    """
    Error persisting or retrieving LLM artifacts.
    
    Raised when:
    - Cannot write to artifact store
    - Cannot read from artifact store
    - Queue persistence fails
    """
    pass


class LLMPromptError(LLMError):
    """
    Error with prompt template or rendering.
    
    Raised when:
    - Prompt template not found
    - Template rendering fails
    - Template variables missing
    """
    pass


class LLMEvidenceError(LLMError):
    """
    Error with evidence bundle.
    
    Raised when:
    - Evidence source cannot be loaded
    - Evidence hash mismatch (integrity failure)
    - Evidence bundle is empty
    """
    pass
