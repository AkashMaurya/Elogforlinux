from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django import forms
import csv
import io
from accounts.models import CustomUser, Doctor
from admin_section.models import Department
from admin_section.forms import DoctorUserForm, DoctorForm, AssignDoctorToDepartmentForm, BulkDoctorUploadForm


@login_required
def add_doctor(request):
    # Check if user is admin
    if request.user.role != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('admin_section:admin_dash')
    # Initialize forms
    user_form = DoctorUserForm()
    doctor_form = DoctorForm()
    bulk_form = BulkDoctorUploadForm()
    assign_form = AssignDoctorToDepartmentForm()
    bulk_results = None

    # Handle form submissions
    if request.method == 'POST':
        # Check which form was submitted
        if 'add_doctor' in request.POST:
            # Individual doctor addition
            user_form = DoctorUserForm(request.POST)
            doctor_form = DoctorForm(request.POST)

            if user_form.is_valid() and doctor_form.is_valid():
                try:
                    with transaction.atomic():
                        # Create user with doctor role
                        user = user_form.save(commit=False)
                        user.role = 'doctor'
                        user.save()

                        # Create doctor profile
                        doctor = doctor_form.save(commit=False)
                        doctor.user = user
                        doctor.save()

                        # Add departments (many-to-many relationship)
                        if doctor_form.cleaned_data.get('departments'):
                            doctor.departments.set(doctor_form.cleaned_data['departments'])

                        messages.success(request, f'Doctor {user.first_name} {user.last_name} added successfully!')
                        return redirect('admin_section:add_doctor')
                except Exception as e:
                    messages.error(request, f'Error adding doctor: {str(e)}')

        elif 'bulk_upload' in request.POST:
            # Bulk doctor upload
            bulk_form = BulkDoctorUploadForm(request.POST, request.FILES)
            if bulk_form.is_valid():
                csv_file = request.FILES['csv_file']
                department = bulk_form.cleaned_data['department']

                # Validate file size (5MB limit)
                if csv_file.size > 5 * 1024 * 1024:
                    messages.error(request, 'File size must be less than 5MB')
                    return redirect('admin_section:add_doctor')

                try:
                    decoded_file = csv_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    messages.error(request, 'Please upload a valid CSV file')
                    return redirect('admin_section:add_doctor')

                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)

                required_fields = ['username', 'email', 'password', 'first_name',
                                 'last_name', 'phone_no', 'city', 'country', 'speciality', 'bio']

                # Validate required fields
                headers = reader.fieldnames
                if not headers:
                    messages.error(request, 'CSV file is empty or has no headers')
                    return redirect('admin_section:add_doctor')

                missing_fields = [field for field in required_fields if field not in headers]
                if missing_fields:
                    messages.error(request, f'Missing required fields: {", ".join(missing_fields)}')
                    return redirect('admin_section:add_doctor')

                # Process CSV data
                success_count = 0
                error_count = 0
                errors = []

                for row in reader:
                    try:
                        with transaction.atomic():
                            # Create user
                            user = CustomUser.objects.create(
                                username=row['username'].strip(),
                                email=row['email'].strip(),
                                password=make_password(row['password'].strip()),
                                first_name=row['first_name'].strip(),
                                last_name=row['last_name'].strip(),
                                phone_no=row['phone_no'].strip(),
                                city=row['city'].strip(),
                                country=row['country'].strip(),
                                speciality=row.get('speciality', '').strip(),
                                bio=row.get('bio', '').strip(),
                                role='doctor'
                            )

                            # Create doctor profile
                            doctor = Doctor.objects.create(user=user)

                            # Add to department
                            doctor.departments.add(department)

                            success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {reader.line_num}: {str(e)}")

                # Prepare results for display
                bulk_results = {
                    'success_count': success_count,
                    'error_count': error_count,
                    'errors': errors[:10]  # Limit to first 10 errors
                }

                if success_count > 0:
                    messages.success(request, f'Successfully added {success_count} doctors')
                if error_count > 0:
                    messages.warning(request, f'Failed to add {error_count} doctors. See details below.')

        elif 'assign_doctor' in request.POST:
            # Assign existing doctor to department
            assign_form = AssignDoctorToDepartmentForm(request.POST)
            if assign_form.is_valid():
                doctor = assign_form.cleaned_data['doctor']
                department = assign_form.cleaned_data['department']

                # Add department to doctor's departments
                doctor.departments.add(department)

                messages.success(request, f'Doctor {doctor.user.first_name} {doctor.user.last_name} assigned to {department.name} successfully!')
                return redirect('admin_section:add_doctor')

    # Get doctors for the table
    search_query = request.GET.get('q', '').strip()
    department_filter = request.GET.get('department')

    # Base queryset
    doctors = Doctor.objects.select_related('user').prefetch_related('departments').all()

    # Apply filters
    if department_filter:
        doctors = doctors.filter(departments__id=department_filter)

    # Apply search
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(departments__name__icontains=search_query)
        ).distinct()

    # Order doctors
    doctors = doctors.order_by('user__last_name', 'user__first_name')

    # Pagination
    paginator = Paginator(doctors, 10)  # Show 10 doctors per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all departments for filtering
    departments = Department.objects.all().order_by('name')

    # Prepare sample CSV data
    sample_csv_data = {
        'username': 'john.smith',
        'email': 'john.smith@example.com',
        'password': 'securepassword123',
        'first_name': 'John',
        'last_name': 'Smith',
        'phone_no': '1234567890',
        'city': 'New York',
        'country': 'USA',
        'speciality': 'Cardiology',
        'bio': 'Experienced cardiologist with 10 years of practice.'
    }

    context = {
        'user_form': user_form,
        'doctor_form': doctor_form,
        'bulk_form': bulk_form,
        'assign_form': assign_form,
        'doctors': page_obj,
        'departments': departments,
        'selected_department': department_filter,
        'search_query': search_query,
        'bulk_results': bulk_results,
        'sample_csv_data': sample_csv_data
    }

    return render(request, "admin_section/add_doctor.html", context)


def remove_from_department(request, doctor_id, department_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    department = get_object_or_404(Department, id=department_id)

    # Remove department from doctor's departments
    doctor.departments.remove(department)

    messages.success(request, f'Doctor {doctor.user.first_name} {doctor.user.last_name} removed from {department.name} successfully!')
    return redirect('admin_section:add_doctor')


def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    user = doctor.user

    # Create a custom form class for editing that doesn't include password fields
    class DoctorUserEditForm(forms.ModelForm):
        class Meta:
            model = CustomUser
            fields = ['username', 'email', 'first_name', 'last_name', 'phone_no', 'city', 'country', 'speciality', 'bio']
            widgets = {
                'username': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter username'
                }),
                'email': forms.EmailInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter email address'
                }),
                'first_name': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter first name'
                }),
                'last_name': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter last name'
                }),
                'phone_no': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter phone number'
                }),
                'city': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter city'
                }),
                'country': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter country'
                }),
                'speciality': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter speciality'
                }),
                'bio': forms.Textarea(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter bio',
                    'rows': 3
                }),
            }

    if request.method == 'POST':
        # Use the custom edit form instead of the UserCreationForm
        user_form = DoctorUserEditForm(request.POST, instance=user)
        doctor_form = DoctorForm(request.POST, instance=doctor)

        if user_form.is_valid() and doctor_form.is_valid():
            try:
                with transaction.atomic():
                    # Update user
                    user = user_form.save(commit=False)
                    user.role = 'doctor'  # Ensure role is still doctor
                    user.save()

                    # Update doctor profile and departments
                    doctor = doctor_form.save()

                    messages.success(request, f'Doctor {user.first_name} {user.last_name} updated successfully!')
                    return redirect('admin_section:add_doctor')
            except Exception as e:
                messages.error(request, f'Error updating doctor: {str(e)}')
    else:
        # Use the custom edit form instead of the UserCreationForm
        user_form = DoctorUserEditForm(instance=user)
        doctor_form = DoctorForm(instance=doctor)

    context = {
        'user_form': user_form,
        'doctor_form': doctor_form,
        'doctor': doctor,
        'is_edit': True
    }

    return render(request, "admin_section/edit_doctor.html", context)


def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    user = doctor.user

    if request.method == 'POST':
        try:
            # Store name for success message
            name = f"{user.first_name} {user.last_name}"

            # Delete doctor and user
            with transaction.atomic():
                doctor.delete()
                user.delete()

            messages.success(request, f'Doctor {name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting doctor: {str(e)}')

        return redirect('admin_section:add_doctor')

    # If GET request, show confirmation page
    context = {
        'doctor': doctor
    }

    return render(request, "admin_section/delete_doctor_confirm.html", context)


def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_doctors.csv"'

    writer = csv.writer(response)
    writer.writerow(['username', 'email', 'password', 'first_name', 'last_name', 'phone_no', 'city', 'country', 'speciality', 'bio'])
    writer.writerow(['john.smith', 'john.smith@example.com', 'securepassword123', 'John', 'Smith', '1234567890', 'New York', 'USA', 'Cardiology', 'Experienced cardiologist with 10 years of practice.'])
    writer.writerow(['jane.doe', 'jane.doe@example.com', 'securepassword456', 'Jane', 'Doe', '0987654321', 'Boston', 'USA', 'Neurology', 'Specialized in neurological disorders.'])

    return response
