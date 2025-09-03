from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import StudentLogFormModel, SupportTicket
from admin_section.models import Department, ActivityType, CoreDiaProSession, DateRestrictionSettings, TrainingSite, MappedAttendance
from accounts.models import Doctor, Student




class StudentLogFormModelForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                "id": "id_department",
            }
        ),
        empty_label="Select Department",
    )

    activity_type = forms.ModelChoiceField(
        queryset=ActivityType.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                "id": "id_activity_type",
            }
        ),
        empty_label="Select Activity Type",
    )

    core_diagnosis = forms.ModelChoiceField(
        queryset=CoreDiaProSession.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                "id": "id_core_diagnosis",
            }
        ),
        empty_label="Select Core Diagnosis",
    )

    tutor = forms.ModelChoiceField(
        queryset=Doctor.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                "id": "id_tutor",
            }
        ),
        empty_label="Select Tutor",
    )

    training_site = forms.ModelChoiceField(
        queryset=TrainingSite.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                "id": "id_training_site",
            }
        ),
        empty_label="Select Training Site",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.user = user
        if user and hasattr(user, "student"):
            student = user.student
            log_year_section = student.group.log_year_section if student.group else None

            if log_year_section:
                # Department queryset
                self.fields["department"].queryset = Department.objects.filter(
                    log_year=student.group.log_year
                )

                # Training Site queryset
                if student.group:
                    mapped_training_sites = MappedAttendance.objects.filter(
                        groups=student.group,
                        is_active=True
                    ).values_list('training_site', flat=True).distinct()
                    self.fields["training_site"].queryset = TrainingSite.objects.filter(
                        id__in=mapped_training_sites
                    ).order_by('name')
                else:
                    self.fields["training_site"].queryset = TrainingSite.objects.none()

                # Department selection logic
                department = None
                if self.instance.pk and self.instance.department:
                    department = self.instance.department
                elif "department" in self.data:
                    try:
                        department_id = self.data.get("department")
                        department = Department.objects.get(id=department_id)
                    except (ValueError, Department.DoesNotExist):
                        pass

                if department:
                    # Activity Type queryset based on department
                    self.fields["activity_type"].queryset = ActivityType.objects.filter(
                        department=department
                    ).order_by('name')
                    # Tutor queryset based on department
                    self.fields["tutor"].queryset = Doctor.objects.filter(
                        departments=department
                    ).distinct()
                    
                    # Activity Type selection logic
                    activity_type = None
                    if self.instance.pk and self.instance.activity_type:
                        activity_type = self.instance.activity_type
                    elif "activity_type" in self.data:
                        try:
                            activity_type_id = self.data.get("activity_type")
                            activity_type = ActivityType.objects.get(id=activity_type_id)
                        except (ValueError, ActivityType.DoesNotExist):
                            pass

                    if activity_type:
                        self.fields["core_diagnosis"].queryset = CoreDiaProSession.objects.filter(
                            activity_type=activity_type
                        )
                    else:
                        self.fields["core_diagnosis"].queryset = CoreDiaProSession.objects.none()
                else:
                    self.fields["activity_type"].queryset = ActivityType.objects.none()
                    self.fields["core_diagnosis"].queryset = CoreDiaProSession.objects.none()
                    self.fields["tutor"].queryset = Doctor.objects.none()
            else:
                self.fields["department"].queryset = Department.objects.none()
                self.fields["activity_type"].queryset = ActivityType.objects.none()
                self.fields["core_diagnosis"].queryset = CoreDiaProSession.objects.none()
                self.fields["tutor"].queryset = Doctor.objects.none()
                self.fields["training_site"].queryset = TrainingSite.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        activity_type = cleaned_data.get("activity_type")
        core_diagnosis = cleaned_data.get("core_diagnosis")
        tutor = cleaned_data.get("tutor")
        date = cleaned_data.get("date")

        # Validate department, activity type, core diagnosis, and tutor
        if department:
            activity_types = ActivityType.objects.filter(department=department)
            tutors = Doctor.objects.filter(departments=department).distinct()

            if activity_type and activity_type not in activity_types:
                self.add_error("activity_type", "Choose the correct option. That option is not one of the available choices")

            if activity_type:
                core_diagnoses = CoreDiaProSession.objects.filter(activity_type=activity_type)
                if core_diagnosis and core_diagnosis not in core_diagnoses:
                    self.add_error("core_diagnosis", "Choose the correct option. That option is not one of the available choices")

            if tutor and tutor not in tutors:
                self.add_error("tutor", "Choose the correct option. That option is not one of the available choices")

        # Validate date based on date restriction settings
        if date:
            today = timezone.now().date()
            request = self.request if hasattr(self, 'request') else None

            try:
                settings = DateRestrictionSettings.objects.first()
                if not settings:
                    settings = DateRestrictionSettings.objects.create(
                        past_days_limit=7,
                        allow_future_dates=False,
                        future_days_limit=0
                    )

                is_active = True
                if request and hasattr(request, 'session'):
                    is_active = request.session.get('date_restrictions_active', True)
                else:
                    is_active = True

                if not is_active:
                    return cleaned_data

            except Exception:
                past_days_limit = 7
                allow_future_dates = False
                future_days_limit = 0
                allowed_days = [0, 1, 2, 3, 4, 5, 6]
                is_active = True
            else:
                past_days_limit = settings.past_days_limit
                allow_future_dates = settings.allow_future_dates
                future_days_limit = settings.future_days_limit

                if request and hasattr(request, 'session'):
                    allowed_days_str = request.session.get('allowed_days_for_students', '0,1,2,3,4,5,6')
                    allowed_days = [int(day) for day in allowed_days_str.split(',') if day.strip()]
                else:
                    allowed_days = [0, 1, 2, 3, 4, 5, 6]

                if not is_active:
                    return cleaned_data

                day_of_week = date.weekday()
                if day_of_week not in allowed_days:
                    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    self.add_error("date", f"Logs cannot be submitted on {day_names[day_of_week]}. Please select an allowed day.")

                earliest_allowed_date = today - timedelta(days=past_days_limit)
                if date < earliest_allowed_date:
                    self.add_error("date", f"Date cannot be more than {past_days_limit} days in the past.")

                if date > today and not allow_future_dates:
                    self.add_error("date", "Future dates are not allowed.")

                if date > today and allow_future_dates:
                    latest_allowed_date = today + timedelta(days=future_days_limit)
                    if date > latest_allowed_date:
                        self.add_error("date", f"Date cannot be more than {future_days_limit} days in the future.")

        # Check attendance validation
        if date and self.user and hasattr(self.user, 'student'):
            student = self.user.student
            training_site = cleaned_data.get('training_site')

            if training_site:
                from doctor_section.models import StudentAttendance
                attendance = StudentAttendance.objects.filter(
                    student=student,
                    training_site=training_site,
                    date=date,
                    status='present'
                ).first()

                if not attendance:
                    any_attendance = StudentAttendance.objects.filter(
                        student=student,
                        training_site=training_site,
                        date=date
                    ).first()

                    if any_attendance and any_attendance.status == 'absent':
                        self.add_error("date", f"You were marked absent on {date.strftime('%B %d, %Y')} at {training_site.name}. You cannot submit logs for days when you were absent.")
                    else:
                        self.add_error("date", f"No attendance record found for {date.strftime('%B %d, %Y')} at {training_site.name}. Please ensure your attendance was marked as present before submitting logs by your Tutor Or Arabian Gulf University.")

        return cleaned_data

    class Meta:
        model = StudentLogFormModel
        fields = [
            "date",
            "department",
            "tutor",
            "training_site",
            "activity_type",
            "core_diagnosis",
            "patient_id",
            "patient_age",
            "patient_gender",
            "description",
            "participation_type",
        ]
        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                }
            ),
            "patient_id": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                    "placeholder": "Enter patient ID",
                }
            ),
            "patient_age": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                    "placeholder": "Enter patient age",
                    "type": "number",
                    "min": "0",
                    "max": "120",
                }
            ),
            "patient_gender": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white h-32",
                    "placeholder": "Enter description",
                }
            ),
            "participation_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                }
            ),
        }

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
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


class AdminResponseForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
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
                    'placeholder': 'Enter your response to the student',
                }
            ),
        }
