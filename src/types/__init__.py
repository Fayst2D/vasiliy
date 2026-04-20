from dataclasses import dataclass, asdict
from datetime import datetime

import aiogram.types as at

from aiogram import Bot

from ..utils import dotdict


@dataclass
class Message:
    sender_name: str
    sender_shortname: str
    timestamp: datetime
    message_id: int
    text: str

    def as_dict(self) -> dict:
        result = asdict(self)
        result['timestamp'] = str(result['timestamp'])
        return result

    @staticmethod
    def from_at_message(message: at.Message) -> 'Message':
        from_user = message.from_user or dotdict({
            'full_name': '',
            'username': ''
        })
        return Message(
            sender_name=from_user.full_name or '',  # type: ignore
            sender_shortname=from_user.username or '',  # type: ignore
            timestamp=message.date,
            message_id=message.message_id,
            text=message.text or '',
        )


@dataclass
class ToolCallContext:
    bot: Bot
    chat_id: int
    context: str
    new_messages: list[Message]


__all__ = [
    'Message', 'ToolCallContext'
]
