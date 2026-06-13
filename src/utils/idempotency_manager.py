import hashlib
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from models import CeleryTaskExecution


class IdempotencyManager:
    def __init__(self, db_client, db_engine):
        self.db_client = db_client
        self.db_engine = db_engine

    def create_args_hash(self, task_name: str, task_args: dict):
        combined_data = {**task_args, "task_name": task_name}
        json_string = json.dumps(combined_data, sort_keys=True, default=str)
        return hashlib.sha256(json_string.encode()).hexdigest()

    async def create_task_record(
        self, task_name: str, task_args: dict, celery_task_id: str = None
    ) -> CeleryTaskExecution:
        """Create new task execution record."""

        args_hash = self.create_args_hash(task_name=task_name, task_args=task_args)

        task_record = CeleryTaskExecution(
            task_name=task_name,
            task_args_hash=args_hash,
            task_args=task_args,
            celery_task_id=celery_task_id,
            status="PENDING",
            started_at=datetime.now(timezone.utc),
        )
        # session = self.db_client()

        async with self.db_client() as session:
            async with session.begin():
                session.add(task_record)
            await session.commit()
            await session.refresh(task_record)

        return task_record

        # try:
        #     session.add(task_record)
        #     await session.commit()
        #     await session.refresh(task_record)
        #     return task_record
        # finally:
        #     await session.close()

    async def update_task_status(
        self, execution_id: int, status: str, result: dict = None
    ):
        """Update task status and result."""
        async with self.db_client() as session:
            async with session.begin():
                task_record = await session.get(CeleryTaskExecution, execution_id)
                if task_record:
                    task_record.status = status
                    if result:
                        task_record.result = result
                    if status in ["SUCCESS", "FAILURE"]:
                        task_record.completed_at = datetime.now(timezone.utc)
                    await session.commit()

    async def get_existing_task(
        self,
        # celery_task_id: str,
        task_name: str,
        task_args: dict,
    ) -> CeleryTaskExecution | None:
        """Check if task with same name and args already exists."""

        args_hash = self.create_args_hash(task_name=task_name, task_args=task_args)
        async with self.db_client() as session:
            async with session.begin():
                query = select(CeleryTaskExecution).where(
                    # CeleryTaskExecution.celery_task_id == celery_task_id,
                    CeleryTaskExecution.task_name == task_name,
                    CeleryTaskExecution.task_args_hash == args_hash,
                )
                task = await session.execute(query)
                result = task.scalar_one_or_none()
        return result

    async def should_execute_task(
        self,
        # celery_task_id: int,
        task_name: str,
        task_args: dict,
        task_time_limit: int = 600,
    ) -> tuple[bool, CeleryTaskExecution | None]:
        """
        Check if task should be executed or return existing result.
        Args:
            task_time_limit: Time limit in seconds after which a stuck task can be re-executed
        Returns (should_execute, existing_task_or_none)
        """

        existing_task = await self.get_existing_task(
            # celery_task_id=celery_task_id,
            task_name=task_name,
            task_args=task_args,
        )

        if not existing_task:
            return True, None

        # Don't execute if task is already completed successfully
        if existing_task.status == "SUCCESS":
            return False, existing_task

        # Check if task is stuck (running longer than time limit + 60 seconds)
        if existing_task.status in ["PENDING", "STARTED", "RETRY"]:
            if existing_task.started_at:
                time_elapsed = (
                    datetime.now(timezone.utc) - existing_task.started_at
                ).total_seconds()
                time_gap = 60  # 60 secs grace period
                if time_elapsed > (task_time_limit + time_gap):
                    return True, existing_task  # Task is stuck, allow re-execution
            return False, existing_task  # Task is still running within time limit

        # Re-execute if previous task failed
        return True, existing_task

    async def cleanup_old_tasks(self, time_retention: int = 86400) -> int:
        """
        Delete old task records older than time_retention seconds.
        Args:
            time_retention: Time in seconds to retain tasks (default: 86400 = 24 hours)
        Returns:
            Number of deleted records
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=time_retention)

        async with self.db_client() as session:
            async with session.begin():
                query = delete(CeleryTaskExecution).where(
                    CeleryTaskExecution.created_at < cutoff_time
                )
                result = await session.execute(query)
                return result.rowcount
