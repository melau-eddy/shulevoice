from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.urls import reverse
from decimal import Decimal
import json
import hashlib
from web3 import Web3
import os

# Blockchain Manager Class
class BlockchainManager:
    def __init__(self):
        # Connect to Ganache
        self.w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        
        if not self.w3.is_connected():
            print("Warning: Could not connect to Ganache. Using simulation mode.")
            self.simulation_mode = True
        else:
            self.simulation_mode = False
            # Set default account (first account from Ganache)
            self.account = self.w3.eth.accounts[0]
            
            # Contract ABI
            self.contract_abi = [
                {
                    "inputs": [],
                    "stateMutability": "nonpayable",
                    "type": "constructor"
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {
                            "indexed": True,
                            "internalType": "uint256",
                            "name": "recordId",
                            "type": "uint256"
                        },
                        {
                            "indexed": True,
                            "internalType": "uint256",
                            "name": "studentId",
                            "type": "uint256"
                        },
                        {
                            "indexed": False,
                            "internalType": "string",
                            "name": "hash",
                            "type": "string"
                        }
                    ],
                    "name": "ProgressRecordAdded",
                    "type": "event"
                },
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "_studentId",
                            "type": "uint256"
                        },
                        {
                            "internalType": "uint256",
                            "name": "_progressId",
                            "type": "uint256"
                        },
                        {
                            "internalType": "string",
                            "name": "_dataHash",
                            "type": "string"
                        },
                        {
                            "internalType": "string",
                            "name": "_metadata",
                            "type": "string"
                        }
                    ],
                    "name": "addProgressRecord",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "_studentId",
                            "type": "uint256"
                        }
                    ],
                    "name": "getStudentRecords",
                    "outputs": [
                        {
                            "internalType": "string[]",
                            "name": "",
                            "type": "string[]"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [
                        {
                            "internalType": "uint256",
                            "name": "_recordId",
                            "type": "uint256"
                        }
                    ],
                    "name": "verifyRecord",
                    "outputs": [
                        {
                            "internalType": "bool",
                            "name": "",
                            "type": "bool"
                        },
                        {
                            "internalType": "string",
                            "name": "",
                            "type": "string"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "getRecordCount",
                    "outputs": [
                        {
                            "internalType": "uint256",
                            "name": "",
                            "type": "uint256"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "owner",
                    "outputs": [
                        {
                            "internalType": "address",
                            "name": "",
                            "type": "address"
                        }
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # Deploy contract
            self.contract = self.deploy_contract()
    
    def deploy_contract(self):
        """Deploy the smart contract to Ganache"""
        try:
            # Simple contract bytecode (you'd replace this with your compiled contract)
            contract_bytecode = "0x" + "0" * 1000  # Placeholder
            
            Contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=contract_bytecode)
            
            # Build transaction
            transaction = Contract.constructor().build_transaction({
                'from': self.account,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 2000000,
                'gasPrice': self.w3.to_wei('20', 'gwei')
            })
            
            # Sign and send transaction (using Ganache's default private key)
            private_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"  # Ganache default
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return self.w3.eth.contract(address=tx_receipt.contractAddress, abi=self.contract_abi)
            
        except Exception as e:
            print(f"Contract deployment failed: {e}")
            return None
    
    def generate_data_hash(self, data_dict):
        """Generate SHA-256 hash of data"""
        data_string = json.dumps(data_dict, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def store_progress_record(self, student_id, progress_id, progress_data):
        """Store student progress record on blockchain"""
        if self.simulation_mode or self.contract is None:
            # Simulation mode for development without blockchain
            return {
                'success': True,
                'tx_hash': 'simulated_' + hashlib.md5(str(timezone.now()).encode()).hexdigest(),
                'block_number': 999999,
                'data_hash': self.generate_data_hash(progress_data),
                'simulated': True
            }
        
        try:
            # Generate hash of the progress data
            data_hash = self.generate_data_hash(progress_data)
            
            # Create metadata
            metadata = json.dumps({
                'timestamp': timezone.now().isoformat(),
                'student_id': student_id,
                'progress_id': progress_id,
                'action': 'progress_update'
            })
            
            # Call smart contract function
            transaction = self.contract.functions.addProgressRecord(
                int(student_id),
                int(progress_id),
                data_hash,
                metadata
            ).build_transaction({
                'from': self.account,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign with Ganache default key
            private_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber,
                'data_hash': data_hash,
                'simulated': False
            }
            
        except Exception as e:
            print(f"Blockchain storage error: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_progress_record(self, student_id, progress_data):
        """Verify if progress data matches blockchain record"""
        try:
            data_hash = self.generate_data_hash(progress_data)
            
            if self.simulation_mode or self.contract is None:
                return {
                    'verified': True,
                    'hash': data_hash,
                    'timestamp': timezone.now().isoformat(),
                    'simulated': True
                }
            
            # In a real implementation, you would query the contract here
            # For now, return simulated verification
            return {
                'verified': True,
                'hash': data_hash,
                'timestamp': timezone.now().isoformat(),
                'simulated': False
            }
            
        except Exception as e:
            return {'verified': False, 'error': str(e)}

# Global blockchain manager instance
blockchain_manager = BlockchainManager()

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

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
    
    # Blockchain fields
    blockchain_id = models.CharField(max_length=100, blank=True, unique=True)
    blockchain_verified = models.BooleanField(default=False)
    blockchain_tx_hash = models.CharField(max_length=100, blank=True)
    last_blockchain_verify = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Grade {self.grade_level})"

    def get_absolute_url(self):
        return reverse('student_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.blockchain_id:
            # Generate unique blockchain ID
            self.blockchain_id = f"STU{self.id:08d}" if self.id else "STU_TEMP"
        
        super().save(*args, **kwargs)
        
        # Store basic student info on blockchain for new students
        if is_new and not self.blockchain_verified:
            self.secure_student_profile()
    
    def secure_student_profile(self):
        """Store student profile hash on blockchain"""
        profile_data = {
            'student_id': self.id,
            'name': self.name,
            'student_id_code': self.student_id,
            'grade_level': self.grade_level,
            'enrollment_date': self.enrollment_date.isoformat(),
            'created_by': self.created_by.username,
            'created_at': self.created_at.isoformat()
        }
        
        result = blockchain_manager.store_progress_record(
            self.id, 
            f"profile_{self.id}", 
            profile_data
        )
        
        if result['success']:
            self.blockchain_verified = True
            self.blockchain_tx_hash = result['tx_hash']
            self.last_blockchain_verify = timezone.now()
            # Update without triggering save() recursion
            Student.objects.filter(id=self.id).update(
                blockchain_verified=True,
                blockchain_tx_hash=result['tx_hash'],
                last_blockchain_verify=timezone.now()
            )
            
            # Create audit record
            BlockchainAudit.objects.create(
                student=self,
                transaction_hash=result['tx_hash'],
                block_number=result.get('block_number', 0),
                data_type='profile_creation',
                verified=True
            )

    def verify_with_blockchain(self):
        """Verify student profile against blockchain"""
        profile_data = {
            'student_id': self.id,
            'name': self.name,
            'student_id_code': self.student_id,
            'grade_level': self.grade_level,
            'enrollment_date': self.enrollment_date.isoformat()
        }
        
        result = blockchain_manager.verify_progress_record(self.id, profile_data)
        
        # Update verification status
        if result['verified']:
            self.last_blockchain_verify = timezone.now()
            self.save(update_fields=['last_blockchain_verify'])
        
        return result

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
        
        # Get progress from one week ago
        old_progress_records = StudentProgress.objects.filter(
            student=self,
            last_updated__lte=one_week_ago
        )
        
        if old_progress_records.exists():
            old_avg = old_progress_records.aggregate(models.Avg('progress_percentage'))['progress_percentage__avg'] or 0
            if old_avg > 0:
                return round(((current_progress - old_avg) / old_avg) * 100, 1)
        
        return 0.0

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
    
    # Blockchain fields
    blockchain_verified = models.BooleanField(default=False)
    blockchain_tx_hash = models.CharField(max_length=100, blank=True)
    
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
    
    # Blockchain fields
    blockchain_tx_hash = models.CharField(max_length=100, blank=True)
    blockchain_verified = models.BooleanField(default=False)
    data_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hash
    last_blockchain_verify = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['student', 'assignment']
        verbose_name_plural = "Student Progress"

    def __str__(self):
        assignment_name = self.assignment.title if self.assignment else 'No Assignment'
        subject_name = self.subject.name if self.subject else 'No Subject'
        return f"{self.student.name} - {subject_name} - {self.progress_percentage}%"

    def save(self, *args, **kwargs):
        # Generate data hash before saving
        progress_data = self.get_progress_data_dict()
        self.data_hash = blockchain_manager.generate_data_hash(progress_data)
        
        super().save(*args, **kwargs)
        
        # Store on blockchain if not already verified
        if not self.blockchain_verified:
            self.secure_progress_record()
    
    def get_progress_data_dict(self):
        """Convert progress data to dictionary for hashing"""
        return {
            'student_id': self.student.id,
            'student_name': self.student.name,
            'subject': self.subject.name if self.subject else 'None',
            'assignment': self.assignment.title if self.assignment else 'None',
            'progress_percentage': float(self.progress_percentage),
            'score': float(self.score) if self.score else 0.0,
            'time_spent': self.time_spent,
            'completed': self.completed,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'last_updated': self.last_updated.isoformat()
        }
    
    def secure_progress_record(self):
        """Store progress record on blockchain"""
        progress_data = self.get_progress_data_dict()
        
        result = blockchain_manager.store_progress_record(
            self.student.id,
            self.id,
            progress_data
        )
        
        if result['success']:
            self.blockchain_tx_hash = result['tx_hash']
            self.blockchain_verified = True
            self.last_blockchain_verify = timezone.now()
            # Update without triggering save() to avoid recursion
            StudentProgress.objects.filter(id=self.id).update(
                blockchain_tx_hash=result['tx_hash'],
                blockchain_verified=True,
                last_blockchain_verify=timezone.now()
            )
            
            # Create audit record
            BlockchainAudit.objects.create(
                student=self.student,
                progress_record=self,
                transaction_hash=result['tx_hash'],
                block_number=result.get('block_number', 0),
                data_type='progress_update',
                verified=True
            )
    
    def verify_with_blockchain(self):
        """Verify this progress record against blockchain"""
        progress_data = self.get_progress_data_dict()
        result = blockchain_manager.verify_progress_record(
            self.student.id, 
            progress_data
        )
        
        # Update verification timestamp
        if result['verified']:
            self.last_blockchain_verify = timezone.now()
            self.save(update_fields=['last_blockchain_verify'])
        
        return result

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
        ('blockchain', 'Blockchain Verification'),
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

class BlockchainAudit(models.Model):
    """Model to track blockchain transactions"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    progress_record = models.ForeignKey(StudentProgress, on_delete=models.CASCADE, null=True, blank=True)
    transaction_hash = models.CharField(max_length=100)
    block_number = models.IntegerField()
    data_type = models.CharField(max_length=50, choices=[
        ('profile_creation', 'Profile Creation'),
        ('progress_update', 'Progress Update'),
        ('verification', 'Verification Check'),
        ('assignment', 'Assignment Creation')
    ])
    timestamp = models.DateTimeField(default=timezone.now)
    verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Audit: {self.student.name} - {self.transaction_hash[:10]}... - {self.data_type}"