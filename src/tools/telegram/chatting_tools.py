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


@as_tool
async def create_poll(
        question: str,
        options: str,
        context: ToolCallContext,
        is_anonymous: bool = False,
        allows_multiple_answers: bool = False,
        allow_adding_options: bool = True,
) -> None:
    """
    Creates a poll or a vote in the chat. Use this when you want to ask users for their opinion or run a survey.

    :param question: The question to ask (e.g., "What is your favorite color?")
    :param options: A list of options separated by commas (e.g., "Red, Green, Blue"). Provide between 2 and 10 options.
    :param is_anonymous: If True, users will vote anonymously. Default is False.
    :param allows_multiple_answers: If True, users can choose more than one option. Default is False.
    :param allow_adding_options: If True, users can add their own poll options. Default is True.
    """


    options_list = [opt for opt in options.split(',')]

    if is_anonymous:
        allow_adding_options = False


    poll_message = await context.bot.send_poll(
        chat_id=context.chat_id,
        question=question,
        options=options_list,
        is_anonymous=is_anonymous,
        allows_multiple_answers=allows_multiple_answers,
        allow_adding_options=allow_adding_options,
    )

    context.new_messages.append(Message.from_at_message(poll_message))


@as_tool
async def create_quiz(
        question: str,
        options: str,
        correct_option_ids: str,
        explanation: str,
        context: ToolCallContext,
        allows_multiple_answers: bool = False
) -> None:
    """
    Creates a quiz in the chat. Use this when you want to ask users about something.

    :param question: The question to ask (e.g., "What is the capital of the Belarus?")
    :param options: A list of options separated by commas (e.g., "Moscow, Berlin, Minsk"). Provide between 2 and 12 options.
    :param correct_option_ids: list of monotonically increasing 0-based identifiers of the correct answer options (e.g., "0, 3, 5")
    :param explanation: Text that is shown when a user chooses an incorrect answer 0-200 characters
    :param allows_multiple_answers: If True, users can choose more than one option. Default is False.
    """


    options_list = [opt for opt in options.split(',')]
    correct_option_ids = [ans for ans in correct_option_ids.split(',')]


    poll_message = await context.bot.send_poll(
        chat_id=context.chat_id,
        question=question,
        options=options_list,
        correct_option_ids=correct_option_ids,
        explanation=explanation,
        allows_multiple_answers=allows_multiple_answers,
        type="quiz"
    )

    context.new_messages.append(Message.from_at_message(poll_message))