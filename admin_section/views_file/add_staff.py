from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django import forms
import csv
import io
from accounts.models import CustomUser, Staff
from admin_section.models import Department
from admin_section.forms import StaffUserForm, StaffForm, AssignStaffToDepartmentForm, BulkStaffUploadForm, StaffUserEditForm


@login_required
def add_staff(request):
    # Initialize forms
    user_form = StaffUserForm()
    staff_form = StaffForm()
    bulk_form = BulkStaffUploadForm()
    assign_form = AssignStaffToDepartmentForm()
    bulk_results = None

    # Handle form submissions
    if request.method == 'POST':
        # Check which form was submitted
        if 'add_staff' in request.POST:
            # Individual staff addition
            user_form = StaffUserForm(request.POST)
            staff_form = StaffForm(request.POST)

            if user_form.is_valid() and staff_form.is_valid():
                try:
                    with transaction.atomic():
                        # Create user with staff role
                        user = user_form.save(commit=False)
                        user.role = 'staff'
                        user.save()

                        # Create staff profile
                        staff = staff_form.save(commit=False)
                        staff.user = user
                        staff.save()

                        # Add departments (many-to-many relationship)
                        if staff_form.cleaned_data.get('departments'):
                            staff.departments.set(staff_form.cleaned_data['departments'])

                        messages.success(request, f'Staff {user.first_name} {user.last_name} added successfully!')
                        return redirect('admin_section:add_staff')
                except Exception as e:
                    messages.error(request, f'Error adding staff: {str(e)}')

        elif 'bulk_upload' in request.POST:
            # Bulk upload staff
            bulk_form = BulkStaffUploadForm(request.POST, request.FILES)
            if bulk_form.is_valid():
                csv_file = request.FILES['csv_file']
                department = bulk_form.cleaned_data['department']
                
                # Process CSV file
                decoded_file = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded_file))
                
                # Track results
                results = {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'errors': []
                }
                
                for row in reader:
                    results['total'] += 1
                    try:
                        with transaction.atomic():
                            # Create user
                            user = CustomUser(
                                username=row['username'],
                                email=row['email'],
                                first_name=row['first_name'],
                                last_name=row['last_name'],
                                role='staff',
                                phone_no=row.get('phone_no', ''),
                                city=row.get('city', ''),
                                country=row.get('country', ''),
                                bio=row.get('bio', '')
                            )
                            user.password = make_password(row['password'])
                            user.save()
                            
                            # Create staff profile
                            staff = Staff.objects.create(user=user)
                            
                            # Add to department
                            staff.departments.add(department)
                            
                            results['success'] += 1
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append(f"Row {results['total']}: {str(e)}")
                
                bulk_results = results
                if results['success'] > 0:
                    messages.success(request, f"Successfully added {results['success']} staff members.")
                if results['failed'] > 0:
                    messages.warning(request, f"Failed to add {results['failed']} staff members. See details below.")

        elif 'assign_staff' in request.POST:
            # Assign existing staff to department
            assign_form = AssignStaffToDepartmentForm(request.POST)
            if assign_form.is_valid():
                staff = assign_form.cleaned_data['staff']
                department = assign_form.cleaned_data['department']

                # Add department to staff's departments
                staff.departments.add(department)

                messages.success(request, f'Staff {staff.user.first_name} {staff.user.last_name} assigned to {department.name} successfully!')
                return redirect('admin_section:add_staff')

    # Get filter parameters
    selected_department = request.GET.get('department')
    search_query = request.GET.get('q', '').strip()

    # Get all departments for the filter dropdown
    departments = Department.objects.all().order_by('name')

    # Base queryset - get all staff with their users and departments
    staff_members = Staff.objects.select_related('user').prefetch_related('departments').all()

    # Apply filters
    if selected_department:
        staff_members = staff_members.filter(departments__id=selected_department)

    if search_query:
        staff_members = staff_members.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    # Order by name
    staff_members = staff_members.order_by('user__first_name', 'user__last_name')

    # Pagination
    paginator = Paginator(staff_members, 10)  # Show 10 staff members per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user_form': user_form,
        'staff_form': staff_form,
        'bulk_form': bulk_form,
        'assign_form': assign_form,
        'staff_members': page_obj,
        'departments': departments,
        'selected_department': selected_department,
        'search_query': search_query,
        'bulk_results': bulk_results,
    }

    return render(request, 'admin_section/add_staff.html', context)


@login_required
def remove_from_department(request, staff_id, department_id):
    staff = get_object_or_404(Staff, id=staff_id)
    department = get_object_or_404(Department, id=department_id)

    # Remove department from staff's departments
    staff.departments.remove(department)

    messages.success(request, f'Staff {staff.user.first_name} {staff.user.last_name} removed from {department.name} successfully!')
    return redirect('admin_section:add_staff')


@login_required
def edit_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    user = staff.user

    if request.method == 'POST':
        user_form = StaffUserEditForm(request.POST, instance=user)
        staff_form = StaffForm(request.POST, instance=staff)

        if user_form.is_valid() and staff_form.is_valid():
            try:
                with transaction.atomic():
                    # Update user
                    user = user_form.save(commit=False)
                    user.role = 'staff'  # Ensure role is still staff
                    user.save()

                    # Update staff profile and departments
                    staff = staff_form.save()

                    messages.success(request, f'Staff {user.first_name} {user.last_name} updated successfully!')
                    return redirect('admin_section:add_staff')
            except Exception as e:
                messages.error(request, f'Error updating staff: {str(e)}')
    else:
        # Use the custom edit form instead of the UserCreationForm
        user_form = StaffUserEditForm(instance=user)
        staff_form = StaffForm(instance=staff)

    context = {
        'user_form': user_form,
        'staff_form': staff_form,
        'staff': staff,
        'is_edit': True
    }

    return render(request, 'admin_section/edit_staff.html', context)


@login_required
def delete_staff(request, staff_id):
    """DEPRECATED: Use remove_staff_role instead for safe role removal"""
    staff = get_object_or_404(Staff, id=staff_id)
    user = staff.user

    if request.method == 'POST':
        # Check if this is a role removal or account deletion
        action = request.POST.get('action', 'remove_role')

        if action == 'remove_role':
            # Safe role removal
            from .safe_role_management import remove_role_from_user
            return remove_role_from_user(request, user.id, 'staff')

        elif action == 'delete_account':
            # Soft delete the entire account
            from .safe_role_management import soft_delete_user
            return soft_delete_user(request, user.id)

        else:
            messages.error(request, 'Invalid action specified.')
            return redirect('admin_section:add_staff')

    context = {
        'staff': staff,
        'user': user,
    }

    return render(request, 'admin_section/delete_staff.html', context)


@login_required
def download_sample_csv(request):
    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_staff_upload.csv"'

    # Create CSV writer
    writer = csv.writer(response)

    # Write header row
    writer.writerow(['username', 'email', 'password', 'first_name', 'last_name', 'phone_no', 'city', 'country', 'bio'])

    # Write sample data
    writer.writerow(['staff1', 'staff1@example.com', 'password123', 'John', 'Doe', '1234567890', 'New York', 'USA', 'Staff bio'])
    writer.writerow(['staff2', 'staff2@example.com', 'password123', 'Jane', 'Smith', '0987654321', 'London', 'UK', 'Staff bio'])

    return response
