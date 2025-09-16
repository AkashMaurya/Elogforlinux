# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction, models
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import timedelta
from threading import Thread
from accounts.models import Staff, CustomUser
from student_section.models import StudentLogFormModel
from admin_section.models import Department, AdminNotification
from .models import StaffSupportTicket, StaffNotification
from .forms import LogReviewForm, BatchReviewForm, ProfileUpdateForm, StaffSupportTicketForm
from django.http import HttpResponse
import csv
import io
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from utils.pdf_utils import add_agu_header, get_common_styles, add_footer_info
import tablib
from django.conf import settings
from datetime import datetime

# Staff Dashboard View

@login_required
def staff_dash(request):
    user = request.user

    # Check if user has staff role
    if user.role != 'staff':
        messages.error(request, 'You do not have permission to access the staff dashboard.')
        return redirect('login')

    try:
        staff = user.staff_profile
    except Staff.DoesNotExist:
        # Create staff profile if it doesn't exist
        staff = Staff.objects.create(user=user)
        messages.success(request, 'Staff profile has been created successfully.')

    # Ensure session data is available
    if 'first_name' not in request.session:
        request.session['first_name'] = user.first_name
        request.session['last_name'] = user.last_name
        request.session['email'] = user.email
        request.session.save()

    # Get filter parameters
    selected_department = request.GET.get('department')
    search_query = request.GET.get('search', '').strip()

    # Get staff's departments
    departments = staff.departments.all()

    # Base queryset for logs - filter by departments the staff is associated with
    logs = StudentLogFormModel.objects.filter(department__in=departments)

    # Get all doctors in staff's departments
    from accounts.models import Doctor
    department_doctors = Doctor.objects.filter(departments__in=departments).distinct()

    # Filter by selected department if provided
    if selected_department:
        # Ensure the selected department is one of the staff's departments
        try:
            selected_dept = Department.objects.get(id=selected_department)
            if selected_dept in departments:
                logs = logs.filter(department=selected_dept)
                # Also filter doctors by the selected department
                department_doctors = department_doctors.filter(departments=selected_dept)
            else:
                # If the department doesn't belong to the staff, ignore the filter
                selected_department = None
        except Department.DoesNotExist:
            # If the department doesn't exist, ignore the filter
            selected_department = None

    # We've removed the doctor filter functionality

    # Filter doctors by search query if provided
    filtered_doctors = department_doctors
    if search_query:
        filtered_doctors = department_doctors.filter(
            models.Q(user__first_name__icontains=search_query) |
            models.Q(user__last_name__icontains=search_query) |
            models.Q(user__email__icontains=search_query) |
            models.Q(user__username__icontains=search_query) |
            models.Q(user__speciality__icontains=search_query)
        )

    # Get current date and start of month
    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get accurate counts for performance metrics
    reviewed_logs = StudentLogFormModel.objects.filter(
        department__in=departments,
        is_reviewed=True
    )

    pending_logs = StudentLogFormModel.objects.filter(
        department__in=departments,
        is_reviewed=False
    )

    monthly_reviews = StudentLogFormModel.objects.filter(
        department__in=departments,
        is_reviewed=True,
        review_date__gte=start_of_month
    ).count()

    # Performance metrics
    performance_data = {
        'total_reviews': reviewed_logs.count(),
        'pending_reviews': pending_logs.count(),
        'monthly_reviews': monthly_reviews,
        'approval_rate': calculate_approval_rate(reviewed_logs),
    }

    # Chart data
    chart_data = {
        'daily_reviews': get_daily_reviews_data(logs),
        'department_stats': get_department_stats(logs, departments),
        'review_status': get_review_status_data(logs),
        'monthly_trend': get_monthly_trend_data(logs),
    }

    # Get accurate counts directly from the database
    # Total records in staff's departments
    total_records = StudentLogFormModel.objects.filter(department__in=departments).count()

    # Records that have been reviewed
    reviewed_count = StudentLogFormModel.objects.filter(
        department__in=departments,
        is_reviewed=True
    ).count()

    # Records left to review
    left_to_review = StudentLogFormModel.objects.filter(
        department__in=departments,
        is_reviewed=False
    ).count()

    # Double-check that counts are consistent
    if total_records != (reviewed_count + left_to_review):
        # If there's a discrepancy, recalculate to ensure consistency
        total_records = reviewed_count + left_to_review

    # Get doctor information for display
    doctors_info = []
    for doctor in filtered_doctors:
        # Get performance metrics for this doctor
        # Use tutor field instead of reviewer since there's no reviewer field
        doctor_logs = StudentLogFormModel.objects.filter(
            department__in=departments,
            tutor=doctor
        )

        # Count total logs and reviewed logs
        total_logs = doctor_logs.count()
        reviewed_logs = doctor_logs.filter(is_reviewed=True).count()
        monthly_logs = doctor_logs.filter(date__gte=start_of_month).count()

        doctors_info.append({
            'id': doctor.id,
            'name': doctor.user.get_full_name() or doctor.user.username,
            'email': doctor.user.email,
            'speciality': doctor.user.speciality,
            'departments': ', '.join([dept.name for dept in doctor.departments.all()]),
            'total_logs': total_logs,
            'reviewed_logs': reviewed_logs,
            'monthly_logs': monthly_logs,
            'review_percentage': round((reviewed_logs / total_logs * 100)) if total_logs > 0 else 0
        })

    # Calculate percentage for progress circle
    review_percentage = 0
    if total_records > 0:
        review_percentage = int((reviewed_count / total_records) * 100)

    context = {
        'staff': staff,
        'user': user,
        'performance_data': performance_data,
        'chart_data': chart_data,
        'departments': departments,
        'selected_department': selected_department,
        'search_query': search_query,
        'total_records': total_records,
        'left_to_review': left_to_review,
        'reviewed': reviewed_count,
        'review_percentage': review_percentage,
        'doctors': doctors_info,
        'today': today,
    }

    return render(request, "staff_section/staff_dash.html", context)

@login_required
def staff_support(request):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    # Get the staff profile
    try:
        staff = request.user.staff_profile
    except Staff.DoesNotExist:
        staff = Staff.objects.create(user=request.user)
        messages.info(request, 'Staff profile has been created.')

    if request.method == "POST":
        form = StaffSupportTicketForm(request.POST)
        if form.is_valid():
            # Use transaction to ensure all database operations succeed or fail together
            with transaction.atomic():
                ticket = form.save(commit=False)
                ticket.staff = staff
                ticket.save()

                # Create notification for admins
                staff_name = request.user.get_full_name() or request.user.username
                notification_title = f"New Staff Support Ticket: {ticket.subject}"
                notification_message = f"{staff_name} has submitted a new support ticket: {ticket.subject}\n\n{ticket.description}"

                # Get all admin users - use values_list for efficiency
                from accounts.models import CustomUser
                from admin_section.models import AdminNotification
                admin_users = CustomUser.objects.filter(role='admin')
                admin_emails = list(admin_users.values_list('email', flat=True))

                # Bulk create notifications for all admins at once
                notifications = [
                    AdminNotification(
                        recipient=admin,
                        title=notification_title,
                        message=notification_message,
                        support_ticket_type='staff',
                        ticket_id=ticket.id
                    ) for admin in admin_users
                ]

                if notifications:
                    AdminNotification.objects.bulk_create(notifications)

                # Start a separate thread to send emails
                if admin_emails:
                    from threading import Thread
                    from admin_section.views import send_admin_emails

                    email_thread = Thread(
                        target=send_admin_emails,
                        args=(admin_emails, notification_title, notification_message)
                    )
                    email_thread.daemon = True
                    email_thread.start()

            messages.success(request, "Support ticket submitted successfully. We will respond to your issue soon.")
            return redirect("staff_section:staff_support")
    else:
        form = StaffSupportTicketForm()

    # Get all tickets for the current staff
    tickets = StaffSupportTicket.objects.filter(staff=staff).order_by('-date_created')

    context = {
        "form": form,
        "tickets": tickets,
        "now": timezone.now(),  # Add current date for the "New" badge
    }
    return render(request, "staff_section/staff_support.html", context)

@login_required
# Staff Reviews View
def staff_reviews(request):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    staff = request.user.staff_profile

    # Get filter parameters
    department_id = request.GET.get('department')
    status = request.GET.get('status', 'pending')
    search_query = request.GET.get('q', '').strip()

    # Get departments associated with this staff
    staff_departments = staff.departments.all()

    # Base queryset - filter by departments the staff is associated with
    logs = StudentLogFormModel.objects.filter(department__in=staff_departments)

    # Filter by review status
    if status == 'pending':
        logs = logs.filter(is_reviewed=False)
    elif status == 'reviewed':
        logs = logs.filter(is_reviewed=True)
    # If 'all' is selected, don't apply any filter

    # Filter by specific department if selected
    if department_id:
        logs = logs.filter(department_id=department_id)

    # Apply search filter if provided
    if search_query:
        logs = logs.filter(
            models.Q(student__user__first_name__icontains=search_query) |
            models.Q(student__user__last_name__icontains=search_query) |
            models.Q(student__student_id__icontains=search_query) |
            models.Q(patient_id__icontains=search_query)
        )

    # Order by most recent first
    logs = logs.order_by('-date', '-created_at')

    # Pagination
    paginator = Paginator(logs, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Create batch review form
    batch_form = BatchReviewForm()

    context = {
        'logs': page_obj,
        'departments': staff_departments,
        'selected_department': department_id,
        'selected_status': status,
        'search_query': search_query,
        'batch_form': batch_form,
    }

    return render(request, "staff_section/staff_reviews.html", context)

@login_required
# Staff Profile View
def staff_profile(request):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    user = request.user
    try:
        staff = user.staff_profile
    except Staff.DoesNotExist:
        staff = Staff.objects.create(user=user)
        messages.info(request, 'Staff profile has been created.')

    # Get the profile photo URL
    profile_photo = user.profile_photo.url if user.profile_photo else "/media/profiles/default.jpg"

    # Handle form submission
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('staff_section:staff_profile')
        else:
            messages.error(request, 'There was an error updating your profile. Please check the form.')
    else:
        form = ProfileUpdateForm(instance=user)

    # Get staff departments
    departments = staff.departments.all()

    data = {
        "staff": staff,
        "profile_photo": profile_photo,
        "full_name": f"{user.first_name} {user.last_name}",
        "user_email": user.email,
        "user_phone": user.phone_no,
        "user_city": user.city,
        "user_country": user.country,
        "user_bio": user.bio if hasattr(user, "bio") else "",
        "form": form,
        "departments": departments,
    }

    return render(request, "staff_section/staff_profile.html", data)


def calculate_approval_rate(reviewed_logs):
    # reviewed_logs should already be filtered for is_reviewed=True
    total_reviewed = reviewed_logs.count()
    if total_reviewed == 0:
        return 0

    # Count rejected logs (those with REJECTED in comments)
    rejected = reviewed_logs.filter(reviewer_comments__startswith='REJECTED').count()

    # Calculate approval rate (percentage of non-rejected logs)
    return round((1 - rejected / total_reviewed) * 100)


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
        # Get accurate counts for each department
        reviewed = StudentLogFormModel.objects.filter(
            department=dept,
            is_reviewed=True
        ).count()

        pending = StudentLogFormModel.objects.filter(
            department=dept,
            is_reviewed=False
        ).count()

        total = reviewed + pending

        dept_stats.append({
            'name': dept.name,
            'total': total,
            'reviewed': reviewed,
            'pending': pending
        })
    return dept_stats


def get_review_status_data(logs):
    # Get accurate counts directly
    reviewed = logs.filter(is_reviewed=True).count()
    pending = logs.filter(is_reviewed=False).count()
    total = reviewed + pending

    return {
        'labels': ['Reviewed', 'Pending'],
        'data': [reviewed, pending]
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

    return {
        'labels': [d['month'].strftime('%B %Y') for d in monthly_data],
        'data': [d['count'] for d in monthly_data]
    }


@login_required
def notifications(request):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    staff = request.user.staff_profile

    # Get all notifications for this staff
    notifications_list = StaffNotification.objects.filter(recipient=staff).order_by('-created_at')

    # Mark notifications as read if requested
    if request.GET.get('mark_read'):
        notification_id = request.GET.get('mark_read')
        notification = get_object_or_404(StaffNotification, id=notification_id, recipient=staff)
        notification.mark_as_read()
        return redirect('staff_section:notifications')

    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications_list.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('staff_section:notifications')

    # Get unread count (for display in the UI)
    unread_count = StaffNotification.objects.filter(recipient=staff, is_read=False).count()

    # Pagination
    paginator = Paginator(notifications_list, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
    }

    return render(request, 'staff_section/staff_notifications.html', context)


@login_required
def review_log(request, log_id):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    # Get the log
    log = get_object_or_404(StudentLogFormModel, id=log_id)

    # Get staff departments
    staff = request.user.staff_profile
    staff_departments = staff.departments.all()

    # Check if the log belongs to a department the staff is associated with
    if log.department not in staff_departments:
        messages.error(request, 'You do not have permission to review this log.')
        return redirect('staff_section:staff_reviews')

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
            staff_name = request.user.get_full_name() or request.user.username
            is_approved_text = 'approved' if is_approved == 'True' else 'rejected'
            notification_title = f"Your log entry has been {is_approved_text}"
            notification_message = f"{staff_name} has {is_approved_text} your log entry for {log.department.name} department on {log.date}."

            if log_entry.reviewer_comments:
                notification_message += f" Comments: {log_entry.reviewer_comments}"

            # Create notification in the database
            from student_section.models import StudentNotification
            StudentNotification.objects.create(
                recipient=log.student,
                log_entry=log,
                title=notification_title,
                message=notification_message
            )

            messages.success(request, f"Log entry has been {'approved' if is_approved == 'True' else 'rejected'}.")
            return redirect('staff_section:staff_reviews')
    else:
        form = LogReviewForm(instance=log)

    context = {
        'form': form,
        'log': log,
    }

    return render(request, 'staff_section/staff_review_log.html', context)


@login_required
def batch_review(request):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    if request.method != 'POST':
        return redirect('staff_section:staff_reviews')

    form = BatchReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid form submission.")
        return redirect('staff_section:staff_reviews')

    # Get form data
    log_ids = form.cleaned_data['log_ids'].split(',')
    action = form.cleaned_data['action']
    comments = form.cleaned_data['comments']

    # Get the staff
    staff = request.user.staff_profile
    staff_departments = staff.departments.all()

    # Get logs that belong to the staff's departments
    logs = StudentLogFormModel.objects.filter(
        id__in=log_ids,
        department__in=staff_departments
    )

    if not logs.exists():
        messages.warning(request, "No logs found to review.")
        return redirect('staff_section:staff_reviews')

    # Process logs in a transaction
    with transaction.atomic():
        for log in logs:
            log.is_reviewed = True

            # Set comments if provided
            if comments:
                log.reviewer_comments = comments

            # Add rejection prefix if rejecting
            if action == 'reject':
                prefix = "REJECTED: "
                if not log.reviewer_comments.startswith(prefix):
                    log.reviewer_comments = prefix + log.reviewer_comments

            # Set review date
            log.review_date = timezone.now()
            log.save()

            # Create notification for the student
            staff_name = request.user.get_full_name() or request.user.username
            is_approved_text = 'approved' if action == 'approve' else 'rejected'
            notification_title = f"Your log entry has been {is_approved_text}"
            notification_message = f"{staff_name} has {is_approved_text} your log entry for {log.department.name} department on {log.date}."

            if log.reviewer_comments:
                notification_message += f" Comments: {log.reviewer_comments}"

            # Create notification in the database
            from student_section.models import StudentNotification
            StudentNotification.objects.create(
                recipient=log.student,
                log_entry=log,
                title=notification_title,
                message=notification_message
            )

    messages.success(request, f"{logs.count()} log entries have been {'approved' if action == 'approve' else 'rejected'}.")
    return redirect('staff_section:staff_reviews')


@login_required
def delete_support_ticket(request, ticket_id):
    if request.user.role != 'staff':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    ticket = get_object_or_404(StaffSupportTicket, id=ticket_id, staff=request.user.staff_profile)
    if ticket.status == 'pending':  # Only allow deletion of pending tickets
        ticket.delete()
        messages.success(request, "Support ticket deleted successfully.")
    else:
        messages.error(request, "Cannot delete a ticket that has been resolved.")
    return redirect('staff_section:staff_support')

@login_required
def export_staff_reviews(request):
    staff = request.user.staff_profile
    export_format = request.GET.get('format', 'csv').lower()
    department_id = request.GET.get('department')
    status = request.GET.get('status', 'pending')
    search_query = request.GET.get('q', '').strip()
    staff_departments = staff.departments.all()
    logs = StudentLogFormModel.objects.select_related(
        'student__user', 'department', 'activity_type', 'core_diagnosis'
    ).filter(department__in=staff_departments)
    if status == 'pending':
        logs = logs.filter(is_reviewed=False)
    elif status == 'reviewed':
        logs = logs.filter(is_reviewed=True)
    if department_id:
        logs = logs.filter(department_id=department_id)
    if search_query:
        logs = logs.filter(
            models.Q(student__user__first_name__icontains=search_query) |
            models.Q(student__user__last_name__icontains=search_query) |
            models.Q(student__student_id__icontains=search_query) |
            models.Q(patient_id__icontains=search_query)
        )
    logs = logs.order_by('-date', '-created_at')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"staff_reviews_{timestamp}"
    if export_format == 'csv':
        return export_staff_reviews_csv(logs, filename_base)
    elif export_format == 'excel':
        return export_staff_reviews_excel(logs, filename_base)
    elif export_format == 'pdf':
        return export_staff_reviews_pdf(logs, filename_base, staff)
    else:
        return export_staff_reviews_csv(logs, filename_base)

def export_staff_reviews_csv(logs, filename_base):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Student Name', 'Date', 'Department',
        'Activity Type', 'Core Diagnosis', 'Status', 'Review Date', 'Comments'
    ])
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
            getattr(log.core_diagnosis, 'name', ''),
            status,
            log.review_date.strftime('%Y-%m-%d') if log.review_date else '',
            log.reviewer_comments or ''
        ])
    return response

def export_staff_reviews_excel(logs, filename_base):
    data = tablib.Dataset()
    data.headers = [
        'Student ID', 'Student Name', 'Date', 'Department',
        'Activity Type', 'Core Diagnosis', 'Status', 'Review Date', 'Comments'
    ]
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
            getattr(log.core_diagnosis, 'name', ''),
            status,
            log.review_date.strftime('%Y-%m-%d') if log.review_date else '',
            log.reviewer_comments or ''
        ])
    response = HttpResponse(
        data.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
    return response

def export_staff_reviews_pdf(logs, filename_base, staff):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    elements = add_agu_header(elements, "Staff Reviews Report")
    custom_styles = get_common_styles()
    staff_name = staff.user.get_full_name() or staff.user.username
    elements.append(Paragraph(f"Staff: {staff_name}", custom_styles['subtitle']))
    elements.append(Paragraph(f"Departments: {', '.join([dept.name for dept in staff.departments.all()])}", custom_styles['normal']))
    elements.append(Paragraph(f"Total Records: {len(logs)}", custom_styles['normal']))
    elements.append(Spacer(1, 0.3*inch))
    data = [
        ['Student ID', 'Student Name', 'Date', 'Department', 'Activity Type', 'Status']
    ]
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
    table = Table(data, repeatRows=1)
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
    for i in range(1, len(data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
    table.setStyle(table_style)
    elements.append(table)
    elements = add_footer_info(
        elements,
        generated_by=staff_name,
        export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
