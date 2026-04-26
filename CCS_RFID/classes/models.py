from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Class(models.Model):
    # Subject Info
    subject_code = models.CharField(max_length=20)
    subject_description = models.CharField(max_length=200)
    college = models.CharField(max_length=200)
    semester = models.CharField(max_length=20, blank=True, null=True)
    school_year = models.CharField(max_length=20, blank=True, null=True)
    student_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Schedule
    day = models.CharField(max_length=50)
    time_from = models.TimeField()
    time_to = models.TimeField()
    room = models.CharField(max_length=50)
    
    # Class Info
    program = models.CharField(max_length=50)
    section = models.CharField(max_length=100)
    class_size = models.IntegerField(default=0)
    
    # Teacher who uploaded/manages this class
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'user_type': 'admin'})
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ['subject_code', 'section', 'semester', 'school_year', 'day', 'time_from', 'time_to']
        ]
        ordering = ['-created_at']
        verbose_name_plural = "Classes"
    
    def __str__(self):
        return f"{self.subject_code} - {self.section} ({self.day} {self.time_from.strftime('%I:%M %p')} - {self.time_to.strftime('%I:%M %p')})"
    
    @property
    def total_students(self):
        return self.enrollments.count()
    
    @property
    def present_today(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.enrollments.filter(attendance_records__date=today, attendance_records__status='present').count()
    
    @property
    def absent_today(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.enrollments.filter(attendance_records__date=today, attendance_records__status='absent').count()
    
    @property
    def late_today(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.enrollments.filter(attendance_records__date=today, attendance_records__status='late').count()


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('dropped', 'Dropped'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    absence_count = models.IntegerField(default=0)
    enrolled_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'class_obj']
        ordering = ['-enrolled_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_obj.subject_code} ({self.status})"
    
    @property
    def is_dropped(self):
        return self.status == 'dropped'
    
    def mark_absent(self, save=True):
        """Increment absence count and auto-drop if reaches 5"""
        if not self.is_dropped:
            self.absence_count += 1
            if self.absence_count >= 5:
                self.status = 'dropped'
            if save:
                self.save()
        return self.absence_count


class ClassSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sessions')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'admin'})
    start_time = models.DateTimeField(auto_now_add=True)  # This will now use local time
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    def __str__(self):
        return f"{self.class_obj.subject_code} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_active(self):
        return self.status == 'active'


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]
    
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    time_in = models.DateTimeField(auto_now_add=True)  # This will now use local time
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    class Meta:
        unique_together = ['session', 'student']
        ordering = ['-time_in']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.session.class_obj.subject_code} - {self.time_in.strftime('%I:%M %p')}"
    
    @property
    def time_formatted(self):
        return self.time_in.strftime('%I:%M %p')
    
    @property
    def date_formatted(self):
        return self.time_in.strftime('%B %d, %Y')
    
class ClassPDFReport(models.Model):
    """Store generated PDF reports for class sessions"""
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='pdf_reports')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='pdf_reports')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'admin'})
    pdf_file = models.FileField(upload_to='attendance_reports/%Y/%m/%d/', max_length=500)
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)  # Size in bytes
    generated_at = models.DateTimeField(auto_now_add=True)
    total_students = models.IntegerField(default=0)
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    attendance_rate = models.FloatField(default=0)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name_plural = "Class PDF Reports"
    
    def __str__(self):
        return f"{self.class_obj.subject_code} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def file_size_kb(self):
        return f"{self.file_size / 1024:.1f} KB"
    
    @property
    def formatted_date(self):
        return self.generated_at.strftime('%B %d, %Y at %I:%M %p')