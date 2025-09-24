from django.contrib import admin
from .models import *

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'student_id', 'grade_level', 'is_active', 'created_by']
    list_filter = ['grade_level', 'is_active', 'enrollment_date']
    search_fields = ['name', 'student_id']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'due_date', 'created_by']
    list_filter = ['subject', 'due_date']
    search_fields = ['title']

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'progress_percentage', 'completed', 'last_updated']
    list_filter = ['subject', 'completed', 'last_updated']
    search_fields = ['student__name', 'subject__name']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_type', 'created_by', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['title', 'description']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'message']

@admin.register(VoiceInteraction)
class VoiceInteractionAdmin(admin.ModelAdmin):
    list_display = ['student', 'voice_command', 'success', 'timestamp']
    list_filter = ['success', 'timestamp']
    search_fields = ['student__name', 'voice_command']


@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ['student', 'author', 'created_at', 'is_important']
    list_filter = ['is_important', 'created_at', 'author']
    search_fields = ['student__name', 'note']