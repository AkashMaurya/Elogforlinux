from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUser, Student, Doctor, Staff
from admin_section.forms import CustomUserForm
import json


def add_user(request):
    # Handle form submission
    if request.method == 'POST':
        form = CustomUserForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()

                # Create role-specific profile based on the selected role
                if user.role == 'student':
                    Student.objects.create(user=user)
                    messages.success(request, f'Student user {user.username} created successfully!')
                elif user.role == 'doctor':
                    Doctor.objects.create(user=user)
                    messages.success(request, f'Doctor user {user.username} created successfully!')
                elif user.role == 'staff':
                    Staff.objects.create(user=user)
                    messages.success(request, f'Staff user {user.username} created successfully!')
                else:  # admin
                    messages.success(request, f'Admin user {user.username} created successfully!')

            return redirect('admin_section:add_user')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserForm()

    # Get search query and role filter if any
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    # Get all users for the table
    users = CustomUser.objects.all().order_by('-date_joined')

    # Apply role filter if provided
    if role_filter and role_filter in dict(CustomUser.ROLE_CHOICES):
        users = users.filter(role=role_filter)

    # Apply search filter if provided
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)  # Search by student ID if available
        )

    # Pagination
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all available roles for the filter dropdown
    roles = CustomUser.ROLE_CHOICES

    context = {
        'form': form,
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'roles': roles,
    }

    return render(request, "admin_section/add_user.html", context)


def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        # For editing, we don't want to change the password
        form = CustomUserForm(request.POST, request.FILES, instance=user)

        # Remove password fields validation for edit
        form.fields['password1'].required = False
        form.fields['password2'].required = False

        if form.is_valid():
            user = form.save(commit=False)
            # Only update password if provided
            if form.cleaned_data.get('password1'):
                user.set_password(form.cleaned_data['password1'])
            user.save()

            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('admin_section:add_user')
    else:
        form = CustomUserForm(instance=user)
        # Remove password fields validation for edit
        form.fields['password1'].required = False
        form.fields['password2'].required = False

    context = {
        'form': form,
        'user_obj': user,
        'is_edit': True,
    }

    return render(request, "admin_section/add_user.html", context)


def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        try:
            username = user.username
            user.delete()
            messages.success(request, f'User {username} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
        return redirect('admin_section:add_user')

    # If it's an AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Otherwise, redirect to the user list
    return redirect('admin_section:add_user')


@require_POST
@login_required
def bulk_delete_users(request):
    """Handle bulk deletion of users"""
    try:
        # Get the list of user IDs from the request
        user_ids = request.POST.getlist('user_ids[]')

        if not user_ids:
            return JsonResponse({
                'success': False,
                'message': 'No users selected for deletion.'
            })

        # Convert to integers and validate
        try:
            user_ids = [int(uid) for uid in user_ids]
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid user IDs provided.'
            })

        # Get users to delete (excluding superusers for safety)
        users_to_delete = CustomUser.objects.filter(
            id__in=user_ids,
            is_superuser=False
        )

        if not users_to_delete.exists():
            return JsonResponse({
                'success': False,
                'message': 'No valid users found for deletion.'
            })

        # Count users and get their usernames for the response
        deleted_count = users_to_delete.count()
        deleted_usernames = list(users_to_delete.values_list('username', flat=True))

        # Perform bulk deletion
        with transaction.atomic():
            users_to_delete.delete()

        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {deleted_count} user(s): {", ".join(deleted_usernames)}',
            'deleted_count': deleted_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error occurred during bulk deletion: {str(e)}'
        })
