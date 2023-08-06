
from typing import Any, Callable, Coroutine, Dict, List, Tuple

from prefect.utilities.asyncutils import create_gather_task_group


async def gather(*calls: Callable[..., Coroutine[Any, Any, Any]], args: List[Tuple[Any, ...]] = [], kwargs: List[Dict[str, Any]] = []) -> List[Any]:
    """
    Run calls concurrently and gather their results.

    Unlike `asyncio.gather` this expects to receive _callables_ not _coroutines_.
    This matches `anyio` semantics.

    Args:
        *calls: Functions or coroutines to be run concurrently.
        args: A list of tuples, where each tuple contains the positional arguments for the corresponding callable in `calls`.
            If no arguments are provided for a callable, use an empty tuple.
        kwargs: A list of dictionaries, where each dictionary contains the keyword arguments for the corresponding callable in `calls`.
            If no keyword arguments are provided for a callable, use an empty dictionary.

    Returns:
        A list containing the results of the calls.
    """
    if args is None:
        args = [()] * len(calls)  # If no positional arguments provided, use empty tuples
    if kwargs is None:
        kwargs = [{}] * len(calls)  # If no keyword arguments provided, use empty dictionaries

    if len(calls) != len(args) or len(calls) != len(kwargs):
        raise ValueError("The lengths of 'calls', 'args', and 'kwargs' should be the same.")

    keys = []
    async with create_gather_task_group() as tg:
        for call, arg, kwarg in zip(calls, args, kwargs):
            keys.append(tg.start_soon(lambda c=call, a=arg, k=kwarg: c(*a, **k)))
    return [tg.get_result(key) for key in keys]
