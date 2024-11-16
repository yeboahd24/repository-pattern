from django.urls import path
from . import views

app_name = 'comparer'

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main URLs
    path('', views.upload_view, name='upload'),
    path('compare/', views.compare_view, name='compare'),
    path('result/', views.result_view, name='result'),
    path('suggest-mappings/', views.suggest_mappings_view, name='suggest_mappings'),
    path('manage-mappings/', views.manage_mappings_view, name='manage_mappings'),
    path('add-mapping/', views.add_mapping_view, name='add_mapping'),
    path('update-mapping/', views.update_mapping_view, name='update_mapping'),
    path('delete-mapping/', views.delete_mapping_view, name='delete_mapping'),
    path('debug-mappings/', views.debug_mappings, name='debug_mappings'),
    path('download-results/', views.download_results, name='download_results'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    # Scheduled Tasks URLs
    path('scheduled-tasks/', views.scheduled_tasks_view, name='scheduled_tasks'),
    path('scheduled-task/create/', views.create_task, name='create_task'),
    path('scheduled-task/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('scheduled-task/<int:task_id>/', views.delete_task, name='delete_task'),
]
