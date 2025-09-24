from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),


    path('students/', views.students_view, name='students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:pk>/delete/', views.delete_student, name='delete_student'),
    path('students/<int:pk>/progress/', views.update_student_progress, name='update_progress'),
    path('students/<int:pk>/analytics/', views.student_analytics, name='student_analytics'),
    path('students/export/', views.export_students, name='export_students'),


    path('analytics/', views.analytics_view, name='analytics'),


    path('assignments/', views.assignments_view, name='assignments'),
    path('assignments/create/', views.create_assignment, name='create_assignment'),
    path('assignments/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:pk>/update-progress/', views.update_assignment_progress, name='update_assignment_progress'),


    path('schedule/', views.schedule_view, name='schedule'),
    path('reports/', views.reports_view, name='reports'),
    path('announcements/', views.announcements_view, name='announcements'),
    path('settings/', views.settings_view, name='settings'),
    path('help/', views.help_view, name='help'),
    path('activity-log/', views.activity_log_view, name='activity_log'),
    path('export-data/', views.export_data_view, name='export_data'),
    path('search/', views.dashboard, name='search'),  # Simplified search
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.custom_signup, name='signup'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
]