import asyncio
import typing as tp

from aiogram.enums.dice_emoji import DiceEmoji

from ..tool import as_tool
from ...types import ToolCallContext, Message


@as_tool
async def write_to_chat(message: str, context: ToolCallContext) -> None:
    """
    Sends one message to the chat. Call the function multiple times to send multiple messages

    :param message: message to send
    """
    output_message = await context.bot.send_message(
        context.chat_id,
        message,
    )
    context.new_messages.append(Message.from_at_message(output_message))


@as_tool
async def leave_chat(context: ToolCallContext) -> None:
    """
    Leave the chat. Forever
    """
    await context.bot.leave_chat(
        context.chat_id,
    )


@as_tool
async def reply_to_message(
    message_id: int,
    message: str,
    context: ToolCallContext
) -> None:
    """
    Reply to a message in chat. Use it to reply to a specific message

    :param message_id: message_id to reply to
    :param message: text of the message
    """

    await context.bot.send_message(
        context.chat_id,
        message,
        reply_to_message_id=message_id
    )



@as_tool
async def play_casino(
    context: ToolCallContext
) -> str:
    """
    Run a slot-machine in the chat. The result is returned
    """

    score = await context.bot.send_dice(
        context.chat_id,
        emoji=DiceEmoji.SLOT_MACHINE,
    )
    await asyncio.sleep(2)

    if score == 64:
        return 'JACKPOT! You got 777!'
    elif score in [1, 22, 43]:
        return 'Big Win! You matched 3 symbols!'

    return 'Better luck next time!'


def make_sticker_tool(sticker_descriptions: list[dict[str, str]]):
    sticker_name_to_id = {
        data['name']: data['id']
        for data in sticker_descriptions
    }
    sticker_names = [
        data['name']
        for data in sticker_descriptions
    ]
    StickerNameType = tp.Literal[tuple(sticker_names)]

    async def send_sticker(
        sticker_name: StickerNameType,
        context: ToolCallContext
    ) -> str | None:
        if sticker_name not in sticker_name_to_id:
            return f'ERROR: Sticker {sticker_name} doesn\'t exist!'

        print(sticker_name_to_id[sticker_name], flush=True)
        await context.bot.send_sticker(
            chat_id=context.chat_id,
            sticker=sticker_name_to_id[sticker_name],
        )

        return 'Success'

    doc = ''
    doc += 'Use this function to send a sticker message\n\n'
    doc += ':param sticker_name: Name of the sticker. '
    doc += 'Following names are supported: '
    doc += ', '.join(sticker_names)
    send_sticker.__doc__ = doc
    return as_tool(send_sticker)
