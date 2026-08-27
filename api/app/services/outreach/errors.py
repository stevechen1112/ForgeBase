class OutreachSendBlocked(RuntimeError):
    """A permanent or policy failure that must not be retried automatically."""


class OutreachSendDeferred(RuntimeError):
    def __init__(self, message: str, delay_seconds: int):
        super().__init__(message)
        self.delay_seconds = max(1, delay_seconds)


class OutreachSendRetryable(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: int = 120):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
