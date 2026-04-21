import asyncio
import typing as tp

from datetime import datetime

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


def parse_slots(dice_value: int) -> dict[str, tp.Any]:
    val = dice_value - 1
    
    symbols = ['➖', '🍇', '🍋', '7️⃣']
    
    reel_1 = val % 4           # Left reel
    reel_2 = (val // 4) % 4    # Middle reel
    reel_3 = (val // 16) % 4   # Right reel
    
    return ''.join([symbols[reel_1], symbols[reel_2], symbols[reel_3]]), \
        dice_value == 64, reel_1 == reel_2 == reel_3


@as_tool
async def play_casino(
    context: ToolCallContext
) -> str:
    """
    Run a slot-machine. You can get following results: JACKPOT! You got 777!; Big Win! You matched 3 symbols!; You lost. Better luck next time.
    Use this function to run a slot-machine or a casino
    """

    score = await context.bot.send_dice(
        context.chat_id,
        emoji=DiceEmoji.SLOT_MACHINE,
    )
    await asyncio.sleep(2)

    outcome, is_jackpot, is_win = parse_slots(score.dice.value)

    context.new_messages.append(Message(
        sender_name='Slot machine',
        sender_shortname='',
        timestamp=datetime.now(),
        message_id=-1,
        text=outcome,
    ))
    return outcome


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
