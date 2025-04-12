#!/bin/bash
cd /home/backend-mesikahq/Tests/file_comparer
source venv/bin/activate
python manage.py run_scheduled_tasks >> /home/backend-mesikahq/Tests/file_comparer/cron.log 2>&1
