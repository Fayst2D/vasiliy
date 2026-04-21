import inspect
import re
import typing as tp

from ..types import ToolCallContext


class Tool:
    def __init__(
        self,
        fn: tp.Callable[[tp.Any, ...], tp.Any],  # type: ignore
        description: dict[str, tp.Any],
        kwargs: dict[str, tp.Any] | None = None,
    ) -> None:
        self._fn = fn
        self._description = description
        self._kwargs = kwargs or dict()

    async def __call__(
        self, context: ToolCallContext,
        *args: tp.Any, **kwargs: tp.Any
    ):
        return await self._fn(
            *args, **kwargs, **self._kwargs,
            context=context
        )  # type: ignore

    def bind(self, kw: dict[str, tp.Any]) -> 'Tool':
        new_kw = self._kwargs.copy()
        new_kw.update(kw)
        return Tool(
            fn=self._fn,
            description=self._description,
            kwargs=new_kw
        )

    @property
    def name(self) -> str:
        return self._fn.__name__

    @property
    def description(self) -> dict[str, tp.Any]:
        return self._description


def _replace_space_characters(s: str) -> str:
    return re.sub(r'\s', ' ', s)


def _parse_function_docstring(
    docstring: str
) -> tuple[str, list[tuple[str, str]]]:
    params_start = docstring.find(':param')
    returns_start = docstring.find(':returns')
    if returns_start != -1:
        docstring = docstring[:returns_start]

    description = docstring[:params_start]
    description = _replace_space_characters(description).strip()

    if params_start == -1:
        return description, []

    params_description = docstring[params_start:]
    params_start_indices = [
        match.start()
        for match in re.finditer(r':param [\w\d]+:', params_description)
    ] + [len(params_description)]

    params_data = []
    for start_index, end_index in zip(
        params_start_indices,
        params_start_indices[1:]
    ):
        match_ = re.match(
            r':param ([\w\d]+): (.*)',
            params_description[start_index:end_index]
        )
        assert match_ is not None

        params_data.append((
            match_.group(1),
            _replace_space_characters(match_.group(2))
        ))

    return description, params_data


def _map_to_tool_paramter_description(
    name: str,
    description: str,
    type_: type,
) -> dict[str, str]:
    type_to_string = {
        str: 'string',
        float: 'number',
        int: 'integer',
        bool: 'boolean',
    }

    result: dict[str, tp.Any] = {
        'description': description
    }
    if type_ in type_to_string:
        result['type'] = type_to_string[type_]
        return result

    if str(type_).startswith('typing.Literal['):
        result['type'] = 'string'
        result['enum'] = [
            str(x)
            for x in tp.get_args(type_)
        ]
        return result

    assert False, 'Could not parse type: ' + str(type_)


def get_required_arguments(function: tp.Callable) -> set[str]:
    sig = inspect.signature(function)
    return {
        name
        for name, param in sig.parameters.items()
        if param.default is inspect._empty
    }


def as_tool(func: tp.Callable):
    assert hasattr(func, '__doc__'), \
        'Function must have a docstring to be parsed as a tool'

    (
        docstring,
        params_info
    ) = _parse_function_docstring(func.__doc__)  # type: ignore
    description: dict[str, tp.Any] = {
        'type': 'function',
        'name': func.__name__,
        'description': docstring,
    }

    arg_types = inspect.getfullargspec(func).annotations
    required_params = get_required_arguments(func)
    if 'context' in required_params:
        required_params.remove('context')
    if 'self' in required_params:
        required_params.remove('self')

    description['parameters'] = {
        'type': 'object',
        'properties': {
            param_name: _map_to_tool_paramter_description(
                param_name, param_description, arg_types[param_name],
            )
            for param_name, param_description in params_info
        }
    }
    if len(required_params) > 0:
        params = description['parameters']
        params['required'] = list(required_params)  # pyrefly: ignore

    return Tool(
        fn=func,
        description=description
    )
