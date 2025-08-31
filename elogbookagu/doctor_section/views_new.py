from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, F, Sum, Avg, Case, When, Value, IntegerField
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime
import json
import csv
import io

from accounts.models import Doctor, CustomUser, Student, DoctorProfile
from .models import DoctorSupportTicket, Notification
from .forms import (
    DoctorProfileForm,
    DoctorSupportTicketForm,
    LogReviewForm,
    BatchReviewForm
)
from student_section.models import (
    StudentLogFormModel,
    StudentNotification,
    Department,
    Procedure,
    ActivityType,
    ParticipationType
)
from admin_section.models import AdminNotification
from .decorators import doctor_required

# -----------------------------------------------------------------------------
# Helper Functions for Dashboard Data
# -----------------------------------------------------------------------------

def get_review_overview_data(logs):
    """Prepares data for the 'Review Overview' chart."""
    reviewed_count = logs.filter(is_reviewed=True).count()
    pending_count = logs.filter(is_reviewed=False).count()
    return {
        'labels': ['Reviewed', 'Pending Review'],
        'data': [reviewed_count, pending_count],
        'colors': ['#4CAF50', '#F44336'] # Green, Red
    }

def get_activity_distribution_data(logs):
    """Prepares data for the 'Activity Distribution' chart."""
    activity_data = logs.values('activity_type__name').annotate(
        count=Count('id')
    ).order_by('-count')

    if not activity_data:
        return {'labels': ['No Data'], 'data': [1]}

    return {
        'labels': [item['activity_type__name'] or 'Unknown' for item in activity_data],
        'data': [item['count'] for item in activity_data],
    }

def get_participation_distribution_data(logs):
    """Prepares data for the 'Participation Distribution' chart."""
    participation_data = logs.values('participation_type__name').annotate(
        count=Count('id')
    ).order_by('-count')

    if not participation_data:
        # Provide default structure if no data
        return {'labels': ['Observed', 'Assisted'], 'data': [0, 0]} # Example default

    return {
        'labels': [item['participation_type__name'] or 'Unknown' for item in participation_data],
        'data': [item['count'] for item in participation_data],
    }

def get_student_comparison_data(student_performance_list):
    """Prepares data for the 'Student Performance Comparison' chart (Top N)."""
    # Sort by total logs descending and take top 10
    top_students = sorted(student_performance_list, key=lambda x: x['total_logs'], reverse=True)[:10]

    if not top_students:
        return {'labels': ['No Data'], 'reviewed_data': [0], 'pending_data': [0]}

    return {
        'labels': [s['name'] for s in top_students],
        'reviewed_data': [s['reviewed_logs'] for s in top_students],
        'pending_data': [s['pending_logs'] for s in top_students],
    }

def get_student_status_data(logs):
    """Prepares data for the 'Student Log Status' chart (overall reviewed vs pending)."""
    # This is the same as review overview
    reviewed_count = logs.filter(is_reviewed=True).count()
    pending_count = logs.filter(is_reviewed=False).count()
    return {
        'labels': ['Reviewed', 'Pending'],
        'data': [reviewed_count, pending_count],
    }

def get_top_students_bar_data(student_performance_list):
    """Prepares data for the 'Top Students by Logs' bar chart."""
    # Sort by total logs descending and take top 5-10
    top_students = sorted(student_performance_list, key=lambda x: x['total_logs'], reverse=True)[:10] # Using top 10

    if not top_students or all(s['total_logs'] == 0 for s in top_students):
        return {'labels': ['No Data'], 'data': [0]}

    return {
        'labels': [s['name'] for s in top_students],
        'data': [s['total_logs'] for s in top_students],
    }

def get_monthly_trend_data(logs):
    """Prepares data for the 'Monthly Log Submission Trend' chart."""
    # Use 'created_at' or 'date' field for trend analysis
    trend_field = 'created_at' # Or 'date' if more appropriate
    last_6_months = timezone.now() - timedelta(days=180)

    monthly_data = logs.filter(
        **{f'{trend_field}__gte': last_6_months} # Dynamic field lookup
    ).annotate(
        month=TruncMonth(trend_field)
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    if not monthly_data:
        # Generate labels for the last 6 months for an empty chart
        labels = []
        current_month = timezone.now()
        for i in range(6):
            month = current_month - timedelta(days=i * 30) # Approximate months
            labels.append(month.strftime('%B %Y'))
        return {'labels': labels[::-1], 'data': [0] * 6} # Reverse labels for chronological order

    return {
        'labels': [d['month'].strftime('%B %Y') for d in monthly_data],
        'data': [d['count'] for d in monthly_data]
    }

def get_department_performance_data(logs, departments):
    """Prepares data for the 'Student Performance by Department' chart."""
    dept_stats = []
    
    # Get all department IDs
    all_department_ids = departments.values_list('id', flat=True)
    
    # Get all logs in these departments
    all_logs_in_depts = logs.filter(department_id__in=all_department_ids)
    
    # Process each department
    for dept in departments:
        dept_logs = all_logs_in_depts.filter(department=dept)
        total = dept_logs.count()
        reviewed = dept_logs.filter(is_reviewed=True).count()
        pending = total - reviewed
        
        if total > 0:
            dept_stats.append({
                'name': dept.name,
                'total': total,
                'reviewed': reviewed,
                'pending': pending,
            })
    
    # If no data, return default structure
    if not dept_stats:
        return {
            'labels': ['No Data'],
            'reviewed': [0],
            'pending': [0]
        }
    
    # Sort by total logs descending
    dept_stats = sorted(dept_stats, key=lambda x: x['total'], reverse=True)
    
    # Extract data for chart
    return {
        'labels': [d['name'] for d in dept_stats],
        'reviewed': [d['reviewed'] for d in dept_stats],
        'pending': [d['pending'] for d in dept_stats]
    }

@login_required
@doctor_required
def doctor_dash(request):
    """
    Displays the main dashboard for doctors, showing statistics,
    priority reviews, student performance, and charts.
    Handles filtering by department and student search.
    """
    try:
        # Get doctor profile and departments
        doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
        doctor_departments = doctor_profile.departments.all()
        
        # Store first name in session for template greeting
        request.session['first_name'] = request.user.first_name

        if not doctor_departments.exists():
            messages.warning(request, "You are not assigned to any departments. Please contact an administrator.")
            # Render a minimal dashboard with default values
            return render(request, 'doctor_dash.html', {
                'doctor_profile': doctor_profile,
                'departments': Department.objects.none(),
                'error_message': 'No departments assigned.',
                'total_records': 0,
                'reviewed': 0,
                'left_to_review': 0,
                'review_percentage': 0,
                'priority_records': [],
                'student_performance': [],
                'chart_data': {
                    'activity_distribution': {'labels': ['No Data'], 'data': [1]},
                    'participation_distribution': {'labels': ['No Data'], 'data': [1]},
                    'monthly_trend': {'labels': ['No Data'], 'data': [0]},
                    'student_status_distribution': {'labels': ['No Data'], 'data': [1]},
                    'top_students': {'labels': ['No Data'], 'data': [0]},
                    'department_performance': {'labels': ['No Data'], 'reviewed': [0], 'pending': [0]}
                }
            })

        # --- Filtering Logic ---
        selected_department_id = request.GET.get('department')
        search_query = request.GET.get('q', '').strip()
        
        # Base queryset - filter by doctor's departments
        base_log_queryset = StudentLogFormModel.objects.filter(
            department__in=doctor_departments
        ).select_related(
            'student__user', 'department', 'activity_type', 'participation_type'
        )
        
        # Apply department filter if selected
        if selected_department_id:
            try:
                selected_department_id = int(selected_department_id)
                base_log_queryset = base_log_queryset.filter(department_id=selected_department_id)
            except (ValueError, TypeError):
                # Invalid department ID, ignore filter
                selected_department_id = None
        
        # Apply search filter if provided
        if search_query:
            base_log_queryset = base_log_queryset.filter(
                Q(student__user__first_name__icontains=search_query) |
                Q(student__user__last_name__icontains=search_query) |
                Q(student__user__email__icontains=search_query) |
                Q(student__student_id__icontains=search_query)
            )

        # --- Dashboard Statistics ---
        total_records = base_log_queryset.count()
        reviewed_count = base_log_queryset.filter(is_reviewed=True).count()
        left_to_review_count = base_log_queryset.filter(is_reviewed=False).count()
        
        # Calculate review percentage
        review_percentage = 0
        if total_records > 0:
            review_percentage = round((reviewed_count / total_records) * 100)
        
        # --- Priority Records ---
        # Get the 5 oldest unreviewed logs
        priority_records = base_log_queryset.filter(
            is_reviewed=False
        ).order_by('created_at')[:5]
        
        priority_records_list = []
        for log in priority_records:
            priority_records_list.append({
                'id': log.id,
                'student_name': log.student.user.get_full_name() or log.student.user.username,
                'student_id': log.student.student_id,
                'department': log.department.name,
                'activity_type': log.activity_type.name if log.activity_type else 'N/A',
                'date_submitted': log.created_at.strftime('%d %b %Y'),
                'days_pending': (timezone.now() - log.created_at).days
            })

        # --- Student Performance Data ---
        # Get unique students from the filtered log set
        student_ids_in_logs = base_log_queryset.values_list('student_id', flat=True).distinct()
        students_for_perf = Student.objects.filter(id__in=student_ids_in_logs).select_related('user', 'department')
        
        student_performance_list = []
        max_logs_for_perf_calc = 1  # Avoid division by zero
        
        log_counts = [base_log_queryset.filter(student=st).count() for st in students_for_perf]
        if log_counts:
            max_logs_for_perf_calc = max(log_counts) if max(log_counts) > 0 else 1
        
        for student in students_for_perf:
            student_logs = base_log_queryset.filter(student=student)
            total_student_logs = student_logs.count()
            reviewed_logs = student_logs.filter(is_reviewed=True).count()
            pending_logs = total_student_logs - reviewed_logs
            
            # Calculate percentages
            s_reviewed_percentage = 0
            s_pending_percentage = 0
            s_completion_percentage = 0
            s_performance_percentage = 0
            
            if total_student_logs > 0:
                s_reviewed_percentage = round((reviewed_logs / total_student_logs) * 100)
                s_pending_percentage = 100 - s_reviewed_percentage
                s_completion_percentage = s_reviewed_percentage
            
            if max_logs_for_perf_calc > 0:
                s_performance_percentage = round((total_student_logs / max_logs_for_perf_calc) * 100)
            
            student_performance_list.append({
                'name': student.user.get_full_name() or student.user.username,
                'email': student.user.email,
                'student_id': student.student_id,
                'department': student.department.name if student.department else 'N/A',
                'total_logs': total_student_logs,
                'reviewed_logs': reviewed_logs,
                'pending_logs': pending_logs,
                'reviewed_percentage': s_reviewed_percentage,
                'pending_percentage': s_pending_percentage,
                'completion_percentage': s_completion_percentage,
                'performance_percentage': s_performance_percentage,
            })

        # --- Chart Data Preparation ---
        chart_data = {
            'activity_distribution': get_activity_distribution_data(base_log_queryset),
            'participation_distribution': get_participation_distribution_data(base_log_queryset),
            'student_status_distribution': get_student_status_data(base_log_queryset),
            'monthly_trend': get_monthly_trend_data(base_log_queryset),
            'top_students': get_top_students_bar_data(student_performance_list),
            'department_performance': get_department_performance_data(base_log_queryset, doctor_departments),
        }

        # --- Context Preparation ---
        context = {
            'doctor_profile': doctor_profile,
            'departments': Department.objects.all().order_by('name'),
            'selected_department': selected_department_id,
            'search_query': search_query,
            'total_records': total_records,
            'reviewed': reviewed_count,
            'left_to_review': left_to_review_count,
            'review_percentage': review_percentage,
            'priority_records': priority_records_list,
            'student_performance': student_performance_list,
            'chart_data': chart_data,  # Pass chart data directly, not as JSON
            'pending_percentage': 100 - review_percentage if total_records > 0 else 0,
            'reviewed_percentage_overall': review_percentage,
        }

        return render(request, 'doctor_dash.html', context)

    except Http404:
        messages.error(request, "Doctor profile not found.")
        return redirect(reverse('accounts:login'))
    except Exception as e:
        # Log the exception for debugging
        import traceback
        print(f"Error in doctor_dash view: {e}")
        print(traceback.format_exc())
        
        messages.error(request, "An unexpected error occurred while loading the dashboard. Please try again later or contact support.")
        
        # Render a simpler error state
        context = {
            'error': True,
            'error_message': str(e),
            'doctor_profile': None,
            'departments': Department.objects.none(),
            'selected_department': None,
            'search_query': '',
            'total_records': 0,
            'reviewed': 0,
            'left_to_review': 0,
            'review_percentage': 0,
            'priority_records': [],
            'student_performance': [],
            'chart_data': {
                'activity_distribution': {'labels': ['Error'], 'data': [1]},
                'participation_distribution': {'labels': ['Error'], 'data': [1]},
                'monthly_trend': {'labels': ['Error'], 'data': [0]},
                'student_status_distribution': {'labels': ['Error'], 'data': [1]},
                'top_students': {'labels': ['Error'], 'data': [0]},
                'department_performance': {'labels': ['Error'], 'reviewed': [0], 'pending': [0]}
            },
            'pending_percentage': 0,
            'reviewed_percentage_overall': 0
        }
        
        return render(request, 'doctor_dash.html', context)
