import pytest
from services.fine_strategy import FineContext, StudentFineStrategy, FacultyFineStrategy

def test_student_fine():
    context = FineContext(StudentFineStrategy())
    assert context.compute_fine(5) == 50.0

def test_faculty_fine():
    context = FineContext(FacultyFineStrategy())
    assert context.compute_fine(5) == 10.0

def test_zero_days_fine():
    context = FineContext(StudentFineStrategy())
    assert context.compute_fine(0) == 0.0