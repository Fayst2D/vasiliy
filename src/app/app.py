import asyncio

from collections import defaultdict
from datetime import datetime

import aiogram.types as at

from aiogram import Bot
from aiogram.utils.chat_action import ChatActionSender

from ..agent import Agent
from ..context import ChatContextManager
from ..logging import setup_logger
from ..types import Message, ToolCallContext


_logger = setup_logger(__name__, 'logs/app.txt')


class Application:
    def __init__(
        self,
        bot: Bot,
        system_prompt: str,
        context_manager: ChatContextManager,
        agent: Agent,
        messages_limit: int = 20,
    ) -> None:
        self._bot = bot
        self._system_prompt = system_prompt
        self._context_manager = context_manager
        self._agent = agent
        self._message_queues = defaultdict(asyncio.Queue)  # type: ignore
        self._messages_limit = messages_limit

        self._execution_counts: dict[int, int] = defaultdict(int)
        self._locks: dict[int, asyncio.Lock] = {}

    async def _get_previous_messages(
        self,
        chat_id: int,
        n_new_messages: int
    ) -> list[Message]:
        if n_new_messages >= self._messages_limit:
            return []

        return await self._context_manager.get_last_messages(
            chat_id, self._messages_limit - n_new_messages
        )

    def _format_message(self, message: Message) -> str:
        return f'ID: {message.message_id} | [{message.timestamp} {message.sender_name} ' \
            f'(@{message.sender_shortname}): {message.text}]'

    async def _execute_agent(
        self,
        context: ToolCallContext,
        previos_messages: list[Message],
        new_messages: list[Message],
    ) -> None:
        prompt = '\n'.join([
            f'Time: {datetime.now()}',
            '## Chat context:',
            context.context or 'The context is empty. Use update_context tool to update it',
            '## Previous messages',
            *[
                self._format_message(message)
                for message in previos_messages
            ],
            '## New messages',
            *[
                self._format_message(message)
                for message in new_messages
            ]
        ])
        await self._agent.execute(
            system_prompt=self._system_prompt,
            prompt=prompt,
            context=context,
        )

    async def _process_chat_updates(self, chat_id: int) -> None:
        message_queue = self._message_queues[chat_id]
        if message_queue.empty():
            return

        new_messages = []
        while not message_queue.empty():
            new_messages.append(await message_queue.get())

        previous_messages = await self._get_previous_messages(
            chat_id, len(new_messages)
        )
        context = await self._context_manager.get_context(chat_id)

        tool_call_context = ToolCallContext(
            bot=self._bot,
            chat_id=chat_id,
            context=context,
            new_messages=[]
        )
        async with ChatActionSender.typing(
            chat_id=chat_id, bot=self._bot
        ):
            try:
                await self._execute_agent(
                    tool_call_context, previous_messages,
                    new_messages
                )
            except Exception:
                _logger.exception(
                    'Exception while executing agent'
                )

        await self._context_manager.append_messages(
            chat_id, new_messages + tool_call_context.new_messages
        )
            
    async def message_handler(self, message: at.Message) -> None:
        chat_id = message.chat.id
        msg = Message.from_at_message(message)

        await self._message_queues[chat_id].put(msg)

        self._execution_counts[chat_id] += 1

        if chat_id not in self._locks:
            self._locks[chat_id] = asyncio.Lock()

        async with self._locks[chat_id]:
            await self._process_chat_updates(chat_id)

            self._execution_counts[chat_id] -= 1
            if self._execution_counts[chat_id] > 0:
                return

            self._execution_counts.pop(chat_id, None)
            self._locks.pop(chat_id, None)