from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models as db_models
from classes.models import Enrollment, Class, ClassSession, Attendance
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
from CCS.models import User
import json
import re


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
    """Student dashboard with accurate data"""
    from classes.models import Enrollment
    import re
    from django.http import JsonResponse  # For debugging
    
    # Get all enrollments for this student
    enrollments = Enrollment.objects.filter(student=request.user).select_related('class_obj')
    
    print(f"=== STUD DASHBOARD DEBUG ===")
    print(f"Student: {request.user.get_full_name()}")
    print(f"Total enrollments found: {enrollments.count()}")
    
    subjects = []
    dropped_count = 0
    at_risk_count = 0
    total_units = 0
    
    for enrollment in enrollments:
        class_obj = enrollment.class_obj
        absence_count = enrollment.absence_count
        status = enrollment.status
        
        print(f"\nProcessing enrollment:")
        print(f"  Class ID: {class_obj.id}")
        print(f"  Subject: {class_obj.subject_code} - {class_obj.subject_description}")
        print(f"  Absences: {absence_count}")
        print(f"  Status: {status}")
        
        # Extract units from day column
        day_text = class_obj.day if class_obj.day else ''
        units = 3
        
        lec_match = re.search(r'Lec\s+(\d+\.?\d*)', day_text, re.IGNORECASE)
        lab_match = re.search(r'Lab\s+(\d+\.?\d*)', day_text, re.IGNORECASE)
        
        lec_units = float(lec_match.group(1)) if lec_match else 0
        lab_units = float(lab_match.group(1)) if lab_match else 0
        total_units_for_subject = lec_units + lab_units
        
        if total_units_for_subject > 0:
            units = total_units_for_subject
            print(f"  Units from day text: {units} (Lec: {lec_units}, Lab: {lab_units})")
        
        total_units += units
        
        if status == 'dropped':
            dropped_count += 1
        elif absence_count >= 4:
            at_risk_count += 1
        
        day_name = re.sub(r'\s*\(.*', '', day_text).strip() if day_text else 'TBA'
        if day_name == '':
            day_name = class_obj.day if class_obj.day else 'TBA'
        
        subjects.append({
            'id': class_obj.id,
            'name': class_obj.subject_description,
            'code': class_obj.subject_code,
            'schedule_day': day_name,
            'time_start': class_obj.time_from,
            'time_end': class_obj.time_to,
            'room': class_obj.room,
            'absence_count': absence_count,
            'status': status,
            'absences_left': 5 - absence_count if absence_count < 5 else 0,
            'units': units,
        })
    
    print(f"\n=== FINAL DATA ===")
    print(f"Total subjects in list: {len(subjects)}")
    print(f"Total units: {total_units}")
    print(f"Dropped count: {dropped_count}")
    print(f"At risk count: {at_risk_count}")
    
    context = {
        'subjects': subjects,
        'total_subjects': len(subjects),
        'total_units': int(total_units) if total_units.is_integer() else total_units,
        'dropped_count': dropped_count,
        'at_risk_count': at_risk_count,
    }
    
    print(f"Context keys: {context.keys()}")
    print(f"Subjects in context: {len(context['subjects'])}")
    
    return render(request, 'stud_dashboard.html', context)


@login_required
def student_subject(request):
    """Display all subjects the student is enrolled in with accurate units from Excel"""
    from classes.models import Enrollment
    import re
    
    enrollments = Enrollment.objects.filter(student=request.user).select_related('class_obj')
    
    subjects = []
    unique_days = set()
    total_units = 0
    
    for enrollment in enrollments:
        class_obj = enrollment.class_obj
        
        # Extract units from day column (format: "M (Lec 2.00) (Lab 0.00)")
        day_text = class_obj.day if class_obj.day else ''
        units = 3  # Default to 3 if parsing fails
        
        # Parse units using regex
        # Pattern to find Lec X.XX or Lab X.XX
        lec_match = re.search(r'Lec\s+(\d+\.?\d*)', day_text, re.IGNORECASE)
        lab_match = re.search(r'Lab\s+(\d+\.?\d*)', day_text, re.IGNORECASE)
        
        lec_units = float(lec_match.group(1)) if lec_match else 0
        lab_units = float(lab_match.group(1)) if lab_match else 0
        total_units_for_subject = lec_units + lab_units
        
        if total_units_for_subject > 0:
            units = total_units_for_subject
        else:
            # If no units found, check for total units format
            total_match = re.search(r'(\d+\.?\d*)\s*units?', day_text, re.IGNORECASE)
            if total_match:
                units = float(total_match.group(1))
        
        total_units += units
        
        # Extract day name (before the parenthesis)
        day_name = re.sub(r'\s*\(.*', '', day_text).strip() if day_text else 'TBA'
        if day_name:
            unique_days.add(day_name)
        
        subjects.append({
            'id': class_obj.id,
            'name': class_obj.subject_description,
            'code': class_obj.subject_code,
            'description': class_obj.subject_description,
            'schedule_day': day_name,
            'time_start': class_obj.time_from,
            'time_end': class_obj.time_to,
            'room': class_obj.room,
            'units': units,
            'status': enrollment.status,
            'absences': enrollment.absence_count,
        })
    
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
        'total_units': int(total_units) if total_units.is_integer() else total_units,
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


# ============================================
# SUPERADMIN USER MANAGEMENT
# ============================================

@login_required
def user_management(request):
    """Superadmin view to manage all users (students and admins)"""
    # Check if user is superadmin
    if request.user.user_type != 'superadmin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get all users except superadmins
    users = User.objects.exclude(user_type='superadmin').order_by('-date_joined')
    
    # Calculate stats
    total_users = users.count()
    total_students = users.filter(user_type='student').count()
    total_admins = users.filter(user_type='admin').count()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            db_models.Q(first_name__icontains=search_query) |
            db_models.Q(last_name__icontains=search_query) |
            db_models.Q(email__icontains=search_query) |
            db_models.Q(student_id__icontains=search_query)
        )
    
    # Filter by user type
    user_type_filter = request.GET.get('user_type', '')
    if user_type_filter and user_type_filter != 'all':
        users = users.filter(user_type=user_type_filter)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'user_type_filter': user_type_filter,
        'total_users': total_users,
        'total_students': total_students,
        'total_admins': total_admins,
    }
    return render(request, 'user_management.html', context)


@login_required
def edit_student(request, user_id):
    """Superadmin view to edit student profile"""
    # Check if user is superadmin
    if request.user.user_type != 'superadmin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    student = get_object_or_404(User, id=user_id, user_type='student')
    
    if request.method == 'POST':
        try:
            # Personal Information
            student.first_name = request.POST.get('first_name')
            student.middle_name = request.POST.get('middle_name', '')
            student.last_name = request.POST.get('last_name')
            student.gender = request.POST.get('gender')
            student.civil_status = request.POST.get('civil_status')
            
            # Date of Birth
            dob = request.POST.get('date_of_birth')
            if dob:
                student.date_of_birth = dob
            else:
                student.date_of_birth = None
            
            # Contact Information
            student.contact_person = request.POST.get('contact_person', '')
            student.contact_number = request.POST.get('contact_number', '')
            
            # Academic Information
            student.college = request.POST.get('college')
            student.department = request.POST.get('department')
            student.course = request.POST.get('course')
            student.student_id = request.POST.get('student_id')
            
            # RFID Tag
            rfid_tag = request.POST.get('rfid_tag')
            clear_rfid = request.POST.get('clear_rfid') == 'on'
            
            if clear_rfid:
                student.rfid_tag = None
            elif rfid_tag:
                # Check if RFID is already used by another student
                existing = User.objects.filter(rfid_tag=rfid_tag).exclude(id=student.id).first()
                if existing:
                    messages.error(request, f'RFID tag {rfid_tag} is already assigned to {existing.get_full_name()}')
                    return redirect('edit_student', user_id=user_id)
                student.rfid_tag = rfid_tag
            
            student.save()
            messages.success(request, f'Student {student.get_full_name()} has been updated successfully!')
            return redirect('user_management')
            
        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')
    
    context = {
        'student': student,
        'is_superadmin': True,
    }
    return render(request, 'edit_student.html', context)


@login_required
def delete_user(request, user_id):
    """Superadmin view to delete a user"""
    if request.user.user_type != 'superadmin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'DELETE':
        try:
            user = User.objects.get(id=user_id)
            user_name = user.get_full_name()
            
            # Don't allow deleting yourself
            if user.id == request.user.id:
                return JsonResponse({'error': 'You cannot delete your own account'}, status=400)
            
            user.delete()
            return JsonResponse({'success': True, 'message': f'User {user_name} has been deleted.'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def super_dashboard(request):
    """Super Admin Dashboard with system overview"""
    from classes.models import Class, ClassSession, Attendance
    from django.utils import timezone
    from datetime import timedelta
    
    # Check if user is superadmin
    if request.user.user_type != 'superadmin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get all users
    all_users = User.objects.all()
    total_users = all_users.count()
    total_students = all_users.filter(user_type='student').count()
    total_admins = all_users.filter(user_type='admin').count()
    total_superadmins = all_users.filter(user_type='superadmin').count()
    
    # Calculate percentages
    total_users_for_percent = total_users if total_users > 0 else 1
    total_students_percent = int((total_students / total_users_for_percent) * 100)
    total_admins_percent = int((total_admins / total_users_for_percent) * 100)
    total_superadmins_percent = int((total_superadmins / total_users_for_percent) * 100)
    
    # Get total classes
    total_classes = Class.objects.count()
    
    # Get recent users (last 10)
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    
    # Get recent activities (last 10 attendance records)
    recent_activities = []
    recent_attendances = Attendance.objects.all().select_related('student', 'session__class_obj').order_by('-time_in')[:10]
    
    for attendance in recent_attendances:
        # Calculate time ago
        time_diff = timezone.now() - attendance.time_in
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day(s) ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour(s) ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} minute(s) ago"
        else:
            time_ago = "Just now"
        
        recent_activities.append({
            'type': 'attendance',
            'description': f"{attendance.student.get_full_name()} marked as {attendance.status} in {attendance.session.class_obj.subject_code if attendance.session else 'N/A'}",
            'timestamp': attendance.time_in.strftime('%b %d, %Y at %I:%M %p'),
            'time_ago': time_ago
        })
    
    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_admins': total_admins,
        'total_superadmins': total_superadmins,
        'total_students_percent': total_students_percent,
        'total_admins_percent': total_admins_percent,
        'total_superadmins_percent': total_superadmins_percent,
        'total_classes': total_classes,
        'recent_users': recent_users,
        'recent_activities': recent_activities,
    }
    return render(request, 'super_dashboard.html', context)

@login_required
def get_super_activity_log(request):
    """API endpoint to get ALL system activities for Super Admin"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Check if user is superadmin
    if request.user.user_type != 'superadmin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    activities = []
    
    # Get all attendance records
    attendances = Attendance.objects.all().select_related('student', 'session__class_obj').order_by('-time_in')
    
    for att in attendances:
        # Calculate time ago
        time_diff = timezone.now() - att.time_in
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day(s) ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour(s) ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} minute(s) ago"
        else:
            time_ago = "Just now"
        
        activities.append({
            'id': att.id,
            'actor_name': att.student.get_full_name(),
            'actor_email': att.student.email,
            'type': 'attendance',
            'action': 'recorded_attendance',
            'details': f"Marked as {att.status} in {att.session.class_obj.subject_code if att.session else 'N/A'}",
            'target_name': att.session.class_obj.subject_code if att.session else 'N/A',
            'timestamp': att.time_in.strftime('%B %d, %Y at %I:%M %p'),
            'time_ago': time_ago
        })
    
    # Sort by timestamp (newest first)
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return JsonResponse({
        'success': True,
        'activities': activities
    })

@login_required
def super_activity(request):
    """Super Admin Activity Log page"""
    # Check if user is superadmin
    if request.user.user_type != 'superadmin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    return render(request, 'super_activity.html')

@login_required
def profile(request):
    """User profile page for all user types with picture upload"""
    if request.method == 'POST':
        try:
            # Check if this is an AJAX file upload
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'profile_picture' in request.FILES:
                request.user.profile_picture = request.FILES['profile_picture']
                request.user.save()
                return JsonResponse({'success': True, 'message': 'Profile picture updated!'})
            
            # Regular form submission
            # Get values with fallbacks to prevent None errors
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip()
            
            # Validate required fields
            if not first_name or not last_name:
                messages.error(request, 'First name and last name are required.')
                return redirect('profile')
            
            # Update personal information
            request.user.first_name = first_name
            request.user.middle_name = middle_name
            request.user.last_name = last_name
            
            # Student-specific fields
            if request.user.user_type == 'student':
                email = request.POST.get('email', '').strip()
                if email:
                    request.user.email = email
                
                dob = request.POST.get('date_of_birth')
                if dob:
                    request.user.date_of_birth = dob
                
                request.user.gender = request.POST.get('gender', '')
                request.user.civil_status = request.POST.get('civil_status', '')
                request.user.contact_number = request.POST.get('contact_number', '')
                request.user.contact_person = request.POST.get('contact_person', '')
                request.user.department = request.POST.get('department', '')
                request.user.course = request.POST.get('course', '')
            
            # Password change
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            
            if new_password:
                if not current_password:
                    messages.error(request, 'Current password is required to change password.')
                    return redirect('profile')
                
                if not check_password(current_password, request.user.password):
                    messages.error(request, 'Current password is incorrect.')
                    return redirect('profile')
                
                if len(new_password) < 8:
                    messages.error(request, 'New password must be at least 8 characters long.')
                    return redirect('profile')
                
                request.user.set_password(new_password)
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')
            
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('profile')
    
    return render(request, 'profile.html', {'user': request.user})