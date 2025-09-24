from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from .models import *
from datetime import datetime, timedelta
import random

from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.db.models import Max

@login_required
def dashboard(request):
    """Main dashboard view with real data only"""
    try:
        # Get basic statistics
        total_students = Student.objects.filter(created_by=request.user, is_active=True).count()
        
        # Calculate average progress from actual data
        progress_data = StudentProgress.objects.filter(
            student__created_by=request.user
        ).aggregate(
            avg_progress=Avg('progress_percentage'),
            total_records=Count('id')
        )
        average_progress = progress_data['avg_progress'] or 0
        total_progress_records = progress_data['total_records'] or 0
        
        # Calculate completed tasks (assignments marked as completed)
        completed_tasks = StudentProgress.objects.filter(
            student__created_by=request.user,
            completed=True
        ).count()
        
        # Real engagement rate based on activity
        # Count students with any progress records in the last 7 days
        one_week_ago = timezone.now() - timedelta(days=7)
        active_students_count = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=one_week_ago
        ).values('student').distinct().count()
        
        engagement_rate = 0
        if total_students > 0:
            engagement_rate = (active_students_count / total_students) * 100
        
        # Real subject progress data
        subjects = Subject.objects.all()
        subject_progress = []
        for subject in subjects:
            subject_avg = StudentProgress.objects.filter(
                student__created_by=request.user,
                subject=subject
            ).aggregate(avg=Avg('progress_percentage'))['avg'] or 0
            
            # Only include subjects that have data
            if StudentProgress.objects.filter(student__created_by=request.user, subject=subject).exists():
                subject_progress.append({
                    'name': subject.name,
                    'progress': round(subject_avg, 1)
                })
        
        # Real recent activities from ActivityLog
        recent_activities = ActivityLog.objects.filter(
            created_by=request.user
        ).select_related('student').order_by('-created_at')[:5]
        
        # Format activities for template
        formatted_activities = []
        for activity in recent_activities:
            if activity.student:
                message = f"{activity.student.name} - {activity.description}"
            else:
                message = activity.description
                
            formatted_activities.append({
                'type': activity.activity_type,
                'icon': activity.icon,
                'message': message,
                'timestamp': activity.created_at
            })
        
        # If no activities yet, show system message
        if not formatted_activities:
            formatted_activities.append({
                'type': 'system',
                'icon': 'info-circle',
                'message': 'Welcome to EduTrack Pro! Your activity log will appear here.',
                'timestamp': timezone.now()
            })
        
        # Real top performers based on actual progress
        top_performers = []
        
        # Always show students even if they have no progress data
        if total_students > 0:
            # First, try to get students with progress data
            students_with_progress = StudentProgress.objects.filter(
                student__created_by=request.user
            ).values(
                'student__id', 
                'student__name', 
                'student__grade_level'
            ).annotate(
                avg_progress=Avg('progress_percentage'),
                last_activity=Max('last_updated')
            ).order_by('-avg_progress')[:5]
            
            for data in students_with_progress:
                # Get most recent subject for this student
                latest_progress = StudentProgress.objects.filter(
                    student__id=data['student__id']
                ).order_by('-last_updated').first()
                
                current_subject = "No recent activity"
                if latest_progress and latest_progress.subject:
                    current_subject = latest_progress.subject.name
                
                top_performers.append({
                    'name': data['student__name'],
                    'grade_level': data['student__grade_level'],
                    'progress': round(data['avg_progress'] or 0, 1),
                    'current_subject': current_subject,
                    'last_activity': data['last_activity']
                })
            
            # If we have fewer than 5 students with progress, add students without progress data
            if len(top_performers) < 5:
                # Get students that don't have progress records yet
                students_without_progress = Student.objects.filter(
                    created_by=request.user, 
                    is_active=True
                ).exclude(
                    id__in=[s['student__id'] for s in students_with_progress]
                )[:5 - len(top_performers)]
                
                for student in students_without_progress:
                    top_performers.append({
                        'name': student.name,
                        'grade_level': student.grade_level,
                        'progress': 0.0,
                        'current_subject': "No progress data yet",
                        'last_activity': student.updated_at
                    })
            
            # If still no students (no progress data at all), show all students
            if not top_performers:
                all_students = Student.objects.filter(created_by=request.user, is_active=True)[:5]
                for student in all_students:
                    top_performers.append({
                        'name': student.name,
                        'grade_level': student.grade_level,
                        'progress': 0.0,
                        'current_subject': "No progress data yet",
                        'last_activity': student.updated_at
                    })
        
        # Real new students this week
        one_week_ago = timezone.now() - timedelta(days=7)
        new_students_this_week = Student.objects.filter(
            created_by=request.user,
            created_at__gte=one_week_ago,
            is_active=True
        ).count()
        
        # Real progress change (compare with last week)
        current_week_avg = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=one_week_ago
        ).aggregate(avg=Avg('progress_percentage'))['avg'] or 0
        
        two_weeks_ago = timezone.now() - timedelta(days=14)
        last_week_avg = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=two_weeks_ago,
            last_updated__lt=one_week_ago
        ).aggregate(avg=Avg('progress_percentage'))['avg'] or 0
        
        progress_change = 0
        if last_week_avg > 0:
            progress_change = round(((current_week_avg - last_week_avg) / last_week_avg) * 100, 1)
        elif current_week_avg > 0:
            progress_change = 100  # First week with data
        
        # Real new tasks completed today
        today = timezone.now().date()
        new_tasks_completed_today = StudentProgress.objects.filter(
            student__created_by=request.user,
            completed=True,
            completion_date__date=today
        ).count()
        
        # Real engagement change (compare active students with last week)
        two_weeks_ago = timezone.now() - timedelta(days=14)
        last_week_active = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=two_weeks_ago,
            last_updated__lt=one_week_ago
        ).values('student').distinct().count()
        
        engagement_change = 0
        if last_week_active > 0:
            engagement_change = round(((active_students_count - last_week_active) / last_week_active) * 100, 1)
        elif active_students_count > 0:
            engagement_change = 100
        
        engagement_change_class = 'positive' if engagement_change >= 0 else 'negative'
        
        # Unread notifications count
        unread_notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Calculate task completion rate
        total_assignments = Assignment.objects.filter(created_by=request.user).count()
        task_completion_rate = 0
        if total_assignments > 0 and total_students > 0:
            total_possible_completions = total_assignments * total_students
            if total_possible_completions > 0:
                task_completion_rate = (completed_tasks / total_possible_completions) * 100
        
        # Student progress percentage for visualization
        student_progress_percentage = min(100, (total_students / 50) * 100) if total_students > 0 else 0
        
        context = {
            'total_students': total_students,
            'average_progress': round(average_progress, 1),
            'completed_tasks': completed_tasks,
            'engagement_rate': round(engagement_rate, 1),
            'subject_progress': subject_progress,
            'recent_activities': formatted_activities,
            'top_performers': top_performers,
            'unread_notifications_count': unread_notifications_count,
            'student_progress_percentage': student_progress_percentage,
            'new_students_this_week': new_students_this_week,
            'progress_change': progress_change,
            'task_completion_rate': round(task_completion_rate, 1),
            'new_tasks_completed': new_tasks_completed_today,
            'engagement_change': engagement_change,
            'engagement_change_class': engagement_change_class,
            'total_progress_records': total_progress_records,
            'active_students_count': active_students_count,
        }
        
        # Debug output to console
        print(f"DEBUG: Total students: {total_students}")
        print(f"DEBUG: Top performers count: {len(top_performers)}")
        print(f"DEBUG: Context keys: {context.keys()}")
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        # Log the error but provide empty context
        print(f"Dashboard error: {e}")
        context = {
            'total_students': 0,
            'average_progress': 0,
            'completed_tasks': 0,
            'engagement_rate': 0,
            'subject_progress': [],
            'recent_activities': [{
                'type': 'system',
                'icon': 'info-circle',
                'message': 'System is initializing. Add students and progress data to see analytics.',
                'timestamp': timezone.now()
            }],
            'top_performers': [],
            'unread_notifications_count': 0,
            'student_progress_percentage': 0,
            'new_students_this_week': 0,
            'progress_change': 0,
            'task_completion_rate': 0,
            'new_tasks_completed': 0,
            'engagement_change': 0,
            'engagement_change_class': 'neutral',
            'total_progress_records': 0,
            'active_students_count': 0,
        }
        return render(request, 'dashboard.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Student, StudentProgress, VoiceInteraction, StudentNote
# from .forms import StudentForm  # We'll create this without forms.py

@login_required
def students_view(request):
    """Student management main view"""
    # Get filter parameters
    grade_filter = request.GET.get('grade', '')
    status_filter = request.GET.get('status', '')
    progress_filter = request.GET.get('progress', '')
    sort_by = request.GET.get('sort', 'name')
    search_query = request.GET.get('search', '')
    view_type = request.GET.get('view', 'grid')  # grid or table
    
    # Start with base queryset
    students = Student.objects.filter(created_by=request.user)
    
    # Apply filters
    if grade_filter and grade_filter != 'All Grades':
        students = students.filter(grade_level=grade_filter)
    
    if status_filter and status_filter != 'All Students':
        if status_filter == 'Active':
            students = students.filter(is_active=True)
        elif status_filter == 'Inactive':
            students = students.filter(is_active=False)
        elif status_filter == 'Needs Attention':
            # Students with progress < 50%
            low_progress_students = StudentProgress.objects.filter(
                progress_percentage__lt=50
            ).values_list('student_id', flat=True)
            students = students.filter(id__in=low_progress_students)
    
    # Apply search
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(student_id__icontains=search_query) |
            Q(grade_level__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'name':
        students = students.order_by('name')
    elif sort_by == 'name-desc':
        students = students.order_by('-name')
    elif sort_by == 'progress-high':
        # This would require more complex querying for actual implementation
        students = students.order_by('?')  # Placeholder
    elif sort_by == 'progress-low':
        students = students.order_by('?')  # Placeholder
    elif sort_by == 'recent':
        students = students.order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(students, 12)  # Show 12 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare student data with calculated fields
    student_data = []
    for student in page_obj:
        student_data.append({
            'object': student,
            'progress': student.get_overall_progress(),
            'last_activity': student.get_last_activity(),
            'voice_interactions_today': student.get_voice_interactions_today(),
            'progress_change': student.get_progress_change(),
        })
    
    context = {
        'students_data': student_data,
        'page_obj': page_obj,
        'grade_filter': grade_filter,
        'status_filter': status_filter,
        'progress_filter': progress_filter,
        'sort_by': sort_by,
        'search_query': search_query,
        'view_type': view_type,
        'total_students': students.count(),
        'active_students': students.filter(is_active=True).count(),
    }
    
    return render(request, 'students.html', context)

@login_required
def student_detail(request, pk):
    """Student detail view"""
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    
    # Get progress data
    progress_data = StudentProgress.objects.filter(student=student)
    voice_interactions = VoiceInteraction.objects.filter(student=student).order_by('-timestamp')[:10]
    notes = StudentNote.objects.filter(student=student).order_by('-created_at')
    
    context = {
        'student': student,
        'progress_data': progress_data,
        'voice_interactions': voice_interactions,
        'notes': notes,
        'overall_progress': student.get_overall_progress(),
    }
    
    return render(request, 'student_detail.html', context)

@login_required
def add_student(request):
    """Add new student view"""
    if request.method == 'POST':
        # Process form data
        name = request.POST.get('name', '').strip()
        student_id = request.POST.get('student_id', '').strip().upper()
        grade_level = request.POST.get('grade_level', '')
        age = request.POST.get('age', '')
        enrollment_date = request.POST.get('enrollment_date', '')
        is_active = request.POST.get('is_active') == 'on'
        notes = request.POST.get('notes', '').strip()
        
        # Validation
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters'
        
        if not student_id:
            errors['student_id'] = 'Student ID is required'
        elif len(student_id) < 3:
            errors['student_id'] = 'Student ID must be at least 3 characters'
        elif Student.objects.filter(student_id=student_id).exists():
            errors['student_id'] = 'Student ID already exists'
        
        if not grade_level:
            errors['grade_level'] = 'Grade level is required'
        
        if age:
            try:
                age_int = int(age)
                if age_int < 4 or age_int > 18:
                    errors['age'] = 'Age must be between 4 and 18'
            except ValueError:
                errors['age'] = 'Age must be a valid number'
        
        if enrollment_date:
            try:
                # Validate date format
                datetime.strptime(enrollment_date, '%Y-%m-%d')
            except ValueError:
                errors['enrollment_date'] = 'Invalid date format'
        
        if not errors:
            try:
                student = Student.objects.create(
                    name=name,
                    student_id=student_id,
                    grade_level=grade_level,
                    age=age or None,
                    enrollment_date=enrollment_date or timezone.now().date(),
                    is_active=is_active,
                    notes=notes,
                    created_by=request.user
                )
                
                # Create initial progress record
                StudentProgress.objects.create(
                    student=student,
                    progress_percentage=0,
                    time_spent=0
                )
                
                messages.success(request, f'Student "{name}" added successfully!')
                return redirect('students')
                
            except Exception as e:
                messages.error(request, f'Error adding student: {str(e)}')
        else:
            for field, error in errors.items():
                messages.error(request, f'{field.title()}: {error}')
    
    # For GET requests, pass the current POST data to repopulate form on error
    context = {
        'grade_choices': Student.GRADE_LEVELS,
    }
    
    return render(request, 'add_student.html', context)

@login_required
def edit_student(request, pk):
    """Edit student view"""
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        student_id = request.POST.get('student_id', '').strip()
        grade_level = request.POST.get('grade_level', '')
        age = request.POST.get('age', '')
        is_active = request.POST.get('is_active') == 'on'
        notes = request.POST.get('notes', '').strip()
        
        # Validation
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        if not student_id:
            errors['student_id'] = 'Student ID is required'
        elif Student.objects.filter(student_id=student_id).exclude(pk=student.pk).exists():
            errors['student_id'] = 'Student ID already exists'
        if not grade_level:
            errors['grade_level'] = 'Grade level is required'
        
        if not errors:
            try:
                student.name = name
                student.student_id = student_id
                student.grade_level = grade_level
                student.age = age or None
                student.is_active = is_active
                student.notes = notes
                student.save()
                
                messages.success(request, f'Student {name} updated successfully!')
                return redirect('students')
            except Exception as e:
                messages.error(request, f'Error updating student: {str(e)}')
        else:
            for error in errors.values():
                messages.error(request, error)
    
    context = {'student': student}
    return render(request, 'edit_student.html', context)

@login_required
def delete_student(request, pk):
    """Delete student view"""
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f'Student {student_name} deleted successfully!')
        return redirect('students')
    
    return render(request, 'confirm_delete.html', {'student': student})

@login_required
def update_student_progress(request, pk):
    """Update student progress via AJAX"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        student = get_object_or_404(Student, pk=pk, created_by=request.user)
        progress_percentage = request.POST.get('progress_percentage')
        
        try:
            progress_percentage = float(progress_percentage)
            if 0 <= progress_percentage <= 100:
                # Update or create progress record
                progress, created = StudentProgress.objects.get_or_create(
                    student=student,
                    defaults={'progress_percentage': progress_percentage}
                )
                if not created:
                    progress.progress_percentage = progress_percentage
                    progress.save()
                
                return JsonResponse({
                    'success': True,
                    'progress': progress_percentage,
                    'message': 'Progress updated successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Progress must be between 0 and 100'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid progress value'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def export_students(request):
    """Export students data"""
    # This would implement CSV/Excel export functionality
    # For now, just redirect back
    messages.info(request, 'Export functionality will be implemented soon!')
    return redirect('students')

@login_required
def student_analytics(request, pk):
    """Student analytics view"""
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    
    # Get analytics data
    progress_history = StudentProgress.objects.filter(
        student=student
    ).order_by('last_updated')
    
    voice_stats = VoiceInteraction.objects.filter(
        student=student
    ).aggregate(
        total_interactions=Count('id'),
        successful_interactions=Count('id', filter=Q(success=True)),
        avg_confidence=Avg('confidence_score')
    )
    
    context = {
        'student': student,
        'progress_history': progress_history,
        'voice_stats': voice_stats,
    }
    
    return render(request, 'student_analytics.html', context)

# Add this to your views.py
@login_required
def analytics_view(request):
    """Comprehensive analytics dashboard view with REAL data"""
    try:
        # Date range handling
        date_preset = request.GET.get('preset', 'last_30_days')
        
        # Calculate date range
        end_date = timezone.now()
        if date_preset == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_preset == 'last_7_days':
            start_date = end_date - timedelta(days=7)
        elif date_preset == 'last_30_days':
            start_date = end_date - timedelta(days=30)
        elif date_preset == 'this_semester':
            current_month = end_date.month
            if current_month >= 8:  # Fall semester
                start_date = end_date.replace(month=8, day=1)
            else:  # Spring semester
                start_date = end_date.replace(month=1, day=1)
        else:
            start_date = end_date - timedelta(days=30)
        
        # REAL DATA: Get basic statistics for the date range
        # Total learning time from StudentProgress (time_spent in minutes)
        total_learning_time = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=start_date
        ).aggregate(total_time=Sum('time_spent'))['total_time'] or 0
        
        total_learning_hours = round(total_learning_time / 60, 1)
        
        # REAL DATA: Topics attempted (using assignments as proxy for topics)
        topics_attempted = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=start_date
        ).count()
        
        # REAL DATA: Voice responses
        voice_responses = VoiceInteraction.objects.filter(
            student__created_by=request.user,
            timestamp__gte=start_date
        ).count()
        
        # REAL DATA: Average accuracy from StudentProgress (progress_percentage)
        avg_accuracy_data = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=start_date
        ).aggregate(avg_acc=Avg('progress_percentage'))
        avg_accuracy = round(avg_accuracy_data['avg_acc'] or 0, 1)
        
        # REAL DATA: Voice response analysis
        total_voice = VoiceInteraction.objects.filter(
            student__created_by=request.user,
            timestamp__gte=start_date
        ).count()
        
        understood = VoiceInteraction.objects.filter(
            student__created_by=request.user,
            timestamp__gte=start_date,
            success=True,
            confidence_score__gte=0.7
        ).count()
        
        # For clarification needed and no response, we'll use confidence score as proxy
        # since we don't have those specific fields in VoiceInteraction
        clarification_needed = VoiceInteraction.objects.filter(
            student__created_by=request.user,
            timestamp__gte=start_date,
            success=True,
            confidence_score__lt=0.7,
            confidence_score__gte=0.4
        ).count()
        
        not_understood = VoiceInteraction.objects.filter(
            student__created_by=request.user,
            timestamp__gte=start_date,
            success=False
        ).count()
        
        no_response = 0  # We don't have this data, so set to 0
        
        # Calculate percentages for voice analysis
        understood_pct = round((understood / total_voice * 100), 1) if total_voice > 0 else 0
        clarification_pct = round((clarification_needed / total_voice * 100), 1) if total_voice > 0 else 0
        not_understood_pct = round((not_understood / total_voice * 100), 1) if total_voice > 0 else 0
        no_response_pct = round((no_response / total_voice * 100), 1) if total_voice > 0 else 0
        
        # REAL DATA: Learning time distribution by subject (last 4 weeks)
        weekly_data = []
        subjects = Subject.objects.all()
        
        # Get data for the last 4 weeks
        for i in range(4):
            week_start = end_date - timedelta(weeks=(4-i))
            week_end = week_start + timedelta(weeks=1)
            
            week_data = {'week': f'Week {i+1}'}
            
            for subject in subjects:
                # Calculate time spent per subject per week
                weekly_time = StudentProgress.objects.filter(
                    student__created_by=request.user,
                    subject=subject,
                    last_updated__gte=week_start,
                    last_updated__lt=week_end
                ).aggregate(total_time=Sum('time_spent'))['total_time'] or 0
                
                week_data[subject.name] = round(weekly_time / 60, 1)
            
            weekly_data.append(week_data)
        
        # REAL DATA: Top "topics" attempted (using assignments as topics)
        top_topics = StudentProgress.objects.filter(
            student__created_by=request.user,
            last_updated__gte=start_date
        ).values(
            'assignment__title', 'subject__name'
        ).annotate(
            attempts=Count('id')
        ).order_by('-attempts')[:10]
        
        # REAL DATA: Accuracy by subject
        subject_accuracy = []
        for subject in subjects:
            accuracy_data = StudentProgress.objects.filter(
                student__created_by=request.user,
                subject=subject,
                last_updated__gte=start_date
            ).aggregate(avg_acc=Avg('progress_percentage'))
            
            accuracy = accuracy_data['avg_acc'] or 0
            if accuracy > 0:  # Only include subjects with data
                subject_accuracy.append({
                    'subject': subject.name,
                    'accuracy': round(accuracy, 1)
                })
        
        # REAL DATA: Student activity details
        student_activity_data = Student.objects.filter(
            created_by=request.user,
            is_active=True
        )
        
        # Format student activity data with REAL calculations
        formatted_students = []
        for student in student_activity_data:
            # Calculate real time spent for this student
            student_time = StudentProgress.objects.filter(
                student=student,
                last_updated__gte=start_date
            ).aggregate(total_time=Sum('time_spent'))['total_time'] or 0
            
            hours = int(student_time // 60)
            minutes = int(student_time % 60)
            time_spent_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            # Count real topics/assignments for this student
            topics_count = StudentProgress.objects.filter(
                student=student,
                last_updated__gte=start_date
            ).count()
            
            # Count real voice responses for this student
            responses_count = VoiceInteraction.objects.filter(
                student=student,
                timestamp__gte=start_date
            ).count()
            
            # Calculate real accuracy for this student
            student_accuracy = StudentProgress.objects.filter(
                student=student,
                last_updated__gte=start_date
            ).aggregate(avg_acc=Avg('progress_percentage'))['avg_acc'] or 0
            
            formatted_students.append({
                'name': student.name,
                'time_spent': time_spent_str,
                'topics': topics_count,
                'responses': responses_count,
                'accuracy': f"{round(student_accuracy, 1)}%"
            })
        
        # Sort students by time spent (descending) and limit to top 10
        formatted_students.sort(key=lambda x: 
            int(x['time_spent'].split('h')[0]) if 'h' in x['time_spent'] else 0, 
            reverse=True
        )
        formatted_students = formatted_students[:10]
        
        context = {
            'total_learning_hours': total_learning_hours,
            'topics_attempted': topics_attempted,
            'voice_responses': voice_responses,
            'average_accuracy': avg_accuracy,
            'weekly_data': weekly_data,
            'top_topics': list(top_topics),
            'subject_accuracy': subject_accuracy,
            'student_activity': formatted_students,
            'voice_analysis': {
                'understood': understood_pct,
                'clarification_needed': clarification_pct,
                'not_understood': not_understood_pct,
                'no_response': no_response_pct,
            },
            'date_preset': date_preset,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }
        
        # Debug output
        print(f"DEBUG Analytics: Total hours: {total_learning_hours}")
        print(f"DEBUG Analytics: Topics attempted: {topics_attempted}")
        print(f"DEBUG Analytics: Student activity count: {len(formatted_students)}")
        
        return render(request, 'analytics.html', context)
        
    except Exception as e:
        print(f"Analytics error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty/zero data on error
        context = {
            'total_learning_hours': 0,
            'topics_attempted': 0,
            'voice_responses': 0,
            'average_accuracy': 0,
            'weekly_data': [],
            'top_topics': [],
            'subject_accuracy': [],
            'student_activity': [],
            'voice_analysis': {
                'understood': 0,
                'clarification_needed': 0,
                'not_understood': 0,
                'no_response': 0,
            },
            'date_preset': 'last_30_days',
            'start_date': (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': timezone.now().strftime('%Y-%m-%d'),
        }
        return render(request, 'analytics.html', context)

# Add to your views.py

@login_required
def assignments_view(request):
    """Assignments management main view"""
    try:
        # Get filter parameters
        subject_filter = request.GET.get('subject', '')
        status_filter = request.GET.get('status', '')
        grade_filter = request.GET.get('grade', '')
        sort_by = request.GET.get('sort', 'due_date')
        search_query = request.GET.get('search', '')
        assignment_type = request.GET.get('type', '')
        
        # Start with base queryset
        assignments = Assignment.objects.filter(created_by=request.user)
        
        # Apply filters
        if subject_filter and subject_filter != 'All Subjects':
            assignments = assignments.filter(subject__name=subject_filter)
        
        if status_filter and status_filter != 'All Statuses':
            if status_filter == 'Active':
                assignments = assignments.filter(status='active')
            elif status_filter == 'Completed':
                assignments = assignments.filter(status='completed')
            elif status_filter == 'Pending':
                assignments = assignments.filter(status='active', due_date__gte=timezone.now())
            elif status_filter == 'Overdue':
                assignments = assignments.filter(status='active', due_date__lt=timezone.now())
        
        if grade_filter and grade_filter != 'All Grades':
            assignments = assignments.filter(target_grade_levels__icontains=grade_filter)
        
        if assignment_type and assignment_type != 'all':
            assignments = assignments.filter(assignment_type=assignment_type)
        
        # Apply search
        if search_query:
            assignments = assignments.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(subject__name__icontains=search_query)
            )
        
        # Apply sorting
        if sort_by == 'due_date':
            assignments = assignments.order_by('due_date')
        elif sort_by == 'due_date_desc':
            assignments = assignments.order_by('-due_date')
        elif sort_by == 'title':
            assignments = assignments.order_by('title')
        elif sort_by == 'completion_rate':
            # This would require annotation for proper sorting
            assignments = assignments.order_by('title')  # Placeholder
        
        # Get assignment statistics
        total_assignments = assignments.count()
        completed_assignments = assignments.filter(status='completed').count()
        active_assignments = assignments.filter(status='active', due_date__gte=timezone.now()).count()
        overdue_assignments = assignments.filter(status='active', due_date__lt=timezone.now()).count()
        
        # Get voice assignments separately
        voice_assignments = assignments.filter(assignment_type='voice')[:3]
        
        # Prepare assignment data with calculated fields
        assignment_data = []
        for assignment in assignments:
            assignment_data.append({
                'object': assignment,
                'completion_rate': assignment.get_completion_rate(),
                'overdue_count': assignment.get_overdue_count(),
                'avg_time_spent': assignment.get_avg_time_spent(),
                'voice_interactions': assignment.get_voice_interactions_count(),
                'due_status': assignment.get_due_status(),
                'assigned_students_count': assignment.assignmentstudent_set.count(),
            })
        
        # Get available subjects for filter
        subjects = Subject.objects.all()
        
        context = {
            'assignments_data': assignment_data,
            'voice_assignments': voice_assignments,
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'active_assignments': active_assignments,
            'overdue_assignments': overdue_assignments,
            'subjects': subjects,
            'subject_filter': subject_filter,
            'status_filter': status_filter,
            'grade_filter': grade_filter,
            'sort_by': sort_by,
            'search_query': search_query,
            'assignment_type': assignment_type,
        }
        
        return render(request, 'assignments.html', context)
        
    except Exception as e:
        print(f"Assignments view error: {e}")
        # Return empty context on error
        context = {
            'assignments_data': [],
            'voice_assignments': [],
            'total_assignments': 0,
            'completed_assignments': 0,
            'active_assignments': 0,
            'overdue_assignments': 0,
            'subjects': [],
            'subject_filter': '',
            'status_filter': '',
            'grade_filter': '',
            'sort_by': 'due_date',
            'search_query': '',
            'assignment_type': '',
        }
        return render(request, 'assignments.html', context)

@login_required
def create_assignment(request):
    """Create new assignment view"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            subject_id = request.POST.get('subject')
            assignment_type = request.POST.get('assignment_type', 'standard')
            instructions = request.POST.get('instructions', '').strip()
            max_score = request.POST.get('max_score', 100)
            estimated_duration = request.POST.get('estimated_duration', 30)
            due_date = request.POST.get('due_date')
            target_grade_levels = request.POST.get('target_grade_levels', '')
            
            # Voice-specific fields
            voice_prompt = request.POST.get('voice_prompt', '').strip()
            expected_responses = request.POST.get('expected_responses', '').strip()
            
            # Validation
            errors = {}
            if not title:
                errors['title'] = 'Title is required'
            if not subject_id:
                errors['subject'] = 'Subject is required'
            if not instructions:
                errors['instructions'] = 'Instructions are required'
            if not due_date:
                errors['due_date'] = 'Due date is required'
            
            if not errors:
                subject = Subject.objects.get(id=subject_id)
                assignment = Assignment.objects.create(
                    title=title,
                    description=description,
                    subject=subject,
                    assignment_type=assignment_type,
                    instructions=instructions,
                    max_score=int(max_score),
                    estimated_duration=int(estimated_duration),
                    due_date=due_date,
                    target_grade_levels=target_grade_levels,
                    voice_prompt=voice_prompt,
                    created_by=request.user,
                    status='active'
                )
                
                # Handle expected responses for voice assignments
                if assignment_type == 'voice' and expected_responses:
                    # Convert text responses to JSON format
                    responses_list = [resp.strip() for resp in expected_responses.split('\n') if resp.strip()]
                    assignment.expected_responses = responses_list
                    assignment.save()
                
                messages.success(request, f'Assignment "{title}" created successfully!')
                return redirect('assignments')
            else:
                for field, error in errors.items():
                    messages.error(request, f'{field.title()}: {error}')
                    
        except Exception as e:
            messages.error(request, f'Error creating assignment: {str(e)}')
    
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
    }
    return render(request, 'create_assignment.html', context)

@login_required
def assignment_detail(request, pk):
    """Assignment detail view"""
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)
    
    # Get assignment students with progress
    assignment_students = AssignmentStudent.objects.filter(assignment=assignment).select_related('student')
    
    # Get voice interactions for this assignment
    voice_interactions = VoiceInteraction.objects.filter(
        student__in=assignment.assigned_students.all()
    ).order_by('-timestamp')[:20]
    
    context = {
        'assignment': assignment,
        'assignment_students': assignment_students,
        'voice_interactions': voice_interactions,
        'completion_rate': assignment.get_completion_rate(),
        'overdue_count': assignment.get_overdue_count(),
        'avg_time_spent': assignment.get_avg_time_spent(),
    }
    
    return render(request, 'assignment_detail.html', context)

@login_required
def update_assignment_progress(request, pk):
    """Update assignment progress via AJAX"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user)
        student_id = request.POST.get('student_id')
        completed = request.POST.get('completed') == 'true'
        score = request.POST.get('score')
        time_spent = request.POST.get('time_spent')
        
        try:
            student = Student.objects.get(id=student_id, created_by=request.user)
            assignment_student, created = AssignmentStudent.objects.get_or_create(
                assignment=assignment,
                student=student
            )
            
            assignment_student.completed = completed
            if completed:
                assignment_student.completion_date = timezone.now()
            
            if score:
                assignment_student.score = Decimal(score)
            
            if time_spent:
                assignment_student.time_spent = int(time_spent)
            
            assignment_student.save()
            
            return JsonResponse({
                'success': True,
                'completion_rate': assignment.get_completion_rate(),
                'message': 'Progress updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def schedule_view(request):
    """Schedule view"""
    return render(request, 'schedule.html')

@login_required
def reports_view(request):
    """Reports view"""
    return render(request, 'reports.html')

@login_required
def announcements_view(request):
    """Announcements view"""
    return render(request, 'announcements.html')

@login_required
def settings_view(request):
    """Settings view"""
    return render(request, 'settings.html')

@login_required
def help_view(request):
    """Help view"""
    return render(request, 'help.html')

@login_required
def add_student_view(request):
    """Add student view"""
    return render(request, 'add_student.html')

@login_required
def activity_log_view(request):
    """Activity log view"""
    activities = ActivityLog.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'activity_log.html', {'activities': activities})

@login_required
def export_data_view(request):
    """Export data view"""
    # This would implement data export functionality
    return redirect('dashboard')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.utils.html import escape
import re

@require_http_methods(["GET", "POST"])
@csrf_protect
def custom_login(request):
    """Custom login view without using Django forms"""
    
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Initialize variables
    error_message = None
    username_error = None
    password_error = None
    username_value = ''
    
    if request.method == 'POST':
        # Get and sanitize input data
        username = escape(request.POST.get('username', '').strip())
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        
        # Store username for re-display
        username_value = username
        
        # Validation
        if not username:
            username_error = 'Please enter your email or username'
        
        if not password:
            password_error = 'Please enter your password'
        
        # If no validation errors, attempt authentication
        if not username_error and not password_error:
            # Check if input is email or username
            if '@' in username and '.' in username:
                # Try to get user by email
                try:
                    user_obj = User.objects.get(email=username)
                    username = user_obj.username
                except User.DoesNotExist:
                    error_message = 'No account found with this email address'
            else:
                # Input is username
                if not User.objects.filter(username=username).exists():
                    error_message = 'No account found with this username'
            
            # If no error yet, attempt authentication
            if not error_message:
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    if user.is_active:
                        # Login the user
                        login(request, user)
                        
                        # Handle remember me functionality
                        if not remember_me:
                            request.session.set_expiry(0)  # Session expires when browser closes
                        else:
                            request.session.set_expiry(1209600)  # 2 weeks
                        
                        # Store login activity (you can extend this with your ActivityLog model)
                        messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                        
                        # Redirect to next page or dashboard
                        next_url = request.GET.get('next', 'dashboard')
                        return redirect(next_url)
                    else:
                        error_message = 'This account has been deactivated'
                else:
                    error_message = 'Invalid password. Please try again.'
        
        # If there's an error message, add it to messages framework
        if error_message:
            messages.error(request, error_message)
    
    # For GET requests or failed POST requests
    context = {
        'error_message': error_message,
        'username_error': username_error,
        'password_error': password_error,
        'username_value': username_value,
    }
    
    return render(request, 'login.html', context)

def custom_logout(request):
    """Custom logout view"""
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')

@require_http_methods(["GET", "POST"])
@csrf_protect
def custom_signup(request):
    """Custom signup view without using Django forms"""
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    error_message = None
    field_errors = {}
    form_data = {}
    
    if request.method == 'POST':
        # Get form data
        first_name = escape(request.POST.get('first_name', '').strip())
        last_name = escape(request.POST.get('last_name', '').strip())
        email = escape(request.POST.get('email', '').strip().lower())
        username = escape(request.POST.get('username', '').strip())
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        agree_terms = request.POST.get('agree_terms') == 'on'
        
        # Store form data for re-display
        form_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'username': username,
        }
        
        # Validation
        if not first_name:
            field_errors['first_name'] = 'First name is required'
        elif len(first_name) < 2:
            field_errors['first_name'] = 'First name must be at least 2 characters'
        
        if not last_name:
            field_errors['last_name'] = 'Last name is required'
        elif len(last_name) < 2:
            field_errors['last_name'] = 'Last name must be at least 2 characters'
        
        if not email:
            field_errors['email'] = 'Email address is required'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            field_errors['email'] = 'Please enter a valid email address'
        elif User.objects.filter(email=email).exists():
            field_errors['email'] = 'An account with this email already exists'
        
        if not username:
            field_errors['username'] = 'Username is required'
        elif len(username) < 3:
            field_errors['username'] = 'Username must be at least 3 characters'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            field_errors['username'] = 'Username can only contain letters, numbers, and underscores'
        elif User.objects.filter(username=username).exists():
            field_errors['username'] = 'This username is already taken'
        
        if not password:
            field_errors['password'] = 'Password is required'
        elif len(password) < 8:
            field_errors['password'] = 'Password must be at least 8 characters'
        elif not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'[0-9]', password):
            field_errors['password'] = 'Password must contain uppercase, lowercase letters and numbers'
        
        if password != confirm_password:
            field_errors['confirm_password'] = 'Passwords do not match'
        
        if not agree_terms:
            field_errors['agree_terms'] = 'You must agree to the terms and conditions'
        
        # If no validation errors, create user
        if not field_errors:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Log the user in
                login(request, user)
                messages.success(request, f'Welcome to EduTrack Pro, {first_name}! Your account has been created successfully.')
                return redirect('dashboard')
                
            except Exception as e:
                error_message = 'An error occurred during registration. Please try again.'
                messages.error(request, error_message)
        else:
            error_message = 'Please correct the errors below.'
            if error_message:
                messages.error(request, error_message)
    
    context = {
        'error_message': error_message,
        'field_errors': field_errors,
        'form_data': form_data,
    }
    
    return render(request, 'signup.html', context)

def password_reset_request(request):
    """Password reset request view"""
    messages.info(request, 'Password reset functionality would be implemented here.')
    return redirect('login')