from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import os
import pandas as pd
import io
from datetime import datetime, timedelta
from collections import defaultdict
from .services import FileComparerService
from .models import ScheduledTask, ComparisonHistory, UserStats
import uuid
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib import messages
import time

@login_required
def upload_view(request):
    return render(request, 'comparer/upload.html')

def save_uploaded_file(uploaded_file):
    file_path = default_storage.save(f'uploads/{uploaded_file.name}', uploaded_file)
    return default_storage.path(file_path)

@csrf_exempt
def suggest_mappings_view(request):
    if request.method == 'POST':
        try:
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')

            if not file1 or not file2:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both files are required'
                })

            # Save files temporarily
            file1_path = save_uploaded_file(file1)
            file2_path = save_uploaded_file(file2)

            # Create service instance
            service = FileComparerService()

            # Read files
            df1 = service.read_file(file1_path)
            df2 = service.read_file(file2_path)

            # Get suggestions
            suggestions = service.suggest_field_mappings(df1, df2)

            # Clean up temporary files
            os.remove(file1_path)
            os.remove(file2_path)

            return JsonResponse({
                'status': 'success',
                'suggestions': suggestions
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@csrf_exempt
def compare_view(request):
    if request.method == 'POST':
        try:
            start_time = time.time()
            
            # Get files from request
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')
            
            if not file1 or not file2:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both files are required'
                })

            # Save files
            file1_path = save_uploaded_file(file1)
            file2_path = save_uploaded_file(file2)
            
            # Get comparison fields
            fields = json.loads(request.POST.get('fields', '[]'))
            
            # Create comparison history record
            comparison = ComparisonHistory.objects.create(
                user=request.user,
                file1=file1.name,
                file2=file2.name,
                status='in_progress'
            )

            try:
                # Run comparison
                service = FileComparerService()
                result = service.compare_files(file1_path, file2_path, fields)
                
                # Update comparison record
                execution_time = time.time() - start_time
                comparison.status = 'completed'
                comparison.differences_found = len(result.get('differences', []))
                comparison.execution_time = execution_time
                comparison.save()

                # Update user stats
                user_stats, _ = UserStats.objects.get_or_create(
                    user=request.user,
                    defaults={'subscription_type': 'free', 'comparisons_limit': 100}
                )
                user_stats.total_comparisons += 1
                user_stats.comparisons_used += 1
                user_stats.total_time_saved += execution_time
                user_stats.save()

                return JsonResponse({
                    'status': 'success',
                    'result': result
                })

            except Exception as e:
                comparison.status = 'failed'
                comparison.save()
                raise e

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return render(request, 'comparer/compare.html')

@csrf_exempt
def manage_mappings_view(request):
    service = FileComparerService()
    mappings = service.get_field_mappings()
    return render(request, 'comparer/manage_mappings.html', {'mappings': mappings})

@csrf_exempt
def add_mapping_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service = FileComparerService()
            mapping = service.add_field_mapping_db(
                field_type=data['field_type'],
                variations=data['variations']
            )
            return JsonResponse({
                'status': 'success',
                'mapping_id': mapping.id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

@csrf_exempt
def update_mapping_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service = FileComparerService()
            service.update_field_mapping(
                mapping_id=data['mapping_id'],
                field_type=data['field_type'],
                variations=data['variations']
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

@require_http_methods(["POST"])
def delete_mapping_view(request):
    try:
        data = json.loads(request.body)
        mapping_id = data.get('mapping_id')
        
        if not isinstance(mapping_id, int):
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid mapping ID: {mapping_id}. Expected an integer.'
            })

        service = FileComparerService()
        service.delete_field_mapping(mapping_id)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Mapping deleted successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def debug_mappings(request):
    service = FileComparerService()
    mappings = service.get_field_mappings()
    return JsonResponse({
        'mappings': [
            {
                'id': m.id,
                'field_type': m.field_type,
                'variations': m.variations
            }
            for m in mappings
        ]
    })

def result_view(request):
    return render(request, 'comparer/result.html')

@require_http_methods(["POST"])
def download_results(request):
    try:
        data = json.loads(request.body)
        results = data.get('results')

        if not results:
            return JsonResponse({'error': 'No results provided'}, status=400)

        # Create a list to store all rows
        rows = []
        
        # Add summary information
        rows.append(['Comparison Summary'])
        rows.append(['File 1 Total Rows', results['total_rows']['file1']])
        rows.append(['File 2 Total Rows', results['total_rows']['file2']])
        rows.append([])  # Empty row for spacing

        # Process each field comparison
        for diff in results['differences']:
            # Add field header
            rows.append(['Field Type:', diff['field_type']])
            if 'error' in diff:
                rows.append(['Error:', diff['error']])
                rows.append([])  # Empty row for spacing
                continue

            rows.append(['File 1 Field:', diff['file1_field']])
            rows.append(['File 2 Field:', diff['file2_field']])
            rows.append(['Matching Values:', diff['matching_count']])
            rows.append(['Different Values:', diff['different_count']])
            rows.append([])  # Empty row for spacing
            
            # Add value comparison headers
            rows.append(['Status', 'File 1 Value', 'File 2 Value'])
            
            # Add matching values
            for value in diff.get('matching_values', []):
                rows.append(['Match', value, value])
            
            # Add values only in file 1
            for value in diff.get('only_in_file1', []):
                rows.append(['Only in File 1', value, 'Not Present'])
            
            # Add values only in file 2
            for value in diff.get('only_in_file2', []):
                rows.append(['Only in File 2', 'Not Present', value])
            
            rows.append([])  # Empty row for spacing

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'comparison_results_{timestamp}.csv'

        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False, header=False)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def dashboard_view(request):
    # Get active scheduled tasks
    scheduled_tasks = ScheduledTask.objects.filter(
        user=request.user,
        status='active'
    ).order_by('next_run')[:5]  # Show 5 most recent tasks

    # Get comparison history for recent activity
    recent_comparisons = ComparisonHistory.objects.filter(
        user=request.user
    ).order_by('-comparison_date')[:10]  # Show 10 most recent comparisons

    # Get user stats
    user_stats, created = UserStats.objects.get_or_create(
        user=request.user,
        defaults={
            'total_comparisons': 0,
            'comparisons_this_month': 0,
            'total_time_saved': 0,
            'subscription_type': 'Free'
        }
    )

    # Format recent activity
    recent_activity = []
    for comp in recent_comparisons:
        activity = {
            'date': comp.comparison_date,
            'type': 'Scheduled Task' if hasattr(comp, 'scheduled_task') else 'Manual Comparison',
            'files': [os.path.basename(comp.file1), os.path.basename(comp.file2)],
            'status': comp.status,
            'result_id': comp.id
        }
        recent_activity.append(activity)

    context = {
        'subscription': {
            'type': user_stats.subscription_type,
            'comparisons_used': user_stats.comparisons_this_month,
            'comparisons_limit': 100 if user_stats.subscription_type == 'Free' else 1000
        },
        'user_stats': {
            'total_comparisons': user_stats.total_comparisons,
            'monthly_comparisons': user_stats.comparisons_this_month,
            'time_saved': user_stats.total_time_saved
        },
        'recent_activity': recent_activity,
        'scheduled_tasks': scheduled_tasks
    }
    
    return render(request, 'comparer/dashboard.html', context)

@login_required
def scheduled_tasks_view(request):
    tasks = ScheduledTask.objects.all().order_by('-created_at')
    return render(request, 'comparer/scheduled_tasks.html', {'tasks': tasks})

@login_required
def create_task(request):
    if request.method == 'POST':
        try:
            # Get files from request
            source_file = request.FILES.get('source_file')
            target_file = request.FILES.get('target_file')
            
            if not source_file or not target_file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both source and target files are required'
                })

            # Save files to a secure location (e.g., media directory)
            source_path = handle_uploaded_file(source_file)
            target_path = handle_uploaded_file(target_file)

            # Get field mappings
            try:
                mappings = json.loads(request.POST.get('mappings', '[]'))
            except json.JSONDecodeError:
                mappings = []

            if not mappings:
                return JsonResponse({
                    'status': 'error',
                    'message': 'At least one field mapping is required'
                })

            # Create the scheduled task
            task = ScheduledTask.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                source_path=source_path,
                target_path=target_path,
                frequency=request.POST.get('frequency'),
                comparison_fields=mappings,  # Store the mappings in the comparison_fields
                status='active',
                user=request.user
            )

            return JsonResponse({
                'status': 'success',
                'task_id': task.id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

def handle_uploaded_file(f):
    # Create a unique filename to prevent collisions
    filename = f"{uuid.uuid4()}_{f.name}"
    
    # Ensure the media directory exists
    media_dir = os.path.join(settings.BASE_DIR, 'media', 'scheduled_tasks')
    os.makedirs(media_dir, exist_ok=True)
    
    # Save the file
    filepath = os.path.join(media_dir, filename)
    with open(filepath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    
    return filepath

@login_required
@require_http_methods(['POST'])
def update_task_status(request, task_id):
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['active', 'paused']:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid status'
            }, status=400)

        task = ScheduledTask.objects.get(id=task_id)
        task.status = new_status
        task.save()

        return JsonResponse({
            'status': 'success'
        })
    except ScheduledTask.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Task not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(['DELETE'])
def delete_task(request, task_id):
    try:
        # Get task and verify ownership
        task = ScheduledTask.objects.get(id=task_id, user=request.user)
        
        # Delete associated files if they exist
        if os.path.exists(task.source_path):
            os.remove(task.source_path)
        if os.path.exists(task.target_path):
            os.remove(task.target_path)
            
        # Delete the task
        task.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Task deleted successfully'
        })
    except ScheduledTask.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Task not found or you do not have permission to delete it'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def browse_files(request):
    """View to handle file browsing requests"""
    try:
        # Get the current directory from the request, default to user's home
        current_dir = request.GET.get('dir', '/home')
        
        # List all files and directories
        entries = []
        with os.scandir(current_dir) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir()
                    entries.append({
                        'name': entry.name,
                        'path': entry.path,
                        'is_dir': is_dir,
                        'size': entry.stat().st_size if not is_dir else None,
                        'modified': datetime.fromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                except (PermissionError, OSError):
                    continue

        # Sort entries: directories first, then files
        entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

        return JsonResponse({
            'status': 'success',
            'current_dir': current_dir,
            'parent_dir': os.path.dirname(current_dir) if current_dir != '/' else None,
            'entries': entries
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Successfully logged in!')
            return redirect('comparer:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'comparer/login.html')

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('comparer:dashboard')
        else:
            for msg in form.error_messages.values():
                messages.error(request, msg)
    return render(request, 'comparer/signup.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('comparer:login')
