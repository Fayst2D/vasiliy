from src.types import ToolCallContext
from abc import ABC, abstractmethod
from collections import defaultdict

from ..tools import as_tool
from ..types import Message, ToolCallContext


class ChatContextManager(ABC):
    @abstractmethod
    async def get_last_messages(
        self,
        chat_id: int,
        limit: int | None
    ) -> list[Message]:
        pass

    @abstractmethod
    async def append_message(
        self,
        chat_id: int,
        message: Message
    ) -> None:
        pass

    async def append_messages(
        self,
        chat_id: int,
        messages: list[Message]
    ) -> None:
        for message in messages:
            await self.append_message(chat_id, message)

    @abstractmethod
    async def get_context(
        self,
        chat_id: int,
    ) -> str:
        pass

    @abstractmethod
    async def update_chat_context(
        self,
        chat_id: int,
        new_context: str,
    ) -> None:
        pass

    async def update_context(
        self,
        new_context: str,
        context: ToolCallContext
    ) -> None:
        """
        Update the context for the conversation. Update it if there is new important information or you learn something new about chat members.
        For example:
        John: he is an interesting guy and earn 300$/month
        Bob: likes car too, so I respect him
        Guys are talking about gambling now, so should I join?

        :param new_context: new context for the chat
        """

        print(context.chat_id, new_context, flush=True)
        await self.update_chat_context(context.chat_id, new_context)


class InMemoryChatContextManager(ChatContextManager):
    def __init__(self) -> None:
        self.messages = defaultdict(list)
        self.contexts = defaultdict(str)

    async def get_last_messages(
        self,
        chat_id: int,
        limit: int | None
    ) -> list[Message]:
        messages = self.messages[chat_id]
        if limit is not None:
            messages = messages[-limit:]
        return messages

    async def append_message(
        self,
        chat_id: int,
        message: Message
    ) -> None:
        self.messages[chat_id].append(message)

    async def get_context(
        self,
        chat_id: int,
    ) -> str:
        return self.contexts[chat_id]

    async def update_chat_context(
        self,
        chat_id: int,
        new_context: str,
    ) -> None:
        self.contexts[chat_id] = new_context
