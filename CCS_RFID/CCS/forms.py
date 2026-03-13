from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User

class AdminLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full py-[11px] pl-[38px] pr-10 border-[1.5px] border-[#e0dbd4] rounded-lg font-dmsans text-[14px]',
            'placeholder': 'Enter your email',
            'id': 'emailInput'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-[11px] pl-[38px] pr-10 border-[1.5px] border-[#e0dbd4] rounded-lg font-dmsans text-[14px]',
            'placeholder': 'Enter your password',
            'id': 'passwordInput'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'password']

class StudentLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full py-[11px] pl-[38px] pr-10 border-[1.5px] border-[#e0dbd4] rounded-lg font-dmsans text-[14px]',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-[11px] pl-[38px] pr-10 border-[1.5px] border-[#e0dbd4] rounded-lg font-dmsans text-[14px]',
            'placeholder': 'Enter your password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'password']

class AdminRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
            'placeholder': 'Create a password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
            'placeholder': 'Re-enter password'
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'middle_name', 'last_name', 'email',
            'date_of_birth', 'gender', 'civil_status',
            'contact_person', 'contact_number', 'college', 
            'department', 'course'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'First Name',
                'id': 'firstName'
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Middle Name',
                'id': 'middleName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Last Name',
                'id': 'lastName'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Email Address',
                'id': 'email'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'id': 'dateOfBirth'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'gender'
            }),
            'civil_status': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'civilStatus'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Contact Person',
                'id': 'contactPerson'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Contact Number',
                'id': 'contactNumber'
            }),
            'college': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'college'
            }),
            'department': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'department'
            }),
            'course': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'course'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.user_type = 'admin'
        if commit:
            user.save()
        return user

class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
            'placeholder': 'Create a password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
            'placeholder': 'Re-enter password'
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'middle_name', 'last_name', 'email',
            'date_of_birth', 'gender', 'civil_status',
            'contact_person', 'contact_number', 'college', 
            'department', 'course'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'First Name',
                'id': 'firstName'
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Middle Name',
                'id': 'middleName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Last Name',
                'id': 'lastName'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Email Address',
                'id': 'email'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'id': 'dateOfBirth'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'gender'
            }),
            'civil_status': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'civilStatus'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Contact Person',
                'id': 'contactPerson'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg',
                'placeholder': 'Contact Number',
                'id': 'contactNumber'
            }),
            'college': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'college'
            }),
            'department': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'department'
            }),
            'course': forms.Select(attrs={
                'class': 'w-full py-3 px-4 border-[1.5px] border-[#e0dbd4] rounded-lg appearance-none',
                'id': 'course'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.user_type = 'student'  # Set as student (changed from admin)
        if commit:
            user.save()
        return user