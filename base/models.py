from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.urls import reverse
from decimal import Decimal
from django.db import models
from django.utils import timezone
import hashlib
import json
from .blockchain import blockchain_service

class BlockchainRecord(models.Model):
    TRANSACTION_TYPES = [
        ('progress', 'Progress Update'),
        ('profile', 'Profile Change'),
        ('achievement', 'Achievement Earned'),
        ('assignment', 'Assignment Completion'),
        ('voice', 'Voice Interaction'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    transaction_hash = models.CharField(max_length=66, unique=True)  # Ethereum hash length
    block_number = models.IntegerField()
    data_hash = models.CharField(max_length=64)
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    gas_used = models.IntegerField(null=True, blank=True)
    contract_used = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['student', 'transaction_type']),
            models.Index(fields=['transaction_hash']),
            models.Index(fields=['block_number']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.transaction_type} - {self.transaction_hash[:16]}"
    
    @classmethod
    def create_from_blockchain_result(cls, student, transaction_type, result, data_hash, metadata):
        """Create record from blockchain transaction result"""
        return cls.objects.create(
            student=student,
            transaction_type=transaction_type,
            transaction_hash=result['transaction_hash'],
            block_number=result['block_number'],
            data_hash=data_hash,
            metadata=metadata,
            gas_used=result.get('gas_used'),
            contract_used=result.get('contract_used', False)
        )


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
    user_account = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='student_profile'
    )
    can_login = models.BooleanField(default=False)
    login_enabled_date = models.DateTimeField(null=True, blank=True)
    blockchain_id = models.CharField(max_length=64, unique=True, null=True)
    profile_hash = models.CharField(max_length=64, null=True)
    last_blockchain_update = models.DateTimeField(null=True, blank=True)
    blockchain_verified = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Generate blockchain ID if not exists
        if not self.blockchain_id:
            self.blockchain_id = self.generate_blockchain_id()
        
        # Update profile hash
        self.update_profile_hash()
        
        super().save(*args, **kwargs)
        
        # Record on blockchain if significant changes
        if self.should_record_on_blockchain():
            self.record_on_blockchain('profile_update')
    
    def generate_blockchain_id(self):
        """Generate unique blockchain ID"""
        base_string = f"{self.student_id}{self.name}{timezone.now().timestamp()}"
        return hashlib.sha256(base_string.encode()).hexdigest()
    
    def update_profile_hash(self):
        """Calculate profile data hash"""
        profile_data = {
            'name': self.name,
            'student_id': self.student_id,
            'grade_level': self.grade_level,
            'age': self.age,
            'is_active': self.is_active,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
        }
        self.profile_hash = self.calculate_hash(profile_data)
    
    def should_record_on_blockchain(self):
        """Determine if profile should be recorded on blockchain"""
        if not self.pk:  # New instance
            return True
        
        try:
            old = Student.objects.get(pk=self.pk)
            significant_fields = ['name', 'student_id', 'grade_level', 'is_active']
            return any(getattr(self, field) != getattr(old, field) for field in significant_fields)
        except Student.DoesNotExist:
            return True
    
    def record_on_blockchain(self, action_type):
        """Record student data on real blockchain"""
        profile_data = {
            'student_id': self.student_id,
            'name': self.name,
            'grade_level': self.grade_level,
            'action': action_type,
            'timestamp': timezone.now().isoformat(),
        }
        
        result = blockchain_service.record_student_progress(
            self.blockchain_id,
            profile_data
        )
        
        if result['success']:
            # Create blockchain record
            BlockchainRecord.create_from_blockchain_result(
                student=self,
                transaction_type='profile',
                result=result,
                data_hash=self.profile_hash,
                metadata=profile_data
            )
            
            self.last_blockchain_update = timezone.now()
            self.blockchain_verified = True
            self.save(update_fields=['last_blockchain_update', 'blockchain_verified'])
            
            return True
        else:
            print(f"Failed to record on blockchain: {result.get('error')}")
            return False
    
    def verify_on_blockchain(self):
        """Verify student data on blockchain"""
        profile_data = {
            'student_id': self.student_id,
            'name': self.name,
            'grade_level': self.grade_level,
        }
        
        return blockchain_service.verify_progress(
            self.blockchain_id,
            profile_data
        )
    
    @staticmethod
    def calculate_hash(data):
        """Calculate SHA-256 hash of data"""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def create_user_account(self, password=None):
        """Create a user account for this student"""
        if self.user_account:
            return self.user_account
            
        # Generate username from student ID
        username = f"student_{self.student_id.lower()}"
        
        # Generate default password if not provided
        if not password:
            password = f"{self.student_id.lower()}_default123"
        
        # Create user account
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=self.name.split()[0] if self.name else '',
            last_name=' '.join(self.name.split()[1:]) if self.name else '',
            email=f"{username}@edutrack.com",  # Placeholder email
            is_staff=False,
            is_superuser=False
        )
        
        self.user_account = user
        self.can_login = True
        self.login_enabled_date = timezone.now()
        self.save()
        
        return user

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
    blockchain_record = models.ForeignKey(
        BlockchainRecord, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    progress_hash = models.CharField(max_length=64, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Calculate progress hash before saving
        self.update_progress_hash()
        
        super().save(*args, **kwargs)
        
        # Record significant progress updates on blockchain
        if self.progress_percentage > 0 and (not self.blockchain_record or self.progress_percentage % 25 == 0):
            self.record_progress_on_blockchain()
    
    def update_progress_hash(self):
        """Calculate hash of progress data for integrity verification"""
        progress_data = {
            'student_id': self.student.blockchain_id,
            'subject': self.subject.name if self.subject else None,
            'assignment': self.assignment.title if self.assignment else None,
            'score': float(self.score) if self.score else None,
            'progress_percentage': float(self.progress_percentage),
            'completed': self.completed,
            'time_spent': self.time_spent,
        }
        progress_json = json.dumps(progress_data, sort_keys=True)
        self.progress_hash = hashlib.sha256(progress_json.encode()).hexdigest()
    
    def record_progress_on_blockchain(self):
        """Record student progress on blockchain"""
        data_hash = self.progress_hash
        metadata = {
            'progress_id': self.id,
            'subject': self.subject.name if self.subject else 'General',
            'milestone': f"{self.progress_percentage}% completion",
        }
        
        # Add to blockchain
        block_index = blockchain.new_transaction(
            student_id=self.student.blockchain_id,
            action_type='progress_update',
            data_hash=data_hash,
            metadata=metadata
        )
        
        # Mine the block
        last_block = blockchain.last_block
        proof = blockchain.proof_of_work(last_block['proof'])
        blockchain.new_block(proof)
        
        # Store blockchain record
        blockchain_record = BlockchainRecord.objects.create(
            student=self.student,
            transaction_type='progress',
            block_index=block_index,
            transaction_hash=blockchain.hash(blockchain.last_block),
            data_hash=data_hash,
            metadata=metadata
        )
        
        self.blockchain_record = blockchain_record
        self.save(update_fields=['blockchain_record'])

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
    blockchain_record = models.ForeignKey(
            BlockchainRecord, 
            on_delete=models.SET_NULL, 
            null=True, 
            blank=True
        )
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Record significant voice interactions on blockchain
        if not self.blockchain_record and self.confidence_score > 0.8:
            self.record_voice_interaction_on_blockchain()
    
    def record_voice_interaction_on_blockchain(self):
        """Record significant voice interaction on blockchain"""
        interaction_data = {
            'student_id': self.student.blockchain_id,
            'command_length': len(self.voice_command),
            'success': self.success,
            'confidence': float(self.confidence_score),
            'timestamp': self.timestamp.isoformat(),
        }
        data_hash = hashlib.sha256(json.dumps(interaction_data, sort_keys=True).encode()).hexdigest()
        
        metadata = {
            'interaction_id': self.id,
            'command_preview': self.voice_command[:50] + '...' if len(self.voice_command) > 50 else self.voice_command,
            'success': self.success,
        }
        
        # Add to blockchain
        block_index = blockchain.new_transaction(
            student_id=self.student.blockchain_id,
            action_type='voice',
            data_hash=data_hash,
            metadata=metadata
        )
        
        # Mine the block
        last_block = blockchain.last_block
        proof = blockchain.proof_of_work(last_block['proof'])
        blockchain.new_block(proof)
        
        # Store blockchain record
        blockchain_record = BlockchainRecord.objects.create(
            student=self.student,
            transaction_type='voice',
            block_index=block_index,
            transaction_hash=blockchain.hash(blockchain.last_block),
            data_hash=data_hash,
            metadata=metadata
        )
        
        self.blockchain_record = blockchain_record
        self.save(update_fields=['blockchain_record'])
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

# Add to models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class StudentGoal(models.Model):
    GOAL_TYPES = [
        ('assignment', 'Complete Assignment'),
        ('subject', 'Master Subject'),
        ('skill', 'Learn Skill'),
        ('time', 'Time Spent'),
        ('streak', 'Learning Streak'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def progress_percentage(self):
        if self.target_value == 0:
            return 0
        return min(100, float(self.current_value) / float(self.target_value) * 100)
    
    def __str__(self):
        return f"{self.student.name} - {self.title}"

class Achievement(models.Model):
    ACHIEVEMENT_LEVELS = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='trophy')
    level = models.CharField(max_length=10, choices=ACHIEVEMENT_LEVELS, default='bronze')
    requirement = models.TextField(help_text="What's required to earn this achievement")
    points = models.IntegerField(default=10)
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

class StudentAchievement(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    blockchain_record = models.ForeignKey(
        BlockchainRecord, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Record achievement on blockchain
        if not self.blockchain_record:
            self.record_achievement_on_blockchain()
    
    def record_achievement_on_blockchain(self):
        """Record student achievement on blockchain"""
        achievement_data = {
            'achievement_name': self.achievement.name,
            'achievement_level': self.achievement.level,
            'points': self.achievement.points,
            'earned_date': self.earned_date.isoformat(),
        }
        data_hash = hashlib.sha256(json.dumps(achievement_data, sort_keys=True).encode()).hexdigest()
        
        metadata = {
            'achievement_id': self.id,
            'achievement_name': self.achievement.name,
            'level': self.achievement.level,
        }
        
        # Add to blockchain
        block_index = blockchain.new_transaction(
            student_id=self.student.blockchain_id,
            action_type='achievement',
            data_hash=data_hash,
            metadata=metadata
        )
        
        # Mine the block
        last_block = blockchain.last_block
        proof = blockchain.proof_of_work(last_block['proof'])
        blockchain.new_block(proof)
        
        # Store blockchain record
        blockchain_record = BlockchainRecord.objects.create(
            student=self.student,
            transaction_type='achievement',
            block_index=block_index,
            transaction_hash=blockchain.hash(blockchain.last_block),
            data_hash=data_hash,
            metadata=metadata
        )
        
        self.blockchain_record = blockchain_record
        self.save(update_fields=['blockchain_record'])

    
    class Meta:
        unique_together = ['student', 'achievement']
    
    def __str__(self):
        return f"{self.student.name} - {self.achievement.name}"

class LearningStreak(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(default=timezone.now)
    
    def update_streak(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        if self.last_activity_date == yesterday:
            self.current_streak += 1
        elif self.last_activity_date < yesterday:
            self.current_streak = 1
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.last_activity_date = today
        self.save()
    
    def __str__(self):
        return f"{self.student.name} - {self.current_streak} day streak"

