from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from accounts.models import Doctor, CustomUser,Student
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models, transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
import os
import json
import csv
import io
from threading import Thread
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from utils.pdf_utils import add_agu_header, get_common_styles, add_footer_info
from .models import DoctorSupportTicket, Notification
from .forms import DoctorSupportTicketForm, LogReviewForm, BatchReviewForm
from student_section.models import StudentLogFormModel, StudentNotification
from admin_section.models import AdminNotification, DateRestrictionSettings
from django.db.models import Count
from django.db.models.functions import TruncMonth


# Helper functions for asynchronous email sending
def send_admin_emails_doctor(admin_emails, subject, message):
    """Send emails to admins in a separate thread"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=admin_emails,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def send_student_email(student_email, subject, message):
    """Send email to student in a separate thread"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[student_email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


@login_required
def doctor_dash(request):
    doctor = request.user.doctor_profile
    selected_department = request.GET.get('department')
    search_query = request.GET.get('q', '').strip()

    # Get doctor's departments
    departments = doctor.departments.all()

    # Base queryset for logs
    logs = StudentLogFormModel.objects.filter(department__in=departments)

    if selected_department:
        logs = logs.filter(department_id=selected_department)

    # Get current date and start of month
    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Performance metrics
    performance_data = {
        'total_reviews': logs.filter(is_reviewed=True).count(),
        'pending_reviews': logs.filter(is_reviewed=False).count(),
        'monthly_reviews': logs.filter(review_date__gte=start_of_month).count(),
        'approval_rate': calculate_approval_rate(logs),
    }

    # Basic chart data (without student performance data yet)
    chart_data = {
        'daily_reviews': get_daily_reviews_data(logs),
        'department_stats': get_department_stats(logs, departments),
        'review_status': get_review_status_data(logs),
        'monthly_trend': get_monthly_trend_data(logs),
        'activity_distribution': get_activity_distribution_data(logs),
        'participation_distribution': get_participation_distribution_data(logs),
        'student_status_distribution': get_student_status_distribution(logs),
        'department_performance': get_department_performance_data(logs, departments),
    }

    # Calculate total records, left to review, and reviewed counts
    total_records = logs.count()
    left_to_review = logs.filter(is_reviewed=False).count()
    reviewed = logs.filter(is_reviewed=True).count()

    # Calculate percentage for progress circle
    review_percentage = 0
    if total_records > 0:
        review_percentage = int((reviewed / total_records) * 100)

    # Get student performance data
    student_performance = []
    priority_records = []

    # Get unique students who submitted logs in the doctor's departments
    student_ids = logs.values_list('student', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids)

    # Filter students by search query if provided
    if search_query:
        students = students.filter(
            models.Q(user__first_name__icontains=search_query) |
            models.Q(user__last_name__icontains=search_query) |
            models.Q(user__email__icontains=search_query) |
            models.Q(student_id__icontains=search_query)
        )

    # Get performance data for each student
    for student in students:
        student_logs = logs.filter(student=student)
        total_student_logs = student_logs.count()
        reviewed_logs = student_logs.filter(is_reviewed=True).count()
        pending_logs = total_student_logs - reviewed_logs
        approved_logs = student_logs.filter(is_reviewed=True).exclude(reviewer_comments__startswith='REJECTED').count()
        rejected_logs = student_logs.filter(is_reviewed=True, reviewer_comments__startswith='REJECTED').count()

        # Calculate completion percentage
        completion_percentage = 0
        if total_student_logs > 0:
            completion_percentage = int((reviewed_logs / total_student_logs) * 100)

        student_performance.append({
            'id': student.id,
            'name': student.user.get_full_name() or student.user.username,
            'student_id': student.student_id,
            'email': student.user.email,
            'group': student.group.group_name if student.group else 'No Group',
            'total_logs': total_student_logs,
            'reviewed_logs': reviewed_logs,
            'pending_logs': pending_logs,
            'approved_logs': approved_logs,
            'rejected_logs': rejected_logs,
            'completion_percentage': completion_percentage
        })

        # Add to priority records if there are pending logs
        if pending_logs > 0:
            # Get the oldest pending log for this student
            oldest_pending = student_logs.filter(is_reviewed=False).order_by('date').first()
            if oldest_pending:
                priority_records.append({
                    'id': oldest_pending.id,
                    'student_name': student.user.get_full_name() or student.user.username,
                    'due_date': oldest_pending.date,
                    'department': oldest_pending.department.name
                })

    # Sort priority records by due date (oldest first)
    priority_records = sorted(priority_records, key=lambda x: x['due_date'])

    # Add top students data to chart_data after student_performance is populated
    chart_data['top_students'] = get_top_students_data(student_performance[:5] if student_performance else [])

    # Activity and participation distribution data is now handled by helper functions

    # Debug chart data
    print("Chart Data:")
    for key, value in chart_data.items():
        print(f"  {key}: {value}")

    # Ensure all chart data has valid format
    for key, data in chart_data.items():
        if 'labels' not in data or 'data' not in data:
            print(f"WARNING: Invalid chart data format for {key}")
            chart_data[key] = {'labels': ['No Data'], 'data': [1]}
        elif not data['labels'] or not data['data']:
            print(f"WARNING: Empty chart data for {key}")
            chart_data[key] = {'labels': ['No Data'], 'data': [1]}

    context = {
        'performance_data': performance_data,
        'chart_data': chart_data,
        'departments': departments,
        'selected_department': selected_department,
        'total_records': total_records,
        'left_to_review': left_to_review,
        'reviewed': reviewed,
        'review_percentage': review_percentage,
        'student_performance': student_performance,
        'priority_records': priority_records[:5],  # Limit to top 5 priority records
        'search_query': search_query
    }

    return render(request, "doctor_dash.html", context)

def calculate_approval_rate(logs):
    reviewed_logs = logs.filter(is_reviewed=True)
    total_reviewed = reviewed_logs.count()
    if total_reviewed == 0:
        return 0
    approved = reviewed_logs.filter(reviewer_comments__startswith='REJECTED').count()
    return round((1 - approved / total_reviewed) * 100)

def get_daily_reviews_data(logs):
    last_7_days = timezone.now() - timedelta(days=7)
    daily_reviews = logs.filter(
        review_date__gte=last_7_days
    ).values('review_date__date').annotate(
        count=Count('id')
    ).order_by('review_date__date')

    return {
        'labels': [d['review_date__date'].strftime('%Y-%m-%d') for d in daily_reviews],
        'data': [d['count'] for d in daily_reviews]
    }

def get_department_stats(logs, departments):
    dept_stats = []
    for dept in departments:
        dept_logs = logs.filter(department=dept)
        total = dept_logs.count()
        reviewed = dept_logs.filter(is_reviewed=True).count()
        dept_stats.append({
            'name': dept.name,
            'total': total,
            'reviewed': reviewed,
            'pending': total - reviewed
        })
    return dept_stats

def get_department_performance_data(logs, departments):
    """Get data for department performance chart"""
    # If no departments, return default values
    if not departments:
        return {
            'labels': ['No Department Data'],
            'reviewed': [0],
            'pending': [0]
        }

    dept_stats = get_department_stats(logs, departments)

    # Sort by total logs (descending)
    dept_stats = sorted(dept_stats, key=lambda x: x['total'], reverse=True)

    return {
        'labels': [dept['name'] for dept in dept_stats],
        'reviewed': [dept['reviewed'] for dept in dept_stats],
        'pending': [dept['pending'] for dept in dept_stats]
    }

def get_review_status_data(logs):
    total = logs.count()
    reviewed = logs.filter(is_reviewed=True).count()
    return {
        'labels': ['Reviewed', 'Pending'],
        'data': [reviewed, total - reviewed]
    }

def get_monthly_trend_data(logs):
    last_6_months = timezone.now() - timedelta(days=180)
    monthly_data = logs.filter(
        review_date__gte=last_6_months
    ).annotate(
        month=TruncMonth('review_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    # Handle empty data case
    if not monthly_data:
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'data': [0, 0, 0, 0, 0, 0]
        }

    return {
        'labels': [d['month'].strftime('%B %Y') for d in monthly_data],
        'data': [d['count'] for d in monthly_data]
    }


def get_activity_distribution_data(logs):
    """Get distribution of logs by activity type"""
    activity_data = logs.values('activity_type__name').annotate(
        count=Count('id')
    ).order_by('-count')

    # Handle empty data case
    if not activity_data:
        return {
            'labels': ['No Activity Data'],
            'data': [1]
        }

    return {
        'labels': [d['activity_type__name'] for d in activity_data],
        'data': [d['count'] for d in activity_data]
    }


def get_participation_distribution_data(logs):
    """Get distribution of logs by participation type"""
    participation_data = logs.values('participation_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # Handle empty data case
    if not participation_data:
        return {
            'labels': ['Observed', 'Assisted'],
            'data': [1, 1]
        }

    return {
        'labels': [d['participation_type'] for d in participation_data],
        'data': [d['count'] for d in participation_data]
    }


def get_student_status_distribution(logs):
    """Get distribution of logs by review status"""
    reviewed = logs.filter(is_reviewed=True).count()
    pending = logs.filter(is_reviewed=False).count()

    # If there are no logs, return default values to avoid empty charts
    if reviewed == 0 and pending == 0:
        return {
            'labels': ['Reviewed', 'Pending'],
            'data': [1, 1]  # Default values for empty data
        }

    return {
        'labels': ['Reviewed', 'Pending'],
        'data': [reviewed, pending]
    }


def get_top_students_data(student_performance):
    """Get data for top students by log count"""
    # If no student performance data, return default values
    if not student_performance:
        return {
            'labels': ['No Student Data'],
            'data': [0]
        }

    # Sort student performance data by total logs (descending)
    sorted_students = sorted(student_performance, key=lambda x: x['total_logs'], reverse=True)

    # Get top 5 students (or fewer if less than 5 students)
    top_students = sorted_students[:5]

    # If no students have logs, return default values
    if not top_students or all(student['total_logs'] == 0 for student in top_students):
        return {
            'labels': ['No Log Data'],
            'data': [0]
        }

    return {
        'labels': [student['name'] for student in top_students],
        'data': [student['total_logs'] for student in top_students]
    }


@login_required
def doctor_profile(request):
    # Get the currently logged-in user from the request
    user = request.user

    # Get the profile photo URL correctly
    if user.profile_photo:
        profile_photo = user.profile_photo.url
    else:
        profile_photo = "/media/profiles/default.jpg"  # Default image if no profile photo

    # Get Doctor Profile
    doctor = getattr(user, "doctor_profile", None)

    # Get doctor's departments
    if doctor:
        # Get departments as a comma-separated string
        doctor_departments = ", ".join(dept.name for dept in doctor.departments.all())
        # Get departments as a list for template iteration
        department_list = [dept.name for dept in doctor.departments.all()]

        # Get activity statistics
        # Get current date and start of month
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get logs for this doctor's departments
        logs = StudentLogFormModel.objects.filter(department__in=doctor.departments.all())

        # Calculate statistics
        reviews_count = logs.filter(is_reviewed=True).count()
        monthly_reviews = logs.filter(is_reviewed=True, review_date__gte=start_of_month).count()
        pending_reviews = logs.filter(is_reviewed=False, department__in=doctor.departments.all()).count()

        # Calculate approval rate
        reviewed_logs = logs.filter(is_reviewed=True)
        total_reviewed = reviewed_logs.count()
        if total_reviewed > 0:
            rejected = reviewed_logs.filter(reviewer_comments__startswith='REJECTED').count()
            approval_rate = round(((total_reviewed - rejected) / total_reviewed) * 100)
        else:
            approval_rate = 0
    else:
        doctor_departments = None
        department_list = []
        reviews_count = 0
        monthly_reviews = 0
        pending_reviews = 0
        approval_rate = 0

    # Get user information
    full_name = user.get_full_name() or user.username
    user_role = user.role.upper() if hasattr(user, 'role') else "DOCTOR"
    user_city = user.city or ""
    user_country = user.country or ""
    user_phone = user.phone_no or ""
    user_speciality = user.speciality or ""
    user_email = user.email

    # Prepare the context dictionary with all the necessary data
    data = {
        "full_name": full_name,
        "profile_photo": profile_photo,
        "user_role": user_role,
        "user_city": user_city,
        "user_country": user_country,
        "user_phone": user_phone,
        "user_speciality": user_speciality,
        "user_email": user_email,
        "doctor_departments": doctor_departments,
        "department_list": department_list,
        # Activity statistics
        "reviews_count": reviews_count,
        "monthly_reviews": monthly_reviews,
        "pending_reviews": pending_reviews,
        "approval_rate": approval_rate,
    }

    return render(request, "doctor_profile.html", data)


@login_required
def update_contact_info(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        city = request.POST.get("city")
        country = request.POST.get("country")

        try:
            # Update user profile info
            user = request.user
            user.phone_no = phone
            user.city = city
            user.country = country
            user.save()

            # Update session data
            request.session["phone_no"] = phone
            request.session["city"] = city
            request.session["country"] = country
            request.session.modified = True

            return JsonResponse(
                {
                    "success": True,
                    "user_phone": phone,
                    "user_city": city,
                    "user_country": country,
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


@login_required
def update_profile_photo(request):
    if request.method == "POST" and request.FILES.get("profile_photo"):
        user = request.user
        # Delete old profile photo if it exists
        if user.profile_photo and hasattr(user.profile_photo, "path"):
            try:
                if os.path.exists(user.profile_photo.path):
                    os.remove(user.profile_photo.path)
            except Exception as e:
                print(f"Error deleting old profile photo: {e}")

        # Save new profile photo
        user.profile_photo = request.FILES["profile_photo"]
        user.save()

        return JsonResponse({"success": True, "profile_photo": user.profile_photo.url})

    return JsonResponse({"success": False, "error": "No photo provided"})


@login_required
def get_date_restrictions(request):
    """API endpoint to get date restriction settings for doctors"""
    try:
        # Get date restriction settings or create default if none exist
        settings = DateRestrictionSettings.objects.first()
        if not settings:
            settings = DateRestrictionSettings.objects.create(
                past_days_limit=7,
                allow_future_dates=False,
                future_days_limit=0,
                doctor_past_days_limit=30,
                doctor_allow_future_dates=False,
                doctor_future_days_limit=0,
                allowed_days_for_students='0,1,2,3,4,5,6',
                allowed_days_for_doctors='0,1,2,3,4,5,6',
                is_active=True
            )

        # Get current day of week (0=Monday, 6=Sunday)
        current_day = timezone.now().weekday()

        # Get settings from the model
        doctor_past_days_limit = settings.doctor_past_days_limit
        doctor_allow_future_dates = settings.doctor_allow_future_dates
        doctor_future_days_limit = settings.doctor_future_days_limit
        allowed_days = settings.get_allowed_days_for_doctors()
        is_active = settings.is_active

        # Return settings as JSON
        data = {
            "pastDaysLimit": doctor_past_days_limit,
            "allowFutureDates": doctor_allow_future_dates,
            "futureDaysLimit": doctor_future_days_limit,
            "isCurrentDayAllowed": current_day in allowed_days,
            "allowedDays": allowed_days,
            "isActive": is_active
        }
        return JsonResponse(data)
    except Exception as e:
        # Return default settings in case of error
        return JsonResponse({
            "pastDaysLimit": 30,
            "allowFutureDates": False,
            "futureDaysLimit": 0,
            "isCurrentDayAllowed": True,
            "allowedDays": [0, 1, 2, 3, 4, 5, 6],
            "isActive": True,
            "error": str(e)
        })



@login_required
def doctor_help(request):
    if request.method == "POST":
        form = DoctorSupportTicketForm(request.POST)
        if form.is_valid():
            # Use transaction to ensure all database operations succeed or fail together
            with transaction.atomic():
                ticket = form.save(commit=False)
                ticket.doctor = request.user.doctor_profile
                ticket.save()

                # Create notification for admins
                doctor_name = request.user.get_full_name() or request.user.username
                notification_title = f"New Doctor Support Ticket: {ticket.subject}"
                notification_message = f"Dr. {doctor_name} has submitted a new support ticket: {ticket.subject}\n\n{ticket.description}"

                # Get all admin users - use values_list for efficiency
                admin_users = CustomUser.objects.filter(role='admin')
                admin_emails = list(admin_users.values_list('email', flat=True))

                # Bulk create notifications for all admins at once
                notifications = [
                    AdminNotification(
                        recipient=admin,
                        title=notification_title,
                        message=notification_message,
                        support_ticket_type='doctor',
                        ticket_id=ticket.id
                    ) for admin in admin_users
                ]

                if notifications:
                    AdminNotification.objects.bulk_create(notifications)

                # Start a separate thread to send emails
                if admin_emails:
                    email_thread = Thread(
                        target=send_admin_emails_doctor,
                        args=(admin_emails, notification_title, notification_message)
                    )
                    email_thread.daemon = True
                    email_thread.start()

            messages.success(request, "Support ticket submitted successfully. We will respond to your issue soon.")
            return redirect("doctor_section:doctor_help")
    else:
        form = DoctorSupportTicketForm()

    # Get all tickets for the current doctor
    tickets = DoctorSupportTicket.objects.filter(doctor=request.user.doctor_profile).order_by('-date_created')

    context = {
        "form": form,
        "tickets": tickets,
        "now": timezone.now(),  # Add current date for the "New" badge
    }
    return render(request, "doctor_help.html", context)


@login_required
def doctor_reviews(request):
    """
    Optimized Doctor Reviews Page
    Shows student logs for review with proper filtering and status display
    """
    # Check if user has doctor profile
    try:
        doctor = request.user.doctor_profile
    except AttributeError:
        messages.error(request, "Doctor profile not found. Please contact the administrator.")
        return redirect('doctor_section:doctor_dash')

    # Get filter parameters
    department_id = request.GET.get('department')
    status = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    # Auto-assign departments if requested (for testing)
    if request.GET.get('auto_assign') == 'true':
        from admin_section.models import Department
        all_departments = Department.objects.all()
        if all_departments.exists():
            doctor.departments.set(all_departments)
            messages.success(request, f"Auto-assigned Dr. {doctor.user.get_full_name()} to all departments.")
        return redirect('doctor_section:doctor_reviews')

    # Get departments associated with this doctor
    doctor_departments = doctor.departments.all()

    # If no departments assigned, show auto-assign option
    if not doctor_departments.exists():
        from admin_section.models import Department
        all_departments = Department.objects.all()
        context = {
            'logs': [],
            'departments': doctor_departments,
            'selected_department': department_id,
            'selected_status': status,
            'search_query': search_query,
            'show_auto_assign': True,
            'available_departments': all_departments,
            'stats': {'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0}
        }
        if all_departments.exists():
            messages.warning(request, "You are not assigned to any departments. Click 'Auto-assign' to assign yourself to all departments.")
        else:
            messages.error(request, "No departments exist in the system.")
        return render(request, "doctor_reviews.html", context)

    # Base queryset with optimized select_related and prefetch_related
    logs = StudentLogFormModel.objects.select_related(
        'student__user', 'department', 'activity_type', 'core_diagnosis'
    ).filter(department__in=doctor_departments)

    # Apply status filters
    if status == 'pending':
        logs = logs.filter(is_reviewed=False)
    elif status == 'approved':
        logs = logs.filter(is_reviewed=True).filter(
            models.Q(reviewer_comments__isnull=True) |
            ~models.Q(reviewer_comments__startswith='REJECTED:')
        )
    elif status == 'rejected':
        logs = logs.filter(is_reviewed=True, reviewer_comments__startswith='REJECTED:')
    # 'all' shows everything

    if department_id:
        logs = logs.filter(department_id=department_id)

    if search_query:
        logs = logs.filter(
            models.Q(student__user__first_name__icontains=search_query) |
            models.Q(student__user__last_name__icontains=search_query) |
            models.Q(student__student_id__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(patient_id__icontains=search_query)
        )

    # Order by most recent first
    logs = logs.order_by('-date', '-created_at')

    # Calculate statistics
    all_logs = StudentLogFormModel.objects.filter(department__in=doctor_departments)
    stats = {
        'total': all_logs.count(),
        'pending': all_logs.filter(is_reviewed=False).count(),
        'approved': all_logs.filter(is_reviewed=True).filter(
            models.Q(reviewer_comments__isnull=True) |
            ~models.Q(reviewer_comments__startswith='REJECTED:')
        ).count(),
        'rejected': all_logs.filter(is_reviewed=True, reviewer_comments__startswith='REJECTED:').count(),
    }

    # Pagination
    paginator = Paginator(logs, 15)  # 15 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get review settings
    settings = DateRestrictionSettings.objects.first()
    review_period_enabled = settings and settings.doctor_review_enabled if settings else False

    # Add computed fields to logs for template
    for log in page_obj:
        # Determine review status
        if log.is_reviewed:
            if log.reviewer_comments and log.reviewer_comments.startswith('REJECTED:'):
                log.review_status = 'rejected'
                log.review_status_display = 'Rejected'
                log.review_status_class = 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                log.review_status_icon = 'fas fa-times-circle'
            else:
                log.review_status = 'approved'
                log.review_status_display = 'Approved'
                log.review_status_class = 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                log.review_status_icon = 'fas fa-check-circle'
        else:
            log.review_status = 'pending'
            log.review_status_display = 'Pending'
            log.review_status_class = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
            log.review_status_icon = 'fas fa-clock'

        # Add deadline information if enabled
        if review_period_enabled and hasattr(log, 'review_deadline') and log.review_deadline:
            log.deadline_passed = timezone.now() > log.review_deadline
            if not log.deadline_passed:
                time_remaining = log.review_deadline - timezone.now()
                log.days_remaining = time_remaining.days
                log.deadline_warning = log.days_remaining <= (settings.doctor_notification_days if settings else 3)
            else:
                log.days_remaining = 0
                log.deadline_warning = False
        else:
            log.deadline_passed = False
            log.days_remaining = None
            log.deadline_warning = False

    context = {
        'logs': page_obj,
        'departments': doctor_departments,
        'selected_department': department_id,
        'selected_status': status,
        'search_query': search_query,
        'stats': stats,
        'review_period_enabled': review_period_enabled,
        'review_period_days': settings.doctor_review_period if settings else 30,
        'notification_days': settings.doctor_notification_days if settings else 3,
    }

    return render(request, "doctor_reviews.html", context)


def logout(request):
    auth_logout(request)
    # Clear the session username
    request.session.pop("username", None)
    return redirect("login")


@login_required
def notifications(request):
    doctor = request.user.doctor_profile

    # Get all notifications for this doctor
    notifications_list = Notification.objects.filter(recipient=doctor).order_by('-created_at')

    # Mark notifications as read if requested
    if request.GET.get('mark_read'):
        notification_id = request.GET.get('mark_read')
        notification = get_object_or_404(Notification, id=notification_id, recipient=doctor)
        notification.mark_as_read()
        return redirect('doctor_section:notifications')

    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications_list.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('doctor_section:notifications')

    # Pagination
    paginator = Paginator(notifications_list, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'unread_count': notifications_list.filter(is_read=False).count(),
    }

    return render(request, "doctor_notifications.html", context)


@login_required
def delete_support_ticket(request, ticket_id):
    ticket = get_object_or_404(DoctorSupportTicket, id=ticket_id, doctor=request.user.doctor_profile)
    if ticket.status == 'pending':  # Only allow deletion of pending tickets
        ticket.delete()
        messages.success(request, "Support ticket deleted successfully.")
    else:
        messages.error(request, "Cannot delete a ticket that has been resolved.")
    return redirect('doctor_section:doctor_help')


@login_required
def review_log(request, log_id):
    # Get the doctor and the log
    doctor = request.user.doctor_profile
    log = get_object_or_404(StudentLogFormModel, id=log_id)

    # Check if the doctor is associated with the log's department
    if log.department not in doctor.departments.all():
        messages.error(request, "You don't have permission to review this log.")
        return redirect('doctor_section:doctor_reviews')

    # Check if review deadline has passed
    settings = DateRestrictionSettings.objects.first()
    if settings and settings.doctor_review_enabled and log.review_deadline:
        if timezone.now() > log.review_deadline:
            messages.error(request, f"The review period for this log has expired. Logs must be reviewed within {settings.doctor_review_period} days of submission.")
            return redirect('doctor_section:doctor_reviews')

    if request.method == 'POST':
        form = LogReviewForm(request.POST, instance=log)
        if form.is_valid():
            # Save the form but don't commit yet
            log_entry = form.save(commit=False)

            # Set review status based on the form choice
            is_approved = form.cleaned_data['is_approved']
            log_entry.is_reviewed = True

            # Add rejection prefix to comments if rejected
            if is_approved == 'False':
                prefix = "REJECTED: "
                if not log_entry.reviewer_comments.startswith(prefix):
                    log_entry.reviewer_comments = prefix + log_entry.reviewer_comments

            # Set review date
            log_entry.review_date = timezone.now()
            log_entry.save()

            # Create notification for the student
            doctor_name = request.user.get_full_name() or request.user.username
            is_approved_text = 'approved' if is_approved == 'True' else 'rejected'
            notification_title = f"Your log entry has been {is_approved_text}"
            notification_message = f"Dr. {doctor_name} has {is_approved_text} your log entry for {log.department.name} department on {log.date}."

            if log_entry.reviewer_comments:
                notification_message += f" Comments: {log_entry.reviewer_comments}"

            # Create notification in the database
            StudentNotification.objects.create(
                recipient=log.student,
                log_entry=log,
                title=notification_title,
                message=notification_message
            )

            # Send email notification to the student in a separate thread
            if log.student.user.email:
                email_thread = Thread(
                    target=send_student_email,
                    args=(log.student.user.email, notification_title, notification_message)
                )
                email_thread.daemon = True
                email_thread.start()

            messages.success(request, f"Log entry has been {is_approved_text}.")
            return redirect('doctor_section:doctor_reviews')
    else:
        form = LogReviewForm(instance=log)

    # Add deadline information
    now = timezone.now()
    days_remaining = 0
    if log.review_deadline:
        time_remaining = log.review_deadline - now
        days_remaining = max(0, time_remaining.days)

    # Get date restriction settings for doctor
    date_settings = DateRestrictionSettings.objects.first()
    doctor_past_days_limit = date_settings.doctor_past_days_limit if date_settings else 30

    context = {
        'form': form,
        'log': log,
        'now': now,
        'days_remaining': days_remaining,
        'doctor_past_days_limit': doctor_past_days_limit,
    }

    return render(request, 'doctor_review_log.html', context)


@login_required
def batch_review(request):
    if request.method != 'POST':
        return redirect('doctor_section:doctor_reviews')

    form = BatchReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid form submission.")
        return redirect('doctor_section:doctor_reviews')

    # Get form data
    log_ids = form.cleaned_data['log_ids'].split(',')
    action = form.cleaned_data['action']
    comments = form.cleaned_data['comments']

    # Get the doctor
    doctor = request.user.doctor_profile
    doctor_departments = doctor.departments.all()

    # Get logs that belong to the doctor's departments
    logs = StudentLogFormModel.objects.filter(
        id__in=log_ids,
        department__in=doctor_departments
    )

    # Check for review deadline
    settings = DateRestrictionSettings.objects.first()
    if settings and settings.doctor_review_enabled:
        # Filter out logs that have passed their review deadline
        logs = logs.filter(
            models.Q(review_deadline__isnull=True) |
            models.Q(review_deadline__gt=timezone.now())
        )

        # If all logs were filtered out due to expired deadlines
        if not logs.exists():
            messages.error(request, f"Cannot review the selected logs as their review periods have expired. Logs must be reviewed within {settings.doctor_review_period} days of submission.")
            return redirect('doctor_section:doctor_reviews')

    # Process each log
    with transaction.atomic():
        for log in logs:
            log.is_reviewed = True
            log.review_date = timezone.now()

            # Set comments based on action
            if action == 'reject':
                prefix = "REJECTED: "
                log.reviewer_comments = prefix + comments if comments else prefix + "Batch rejected"
            else:  # approve
                log.reviewer_comments = comments if comments else "Approved"

            log.save()

            # Create notification for the student
            doctor_name = request.user.get_full_name() or request.user.username
            is_approved_text = 'approved' if action == 'approve' else 'rejected'
            notification_title = f"Your log entry has been {is_approved_text}"
            notification_message = f"Dr. {doctor_name} has {is_approved_text} your log entry for {log.department.name} department on {log.date}."

            if log.reviewer_comments:
                notification_message += f" Comments: {log.reviewer_comments}"

            # Create notification in the database
            StudentNotification.objects.create(
                recipient=log.student,
                log_entry=log,
                title=notification_title,
                message=notification_message
            )

            # Send email notification to the student in a separate thread
            if log.student.user.email:
                email_thread = Thread(
                    target=send_student_email,
                    args=(log.student.user.email, notification_title, notification_message)
                )
                email_thread.daemon = True
                email_thread.start()

    count = logs.count()
    # If this was an AJAX request, return JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.is_ajax():
        return JsonResponse({
            'success': True,
            'count': count,
            'message': f"{count} log entries have been {'approved' if action == 'approve' else 'rejected'}."
        })

    messages.success(request, f"{count} log entries have been {'approved' if action == 'approve' else 'rejected'}.")
    return redirect('doctor_section:doctor_reviews')


@login_required
def get_log_ids(request):
    """Return a JSON array of log IDs matching current filters for the logged-in doctor."""
    try:
        doctor = request.user.doctor_profile
    except AttributeError:
        return JsonResponse({'log_ids': []})

    department_id = request.GET.get('department')
    status = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    logs = StudentLogFormModel.objects.filter(department__in=doctor.departments.all())

    if status == 'pending':
        logs = logs.filter(is_reviewed=False)
    elif status == 'approved':
        logs = logs.filter(is_reviewed=True).filter(
            models.Q(reviewer_comments__isnull=True) |
            ~models.Q(reviewer_comments__startswith='REJECTED:')
        )
    elif status == 'rejected':
        logs = logs.filter(is_reviewed=True, reviewer_comments__startswith='REJECTED:')

    if department_id:
        logs = logs.filter(department_id=department_id)

    if search_query:
        logs = logs.filter(
            models.Q(student__user__first_name__icontains=search_query) |
            models.Q(student__user__last_name__icontains=search_query) |
            models.Q(student__student_id__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(patient_id__icontains=search_query)
        )

    # Return only IDs
    ids = list(logs.values_list('id', flat=True))
    return JsonResponse({'log_ids': ids})


@login_required
def export_logs(request):
    """Export logs as CSV or PDF based on the current filters"""
    doctor = request.user.doctor_profile
    export_format = request.GET.get('format', 'csv').lower()

    # Get filter parameters (same as in doctor_reviews view)
    department_id = request.GET.get('department')
    status = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    # Get departments associated with this doctor
    doctor_departments = doctor.departments.all()

    # Base queryset - filter by departments the doctor is associated with
    logs = StudentLogFormModel.objects.select_related(
        'student__user', 'department', 'activity_type', 'core_diagnosis'
    ).filter(department__in=doctor_departments)

    # Apply status filters (same logic as doctor_reviews)
    if status == 'pending':
        logs = logs.filter(is_reviewed=False)
    elif status == 'approved':
        logs = logs.filter(is_reviewed=True).filter(
            models.Q(reviewer_comments__isnull=True) |
            ~models.Q(reviewer_comments__startswith='REJECTED:')
        )
    elif status == 'rejected':
        logs = logs.filter(is_reviewed=True, reviewer_comments__startswith='REJECTED:')
    # 'all' shows everything

    if department_id:
        logs = logs.filter(department_id=department_id)

    if search_query:
        logs = logs.filter(
            models.Q(student__user__first_name__icontains=search_query) |
            models.Q(student__user__last_name__icontains=search_query) |
            models.Q(student__student_id__icontains=search_query) |
            models.Q(department__name__icontains=search_query) |
            models.Q(activity_type__name__icontains=search_query)
        )

    # Order by most recent first
    logs = logs.order_by('-date', '-created_at')

    # Prepare filename with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"student_logs_{timestamp}"

    if export_format == 'csv':
        return export_logs_csv(logs, filename_base)
    elif export_format == 'pdf':
        return export_logs_pdf(logs, filename_base, doctor)
    else:
        # Default to CSV if format is not recognized
        return export_logs_csv(logs, filename_base)


def export_logs_csv(logs, filename_base):
    """Export logs as CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'

    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'Student ID', 'Student Name', 'Date', 'Department',
        'Activity Type', 'Core Diagnosis', 'Status', 'Review Date', 'Comments'
    ])

    # Write data rows
    for log in logs:
        status = 'Pending'
        if log.is_reviewed:
            status = 'Rejected' if log.reviewer_comments and log.reviewer_comments.startswith('REJECTED:') else 'Approved'

        writer.writerow([
            log.student.student_id,
            log.student.user.get_full_name(),
            log.date.strftime('%Y-%m-%d'),
            log.department.name,
            log.activity_type.name,
            log.core_diagnosis.name,
            status,
            log.review_date.strftime('%Y-%m-%d') if log.review_date else '',
            log.reviewer_comments or ''
        ])

    return response


def export_logs_pdf(logs, filename_base, doctor):
    """Export logs as PDF file"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'

    # Create a buffer for the PDF
    buffer = io.BytesIO()

    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Add AGU header with logo and university name
    elements = add_agu_header(elements, "Student Logs Report")

    # Get custom styles
    custom_styles = get_common_styles()

    # Add doctor info
    doctor_name = doctor.user.get_full_name() or doctor.user.username
    elements.append(Paragraph(f"Doctor: {doctor_name}", custom_styles['subtitle']))
    elements.append(Paragraph(f"Departments: {', '.join([dept.name for dept in doctor.departments.all()])}", custom_styles['normal']))
    elements.append(Paragraph(f"Total Records: {len(logs)}", custom_styles['normal']))
    elements.append(Spacer(1, 0.3*inch))

    # Create table data
    data = [
        ['Student ID', 'Student Name', 'Date', 'Department', 'Activity Type', 'Status']
    ]

    # Add log data to table
    for log in logs:
        status = 'Pending'
        if log.is_reviewed:
            status = 'Rejected' if log.reviewer_comments and log.reviewer_comments.startswith('REJECTED:') else 'Approved'

        data.append([
            log.student.student_id,
            log.student.user.get_full_name(),
            log.date.strftime('%Y-%m-%d'),
            log.department.name,
            log.activity_type.name,
            status
        ])

    # Create the table
    table = Table(data, repeatRows=1)

    # Style the table
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    # Add alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)

    table.setStyle(table_style)
    elements.append(table)

    # Add footer information
    elements = add_footer_info(
        elements,
        generated_by=doctor_name,
        export_date=timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # Build the PDF
    doc.build(elements)

    # Get the value of the buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


@login_required
def debug_doctor_reviews(request):
    """Debug endpoint to check doctor status and departments"""
    debug_info = {
        'user_authenticated': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', 'No role attribute'),
        'username': request.user.username,
        'user_id': request.user.id,
    }

    # Check doctor profile
    try:
        doctor = request.user.doctor_profile
        debug_info['doctor_profile_exists'] = True
        debug_info['doctor_id'] = doctor.id
        debug_info['doctor_departments'] = [dept.name for dept in doctor.departments.all()]
        debug_info['doctor_departments_count'] = doctor.departments.count()

        # Check logs for this doctor
        logs = StudentLogFormModel.objects.filter(department__in=doctor.departments.all())
        debug_info['total_logs'] = logs.count()
        debug_info['pending_logs'] = logs.filter(is_reviewed=False).count()
        debug_info['reviewed_logs'] = logs.filter(is_reviewed=True).count()

        # Check all logs in system
        all_logs = StudentLogFormModel.objects.all()
        debug_info['total_logs_in_system'] = all_logs.count()
        debug_info['all_departments_with_logs'] = list(set([log.department.name for log in all_logs]))

        # Check if there are any students in the system
        from accounts.models import Student
        all_students = Student.objects.all()
        debug_info['total_students_in_system'] = all_students.count()
        debug_info['students_in_doctor_departments'] = Student.objects.filter(
            group__departments__in=doctor.departments.all()
        ).count() if doctor.departments.exists() else 0

    except AttributeError:
        debug_info['doctor_profile_exists'] = False
        debug_info['doctor_error'] = 'Doctor profile does not exist'

        # Check if any doctor profiles exist
        from accounts.models import Doctor
        all_doctors = Doctor.objects.all()
        debug_info['total_doctors_in_system'] = all_doctors.count()
        debug_info['all_doctor_usernames'] = [d.user.username for d in all_doctors]

    # Create a properly formatted JSON response
    import json
    json_data = json.dumps(debug_info, indent=2, ensure_ascii=False)
    response = HttpResponse(json_data, content_type='application/json')
    return response