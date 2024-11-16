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
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')
            field_mappings = json.loads(request.POST.get('fieldMappings', '{}'))

            if not file1 or not file2:
                return JsonResponse({'error': 'Both files are required'}, status=400)

            if not field_mappings:
                return JsonResponse({'error': 'At least one field mapping is required'}, status=400)

            # Save files temporarily
            file1_path = save_uploaded_file(file1)
            file2_path = save_uploaded_file(file2)

            # Create service instance and compare files
            service = FileComparerService()
            results = service.compare_files(file1_path, file2_path, field_mappings)

            # Clean up temporary files
            os.remove(file1_path)
            os.remove(file2_path)

            # Convert results to JSON for template
            results_json = json.dumps(results)
            
            return render(request, 'comparer/result.html', {
                'results': results,
                'results_json': results_json
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid field mappings format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

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
    # Mock data for demonstration - in production, this would come from your database
    context = {
        'user_stats': {
            'total_comparisons': 1234,
            'monthly_comparisons': 156,
            'accuracy_rate': 99.8,
            'time_saved': 127
        },
        'subscription': {
            'type': 'Premium',
            'comparisons_used': 75,
            'comparisons_limit': 100
        },
        'recent_activity': [
            {
                'date': datetime.now() - timedelta(hours=2),
                'type': 'Batch Comparison',
                'files': ['inventory_jan.csv', 'inventory_feb.csv'],
                'status': 'Completed'
            },
            {
                'date': datetime.now() - timedelta(days=1),
                'type': 'Scheduled Comparison',
                'files': ['sales_data_*.json'],
                'status': 'Scheduled'
            }
        ],
        'analytics': {
            'monthly_trends': [65, 59, 80, 81, 56, 55],
            'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        }
    }
    
    return render(request, 'comparer/dashboard.html', context)
