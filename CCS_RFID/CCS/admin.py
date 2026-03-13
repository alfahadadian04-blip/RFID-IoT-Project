from django.contrib import admin
from .models import User

# Register your models here
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'gender', 'civil_status', 'college', 'department']
    search_fields = ['email', 'first_name', 'last_name', 'rfid_tag']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password', 'user_type')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'date_of_birth', 'gender', 'civil_status')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_number')
        }),
        ('Academic Information', {
            'fields': ('college', 'department', 'course', 'rfid_tag')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']