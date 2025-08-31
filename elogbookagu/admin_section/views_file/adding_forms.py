from django import forms
from admin_section.models import ActivityType, CoreDiaProSession, Department

import logging

logger = logging.getLogger(__name__)


class ActivityTypeForm(forms.ModelForm):
    # Adding an advanced field not in the model
    is_advanced = forms.BooleanField(
        label="Advanced Activity",
        required=False,
        help_text="Check if this is an advanced activity type",
    )

    class Meta:
        model = ActivityType
        fields = ["name", "department"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:text-white",
                    "placeholder": "Enter activity type name",
                }
            ),
            "department": forms.Select(
                attrs={
                    "class": "w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:text-white"
                }
            ),
        }
        labels = {
            "name": "Activity Name",
            "department": "Department",
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        department = cleaned_data.get("department")

        # Check for uniqueness
        if ActivityType.objects.filter(name=name, department=department).exists():
            raise forms.ValidationError(
                "An activity type with this name already exists in this department."
            )
        return cleaned_data


class CoreDiaProSessionForm(forms.ModelForm):
    class Meta:
        model = CoreDiaProSession
        fields = ['name', 'department', 'activity_type']
        widgets = {
            'department': forms.Select(attrs={
                'class': 'form-select',
                'id': 'department-select'
            }),
            'activity_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'activity-type-select'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance (editing mode)
        if self.instance.pk:
            self.fields['activity_type'].queryset = ActivityType.objects.filter(
                department=self.instance.department
            )
            # Don't disable activity_type in edit mode
            self.fields['activity_type'].widget.attrs.pop('disabled', None)
        else:
            # Only disable in create mode
            self.fields['activity_type'].widget.attrs['disabled'] = 'disabled'
        
        # If we have initial data with department
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['activity_type'].queryset = ActivityType.objects.filter(
                    department_id=department_id
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        department = cleaned_data.get("department")
        activity_type = cleaned_data.get("activity_type")
        
        if department and activity_type and activity_type.department != department:
            raise forms.ValidationError(
                "Selected activity type does not belong to the selected department."
            )

        logger.debug(
            "Data provided for a new session: name=%s, department=%s, activity_type=%s",
            name,
            department.name if department else None,
            activity_type.name if activity_type else None
        )

        try:
            if self.instance.pk:
                existing_sessions = CoreDiaProSession.objects.exclude(
                    pk=self.instance.pk
                )
            else:
                existing_sessions = CoreDiaProSession.objects.all()

            if existing_sessions.filter(
                name=name, department=department, activity_type=activity_type
            ).exists():
                raise forms.ValidationError(
                    "A session with this name already exists for this department and activity type."
                )
        except Exception as e:
            logger.error(
                "Error validating unique fields for session: name=%s, department=%s, activity_type=%s, error=%s",
                name,
                department.name if department else None,
                activity_type.name if activity_type else None,
                str(e)
            )
            raise forms.ValidationError(
                "An error was raised while validating uniqueness"
            )
        return cleaned_data
