import asyncio
import time
import json
from dataclasses import dataclass
from typing import Callable, Awaitable, Any, List, Dict, Optional
import aiofiles 
from dataclasses import dataclass, field
from collections import deque
from utils import logger


@dataclass
class WorkTask:
    name: str
    coro: Callable[[], Awaitable[Any]]
    status: str = "pending"   # "pending", "running", "completed", "failed"
    start_time: Optional[float] = None
    complete_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        format_time = lambda t: time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(t))
        return {
            "name": self.name,
            "status": self.status,
            "start_time": format_time(self.start_time) if self.start_time else None,
            "complete_time": format_time(self.complete_time) if self.complete_time else None,
        }

class TaskManager:
    def __init__(self):
        self.pending_tasks: asyncio.Queue[WorkTask] = asyncio.Queue()
        self.running_tasks: Dict[int, WorkTask] = {}
        self.completed_tasks: List[WorkTask] = []
        self.lock = asyncio.Lock()

    async def add_task(self, task: WorkTask):
        # Add a task to the asyncio.Queue.
        async with self.lock:
            await self.pending_tasks.put(task)

    async def start_task(self, worker_id: int) -> Optional[WorkTask]:
        # If there is no task, wait until one is available.
        task = await self.pending_tasks.get()
        async with self.lock:
            task.status = "running"
            task.start_time = time.time()
            self.running_tasks[worker_id] = task
        return task

    async def complete_task(self, worker_id: int, status: str = "completed"):
        async with self.lock:
            task = self.running_tasks.pop(worker_id, None)
            if task is not None:
                task.status = status
                task.complete_time = time.time()
                self.completed_tasks.append(task)

    async def get_state_dict(self) -> Dict[str, Any]:
        async with self.lock:
            # Copy state data to avoid race conditions.
            pending_list = []
            # asyncio.Queue does not support direct iteration, so we use a workaround.
            # This is not ideal for large queues but works for monitoring purposes.
            pending_size = self.pending_tasks.qsize()
            for _ in range(pending_size):
                task = await self.pending_tasks.get()
                pending_list.append(task)
                await self.pending_tasks.put(task)

            return {
                "pending": [t.to_dict() for t in pending_list],
                "running": {k: v.to_dict() for k, v in self.running_tasks.items()},
                "completed": [t.to_dict() for t in self.completed_tasks],
            }
        
    async def get_task_count_with(self, name: str) -> int:
        async with self.lock:
            return len([t for t in self.running_tasks.values() if t.name == name])
        
async def worker(task_manager: TaskManager, worker_id: int):
    while True:
        task = await task_manager.start_task(worker_id)
        logger.info(f"Worker {worker_id}: Starting task {task.name} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.start_time))}")
        try:
            await task.coro()
            await task_manager.complete_task(worker_id, status="completed")
        except Exception as e:
            logger.error(f"Worker {worker_id}: Task {task.name} failed with error: {e}")
            await task_manager.complete_task(worker_id, status="failed")
        logger.info(f"Worker {worker_id}: Finished task {task.name} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

async def checkpoint_writer(task_manager: TaskManager, interval: int = 5):
    while True:
        await asyncio.sleep(interval)
        state = await task_manager.get_state_dict()
        async with aiofiles.open("task_history.json", "w") as f:
            await f.write(json.dumps(state, indent=2))
        logger.debug("Checkpoint: Logs written to files.")
