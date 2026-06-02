from openai import APIStatusError, OpenAIError, RateLimitError


class AIProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def to_ai_provider_error(exc: Exception) -> AIProviderError:
    raw_message = str(exc)
    if "insufficient_quota" in raw_message:
        return AIProviderError(
            "OpenAI API quota is unavailable. Add API billing/credits or increase your quota in the OpenAI Platform.",
            status_code=429,
        )

    if isinstance(exc, RateLimitError):
        return AIProviderError(_openai_message(exc), status_code=429)

    if isinstance(exc, APIStatusError):
        return AIProviderError(_openai_message(exc), status_code=exc.status_code)

    if isinstance(exc, OpenAIError):
        return AIProviderError(str(exc), status_code=502)

    return AIProviderError(str(exc), status_code=500)


def _openai_message(exc: APIStatusError) -> str:
    body = exc.body
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)

    return str(exc)
