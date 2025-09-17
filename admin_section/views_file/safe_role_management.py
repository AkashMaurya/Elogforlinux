"""
Safe Role Management Views
Provides safe role removal and user management without accidental deletions
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from accounts.models import CustomUser, Student, Doctor, Staff
from admin_section.models import AdminNotification
import logging

logger = logging.getLogger(__name__)


@login_required
def remove_role_from_user(request, user_id, role):
    """Safely remove a role from a user without deleting the user account"""
    if request.user.role != 'admin':
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('admin_section:admin_dash')
    
    user = get_object_or_404(CustomUser.all_objects, id=user_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Log the action for audit
                logger.info(f"Admin {request.user.email} removing {role} role from user {user.email}")
                
                success = user.remove_role(role)
                if success:
                    messages.success(
                        request, 
                        f'{role.title()} role removed from {user.get_full_name() or user.username}. '
                        f'User account preserved with defaultuser role.'
                    )
                    
                    # Create audit notification
                    AdminNotification.objects.create(
                        recipient=request.user,
                        title=f"Role Removed: {role.title()}",
                        message=f"Removed {role} role from {user.get_full_name() or user.username} ({user.email})",
                        support_ticket_type='admin',
                        created_at=timezone.now()
                    )
                else:
                    messages.warning(request, f'User does not have {role} role.')
                    
        except Exception as e:
            logger.error(f"Error removing {role} role from user {user.email}: {e}")
            messages.error(request, f'Error removing role: {str(e)}')
    
    # Redirect based on role
    redirect_map = {
        'student': 'admin_section:add_student',
        'doctor': 'admin_section:add_doctor', 
        'staff': 'admin_section:add_staff'
    }
    return redirect(redirect_map.get(role, 'admin_section:add_user'))


@login_required
def soft_delete_user(request, user_id):
    """Soft delete a user account (can be restored)"""
    if request.user.role != 'admin':
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('admin_section:admin_dash')
    
    user = get_object_or_404(CustomUser.all_objects, id=user_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Prevent self-deletion
                if user.id == request.user.id:
                    messages.error(request, "You cannot delete your own account.")
                    return redirect('admin_section:add_user')
                
                # Prevent deletion of superusers
                if user.is_superuser:
                    messages.error(request, "Cannot delete superuser accounts.")
                    return redirect('admin_section:add_user')
                
                # Log the action
                logger.warning(f"Admin {request.user.email} soft-deleting user {user.email}")
                
                user.soft_delete(deleted_by=request.user)
                
                messages.success(
                    request, 
                    f'User {user.get_full_name() or user.username} has been deactivated. '
                    f'Account can be restored if needed.'
                )
                
                # Create audit notification
                AdminNotification.objects.create(
                    recipient=request.user,
                    title="User Account Deactivated",
                    message=f"Deactivated user account: {user.get_full_name() or user.username} ({user.email})",
                    support_ticket_type='admin',
                    created_at=timezone.now()
                )
                
        except Exception as e:
            logger.error(f"Error soft-deleting user {user.email}: {e}")
            messages.error(request, f'Error deactivating user: {str(e)}')
    
    return redirect('admin_section:add_user')


@login_required
def restore_user(request, user_id):
    """Restore a soft-deleted user"""
    if request.user.role != 'admin':
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('admin_section:admin_dash')
    
    user = get_object_or_404(CustomUser.all_objects.deleted_only(), id=user_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                logger.info(f"Admin {request.user.email} restoring user {user.email}")
                
                user.restore()
                
                messages.success(
                    request, 
                    f'User {user.get_full_name() or user.username} has been restored.'
                )
                
        except Exception as e:
            logger.error(f"Error restoring user {user.email}: {e}")
            messages.error(request, f'Error restoring user: {str(e)}')
    
    return redirect('admin_section:add_user')


@login_required
def hard_delete_user(request, user_id):
    """PERMANENTLY delete a user (superuser only, with confirmation)"""
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can permanently delete accounts.")
        return redirect('admin_section:admin_dash')
    
    user = get_object_or_404(CustomUser.all_objects, id=user_id)
    
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '').strip()
        expected_confirmation = f"DELETE {user.username}"
        
        if confirmation != expected_confirmation:
            messages.error(
                request, 
                f'Confirmation failed. You must type exactly: "{expected_confirmation}"'
            )
            return render(request, 'admin_section/hard_delete_confirm.html', {'user': user})
        
        try:
            with transaction.atomic():
                # Prevent self-deletion
                if user.id == request.user.id:
                    messages.error(request, "You cannot delete your own account.")
                    return redirect('admin_section:add_user')
                
                # Log the critical action
                logger.critical(f"SUPERUSER {request.user.email} PERMANENTLY DELETING user {user.email}")
                
                username = user.username
                user.delete()  # This is the actual hard delete
                
                messages.success(
                    request, 
                    f'User {username} has been PERMANENTLY deleted. This action cannot be undone.'
                )
                
        except Exception as e:
            logger.error(f"Error hard-deleting user {user.email}: {e}")
            messages.error(request, f'Error deleting user: {str(e)}')
        
        return redirect('admin_section:add_user')
    
    # Show confirmation page
    return render(request, 'admin_section/hard_delete_confirm.html', {'user': user})


@login_required
def view_deleted_users(request):
    """View soft-deleted users for potential restoration"""
    if request.user.role != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('admin_section:admin_dash')
    
    deleted_users = CustomUser.all_objects.deleted_only().order_by('-deleted_at')
    
    context = {
        'deleted_users': deleted_users,
        'unread_notifications_count': AdminNotification.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
    }
    
    return render(request, 'admin_section/deleted_users.html', context)


@require_POST
@login_required
def change_user_role(request, user_id):
    """Change a user's role safely"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    user = get_object_or_404(CustomUser.all_objects, id=user_id)
    new_role = request.POST.get('new_role')
    
    if new_role not in ['defaultuser', 'student', 'doctor', 'staff', 'admin']:
        return JsonResponse({'success': False, 'message': 'Invalid role'})
    
    try:
        with transaction.atomic():
            old_role = user.role
            success = user.add_role(new_role)
            
            if success:
                logger.info(f"Admin {request.user.email} changed user {user.email} role from {old_role} to {new_role}")
                return JsonResponse({
                    'success': True, 
                    'message': f'Role changed from {old_role} to {new_role}'
                })
            else:
                return JsonResponse({'success': False, 'message': 'Failed to change role'})
                
    except Exception as e:
        logger.error(f"Error changing role for user {user.email}: {e}")
        return JsonResponse({'success': False, 'message': str(e)})
