import asyncio
import time
import pyarrow as pa
from typing import List, Dict, Any, Optional
from core.duckdb_engine import DuckDBEngine

class IngestBuffer:
    def __init__(self, duck_engine: DuckDBEngine, batch_size: int = 1000, flush_interval_ms: int = 500, max_buffer: int = 50000):
        self.duck = duck_engine
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_ms / 1000.0
        self.max_buffer = max_buffer
        
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_buffer)
        self.is_running = False
        self.total_ingested = 0
        self.last_flush_time = time.time()
        self._flush_task: Optional[asyncio.Task] = None

    async def push(self, record: Dict[str, Any]):
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            pass

    async def push_batch(self, records: List[Dict[str, Any]]):
        for r in records:
            await self.push(r)

    async def start(self):
        self.is_running = True
        self._flush_task = asyncio.create_task(self._flush_worker())

    async def stop(self):
        self.is_running = False
        if self._flush_task:
            self._flush_task.cancel()
        await self._flush_remaining()

    async def _flush_worker(self):
        while self.is_running:
            try:
                await asyncio.sleep(self.flush_interval_sec)
                await self._flush_remaining()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[IngestBuffer] Lỗi khi flush: {e}")

    async def _flush_remaining(self):
        batch = []
        while not self.queue.empty() and len(batch) < self.batch_size:
            batch.append(self.queue.get_nowait())
            self.queue.task_done()
        
        if batch:
            table = pa.Table.from_pylist(batch)
            self.duck.insert_arrow_batch(table)
            self.total_ingested += len(batch)
            self.last_flush_time = time.time()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffer_queue_size": self.queue.qsize(),
            "total_ingested": self.total_ingested,
            "last_flush_time": self.last_flush_time
        }
