from django import forms
from django.utils import timezone
from datetime import date, timedelta
from student_section.models import StudentLogFormModel, SupportTicket
from accounts.models import CustomUser, Student
from .models import StaffSupportTicket, StaffEmergencyAttendance
from admin_section.models import Department, TrainingSite, Group

class StaffSupportTicketForm(forms.ModelForm):
    class Meta:
        model = StaffSupportTicket
        fields = ['subject', 'description']
        widgets = {
            'subject': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter subject of your issue',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32',
                    'placeholder': 'Describe your issue in detail',
                }
            ),
        }


class AdminStaffResponseForm(forms.ModelForm):
    class Meta:
        model = StaffSupportTicket
        fields = ['status', 'admin_comments']
        widgets = {
            'status': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                }
            ),
            'admin_comments': forms.Textarea(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32',
                    'placeholder': 'Enter your response to the staff member',
                }
            ),
        }


class LogReviewForm(forms.ModelForm):
    REVIEW_CHOICES = [
        (True, 'Approve'),
        (False, 'Reject')
    ]

    is_approved = forms.ChoiceField(
        choices=REVIEW_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}),
        initial=True,
        required=True
    )

    class Meta:
        model = StudentLogFormModel
        fields = ['reviewer_comments']
        widgets = {
            'reviewer_comments': forms.Textarea(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32',
                    'placeholder': 'Enter your comments (optional)',
                }
            ),
        }


class BatchReviewForm(forms.Form):
    log_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve Selected'),
            ('reject', 'Reject Selected')
        ],
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}),
        initial='approve'
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32',
                'placeholder': 'Enter comments for all selected logs (optional)',
            }
        )
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['city', 'country', 'phone_no', 'bio', 'profile_photo']
        widgets = {
            'city': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter your city',
                }
            ),
            'country': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter your country',
                }
            ),
            'phone_no': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter your phone number',
                }
            ),
            'bio': forms.Textarea(
                attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32',
                    'placeholder': 'Tell us about yourself',
                    'rows': 4,
                }
            ),
            'profile_photo': forms.FileInput(
                attrs={
                    'class': 'hidden',
                    'id': 'profile-photo-input',
                    'accept': 'image/*',
                }
            ),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            # Validate file size (120KB = 120 * 1024 bytes)
            max_size = 120 * 1024  # 120KB in bytes
            if photo.size > max_size:
                raise forms.ValidationError(
                    f"File size too large. Maximum allowed size is 120KB. Your file is {photo.size // 1024}KB."
                )

            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if photo.content_type not in allowed_types:
                raise forms.ValidationError(
                    "Invalid file type. Only JPEG, PNG, and GIF images are allowed."
                )

        return photo


class EmergencyAttendanceForm(forms.Form):
    """Form for taking emergency attendance of students"""
    department = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        empty_label="Select Department",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
        })
    )

    training_site = forms.ModelChoiceField(
        queryset=TrainingSite.objects.all(),
        empty_label="Select Training Site (Optional)",
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
        })
    )

    attendance_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
        })
    )

    def __init__(self, staff=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if staff:
            # Get departments where this staff is mapped
            self.fields['department'].queryset = staff.departments.all()

            # If only one department, select it by default
            if staff.departments.count() == 1:
                self.fields['department'].initial = staff.departments.first()

    def clean_attendance_date(self):
        attendance_date = self.cleaned_data.get('attendance_date')
        today = date.today()

        # Allow any date for emergency attendance (past, present, or future)
        # But add validation for reasonable date range
        if attendance_date:
            # Don't allow dates more than 1 year in the past or future
            one_year_ago = today - timedelta(days=365)
            one_year_future = today + timedelta(days=365)

            if attendance_date < one_year_ago:
                raise forms.ValidationError("Date cannot be more than 1 year in the past.")
            if attendance_date > one_year_future:
                raise forms.ValidationError("Date cannot be more than 1 year in the future.")

        return attendance_date


class StudentEmergencyAttendanceForm(forms.ModelForm):
    """Form for individual student emergency attendance"""
    class Meta:
        model = StaffEmergencyAttendance
        fields = ['status', 'notes']
        widgets = {
            'status': forms.RadioSelect(attrs={
                'class': 'mr-2'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                'rows': 2,
                'placeholder': 'Optional notes'
            })
        }
