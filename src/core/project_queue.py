import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProjectTask:
    """Represents a single project task in the queue."""
    project_id: str
    user_id: int
    outline: str
    sonnet_prompt: str
    target_volume: str
    min_length: int
    max_length: int
    created_at: datetime = field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.QUEUED
    attempt_count: int = 0
    successful_attempts: int = 0
    valid_responses: int = 0
    invalid_responses: int = 0
    valid_files: List[dict] = field(default_factory=list)
    invalid_files: List[dict] = field(default_factory=list)
    error_message: Optional[str] = None


class ProjectQueue:
    """Manages multiple project processing with Claude Sonnet 4 rate limits."""
    
    def __init__(self, max_concurrent_projects: int = 1):
        self.max_concurrent_projects = max_concurrent_projects
        self.projects: Dict[str, ProjectTask] = {}
        self.queue: List[str] = []
        self.processing: List[str] = []
        self.completed: List[str] = []
        self.failed: List[str] = []
        self._processing_lock = asyncio.Lock()
        self._queue_processor_task = None
        
        # Persistent counters for statistics that don't get reset by cleanup
        self.total_completed_count = 0
        self.total_failed_count = 0
        self.total_processed_count = 0
        
    async def start_queue_processor(self):
        """Start the queue processor task."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_queue())
            logger.info("Queue processor started")
    
    async def stop_queue_processor(self):
        """Stop the queue processor task."""
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
            logger.info("Queue processor stopped")
    
    async def add_project(self, task: ProjectTask) -> str:
        """Add a new project to the queue."""
        async with self._processing_lock:
            self.projects[task.project_id] = task
            self.queue.append(task.project_id)
            logger.info(f"Added project {task.project_id} to queue. Queue size: {len(self.queue)}")
            
            # Start queue processor if not running
            await self.start_queue_processor()
            
            return task.project_id
    
    async def get_project_status(self, project_id: str) -> Optional[ProjectTask]:
        """Get project status by ID."""
        return self.projects.get(project_id)
    
    async def get_user_projects(self, user_id: int) -> List[ProjectTask]:
        """Get all projects for a specific user."""
        return [task for task in self.projects.values() if task.user_id == user_id]
    
    async def remove_project(self, project_id: str) -> bool:
        """Remove a project from the queue and tracking."""
        async with self._processing_lock:
            if project_id in self.projects:
                # Remove from all lists
                if project_id in self.queue:
                    self.queue.remove(project_id)
                if project_id in self.processing:
                    self.processing.remove(project_id)
                if project_id in self.completed:
                    self.completed.remove(project_id)
                if project_id in self.failed:
                    self.failed.remove(project_id)
                
                # Remove from projects dict
                del self.projects[project_id]
                logger.info(f"Removed project {project_id}")
                return True
            return False
    
    async def _process_queue(self):
        """Main queue processing loop."""
        logger.info("Queue processor started")
        cleanup_counter = 0
        
        while True:
            try:
                async with self._processing_lock:
                    # Move projects from queue to processing if we have capacity
                    while (len(self.processing) < self.max_concurrent_projects and 
                           len(self.queue) > 0):
                        
                        project_id = self.queue.pop(0)
                        self.processing.append(project_id)
                        task = self.projects[project_id]
                        task.status = ProjectStatus.PROCESSING
                        
                        logger.info(f"Starting processing for project {project_id}")
                        
                        # Start processing task
                        asyncio.create_task(self._process_single_project(project_id))
                
                # Periodic cleanup (every 10 minutes)
                cleanup_counter += 1
                if cleanup_counter >= 600:  # 600 seconds = 10 minutes
                    await self.cleanup_old_projects()
                    cleanup_counter = 0
                
                # Wait a bit before checking again
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(5)
    
    async def _process_single_project(self, project_id: str):
        """Process a single project."""
        from ..ai_services import AIOrchestrator
        from ..bot.processors import save_generation_result
        
        try:
            task = self.projects[project_id]
            ai_orchestrator = AIOrchestrator()
            
            logger.info(f"Processing project {project_id} for user {task.user_id}")
            
            found_valid = False
            max_attempts = 20
            
            while not found_valid and task.attempt_count < max_attempts:
                task.attempt_count += 1
                
                try:
                    result = await ai_orchestrator.claude_service.process_outline(
                        task.outline,
                        target_length=(task.min_length + task.max_length) // 2,
                        sonnet_prompt=task.sonnet_prompt
                    )
                    
                    # Save result using existing logic
                    found_valid = await self._save_project_result(
                        result, task, task.min_length, task.max_length
                    )
                    
                    if not found_valid:
                        await asyncio.sleep(1)  # Short delay before next attempt
                    
                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error in project {project_id} attempt {task.attempt_count}: {e}")
                    
                    # If it's a rate limit error, wait longer before retrying
                    if "rate_limit" in error_str.lower() or "429" in error_str:
                        logger.info(f"Rate limit hit for project {project_id}, waiting 60 seconds")
                        await asyncio.sleep(60)  # Wait 1 minute for rate limits
                    else:
                        await asyncio.sleep(5)  # Regular error delay
                    continue
            
            # Mark as completed or failed
            async with self._processing_lock:
                self.processing.remove(project_id)
                if found_valid:
                    task.status = ProjectStatus.COMPLETED
                    self.completed.append(project_id)
                    self.total_completed_count += 1
                    self.total_processed_count += 1
                    logger.info(f"Project {project_id} completed successfully")
                else:
                    task.status = ProjectStatus.FAILED
                    task.error_message = f"Max attempts ({max_attempts}) reached without valid result"
                    self.failed.append(project_id)
                    self.total_failed_count += 1
                    self.total_processed_count += 1
                    logger.info(f"Project {project_id} failed after {max_attempts} attempts")
                    
        except Exception as e:
            logger.error(f"Critical error processing project {project_id}: {e}")
            async with self._processing_lock:
                if project_id in self.processing:
                    self.processing.remove(project_id)
                task = self.projects[project_id]
                task.status = ProjectStatus.FAILED
                task.error_message = str(e)
                self.failed.append(project_id)
                self.total_failed_count += 1
                self.total_processed_count += 1
    
    async def _save_project_result(self, result: str, task: ProjectTask, min_length: int, max_length: int) -> bool:
        """Save project result and return whether it's valid."""
        char_count = len(result)
        is_valid = min_length <= char_count <= max_length
        
        # Increment successful attempts counter
        task.successful_attempts += 1
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        file_data = {
            "content": result,
            "char_count": char_count,
            "timestamp": timestamp,
            "attempt": task.attempt_count,
            "successful_attempt": task.successful_attempts,
            "min_length": min_length,
            "max_length": max_length
        }
        
        if is_valid:
            task.valid_responses += 1
            task.valid_files.append(file_data)
            logger.info(f"Project {task.project_id}: Valid result - {char_count:,} chars")
        else:
            task.invalid_responses += 1
            task.invalid_files.append(file_data)
            logger.info(f"Project {task.project_id}: Invalid result - {char_count:,} chars (target: {min_length:,}-{max_length:,})")
        
        return is_valid
    
    def get_queue_stats(self) -> dict:
        """Get current queue statistics."""
        # Count current active projects by their actual status
        current_stats = {
            "queued": 0,
            "processing": 0,
            "completed_active": 0,
            "failed_active": 0,
        }
        
        for task in self.projects.values():
            if task.status == ProjectStatus.QUEUED:
                current_stats["queued"] += 1
            elif task.status == ProjectStatus.PROCESSING:
                current_stats["processing"] += 1
            elif task.status == ProjectStatus.COMPLETED:
                current_stats["completed_active"] += 1
            elif task.status == ProjectStatus.FAILED:
                current_stats["failed_active"] += 1
        
        # Return combined statistics
        return {
            "queued": current_stats["queued"],
            "processing": current_stats["processing"],
            "completed": self.total_completed_count,  # Total including cleaned up
            "failed": self.total_failed_count,  # Total including cleaned up
            "total_projects": len(self.projects),  # Current active projects
            "total_processed": self.total_processed_count  # All-time processed count
        }
    
    async def cleanup_old_projects(self, max_age_hours: int = 24):
        """Clean up old completed and failed projects."""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        projects_to_remove = []
        
        async with self._processing_lock:
            for project_id, task in self.projects.items():
                if (task.status in [ProjectStatus.COMPLETED, ProjectStatus.FAILED] and 
                    task.created_at < cutoff_time):
                    projects_to_remove.append(project_id)
            
            # Remove old projects
            for project_id in projects_to_remove:
                await self.remove_project(project_id)
                logger.info(f"Cleaned up old project {project_id}")
            
            if projects_to_remove:
                logger.info(f"Cleaned up {len(projects_to_remove)} old projects")


# Global project queue instance
project_queue = ProjectQueue()