from django.core.management.base import BaseCommand
from django.utils import timezone
from comparer.models import ScheduledTask, ComparisonJob
from comparer.services import FileComparerService
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run scheduled file comparison tasks'

    def handle(self, *args, **options):
        now = timezone.now()
        tasks = ScheduledTask.objects.filter(
            status='active',
            next_run__lte=now
        )

        for task in tasks:
            try:
                self.stdout.write(f"Running task: {task.name}")
                
                # Check if files exist
                if not os.path.exists(task.source_path):
                    raise FileNotFoundError(f"Source path not found: {task.source_path}")
                if not os.path.exists(task.target_path):
                    raise FileNotFoundError(f"Target path not found: {task.target_path}")

                # Create comparison job
                job = ComparisonJob.objects.create(
                    file1=task.source_path,
                    file2=task.target_path,
                    comparison_fields=task.comparison_fields,
                    status='pending'
                )

                # Run comparison
                service = FileComparerService()
                
                # Extract field names from mappings
                fields = [mapping['field1'] for mapping in task.comparison_fields]
                
                result = service.compare_files(
                    task.source_path,
                    task.target_path,
                    fields
                )

                # Update job with results
                job.status = 'completed'
                job.result = result
                job.save()

                # Update task's last run and calculate next run
                task.last_run = now
                if task.frequency == 'hourly':
                    task.next_run = now + timezone.timedelta(hours=1)
                elif task.frequency == 'daily':
                    task.next_run = now + timezone.timedelta(days=1)
                elif task.frequency == 'weekly':
                    task.next_run = now + timezone.timedelta(weeks=1)
                else:  # monthly
                    task.next_run = now + timezone.timedelta(days=30)
                
                task.save()
                self.stdout.write(self.style.SUCCESS(f"Successfully completed task: {task.name}"))

            except Exception as e:
                logger.error(f"Error running task {task.name}: {str(e)}")
                task.status = 'error'
                task.save()
                self.stdout.write(self.style.ERROR(f"Failed to run task {task.name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Processed {tasks.count()} tasks"))
