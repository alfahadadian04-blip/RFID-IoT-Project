import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import Class, Enrollment, ClassSession, Attendance
from CCS.models import User, PendingRFID
from CCS.forms import AdminLoginForm, StudentLoginForm, AdminRegistrationForm, StudentRegistrationForm
import traceback
import json
import logging
import re

logger = logging.getLogger(__name__)


# ============================================
# Validation function for Student ID and Email
# ============================================
def validate_student_registration_data(data):
    """Validate Student ID format and Email domain before form submission"""
    errors = {}
    
    student_id = data.get('student_id')
    if student_id:
        student_id_pattern = r'^\d{4}-\d{5}$'
        if not re.match(student_id_pattern, student_id):
            errors['student_id'] = 'Student ID must be in format: YYYY-XXXXX (e.g., 2022-00779)'
    
    email = data.get('email')
    if email:
        if not email.lower().endswith('@wmsu.edu.ph'):
            errors['email'] = 'Only @wmsu.edu.ph email addresses are allowed'
    
    return errors


def get_cell_value(cell):
    """Safely get value from a cell"""
    if cell is None:
        return None
    if hasattr(cell, 'value'):
        return cell.value
    return cell


def parse_excel_time(value):
    """Convert Excel time (datetime, float, or string) to time object"""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, (int, float)):
        total_seconds = int(value * 86400)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hours, minutes, seconds)
    if isinstance(value, str):
        value = value.strip()
        for fmt in ['%I:%M%p', '%I:%M %p', '%H:%M', '%I:%M%p']:
            try:
                return datetime.strptime(value, fmt).time()
            except:
                continue
    return None


# ============================================
# RFID HANDLER (for Arduino)
# ============================================
@csrf_exempt
def rfid_handler(request):
    """API endpoint that receives RFID data from Arduino"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            student_id = data.get('student_id')
            
            if not rfid_tag:
                return JsonResponse({'error': 'No RFID tag provided'}, status=400)
            
            print(f"📇 RFID received: {rfid_tag}, Student ID: {student_id}")
            
            if student_id:
                try:
                    student = User.objects.get(id=student_id, user_type='student')
                    existing = User.objects.filter(rfid_tag=rfid_tag).exclude(id=student_id).first()
                    if existing:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'RFID tag already registered to another student'
                        }, status=400)
                    
                    student.rfid_tag = rfid_tag
                    student.save()
                    
                    print(f"✅ RFID registered for student: {student.get_full_name()}")
                    return JsonResponse({
                        'status': 'success',
                        'action': 'registered',
                        'name': student.get_full_name(),
                        'rfid_tag': rfid_tag
                    })
                    
                except User.DoesNotExist:
                    return JsonResponse({'error': 'Student not found'}, status=404)
            
            else:
                student = User.objects.filter(
                    rfid_tag=rfid_tag, 
                    user_type='student',
                    is_active=True
                ).first()
                
                if student:
                    print(f"✅ Attendance recorded for: {student.get_full_name()}")
                    return JsonResponse({
                        'status': 'success',
                        'name': student.get_full_name(),
                        'action': 'attendance_recorded'
                    })
                else:
                    print(f"❌ No student found with RFID: {rfid_tag}")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Student not found'
                    }, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"❌ RFID handler error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================
# RFID PENDING REGISTRATION
# ============================================
@login_required
def register_rfid_for_student(request, student_id):
    """Assign RFID tag to a student during registration"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            
            if not rfid_tag:
                return JsonResponse({'error': 'No RFID tag provided'}, status=400)
            
            if User.objects.filter(rfid_tag=rfid_tag).exists():
                return JsonResponse({
                    'error': 'RFID tag already registered to another student'
                }, status=400)
            
            student = User.objects.get(id=student_id, user_type='student')
            student.rfid_tag = rfid_tag
            student.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'RFID registered successfully'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def check_rfid_status(request, student_id):
    """Check if an RFID has been registered for this student"""
    try:
        student = User.objects.get(id=student_id, user_type='student')
        
        if student.rfid_tag:
            return JsonResponse({
                'rfid_detected': True,
                'rfid_tag': student.rfid_tag
            })
        else:
            return JsonResponse({
                'rfid_detected': False
            })
    except User.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)


def create_pending_rfid(request, student_id):
    """Create a pending RFID registration for a student"""
    if request.method == 'POST':
        try:
            student = User.objects.get(id=student_id, user_type='student')
            PendingRFID.objects.filter(student=student).delete()
            pending = PendingRFID.objects.create(
                student=student,
                expires_at=timezone.now() + timedelta(minutes=5)
            )
            
            return JsonResponse({
                'success': True,
                'expires_at': pending.expires_at.isoformat()
            })
        except User.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def check_pending_rfid(request):
    """Check if any student is waiting for RFID registration"""
    PendingRFID.objects.filter(expires_at__lt=timezone.now()).delete()
    pending = PendingRFID.objects.first()
    
    if pending and not pending.is_expired():
        return JsonResponse({
            'waiting': True,
            'student_id': pending.student.id,
            'student_name': pending.student.get_full_name(),
            'expires_at': pending.expires_at.isoformat()
        })
    else:
        return JsonResponse({'waiting': False})


# ============================================
# AUTHENTICATION VIEWS
# ============================================
def adminLogin(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.user_type == 'admin':
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'This account is not an admin account.')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'adminLogin.html', {})


def studentLogin(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.user_type == 'student':
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'This account is not a student account.')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'studentLogin.html', {})


def adminRegistration(request):
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, 'Account created successfully! You can now login.')
                return redirect('adminLogin')
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AdminRegistrationForm()
    
    return render(request, 'adminRegistration.html', {'form': form})


def studentRegistration(request):
    if request.method == 'POST':
        print("=" * 50)
        print("Received POST data:")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        validation_errors = validate_student_registration_data(request.POST)
        
        if validation_errors:
            print("❌ Validation errors:", validation_errors)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                error_messages = []
                for field, error in validation_errors.items():
                    error_messages.append(f"{field}: {error}")
                return JsonResponse({
                    'success': False, 
                    'error': ' | '.join(error_messages)
                }, status=400)
            else:
                for field, error in validation_errors.items():
                    messages.error(request, error)
                return render(request, 'studentRegistration.html')
        
        student_id = request.POST.get('student_id')
        if student_id and User.objects.filter(student_id=student_id).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Student ID already exists.'}, status=400)
            else:
                messages.error(request, 'Student ID already exists.')
                return render(request, 'studentRegistration.html')
        
        email = request.POST.get('email')
        if email and User.objects.filter(email=email).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Email already exists.'}, status=400)
            else:
                messages.error(request, 'Email already exists.')
                return render(request, 'studentRegistration.html')
        
        form = StudentRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                user = form.save()
                print(f"✅ User created with ID: {user.id}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'student_id': user.id,
                        'message': 'Student created successfully'
                    })
                else:
                    messages.success(request, 'Student account created successfully!')
                    return render(request, 'studentRegistration.html', {'student_id': user.id})
                    
            except Exception as e:
                print(f"❌ Error saving user: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                else:
                    messages.error(request, f'Error creating account: {str(e)}')
                    return render(request, 'studentRegistration.html')
        else:
            print("❌ Form is invalid!")
            print("Form errors:", form.errors)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.append(f"{field}: {', '.join(errors)}")
                return JsonResponse({'success': False, 'error': ' | '.join(error_messages)}, status=400)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return render(request, 'studentRegistration.html')
    
    return render(request, 'studentRegistration.html', {})


# ============================================
# TEACHER CLASS VIEWS
# ============================================
@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})


@login_required
def attendance(request):
    return render(request, 'attendance.html')


@login_required
def classes(request):
    """Display all classes for the logged-in teacher"""
    user_classes = Class.objects.filter(teacher=request.user)
    total_students = sum(c.enrollments.count() for c in user_classes)
    
    context = {
        'classes': user_classes,
        'total_classes': user_classes.count(),
        'total_students': total_students,
        'avg_attendance': 87,
    }
    return render(request, 'classes.html', context)


@login_required
def view_class(request):
    """Display details of a specific class with student list"""
    class_id = request.GET.get('class_id')
    if not class_id:
        messages.error(request, 'No class specified.')
        return redirect('classes')
    
    try:
        class_obj = Class.objects.get(id=class_id, teacher=request.user)
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('classes')
    
    enrollments = class_obj.enrollments.select_related('student').all()
    total_students = enrollments.count()
    
    students = []
    for idx, enrollment in enumerate(enrollments, 1):
        student = enrollment.student
        students.append({
            'number': idx,
            'student_id': student.student_id if hasattr(student, 'student_id') else '',
            'name': student.get_full_name(),
            'email': student.email,
            'gender': getattr(student, 'gender', 'N/A'),
            'status': enrollment.status,
            'absences': enrollment.absence_count,
            'course': getattr(student, 'course', ''),
        })
    
    context = {
        'class': class_obj,
        'students': students,
        'total_students': total_students,
        'present_today': 0,
        'absent_today': 0,
        'late_today': 0,
    }
    return render(request, 'view_class.html', context)


@login_required
def upload_masterlist(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        print(f"[DEBUG] File received: {excel_file.name}")
        
        try:
            workbook = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = workbook.active
            
            print("=== FIRST 20 ROWS OF EXCEL ===")
            for i in range(1, 21):
                row = []
                for j in range(1, 9):
                    val = get_cell_value(sheet.cell(row=i, column=j))
                    row.append(val)
                print(f"Row {i}: {row}")
            
            school_year = None
            semester = None
            student_type = None
            for i in range(1, 15):
                val = get_cell_value(sheet.cell(row=i, column=1))
                if val and 'SCHOOL YEAR' in str(val).upper():
                    school_year = get_cell_value(sheet.cell(row=i, column=2))
                elif val and 'SEMESTER' in str(val).upper():
                    semester = get_cell_value(sheet.cell(row=i, column=2))
                elif val and 'STUDENT TYPE' in str(val).upper():
                    student_type = get_cell_value(sheet.cell(row=i, column=2))
            
            print(f"[DEBUG] Metadata - School Year: {school_year}, Semester: {semester}, Student Type: {student_type}")
            
            subject_start_row = None
            for i in range(1, 100):
                val = get_cell_value(sheet.cell(row=i, column=1))
                if val and 'Subject ID' in str(val):
                    subject_start_row = i + 1
                    print(f"[DEBUG] Found 'Subject ID' at row {i}, data starts at row {subject_start_row}")
                    break
            
            if not subject_start_row:
                return JsonResponse({'error': 'Could not find subject data.'}, status=400)
            
            classes_created = []
            row_idx = subject_start_row
            consecutive_empty = 0
            
            while True:
                subject_id = get_cell_value(sheet.cell(row=row_idx, column=1))
                subject_code = get_cell_value(sheet.cell(row=row_idx, column=2))
                description = get_cell_value(sheet.cell(row=row_idx, column=3))
                college = get_cell_value(sheet.cell(row=row_idx, column=4))
                time_from_val = get_cell_value(sheet.cell(row=row_idx, column=5))
                time_to_val = get_cell_value(sheet.cell(row=row_idx, column=6))
                day = get_cell_value(sheet.cell(row=row_idx, column=7))
                room = get_cell_value(sheet.cell(row=row_idx, column=8))
                program = get_cell_value(sheet.cell(row=row_idx, column=9))
                class_size_str = get_cell_value(sheet.cell(row=row_idx, column=10))
                section = get_cell_value(sheet.cell(row=row_idx, column=11))
                
                if subject_id and 'No.' in str(subject_id):
                    print(f"[DEBUG] Found student table at row {row_idx}")
                    break
                
                if not subject_id or str(subject_id).strip() == '':
                    consecutive_empty += 1
                    row_idx += 1
                    if consecutive_empty > 10:
                        break
                    continue
                else:
                    consecutive_empty = 0
                
                if not subject_code or str(subject_code).strip() == '':
                    row_idx += 1
                    continue
                
                time_from = parse_excel_time(time_from_val)
                time_to = parse_excel_time(time_to_val)
                
                if not time_from or not time_to:
                    row_idx += 1
                    continue
                
                class_obj, created = Class.objects.get_or_create(
                    subject_code=str(subject_code).strip(),
                    section=str(section).strip() if section else '',
                    semester=str(semester).strip() if semester else '',
                    school_year=str(school_year).strip() if school_year else '',
                    day=str(day).strip() if day else '',
                    time_from=time_from,
                    time_to=time_to,
                    defaults={
                        'subject_description': str(description).strip() if description else '',
                        'college': str(college).strip() if college else '',
                        'student_type': str(student_type).strip() if student_type else '',
                        'room': str(room).strip() if room else '',
                        'program': str(program).strip() if program else '',
                        'class_size': int(class_size_str) if class_size_str and str(class_size_str).isdigit() else 0,
                        'teacher': request.user,
                    }
                )
                if created:
                    classes_created.append(class_obj)
                
                row_idx += 1
                
                if row_idx > subject_start_row + 50:
                    break
            
            student_start_row = None
            for i in range(1, 500):
                col1 = get_cell_value(sheet.cell(row=i, column=1))
                col2 = get_cell_value(sheet.cell(row=i, column=2))
                if col1 and 'No.' in str(col1) and col2 and 'Student ID' in str(col2):
                    student_start_row = i + 1
                    break
            
            if not student_start_row:
                if len(classes_created) > 0:
                    return JsonResponse({'success': True, 'message': f"Uploaded {len(classes_created)} class(es)."})
                else:
                    return JsonResponse({'error': 'Could not find student data'}, status=400)
            
            students_processed = 0
            students_skipped = []
            row_idx = student_start_row
            
            while True:
                student_id = get_cell_value(sheet.cell(row=row_idx, column=2))
                name = get_cell_value(sheet.cell(row=row_idx, column=3))
                email = get_cell_value(sheet.cell(row=row_idx, column=4))
                
                if not student_id or not name:
                    break
                
                if not email:
                    email = f"{student_id}@wmsu.edu.ph"
                
                name_parts = str(name).split(',')
                if len(name_parts) == 2:
                    last_name = name_parts[0].strip()
                    first_middle = name_parts[1].strip().split()
                    first_name = first_middle[0] if first_middle else ''
                else:
                    first_name = str(name)
                    last_name = ''
                
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'user_type': 'student',
                    }
                )
                if not created:
                    if hasattr(user, 'student_id') and user.student_id != student_id:
                        user.student_id = student_id
                        user.save()
                    students_skipped.append(f"{name} (already exists)")
                else:
                    if hasattr(user, 'student_id'):
                        user.student_id = student_id
                        user.save()
                    students_processed += 1
                
                for class_obj in classes_created:
                    Enrollment.objects.get_or_create(
                        student=user,
                        class_obj=class_obj,
                        defaults={'status': 'enrolled', 'absence_count': 0}
                    )
                
                row_idx += 1
                
                if row_idx > student_start_row + 500:
                    break
            
            if len(classes_created) == 0:
                return JsonResponse({'error': 'No valid classes found.'}, status=400)
            
            message = f"Uploaded {len(classes_created)} class(es) and enrolled {students_processed} student(s)."
            if students_skipped:
                message += f" Skipped {len(students_skipped)} existing students."
            
            return JsonResponse({'success': True, 'message': message})
        
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'No file provided'}, status=400)


@csrf_exempt
@login_required
def delete_class(request, class_id):
    """Delete a class and its enrollments"""
    if request.method == 'DELETE':
        try:
            class_obj = Class.objects.get(id=class_id, teacher=request.user)
            class_name = str(class_obj)
            class_obj.delete()
            return JsonResponse({'success': True, 'message': f'Class "{class_name}" has been deleted.'})
        except Class.DoesNotExist:
            return JsonResponse({'error': 'Class not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ============================================
# CLASS SESSION AND ATTENDANCE VIEWS
# ============================================
@login_required
def start_class_session(request, class_id):
    """Start a new class session"""
    if request.method == 'POST':
        try:
            class_obj = Class.objects.get(id=class_id, teacher=request.user)
            print(f"[DEBUG] Starting class session for: {class_obj.subject_code}")
            
            active_session = ClassSession.objects.filter(class_obj=class_obj, status='active').first()
            if active_session:
                return JsonResponse({'error': 'A class session is already active for this class.'}, status=400)
            
            session = ClassSession.objects.create(
                class_obj=class_obj,
                teacher=request.user,
                status='active'
            )
            
            print(f"[DEBUG] Session created with ID: {session.id}")
            
            return JsonResponse({
                'success': True, 
                'message': 'Class session started successfully!',
                'session_id': session.id
            })
        except Class.DoesNotExist:
            return JsonResponse({'error': 'Class not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def end_class_session(request, session_id):
    """End an active class session"""
    if request.method == 'POST':
        try:
            session = ClassSession.objects.get(id=session_id, teacher=request.user, status='active')
            session.status = 'ended'
            session.end_time = timezone.now()
            session.save()
            
            return JsonResponse({'success': True, 'message': 'Class session ended successfully!'})
        except ClassSession.DoesNotExist:
            return JsonResponse({'error': 'Active session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def active_class_session(request, class_id):
    """Get active session for a class and display attendance page"""
    try:
        class_obj = Class.objects.get(id=class_id, teacher=request.user)
        active_session = ClassSession.objects.filter(class_obj=class_obj, status='active').first()
        
        if not active_session:
            messages.error(request, 'No active session for this class.')
            return redirect(f'/view_class/?class_id={class_id}')
        
        attendances = Attendance.objects.filter(session=active_session).select_related('student')
        enrollments = Enrollment.objects.filter(class_obj=class_obj).select_related('student')
        
        students_data = []
        for enrollment in enrollments:
            attendance = attendances.filter(student=enrollment.student).first()
            students_data.append({
                'id': enrollment.student.id,
                'name': enrollment.student.get_full_name(),
                'student_id': enrollment.student.student_id if hasattr(enrollment.student, 'student_id') else '',
                'status': attendance.status if attendance else 'Not yet tapped',
                'time_in': attendance.time_in.strftime('%I:%M %p') if attendance and attendance.time_in else None,
            })
        
        attendance_rate = int((len(attendances) / len(students_data)) * 100) if len(students_data) > 0 else 0
        
        context = {
            'class': class_obj,
            'session': active_session,
            'students': students_data,
            'total_students': len(students_data),
            'present_count': len(attendances),
            'attendance_rate': attendance_rate,
        }
        return render(request, 'active_class_session.html', context)
        
    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('classes')


@csrf_exempt
def record_attendance(request):
    """Record student attendance via RFID scanner - NO LOGIN REQUIRED"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            session_id = data.get('session_id')
            
            if not rfid_tag or not session_id:
                return JsonResponse({'error': 'Missing RFID tag or session ID'}, status=400)
            
            session = ClassSession.objects.get(id=session_id, status='active')
            
            student = User.objects.filter(rfid_tag=rfid_tag, user_type='student').first()
            if not student:
                return JsonResponse({'error': 'Student not found. Please register your RFID first.'}, status=404)
            
            enrollment = Enrollment.objects.filter(student=student, class_obj=session.class_obj).first()
            if not enrollment:
                return JsonResponse({'error': f'{student.get_full_name()} is not enrolled in this class.'}, status=403)
            
            if enrollment.status == 'dropped':
                return JsonResponse({'error': f'{student.get_full_name()} has been dropped from this class.'}, status=403)
            
            existing_attendance = Attendance.objects.filter(session=session, student=student).first()
            if existing_attendance:
                return JsonResponse({'error': f'{student.get_full_name()} already recorded attendance.'}, status=400)
            
            attendance = Attendance.objects.create(
                session=session,
                student=student,
                status='present'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Attendance recorded for {student.get_full_name()}',
                'student_name': student.get_full_name(),
                'time_in': attendance.time_in.strftime('%I:%M %p')
            })
            
        except ClassSession.DoesNotExist:
            return JsonResponse({'error': 'No active session found. Teacher needs to start the class first.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def get_active_session(request):
    """API endpoint for RFID reader to check active session - NO LOGIN REQUIRED"""
    active_session = ClassSession.objects.filter(status='active').first()
    
    if active_session:
        return JsonResponse({
            'has_active_session': True,
            'session_id': active_session.id,
            'class_name': active_session.class_obj.subject_description,
        })
    else:
        return JsonResponse({'has_active_session': False})


@login_required
def activity(request):
    return render(request, 'activity.html')


@login_required
def schedule(request):
    return render(request, 'schedule.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('adminLogin')