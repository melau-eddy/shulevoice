# context_processors.py
from .models import Student

def grade_choices(request):
    return {
        'grade_choices': Student.GRADE_LEVELS
    }