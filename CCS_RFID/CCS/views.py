from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import json
import logging
import re

from .forms import AdminLoginForm, StudentLoginForm, AdminRegistrationForm, StudentRegistrationForm
from .models import User, PendingRFID

logger = logging.getLogger(__name__)

# ============================================
# Validation function for Student ID and Email
# ============================================
def validate_student_registration_data(data):
    """
    Validate Student ID format and Email domain before form submission
    """
    errors = {}
    
    # Validate Student ID format (YYYY-XXXXX)
    student_id = data.get('student_id')
    if student_id:
        student_id_pattern = r'^\d{4}-\d{5}$'
        if not re.match(student_id_pattern, student_id):
            errors['student_id'] = 'Student ID must be in format: YYYY-XXXXX (e.g., 2022-00779)'
    
    # Validate Email domain (@wmsu.edu.ph)
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
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_tag = data.get('rfid_tag')
            student_id = data.get('student_id')
            
            if not rfid_tag:
                return JsonResponse({'error': 'No RFID tag provided'}, status=400)
            
            print(f"📇 RFID received: {rfid_tag}, Student ID: {student_id}")
            
            # CASE 1: This is for REGISTRATION (student_id is provided)
            if student_id:
                try:
                    student = User.objects.get(id=student_id, user_type='student')
                    
                    # Check if RFID is already used by another student
                    existing = User.objects.filter(rfid_tag=rfid_tag).exclude(id=student_id).first()
                    if existing:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'RFID tag already registered to another student'
                        }, status=400)
                    
                    # Assign RFID to student
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
            
            # CASE 2: This is for ATTENDANCE (no student_id)
            else:
                # Find student by RFID
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
                        'message': 'Student not found. Please register your RFID first.'
                    }, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"❌ RFID handler error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


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


# ============================================
# FIXED: Single studentRegistration function
# ============================================
def studentRegistration(request):
    if request.method == 'POST':
        print("=" * 50)
        print("Received POST data:")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        # Validate Student ID and Email FIRST
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
        
        # Check for duplicate Student ID
        student_id = request.POST.get('student_id')
        if student_id:
            existing_student_id = User.objects.filter(student_id=student_id).exists()
            if existing_student_id:
                print(f"❌ Duplicate Student ID: {student_id}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': 'Student ID already exists. Please use a different Student ID.'
                    }, status=400)
                else:
                    messages.error(request, 'Student ID already exists. Please use a different Student ID.')
                    return render(request, 'studentRegistration.html')
        
        # Check for duplicate Email
        email = request.POST.get('email')
        if email:
            existing_email = User.objects.filter(email=email).exists()
            if existing_email:
                print(f"❌ Duplicate Email: {email}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': 'Email already exists. Please use a different email address.'
                    }, status=400)
                else:
                    messages.error(request, 'Email already exists. Please use a different email address.')
                    return render(request, 'studentRegistration.html')
        
        form = StudentRegistrationForm(request.POST)
        
        if form.is_valid():
            print("Form is VALID")
            print(f"Cleaned data student_id: {form.cleaned_data.get('student_id')}")
            
            try:
                user = form.save()
                print(f"✅ User created with ID: {user.id}")
                print(f"✅ Student ID saved: {user.student_id}")
                
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
                import traceback
                traceback.print_exc()
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
                
                return JsonResponse({
                    'success': False, 
                    'error': ' | '.join(error_messages)
                }, status=400)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return render(request, 'studentRegistration.html')
    
    # GET request - just show the form
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
    return redirect('adminLogin')