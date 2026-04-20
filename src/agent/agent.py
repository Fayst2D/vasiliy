import typing as tp

from abc import ABC, abstractmethod
from asyncio import sleep, Semaphore

from google import genai as ga

from ..logging import setup_logger
from ..tools import Tool
from ..types import ToolCallContext


_logger = setup_logger(__name__, 'logs/agent.txt')


async def try_n_times(callable_, n: int):
    for i in range(n):
        try:
            result = await callable_()
            if i > 0:
                _logger.info(f'Successful retry after {i} tries')
            return result
        except Exception:
            _logger.exception('Exception during retrying')


class Agent(ABC):
    @abstractmethod
    async def execute(
        self,
        system_prompt: str,
        prompt: str,
        context: ToolCallContext,
    ) -> None:
        pass


class GeminiAgent(Agent):
    def __init__(
        self,
        client: ga.Client,
        model_name: str,
        tools: list[Tool],
        generation_config: dict[str, tp.Any] | None = None,
        sleep_time: float = 0.3,
        concurrency_limit: int = 4,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._tools = tools
        self._generation_config = generation_config
        self._sleep_time = sleep_time
        self._concurrency_limit = concurrency_limit

        self._name_to_tool = {
            tool.name: tool
            for tool in self._tools
        }
        self._semaphore = Semaphore(self._concurrency_limit)

    async def execute(
        self,
        system_prompt: str,
        prompt: str,
        context: ToolCallContext
    ) -> None:
        async with self._semaphore:
            interaction = await self._client.aio.interactions.create(
                model=self._model_name,
                input=prompt,
                tools=[
                    tool.description
                    for tool in self._tools
                ],
                generation_config=self._generation_config,
                system_instruction=system_prompt,
            )  # type: ignore
            while True:
                if not interaction.outputs:
                    break

                function_calls = [
                    out
                    for out in interaction.outputs
                    if out.type == 'function_call'
                ]
                if len(function_calls) == 0:
                    break

                function_results = []
                for output in function_calls:
                    tool_name = output.name
                    arguments = output.arguments
                    if 'context' in arguments:
                        arguments['new_context'] = arguments['context']
                        del arguments['context']

                    if tool_name in self._name_to_tool:
                        tool = self._name_to_tool[tool_name]
                        _logger.debug(
                            f'[{output.id}; {context.chat_id}] ' +
                            f'Calling {tool_name}' +
                            f' with parameters: {arguments}'
                        )
                        try:
                            result = await tool(context=context, **arguments)
                            if result is None:
                                result = 'Success'
                        except Exception as e:
                            _logger.exception(
                                f'Error during tool call with id {output.id}'
                            )
                            result = f'ERROR: {e}'
                    else:
                        result = f'ERROR: Tool {tool_name} not found'

                    _logger.debug(f'[{output.id}] Result: {result}')
                    function_results.append({
                        'type': 'function_result',
                        'name': output.name,
                        'call_id': output.id,
                        'result': result
                    })

                interaction = await try_n_times(
                    lambda: self._client.aio.interactions.create(
                        model=self._model_name,
                        previous_interaction_id=interaction.id,
                        input=function_results,  # type: ignore
                    ), 3
                )
                if interaction is None:
                    break

                await sleep(self._sleep_time)
