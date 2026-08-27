"""
Channel abstraction — base interface for all notification channels.
All channels implement: send(recipient_config, message, buttons)
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseChannel(ABC):
    """Abstract notification channel."""

    @abstractmethod
    async def send(
        self,
        recipient_config: dict,
        message: str,
        buttons: Optional[list[dict]] = None,
    ) -> bool:
        """
        Send a message to a recipient.

        Args:
            recipient_config: Channel-specific recipient info
                Telegram: {"chat_id": "123456789"}
                LINE:     {"line_user_id": "Uxxxxx"}
                Email:    {"email": "user@example.com", "name": "John"}
            message: Plain text or channel-specific formatted string
            buttons: Optional list of quick-reply buttons
                     [{"label": "查看後台", "url": "https://..."}]

        Returns:
            True if sent successfully, False otherwise.
        """
        ...

    @abstractmethod
    def channel_name(self) -> str:
        """Return the channel identifier string."""
        ...
