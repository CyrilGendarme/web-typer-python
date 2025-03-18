import os
import sys
import threading
from typing import Callable, Dict, List, Optional, Tuple, Any

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from task_engine.enums_and_mappings import common_func_map


# Define a generic type for function maps
FuncMapType = Dict[Any, Callable[..., None]]  # Allows any Enum-based mapping


class TasksQueue:
    def __init__(self, func_maps: List[FuncMapType]) -> None:
        """Initialize the task queue with a flexible function map."""
        self.task_queue: List[Tuple[Callable[..., None], ...]] = []
        self.lock = threading.Lock()
        self.func_maps = func_maps

    def add_task(
        self,
        task_enum: Any,
        *args: Any,
        check_duplicate: bool = False,
        add_to_top: bool = False,
    ) -> None:
        """Add a task using an Enum instead of a raw function reference.

        Args:
            task_enum (Any): The Enum key representing the task.
            *args (Any): Arguments for the function.
            check_duplicate (bool, optional): If True, prevents adding duplicate function types. Defaults to False.
        """
        with self.lock:
            func = None

            # Try to find the function in either of the function maps
            for func_map in self.func_maps:
                if task_enum in func_map:
                    func = func_map[task_enum]
                    break

            if func is None:
                print(f"Warning: No function mapped for {task_enum}")
                return

            # Check for duplicates if the flag is enabled
            if check_duplicate and any(
                existing_task[0] == func for existing_task in self.task_queue
            ):
                print(f"Skipping duplicate task: {task_enum}")
                return

            if add_to_top:
                self.task_queue.insert(0, (func, *args))
            else:
                self.task_queue.append((func, *args))

    def get_next_task(
        self, remove: bool = True
    ) -> Optional[Tuple[Callable[..., None], ...]]:
        """Retrieve (and optionally remove) the next task from the queue.

        Args:
            remove (bool, optional): If True, removes the task from the queue. If False, only retrieves it.
                                    Defaults to True.

        Returns:
            Optional[Tuple[Callable[..., None], ...]]: The next task (function and its arguments) or None if empty.
        """
        with self.lock:
            if not self.task_queue:
                return None

            return self.task_queue.pop(0) if remove else self.task_queue[0]

    def remove_next_task(self) -> Optional[Tuple[Callable[..., None], ...]]:
        """Remove and return the next task from the queue."""
        return self.get_next_task(remove=True)

    def load_tasks_from_file(self, file_path: str) -> None:
        """Load tasks from a .txt file and add them to the queue."""
        try:
            with open(file_path, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if not parts:
                        continue

                    func_name = parts[0].strip()
                    args = [arg.strip() for arg in parts[1:]]

                    task_enum = next(
                        (
                            key
                            for key, value in self.func_map.items()
                            if value.__name__ == func_name
                        ),
                        None,
                    )

                    if task_enum:
                        self.add_task(task_enum, *args)
                    else:
                        print(f"Warning: Function '{func_name}' not found in func_map")

        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
        except Exception as e:
            print(f"An error occurred: {e}")


def process_queue(task_queue: TasksQueue) -> bool:
    """
    Process and execute tasks from the queue every `delay` seconds.

    Args:
        task_queue (TasksQueue): The queue object managing tasks.
        delay (int, optional): Time (in seconds) to wait between executions. Default is 2.
    """
    task = task_queue.get_next_task(remove=False)
    if not task:
        return False

    func, *args = task
    if callable(func):
        func(*args)
        task_queue.remove_next_task()
        return True
    else:
        print(f"Warning: {func} is not callable")

    return False
