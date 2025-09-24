from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.urls import reverse
from decimal import Decimal


class Student(models.Model):
    GRADE_LEVELS = [
        ('K', 'Kindergarten'),
        ('1', 'Grade 1'),
        ('2', 'Grade 2'),
        ('3', 'Grade 3'),
        ('4', 'Grade 4'),
        ('5', 'Grade 5'),
        ('6', 'Grade 6'),
        ('7', 'Grade 7'),
        ('8', 'Grade 8'),
        ('9', 'Grade 9'),
        ('10', 'Grade 10'),
        ('11', 'Grade 11'),
        ('12', 'Grade 12'),
    ]

    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, unique=True)
    grade_level = models.CharField(max_length=2, choices=GRADE_LEVELS)
    age = models.IntegerField(null=True, blank=True)
    enrollment_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Grade {self.grade_level})"

    def get_absolute_url(self):
        return reverse('student_detail', kwargs={'pk': self.pk})

    def get_overall_progress(self):
        """Calculate overall progress percentage"""
        progress_records = StudentProgress.objects.filter(student=self)
        if progress_records.exists():
            avg_progress = progress_records.aggregate(models.Avg('progress_percentage'))['progress_percentage__avg']
            return round(avg_progress or 0, 1)
        return 0

    def get_last_activity(self):
        """Get last activity timestamp"""
        progress = StudentProgress.objects.filter(student=self).order_by('-last_updated').first()
        if progress:
            return progress.last_updated
        return self.updated_at

    def get_voice_interactions_today(self):
        """Get today's voice interactions count"""
        today = timezone.now().date()
        return VoiceInteraction.objects.filter(
            student=self, 
            timestamp__date=today
        ).count()

    def get_progress_change(self):
        """Calculate progress change from last week"""
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        current_progress = self.get_overall_progress()
        
        # This would be more complex in a real implementation
        # For now, return a simulated change
        return round(current_progress * 0.05, 1)  # 5% of current progress


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# SINGLE Assignment model definition (remove the duplicate)
class Assignment(models.Model):
    ASSIGNMENT_TYPES = [
        ('standard', 'Standard Assignment'),
        ('voice', 'Voice-Activated Assignment'),
        ('interactive', 'Interactive Quiz'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Assignment details
    instructions = models.TextField(blank=True)
    max_score = models.IntegerField(default=100)
    estimated_duration = models.IntegerField(help_text="Estimated duration in minutes", default=30)
    
    # Voice-specific fields
    voice_prompt = models.TextField(blank=True, help_text="Voice prompt for voice-activated assignments")
    expected_responses = models.JSONField(blank=True, null=True, help_text="Expected voice responses")
    
    # Scheduling
    assigned_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    
    # Assignment targeting
    target_grade_levels = models.CharField(max_length=100, blank=True, help_text="Comma-separated grade levels")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.subject.name})"
    
    def get_completion_rate(self):
        """Calculate completion rate percentage"""
        total_assigned = self.assignmentstudent_set.count()
        if total_assigned == 0:
            return 0
        
        completed = self.assignmentstudent_set.filter(completed=True).count()
        return round((completed / total_assigned) * 100, 1)
    
    def get_overdue_count(self):
        """Count overdue assignments"""
        return self.assignmentstudent_set.filter(
            completed=False,
            assignment__due_date__lt=timezone.now()
        ).count()
    
    def get_avg_time_spent(self):
        """Calculate average time spent on assignment"""
        avg_time = self.assignmentstudent_set.filter(
            time_spent__gt=0
        ).aggregate(avg_time=models.Avg('time_spent'))['avg_time']
        return round(avg_time or 0, 1)
    
    def get_voice_interactions_count(self):
        """Count voice interactions for this assignment"""
        return VoiceInteraction.objects.filter(
            student__in=[as_obj.student for as_obj in self.assignmentstudent_set.all()],
            timestamp__gte=self.assigned_date
        ).count()
    
    def is_overdue(self):
        """Check if assignment is overdue"""
        return self.due_date < timezone.now() and self.status == 'active'
    
    def get_due_status(self):
        """Get due status for display"""
        if self.is_overdue():
            return 'overdue'
        
        days_until_due = (self.due_date - timezone.now()).days
        if days_until_due <= 3:
            return 'due_soon'
        return 'due_later'


class StudentProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_spent = models.IntegerField(default=0, help_text="Time spent in minutes")
    completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['student', 'assignment']
        verbose_name_plural = "Student Progress"

    def __str__(self):
        assignment_name = self.assignment.title if self.assignment else 'No Assignment'
        subject_name = self.subject.name if self.subject else 'No Subject'
        return f"{self.student.name} - {subject_name} - {self.progress_percentage}%"


class AssignmentStudent(models.Model):
    """Links students to assignments with progress tracking"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    
    # Progress tracking
    completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_spent = models.IntegerField(default=0, help_text="Time spent in minutes")
    
    # Voice interaction data
    voice_responses_count = models.IntegerField(default=0)
    last_voice_interaction = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    assigned_date = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"


class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ('assignment', 'Assignment Submitted'),
        ('progress', 'Progress Update'),
        ('message', 'New Message'),
        ('enrollment', 'New Enrollment'),
        ('system', 'System Activity'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='info-circle')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.activity_type} - {self.title}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    link = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}"


class VoiceInteraction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    voice_command = models.TextField()
    system_response = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.student.name} - {self.timestamp}"


class StudentNote(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_important = models.BooleanField(default=False)

    def __str__(self):
        return f"Note for {self.student.name} by {self.author.username}"


class LearningSession(models.Model):
    """Tracks individual learning sessions for analytics"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    topics_covered = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    @property
    def duration_hours(self):
        return round(self.duration_minutes / 60, 2)
    
    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.duration_minutes}min"


class Topic(models.Model):
    """Topics for tracking what students are learning"""
    name = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ])
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.subject.name})"


class TopicAttempt(models.Model):
    """Tracks student attempts on specific topics"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    attempt_date = models.DateTimeField(default=timezone.now)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.student.name} - {self.topic.name}"


class VoiceResponse(models.Model):
    """Detailed voice interaction tracking for analytics"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    voice_command = models.TextField()
    system_response = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    response_accuracy = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    clarification_needed = models.BooleanField(default=False)
    no_response = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.student.name} - {self.timestamp}"