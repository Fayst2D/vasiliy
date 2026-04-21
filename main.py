import asyncio
import json
import typing as tp

from pathlib import Path

import yaml  # type: ignore

from aiogram import Bot, Dispatcher, F
from google import genai as ga

from src.agent import GeminiAgent
from src.app import Application
from src.context import SQLiteChatContextManager
from src.tools import Tool, as_tool
from src.tools.telegram import write_to_chat, leave_chat, \
    make_sticker_tool, play_casino


def read_yaml(p: str) -> dict:
    with open(p, 'r') as file:
        return yaml.safe_load(file)


def create_sticker_tool() -> Tool:
    config = read_yaml('config/stickers.yaml')
    data = [
        {
            'name': name,
            **value
        } for name, value in config.items()
    ]
    return make_sticker_tool(data)


def get_tools() -> list[Tool]:
    return [
        write_to_chat,
        leave_chat,
        play_casino,
        create_sticker_tool()
    ]


def tool_description_to_string(description: dict[str, tp.Any]) -> str:
    return json.dumps(description, indent=4)


async def build_system_prompt(bot: Bot) -> str:
    with open('config/system_prompt.txt', 'r', encoding='utf-8') as file:
        content = file.read()

    me = await bot.me()
    return content.format(
        bot_username=me.full_name,
        bot_shortname=me.username,
    )


async def main() -> None:
    Path('logs').mkdir(exist_ok=True)

    config = read_yaml('config/config.yaml')
    keys = read_yaml('keys.yaml')

    bot = Bot(token=keys['telegram'])
    dp = Dispatcher()

    context_manager = SQLiteChatContextManager(
        db_url=config['database']['url']
    )
    await context_manager.initialize_db()

    tools = get_tools()
    tools.append(as_tool(context_manager.update_context))

    print(f'Total: {len(tools)} tools')
    for tool in tools:
        print(tool_description_to_string(tool.description))

    agent = GeminiAgent(
        client=ga.Client(
            api_key=keys['gemini']
        ),
        model_name=config['model']['name'],
        tools=tools,
        generation_config=config['generation_config'],
        concurrency_limit=config['app']['concurrency_limit'],
    )

    app = Application(
        bot=bot,
        system_prompt=await build_system_prompt(bot),
        context_manager=context_manager,
        agent=agent,
        messages_limit=config['app']['messages_context_limit']
    )

    dp.message(F.text)(app.message_handler)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
