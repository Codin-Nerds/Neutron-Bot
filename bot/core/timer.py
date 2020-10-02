import asyncio
import inspect
import typing as t
from contextlib import suppress
from datetime import datetime

from loguru import logger


class Timer:
    """
    Delay the execution of any task.

    If an exception occurres in the coroutine, it will be logged after it's executed.

    In order to delay a task by n seconds use the `delay` function.
    In order to run a task at specific time use the `run_at` function.

    Both of these require a unique `task_name` which will be showed together with this
    Timers `id` in all logs regarding that task.
    These tasks are also stored in the `delayed_tasks` dict.
    """

    def __init__(self, _id: t.Hashable):
        self.id = _id
        self.delayed_tasks: t.Dict[t.Hashable, asyncio.Task] = {}

    def delay(self, delay: t.Union[int, float], task_name: t.Hashable, coro: t.Coroutine) -> None:
        """
        Postpone the execution of `coro` by given amount of seconds in `delay`

        If delay is negative, run the coroutine immediately.

        Close the `coro` in case there is already a delayed task with the same task name
        in order to avoid never awaited error.
        """
        if delay > 0:
            coroutine = self._postpone(task_name, coro, delay)
        else:
            coroutine = coro

        if task_name in self.delayed_tasks:
            logger.warning("Tried to delay already active task, ignoring")
            coroutine.close()  # Close the coroutine to avoid never awaited error
            return

        task = asyncio.create_task(coroutine, name=f"{self.id}:{task_name}")
        task.add_done_callback(lambda executed_task: self._task_executed(task_name, executed_task))

        self.delayed_tasks[task_name] = task
        logger.debug(f"Task {task.get_name()} will run delayed.")

    def run_at(self, time: datetime, task_name: t.Hashable, coro: t.Coroutine) -> None:
        """
        Postpone the execution of `coro` to given `time` (UTC)

        If delay is negative, run the coroutine immediately.

        Close the `coro` in case there is already a delayed task with the same task name
        in order to avoid never awaited error.
        """
        delay = (time - datetime.utcnow()).total_seconds()
        self.delay(delay, task_name, coro)

    def abort(self, task_name: t.Hashable) -> None:
        """Cancel already delayed task with name of `task_name`"""
        try:
            task = self.delayed_tasks.pop(task_name)
        except KeyError:
            logger.warning(f"Unable to abort task {self.id}:{task_name}, no such task.")
        else:
            task.cancel()
            logger.debug(f"Task {self.id}:{task_name} was aborted.")

    def abort_all(self) -> None:
        """Cancel all currently delayed tasks in this timer."""
        logger.debug(f"Aborting all delayed tasks from {self.id}")

        for task in self.delayed_tasks.values():
            task.cancel()

    async def _postpone(self, task_name: t.Hashable, coro: t.Coroutine, delay: t.Union[int, float]) -> None:
        """
        Execute `coro` after `delay` amount of seconds.

        In case the `coro` would get cancelled during the sleep, close it to
        prevent never awaited error.
        """
        try:
            await asyncio.sleep(delay)
            # Prevent `coro` from canceling itself by shielding it
            await asyncio.shield(coro)
        finally:
            # Prevent coroutine never awaited error if it got cancelled during sleep
            # But only do so if it wasn't awaited yet, since the coro can also cancel itself
            if inspect.getcoroutinestate(coro) == "CORO_CREATED":
                logger.debug(f"Aborting the coroutine from {self.id}:{task_name} task.")
                coro.close()

    def _task_executed(self, task_name: t.Hashable, executed_task: t.Coroutine) -> None:
        """
        Remove the task from `delayed_tasks` dict once it was executed.

        Send a log message in case there was a new task scheduled with the same `task_name`.
        """
        stored_task = self.delayed_tasks.get(task_name)

        if stored_task and stored_task is executed_task:
            # The task was completed successfully, remove it from delayed tasks
            del self.delayed_tasks[task_name]
        elif stored_task:
            # There is a new task which has the same name, this was probably caused by
            # delaying a new task with same name which overwrote the old one
            logger.debug(
                f"Stored task {self.id}:{task_name} ({id(stored_task)}) "
                f"doesn't match the finished task ({id(executed_task)})"
            )
        elif not executed_task.cancelled():
            logger.warning(
                f"Task {self.id}:{task_name} ({id(executed_task)}) wasn't found, "
                f"It seems to have been manually removed without canceling it"
            )

        with suppress(asyncio.CancelledError):
            exception = executed_task.exception()
            if exception:
                logger.error(f"Exception ocurred while executing {self.id}:{task_name} ({id(executed_task)})")
