from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django import forms
import csv
import json
from ..forms import (
    StudentUserForm,
    StudentForm,
    BulkUserUploadForm,  # Changed from BulkUploadForm
    AssignStudentForm
)
from accounts.models import Student
from ..models import Group
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@login_required
def add_student(request):
    # Initialize forms
    user_form = StudentUserForm()
    student_form = StudentForm()
    bulk_form = BulkUserUploadForm()  # Changed from BulkUploadForm
    assign_form = AssignStudentForm()

    # Get search parameters
    search_query = request.GET.get("q", "")
    selected_group = request.GET.get("group", "")
    page_number = request.GET.get("page", 1)

    # Base queryset
    students = Student.objects.select_related("user", "group").all()

    # Apply filters
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
        )

    if selected_group:
        students = students.filter(group_id=selected_group)

    # Pagination
    paginator = Paginator(students, 10)  # Show 10 students per page
    page_obj = paginator.get_page(page_number)

    # Get all groups for the filter dropdown
    groups = Group.objects.all()

    # Handle form submissions
    if request.method == "POST":
        print(f"POST request received with data: {request.POST}")
        if "add_student" in request.POST:
            # Individual student addition
            print(f"Processing add_student form with data: {request.POST}")
            user_form = StudentUserForm(request.POST)
            student_form = StudentForm(request.POST)

            if user_form.is_valid() and student_form.is_valid():
                print("Both forms are valid, saving...")
                try:
                    with transaction.atomic():
                        # Create user with student role
                        user = user_form.save(commit=False)
                        user.role = "student"
                        user.save()

                        # Create student profile
                        student = student_form.save(commit=False)
                        student.user = user
                        student.save()

                        messages.success(
                            request,
                            f"Student {user.first_name} {user.last_name} added successfully!",
                        )
                        return redirect("admin_section:add_student")
                except Exception as e:
                    print(f"Error saving student: {str(e)}")
                    messages.error(request, f"Error adding student: {str(e)}")
            else:
                print(f"Form validation failed. User form errors: {user_form.errors}")
                print(f"Student form errors: {student_form.errors}")

        elif "bulk_upload" in request.POST:
            bulk_form = BulkUserUploadForm(request.POST, request.FILES)  # Changed from BulkUploadForm
            if bulk_form.is_valid():
                try:
                    # Process the CSV file here
                    # Add your bulk upload logic
                    messages.success(request, "Bulk upload completed successfully!")
                except Exception as e:
                    messages.error(request, f"Error during bulk upload: {str(e)}")

        elif "assign_student" in request.POST:
            assign_form = AssignStudentForm(request.POST)
            print(f"Form data: {request.POST}")
            if assign_form.is_valid():
                print(f"Form is valid. Cleaned data: {assign_form.cleaned_data}")
                try:
                    student_id = assign_form.cleaned_data["student_id"]
                    group = assign_form.cleaned_data["group"]

                    # Find the student by ID
                    if student_id:
                        student = Student.objects.get(id=student_id)
                        old_group = student.group
                        student.group = group
                        student.save()

                        if old_group:
                            messages.success(
                                request, f"Student {student.user.get_full_name() or student.user.username} moved from {old_group.group_name} to {group.group_name}"
                            )
                        else:
                            messages.success(
                                request, f"Student {student.user.get_full_name() or student.user.username} assigned to {group.group_name}"
                            )
                    else:
                        messages.error(request, "No student selected. Please search and select a student first.")
                except Student.DoesNotExist:
                    messages.error(request, "Student not found. Please try again.")
                except Exception as e:
                    messages.error(
                        request, f"Error assigning student to group: {str(e)}"
                    )
            else:
                print(f"Form errors: {assign_form.errors}")
                messages.error(request, "Please select both a student and a group.")

    context = {
        "user_form": user_form,
        "student_form": student_form,
        "bulk_form": bulk_form,
        "assign_form": assign_form,
        "students": page_obj,
        "groups": groups,
        "selected_group": selected_group,
        "search_query": search_query,
    }

    return render(request, "admin_section/add_student.html", context)


@login_required
def remove_from_group(request, student_id):
    try:
        student = Student.objects.get(id=student_id)
        group_name = student.group.group_name if student.group else "No group"
        student.group = None
        student.save()
        messages.success(request, f'Student removed from {group_name} successfully!')
    except Student.DoesNotExist:
        messages.error(request, 'Student not found!')
    except Exception as e:
        messages.error(request, f'Error removing student from group: {str(e)}')

    return redirect('admin_section:add_student')


@login_required
def search_students(request):
    """AJAX endpoint to search for students"""
    search_query = request.GET.get('q', '')

    if not search_query or len(search_query) < 2:
        return JsonResponse({'results': []})

    # Search for students by ID, name, or email
    students = Student.objects.select_related('user', 'group').filter(
        Q(student_id__icontains=search_query) |
        Q(user__email__icontains=search_query) |
        Q(user__first_name__icontains=search_query) |
        Q(user__last_name__icontains=search_query)
    ).order_by('user__first_name', 'user__last_name')[:10]  # Limit to 10 results, ordered by name

    results = []
    for student in students:
        results.append({
            'id': student.id,
            'student_id': student.student_id,
            'name': student.user.get_full_name() or student.user.username,
            'email': student.user.email,
            'current_group': student.group.group_name if student.group else 'No Group'
        })

    return JsonResponse({'results': results})


@login_required
def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_students.csv"'

    writer = csv.writer(response)
    writer.writerow(['username', 'email', 'password', 'first_name', 'last_name', 'student_id', 'group', 'phone_no', 'city', 'country'])

    # Add sample data rows
    writer.writerow(['student1', 'student1@example.com', 'SecurePass123', 'John', 'Doe', 'STU12345', 'B1', '1234567890', 'New York', 'USA'])
    writer.writerow(['student2', 'student2@example.com', 'SecurePass456', 'Jane', 'Smith', 'STU67890', 'A2', '9876543210', 'London', 'UK'])
    writer.writerow(['student3', 'student3@example.com', 'SecurePass789', 'Alex', 'Johnson', 'STU24680', 'B2', '5555555555', 'Paris', 'France'])
    writer.writerow(['student4', 'student4@example.com', 'SecurePass101', 'Maria', 'Garcia', 'STU13579', 'A1', '6666666666', 'Berlin', 'Germany'])

    return response


@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    user = student.user

    # Create a custom form class for editing that doesn't include password fields
    class StudentUserEditForm(forms.ModelForm):
        class Meta:
            model = CustomUser
            fields = ['username', 'email', 'first_name', 'last_name', 'phone_no', 'city', 'country']
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
            }

    # Create a custom form for student fields
    class StudentEditForm(forms.ModelForm):
        class Meta:
            model = Student
            fields = ['student_id', 'group']
            widgets = {
                'student_id': forms.TextInput(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                    'placeholder': 'Enter student ID'
                }),
                'group': forms.Select(attrs={
                    'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                }),
            }

    if request.method == 'POST':
        user_form = StudentUserEditForm(request.POST, instance=user)
        student_form = StudentEditForm(request.POST, instance=student)

        if user_form.is_valid() and student_form.is_valid():
            try:
                with transaction.atomic():
                    # Update user
                    user = user_form.save(commit=False)
                    user.role = 'student'  # Ensure role is still student
                    user.save()

                    # Update student profile
                    student = student_form.save()

                    messages.success(request, f'Student {user.first_name} {user.last_name} updated successfully!')
                    return redirect('admin_section:add_student')
            except Exception as e:
                messages.error(request, f'Error updating student: {str(e)}')
    else:
        user_form = StudentUserEditForm(instance=user)
        student_form = StudentEditForm(instance=student)

    context = {
        'user_form': user_form,
        'student_form': student_form,
        'student': student,
    }

    return render(request, 'admin_section/edit_student.html', context)


@login_required
def delete_student(request, student_id):
    """DEPRECATED: Use remove_student_role instead for safe role removal"""
    try:
        student = Student.objects.get(id=student_id)
        user = student.user

        if request.method == 'POST':
            # Check if this is a role removal or account deletion
            action = request.POST.get('action', 'remove_role')

            if action == 'remove_role':
                # Safe role removal
                from .safe_role_management import remove_role_from_user
                return remove_role_from_user(request, user.id, 'student')

            elif action == 'delete_account':
                # Soft delete the entire account
                from .safe_role_management import soft_delete_user
                return soft_delete_user(request, user.id)

            else:
                messages.error(request, 'Invalid action specified.')
                return redirect('admin_section:add_student')

        # Show confirmation page with options
        context = {
            'student': student,
            'user': user,
        }
        return render(request, "admin_section/delete_student_confirm.html", context)

    except Student.DoesNotExist:
        messages.error(request, 'Student not found!')
        return redirect('admin_section:add_student')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('admin_section:add_student')
