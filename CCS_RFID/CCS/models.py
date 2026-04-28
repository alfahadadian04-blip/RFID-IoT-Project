from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')
        
        return self.create_user(email, password, **extra_fields)


# Custom User Model
class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('student', 'Student'),
    )
    
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Prefer not to say', 'Prefer not to say'),
    )
    
    CIVIL_STATUS_CHOICES = (
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
    )
    
    COLLEGE_CHOICES = (
        ('College of Computing Studies', 'College of Computing Studies'),
    )
    
    DEPARTMENT_CHOICES = (
        ('Information Technology', 'Information Technology'),
        ('Computer Science', 'Computer Science'),
        ('ACT Application Development', 'ACT Application Development'),
        ('ACT Networking', 'ACT Networking'),
    )
    
    COURSE_CHOICES = (
        ('BS Information Technology', 'BS Information Technology'),
        ('BS Computer Science', 'BS Computer Science'),
        ('Application Development', 'Application Development'),
        ('Networking', 'Networking'),
    )
    
    # Student ID FIELD
    student_id = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{4}-\d{5}$',
                message='Student ID must be in format: YYYY-XXXXX (e.g., 2022-00779)'
            )
        ],
        help_text="Format: YYYY-XXXXX (e.g., 2022-00779)"
    )
    
    # Authentication fields
    email = models.EmailField(
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[^\s@]+@wmsu\.edu\.ph$',
                message='Only @wmsu.edu.ph email addresses are allowed'
            )
        ]
    )
    password = models.CharField(max_length=128)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)

    # RFID field
    rfid_tag = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    civil_status = models.CharField(max_length=20, choices=CIVIL_STATUS_CHOICES, blank=True)
    
    # Contact Information
    contact_person = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    
    # Academic Information
    college = models.CharField(max_length=50, choices=COLLEGE_CHOICES, blank=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True)
    course = models.CharField(max_length=50, choices=COURSE_CHOICES, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']
    
    class Meta:
        db_table = 'users'
        default_related_name = 'ccs_users'
    
    def __str__(self):
        return f"{self.email} - {self.get_full_name()}"
    
    def get_full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name


class PendingRFID(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    class Meta:
        ordering = ['-created_at']