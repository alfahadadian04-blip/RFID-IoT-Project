from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta  # Add 'datetime' here
import json
import logging
import re

from .forms import AdminLoginForm, StudentLoginForm, AdminRegistrationForm, StudentRegistrationForm
from .models import User, PendingRFID

# Add this import for the Class model
from classes.models import Class

logger = logging.getLogger(__name__)

# Simple in-memory storage for latest RFID (for claiming existing accounts)
latest_rfid_tag = None


def login_page(request):
    """Single unified login page"""
    # If user is already logged in, redirect to appropriate dashboard
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('dashboard')
        elif request.user.user_type == 'student':
            return redirect('stud_dashboard')
    return render(request, 'login.html')


# ============================================
# Validation function for Student ID and Email
# ============================================
def validate_student_registration_data(data):
    """
    Validate Student ID format and Email domain before form submission
    """
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


@csrf_exempt
def rfid_handler(request):
    """
    API endpoint that receives RFID data from Arduino
    Handles both attendance (no student_id) and registration (with student_id)
    """
    global latest_rfid_tag
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            student_id = data.get('student_id')
            
            if not rfid_tag:
                return JsonResponse({'error': 'No RFID tag provided'}, status=400)
            
            # Store the latest RFID tag for claiming existing accounts
            latest_rfid_tag = rfid_tag
            
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
                    # Check if there's an active session
                    try:
                        from classes.models import ClassSession
                        active_session = ClassSession.objects.filter(status='active').first()
                        if active_session:
                            # Record attendance
                            from classes.models import Attendance
                            Attendance.objects.get_or_create(
                                session=active_session,
                                student=student,
                                defaults={'status': 'present'}
                            )
                            print(f"✅ Attendance recorded for: {student.get_full_name()}")
                            return JsonResponse({
                                'status': 'success',
                                'name': student.get_full_name(),
                                'action': 'attendance_recorded'
                            })
                        else:
                            print(f"✅ RFID recognized: {student.get_full_name()} (no active session)")
                            return JsonResponse({
                                'status': 'success',
                                'name': student.get_full_name(),
                                'action': 'rfid_recognized'
                            })
                    except ImportError:
                        print(f"✅ RFID recognized: {student.get_full_name()}")
                        return JsonResponse({
                            'status': 'success',
                            'name': student.get_full_name(),
                            'action': 'rfid_recognized'
                        })
                else:
                    print(f"❌ No student found with RFID: {rfid_tag}")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Student not found. Please register your RFID first.'
                    }, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"❌ RFID handler error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def receive_rfid(request):
    """Receive RFID tap from reader and store temporarily for claiming accounts"""
    global latest_rfid_tag
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latest_rfid_tag = data.get('rfid_tag')
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def get_latest_rfid(request):
    """Get the latest RFID tag that was tapped"""
    global latest_rfid_tag
    return JsonResponse({'rfid_tag': latest_rfid_tag})


@csrf_exempt
def check_user_by_rfid(request):
    """Check if a user exists with the given RFID tag"""
    rfid_tag = request.GET.get('rfid_tag')
    if rfid_tag:
        user = User.objects.filter(rfid_tag=rfid_tag, user_type='student').first()
        if user:
            return JsonResponse({
                'exists': True,
                'name': user.get_full_name(),
                'student_id': user.student_id
            })
    return JsonResponse({'exists': False})


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


@csrf_exempt
def claim_existing_account(request):
    """Claim existing student account by tapping RFID card"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            student_id = data.get('student_id')
            email = data.get('email')
            
            if not rfid_tag:
                return JsonResponse({'error': 'No RFID tag provided'}, status=400)
            
            # Find the existing user by Student ID or Email
            user = None
            if student_id:
                user = User.objects.filter(student_id=student_id, user_type='student').first()
            elif email:
                user = User.objects.filter(email=email, user_type='student').first()
            
            if not user:
                return JsonResponse({'error': 'Account not found'}, status=404)
            
            # Check if RFID is already used by another student
            existing = User.objects.filter(rfid_tag=rfid_tag).exclude(id=user.id).first()
            if existing:
                return JsonResponse({'error': 'RFID tag already registered to another student'}, status=400)
            
            # Assign RFID to the existing account
            user.rfid_tag = rfid_tag
            
            # If this account didn't have a Student ID yet, set it
            if student_id and not user.student_id:
                user.student_id = student_id
            
            # If this account didn't have an email yet, set it
            if email and not user.email:
                user.email = email
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Account claimed successfully! You can now login with your RFID card.',
                'user_id': user.id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def adminLogin(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('dashboard')
        else:
            return redirect('stud_dashboard')
    
    # Redirect to unified login page
    return redirect('login_page')


def studentLogin(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.user_type == 'student':
            return redirect('stud_dashboard')
        else:
            return redirect('dashboard')
    
    # Redirect to unified login page
    return redirect('login_page')


def studentLogin(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.user_type == 'student':
            return redirect('stud_dashboard')
        else:
            return redirect('dashboard')
    
    # Redirect to unified login page instead of rendering a non-existent template
    return redirect('login_page')


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


# ============================================
# UPDATED: studentRegistration with modal popup for RFID claim
# ============================================
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
        email = request.POST.get('email')
        
        # Check if student already exists by Student ID
        existing_user_by_student_id = User.objects.filter(student_id=student_id).first() if student_id else None
        
        # Check if email already exists
        existing_user_by_email = User.objects.filter(email=email).first() if email else None
        
        # If student exists by Student ID, return existing user info for modal
        if existing_user_by_student_id:
            print(f"⚠️ Student ID {student_id} already exists.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'exists': True,
                    'type': 'student_id',
                    'student_id': student_id,
                    'user_id': existing_user_by_student_id.id,
                    'email': existing_user_by_student_id.email,
                    'message': f'Student ID {student_id} already exists. Tap your RFID card to claim this account.'
                }, status=200)
            else:
                messages.warning(request, f'Student ID {student_id} already exists. Please contact administrator.')
                return render(request, 'studentRegistration.html')
        
        # If email exists but no Student ID, return existing user info for modal
        if existing_user_by_email and not existing_user_by_email.student_id:
            print(f"⚠️ Email {email} exists but has no Student ID.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'exists': True,
                    'type': 'email',
                    'email': email,
                    'user_id': existing_user_by_email.id,
                    'student_id': existing_user_by_email.student_id,
                    'message': f'Email {email} already exists. Tap your RFID card to claim this account.'
                }, status=200)
            else:
                messages.warning(request, f'Email {email} already exists. Please contact administrator.')
                return render(request, 'studentRegistration.html')
        
        # If email exists and already has Student ID
        if existing_user_by_email and existing_user_by_email.student_id:
            print(f"⚠️ Email {email} already registered to {existing_user_by_email.student_id}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Email already registered to another student. Please use a different email.'
                }, status=400)
            else:
                messages.error(request, 'Email already registered to another student.')
                return render(request, 'studentRegistration.html')
        
        # NEW STUDENT - neither Student ID nor Email exists
        print("✅ Creating new student account...")
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
                    messages.success(request, 'Student account created successfully! Please scan your RFID card.')
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


@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})


@login_required
def attendance(request):
    return render(request, 'attendance.html')


@login_required
def classes(request):
    return render(request, 'classes.html')


@login_required
def activity(request):
    return render(request, 'activity.html')


@login_required
def schedule(request):
    return render(request, 'schedule.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login_page')


@login_required
def get_upcoming_classes(request):
    """API endpoint to get classes that are starting soon"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    now = timezone.now()
    current_date = now.date()
    
    # Get all classes for the teacher
    user_classes = Class.objects.filter(teacher=request.user)
    
    upcoming_notifications = []
    
    for class_obj in user_classes:
        class_start_time = class_obj.time_from
        class_day = class_obj.day.lower()
        
        # Get current day of week
        current_day = current_date.strftime('%A').lower()
        
        # Check if class is today
        if class_day not in current_day:
            continue
        
        # Combine date and time
        class_start_datetime = datetime.combine(current_date, class_start_time)
        class_start_datetime = timezone.make_aware(class_start_datetime)
        
        # Calculate time difference in minutes
        time_diff = (class_start_datetime - now).total_seconds() / 60
        
        # Check for thresholds (60, 30, 10 minutes)
        thresholds = [60, 30, 10]
        
        for threshold in thresholds:
            if 0 < time_diff <= threshold + 5:
                notification_key = f'notified_{class_obj.id}_{threshold}'
                
                if not request.session.get(notification_key, False):
                    upcoming_notifications.append({
                        'class_id': class_obj.id,
                        'class_name': class_obj.subject_code,
                        'class_description': class_obj.subject_description,
                        'room': class_obj.room,
                        'start_time': class_start_time.strftime('%I:%M %p'),
                        'minutes_until': round(time_diff),
                        'threshold': threshold,
                        'url': f'/view_class/?class_id={class_obj.id}',
                        'notification_key': notification_key
                    })
    
    return JsonResponse({
        'success': True,
        'notifications': upcoming_notifications
    })


@login_required
def dismiss_notification(request):
    """Mark a notification as dismissed so it doesn't show again"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            class_id = data.get('class_id')
            threshold = data.get('threshold')
            
            if class_id and threshold:
                notification_key = f'notified_{class_id}_{threshold}'
                request.session[notification_key] = True
                request.session.modified = True
                return JsonResponse({'success': True})
            
            return JsonResponse({'error': 'Missing data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=400)


@csrf_exempt
def api_login(request):
    """API endpoint for login"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                # Check user type and redirect accordingly
                if user.user_type == 'superadmin':
                    return JsonResponse({
                        'success': True,
                        'user_type': user.user_type,
                        'redirect_url': '/dashboard/'
                    })
                elif user.user_type == 'admin':
                    return JsonResponse({
                        'success': True,
                        'user_type': user.user_type,
                        'redirect_url': '/dashboard/'
                    })
                elif user.user_type == 'student':
                    return JsonResponse({
                        'success': True,
                        'user_type': user.user_type,
                        'redirect_url': '/stud_dashboard/'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Unknown user type'
                    }, status=401)
            else:
                return JsonResponse({'success': False, 'error': 'Invalid email or password'}, status=401)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@csrf_exempt
def clear_pending_rfid(request):
    """Clear pending RFID registration"""
    if request.method == 'POST':
        try:
            PendingRFID.objects.all().delete()
            return JsonResponse({'success': True, 'message': 'Pending registrations cleared'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)