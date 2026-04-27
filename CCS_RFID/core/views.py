from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from classes.models import Enrollment, Class, ClassSession, Attendance
import json


@login_required
def dashboard(request):
    """Teacher dashboard with real data"""
    from classes.models import Class, ClassSession, Attendance
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get all classes for the teacher
    teacher_classes = Class.objects.filter(teacher=request.user)
    total_classes = teacher_classes.count()
    
    # Calculate total students
    total_students = sum(c.total_students for c in teacher_classes)
    
    # Get today's classes and next upcoming class
    today = timezone.now().date()
    current_day = today.strftime('%A').lower()  # e.g., 'tuesday'
    current_time = timezone.now().time()
    
    print(f"Current day: {current_day}")
    
    today_classes = []
    upcoming_classes = []
    
    for class_obj in teacher_classes:
        class_day = class_obj.day.lower()
        print(f"Class: {class_obj.subject_code}, Day: {class_day}")
        
        # Check if today is in the class day string
        # Class day could be like "M (Lec 2.00) (Lab 0.00)" or "Monday" or "M T W"
        is_today = False
        
        # Full day name match
        if current_day in class_day:
            is_today = True
        # Short day name match (M, T, W, Th, F)
        elif current_day == 'monday' and 'm' in class_day and 'mon' not in class_day:
            is_today = True
        elif current_day == 'tuesday' and 't' in class_day and 'tu' in class_day:
            is_today = True
        elif current_day == 'wednesday' and 'w' in class_day:
            is_today = True
        elif current_day == 'thursday' and 'th' in class_day:
            is_today = True
        elif current_day == 'friday' and 'f' in class_day:
            is_today = True
        elif current_day == 'saturday' and 'sa' in class_day:
            is_today = True
        elif current_day == 'sunday' and 'su' in class_day:
            is_today = True
        
        if is_today:
            today_classes.append({
                'id': class_obj.id,
                'subject_code': class_obj.subject_code,
                'subject_description': class_obj.subject_description,
                'room': class_obj.room,
                'section': class_obj.section,
                'time_from': class_obj.time_from,
                'time_to': class_obj.time_to,
            })
        else:
            upcoming_classes.append(class_obj)
    
    # Sort today's classes by time
    today_classes.sort(key=lambda x: x['time_from'])
    
    # Find next upcoming class
    next_class = None
    display_classes = today_classes if today_classes else []
    
    if not today_classes and upcoming_classes:
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        today_index = weekdays.index(current_day)
        
        upcoming_with_day = []
        for class_obj in upcoming_classes:
            class_day_lower = class_obj.day.lower()
            day_index = -1
            
            # Find which day this class is on
            for idx, day in enumerate(weekdays):
                if day in class_day_lower:
                    day_index = idx
                    break
                # Check short codes
                elif idx == 0 and 'm' in class_day_lower and 'mon' not in class_day_lower:
                    day_index = 0
                    break
                elif idx == 1 and 't' in class_day_lower and 'tu' in class_day_lower:
                    day_index = 1
                    break
                elif idx == 2 and 'w' in class_day_lower:
                    day_index = 2
                    break
                elif idx == 3 and 'th' in class_day_lower:
                    day_index = 3
                    break
                elif idx == 4 and 'f' in class_day_lower:
                    day_index = 4
                    break
                elif idx == 5 and 'sa' in class_day_lower:
                    day_index = 5
                    break
                elif idx == 6 and 'su' in class_day_lower:
                    day_index = 6
                    break
            
            if day_index >= 0:
                days_until = (day_index - today_index + 7) % 7
                upcoming_with_day.append({
                    'class': class_obj,
                    'days_until': days_until,
                    'day_index': day_index
                })
        
        if upcoming_with_day:
            upcoming_with_day.sort(key=lambda x: (x['days_until'], x['class'].time_from))
            next_class_obj = upcoming_with_day[0]['class']
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            class_day_index = upcoming_with_day[0]['day_index']
            day_display = day_names[class_day_index]
            
            if upcoming_with_day[0]['days_until'] == 0:
                day_display = 'Today'
            elif upcoming_with_day[0]['days_until'] == 1:
                day_display = 'Tomorrow'
            elif upcoming_with_day[0]['days_until'] > 1:
                day_display = f'{day_display} ({upcoming_with_day[0]["days_until"]} days)'
            
            next_class = {
                'id': next_class_obj.id,
                'subject_code': next_class_obj.subject_code,
                'subject_description': next_class_obj.subject_description,
                'room': next_class_obj.room,
                'section': next_class_obj.section,
                'time_from': next_class_obj.time_from,
                'time_to': next_class_obj.time_to,
                'day_display': day_display
            }
            display_classes = [next_class]
    
    # Calculate attendance rate
    total_present = 0
    total_late = 0
    total_absent = 0
    
    for class_obj in teacher_classes:
        sessions = ClassSession.objects.filter(class_obj=class_obj)
        for session in sessions:
            attendances = Attendance.objects.filter(session=session)
            total_present += attendances.filter(status='present').count()
            total_late += attendances.filter(status='late').count()
            total_absent += attendances.filter(status='absent').count()
    
    total_attended = total_present + total_late
    attendance_rate = int((total_attended / (total_attended + total_absent)) * 100) if (total_attended + total_absent) > 0 else 0
    
    # Get total attendance records
    total_records = Attendance.objects.count()
    
    # Get recent activities (last 5)
    recent_activities = []
    recent_attendances = Attendance.objects.all().select_related('student', 'session__class_obj').order_by('-time_in')[:5]
    
    for attendance in recent_attendances:
        recent_activities.append({
            'student_name': attendance.student.get_full_name(),
            'class_name': attendance.session.class_obj.subject_code if attendance.session else 'N/A',
            'date': attendance.time_in.strftime('%b %d, %Y'),
            'time': attendance.time_in.strftime('%I:%M %p'),
            'status': attendance.status
        })
    
    context = {
        'total_classes': total_classes,
        'total_students': total_students,
        'attendance_rate': attendance_rate,
        'total_records': total_records,
        'today_classes': today_classes,
        'display_classes': display_classes,
        'next_class': next_class,
        'recent_activities': recent_activities,
    }
    return render(request, 'dashboard.html', context)


@login_required
def activity(request):
    """Activity log page"""
    return render(request, 'activity.html')


@login_required
def stud_dashboard(request):
    """Student dashboard"""
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


@login_required
def get_activity_log(request):
    """API endpoint to get activity log - FIXED VERSION"""
    try:
        # Get ALL attendance records
        attendances = Attendance.objects.all().select_related('student', 'session__class_obj').order_by('-time_in')
        
        activities = []
        
        for attendance in attendances:
            student = attendance.student
            session = attendance.session
            class_obj = session.class_obj if session else None
            
            activities.append({
                'id': attendance.id,
                'student_name': student.get_full_name(),
                'student_id': student.student_id if hasattr(student, 'student_id') else 'N/A',
                'class_name': class_obj.subject_code if class_obj else 'N/A',
                'class_description': class_obj.subject_description if class_obj else 'N/A',
                'section': class_obj.section if class_obj and class_obj.section else 'N/A',
                'date': session.start_time.strftime('%B %d, %Y') if session else 'N/A',
                'time': attendance.time_in.strftime('%I:%M %p') if attendance.time_in else 'N/A',
                'status': attendance.status
            })
        
        return JsonResponse({
            'success': True,
            'activities': activities
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_attendance_status(request):
    """API endpoint to update attendance status"""
    try:
        data = json.loads(request.body)
        attendance_id = data.get('attendance_id')
        new_status = data.get('status')
        
        attendance = Attendance.objects.get(id=attendance_id)
        
        # Verify valid status
        valid_statuses = ['present', 'late', 'absent']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        # Update status
        attendance.status = new_status
        attendance.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}'
        })
        
    except Attendance.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Attendance record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)