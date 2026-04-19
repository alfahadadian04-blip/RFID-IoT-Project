from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from classes.models import Enrollment, Class

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def activity(request):
    return render(request, 'activity.html')

@login_required
def stud_dashboard(request):
    return render(request, 'stud_dashboard.html')

@login_required
def student_subject(request):
    """Display all subjects the student is enrolled in"""
    enrollments = Enrollment.objects.filter(student=request.user).select_related('class_obj')
    
    subjects = []
    unique_days = set()
    
    for enrollment in enrollments:
        class_obj = enrollment.class_obj
        subjects.append({
            'id': class_obj.id,
            'name': class_obj.subject_description,
            'code': class_obj.subject_code,
            'description': class_obj.subject_description,
            'schedule_day': class_obj.day,
            'time_start': class_obj.time_from,
            'time_end': class_obj.time_to,
            'room': class_obj.room,
            'units': class_obj.class_size or 3,
            'status': enrollment.status,
            'absences': enrollment.absence_count,
        })
        unique_days.add(class_obj.day)
    
    # Create time slots from 7 AM to 8 PM
    time_slots = []
    for hour in range(7, 20):
        am_pm = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        next_hour = hour + 1
        next_display_hour = next_hour if next_hour <= 12 else next_hour - 12
        next_am_pm = "AM" if next_hour < 12 else "PM"
        
        time_slots.append({
            'label': f"{display_hour}:00 {am_pm} - {next_display_hour}:00 {next_am_pm}",
            'hour': f"{hour:02d}"
        })
    
    context = {
        'subjects': subjects,
        'total_units': sum(s['units'] for s in subjects),
        'days_per_week': len(unique_days),
        'time_slots': time_slots,
        'current_semester': '2024-2025',
    }
    return render(request, 'student_subject.html', context)

@login_required
def student_view_class(request):
    """Display class details for a student (view only)"""
    class_id = request.GET.get('class_id')
    if not class_id:
        return redirect('student_subject')
    
    class_obj = get_object_or_404(Class, id=class_id)
    
    # Get all enrollments for this class
    enrollments = Enrollment.objects.filter(class_obj=class_obj).select_related('student')
    
    # Get the current student's enrollment
    user_enrollment = enrollments.filter(student=request.user).first()
    
    students = []
    for enrollment in enrollments:
        student = enrollment.student
        students.append({
            'name': student.get_full_name(),
            'student_id': student.student_id if hasattr(student, 'student_id') else '',
            'email': student.email,
            'gender': getattr(student, 'gender', 'N/A'),
            'status': enrollment.status,
            'absences': enrollment.absence_count,
        })
    
    context = {
        'class': class_obj,
        'students': students,
        'total_students': len(students),
        'user_status': user_enrollment.status if user_enrollment else 'not_enrolled',
        'user_absences': user_enrollment.absence_count if user_enrollment else 0,
        'user_absences_left': 5 - (user_enrollment.absence_count if user_enrollment else 0),
    }
    return render(request, 'student_view_class.html', context)