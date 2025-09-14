from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import date, timedelta
import csv
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import tablib
from utils.pdf_utils import add_agu_header, get_common_styles, add_footer_info
from .models import StudentAttendance
from .forms import AttendanceForm, StudentAttendanceForm
from accounts.models import Student, Doctor
from admin_section.models import MappedAttendance, TrainingSite, Group, DateRestrictionSettings


@login_required
def take_attendance(request):
    """Main attendance taking view"""
    # Check if user has doctor role
    if not hasattr(request.user, 'role') or request.user.role != 'doctor':
        messages.error(request, "You must be a doctor to access this page.")
        return redirect('doctor_section:doctor_dash')

    # Check if attendance tracking is enabled
    settings = DateRestrictionSettings.objects.first()
    if settings and not settings.attendance_tracking_enabled:
        messages.error(request, "Student attendance tracking is currently disabled by the administrator.")
        return redirect('doctor_section:doctor_dash')

    # Check if doctor profile exists
    try:
        doctor = request.user.doctor_profile
    except (Doctor.DoesNotExist, AttributeError):
        messages.error(request, "Doctor profile not found. Please contact the administrator to create your doctor profile.")
        return redirect('doctor_section:doctor_dash')

    # Get mapped training sites for this doctor
    mapped_attendances = MappedAttendance.objects.filter(
        doctors=doctor,
        is_active=True
    ).select_related('training_site').prefetch_related('groups')

    if not mapped_attendances.exists():
        # Check if doctor exists in any mappings (active or inactive)
        all_mappings = MappedAttendance.objects.filter(doctors=doctor)

        if all_mappings.exists():
            inactive_count = all_mappings.filter(is_active=False).count()
            if inactive_count > 0:
                messages.warning(request, f"You have {inactive_count} inactive training site mapping(s). Please contact the administrator to activate them.")
            else:
                messages.warning(request, "Your training site mappings are not active. Please contact the administrator.")
        else:
            messages.warning(request, "You are not mapped to any training sites. Please contact the administrator to create attendance mappings for you.")

        return redirect('doctor_section:doctor_dash')

    selected_training_site = None
    students_data = []
    today = date.today()

    # Handle form processing
    if request.method == 'POST':
        form = AttendanceForm(doctor=doctor, data=request.POST)
        if form.is_valid():
            training_site = form.cleaned_data['training_site']
            attendance_date = form.cleaned_data['attendance_date']
            general_notes = form.cleaned_data['notes']

            # Get students for this training site and doctor mapping
            students_data = get_students_for_attendance(doctor, training_site, attendance_date)
            selected_training_site = training_site

            # Process attendance if submitted
            if 'submit_attendance' in request.POST:
                return process_attendance_submission(request, doctor, training_site, attendance_date, general_notes)
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AttendanceForm(doctor=doctor)

    # Get date restriction settings
    date_settings = DateRestrictionSettings.objects.first()
    doctor_past_days_limit = date_settings.doctor_past_days_limit if date_settings else 30

    context = {
        'form': form,
        'mapped_attendances': mapped_attendances,
        'students_data': students_data,
        'selected_training_site': selected_training_site,
        'today': today,
        'doctor_past_days_limit': doctor_past_days_limit,
    }

    return render(request, 'doctor_section/take_attendance.html', context)


def get_students_for_attendance(doctor, training_site, attendance_date):
    """Get students mapped to the doctor and training site with their attendance status"""
    # Get mapped attendance records for this doctor and training site
    mapped_attendance = MappedAttendance.objects.filter(
        doctors=doctor,
        training_site=training_site,
        is_active=True
    ).prefetch_related('groups__students__user').first()

    if not mapped_attendance:
        return []

    students_data = []
    
    # Get all students from mapped groups
    for group in mapped_attendance.groups.all():
        for student in group.students.select_related('user').all():
            # Check if attendance already exists for this student today
            existing_attendance = StudentAttendance.objects.filter(
                student=student,
                training_site=training_site,
                date=attendance_date
            ).first()

            student_data = {
                'student': student,
                'group': group,
                'existing_attendance': existing_attendance,
                'form': StudentAttendanceForm(instance=existing_attendance) if existing_attendance else StudentAttendanceForm()
            }
            students_data.append(student_data)

    return students_data


def process_attendance_submission(request, doctor, training_site, attendance_date, general_notes):
    """Process the attendance form submission"""
    try:
        with transaction.atomic():
            # Get all students for this mapping
            students_data = get_students_for_attendance(doctor, training_site, attendance_date)
            
            attendance_count = 0
            for student_data in students_data:
                student = student_data['student']
                group = student_data['group']
                
                # Get attendance status from form
                status_key = f'student_{student.id}_status'
                notes_key = f'student_{student.id}_notes'
                
                status = request.POST.get(status_key)
                notes = request.POST.get(notes_key, '')
                
                if status in ['present', 'absent']:
                    # Update or create attendance record
                    attendance, created = StudentAttendance.objects.update_or_create(
                        student=student,
                        training_site=training_site,
                        date=attendance_date,
                        defaults={
                            'doctor': doctor,
                            'group': group,
                            'status': status,
                            'notes': f"{general_notes}\n{notes}".strip() if general_notes and notes else (general_notes or notes),
                        }
                    )
                    attendance_count += 1

            messages.success(request, f"Attendance recorded successfully for {attendance_count} students.")
            return redirect('doctor_section:attendance_history')

    except Exception as e:
        messages.error(request, f"Error recording attendance: {str(e)}")
        return redirect('doctor_section:take_attendance')


@login_required
def attendance_history(request):
    """View attendance history for the doctor with enhanced filtering"""
    # Check if attendance tracking is enabled
    settings = DateRestrictionSettings.objects.first()
    if settings and not settings.attendance_tracking_enabled:
        messages.error(request, "Student attendance tracking is currently disabled by the administrator.")
        return redirect('doctor_section:doctor_dash')

    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "You must be a doctor to access this page.")
        return redirect('doctor_section:doctor_dash')

    # Get attendance records marked by this doctor
    attendances = StudentAttendance.objects.filter(
        doctor=doctor
    ).select_related(
        'student__user', 'training_site', 'group'
    ).order_by('-date', '-marked_at')

    # Enhanced filtering
    # Date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        try:
            start_date_obj = date.fromisoformat(start_date)
            attendances = attendances.filter(date__gte=start_date_obj)
        except ValueError:
            start_date = None

    if end_date:
        try:
            end_date_obj = date.fromisoformat(end_date)
            attendances = attendances.filter(date__lte=end_date_obj)
        except ValueError:
            end_date = None

    # Single date filter (for backward compatibility)
    single_date = request.GET.get('date')
    if single_date and not start_date and not end_date:
        try:
            filter_date = date.fromisoformat(single_date)
            attendances = attendances.filter(date=filter_date)
        except ValueError:
            single_date = None

    # Training site filter
    training_site_filter = request.GET.get('training_site')
    if training_site_filter:
        attendances = attendances.filter(training_site_id=training_site_filter)

    # Student search filter
    student_search = request.GET.get('student_search', '').strip()
    if student_search:
        attendances = attendances.filter(
            Q(student__user__first_name__icontains=student_search) |
            Q(student__user__last_name__icontains=student_search) |
            Q(student__user__username__icontains=student_search) |
            Q(student__student_id__icontains=student_search)
        )

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        attendances = attendances.filter(status=status_filter)

    # Get training sites for filter dropdown
    training_sites = TrainingSite.objects.filter(
        mapped_attendances__doctors=doctor,
        mapped_attendances__is_active=True
    ).distinct()

    # Calculate statistics for the filtered attendances
    total_records = attendances.count()
    present_count = attendances.filter(status='present').count()
    absent_count = attendances.filter(status='absent').count()

    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 20)  # Default 20 records per page

    # Validate per_page parameter
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
    except (ValueError, TypeError):
        per_page = 20

    paginator = Paginator(attendances, per_page)

    try:
        attendances_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        attendances_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        attendances_page = paginator.page(paginator.num_pages)

    context = {
        'attendances': attendances_page,
        'training_sites': training_sites,
        'selected_date': single_date,
        'start_date': start_date,
        'end_date': end_date,
        'selected_training_site': training_site_filter,
        'student_search': student_search,
        'selected_status': status_filter,
        'total_records': total_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'per_page': per_page,
        'paginator': paginator,
    }

    return render(request, 'doctor_section/attendance_history.html', context)


@login_required
def get_students_for_site(request):
    """AJAX endpoint to get students for a selected training site"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        return JsonResponse({'error': 'Not authorized'}, status=403)

    training_site_id = request.GET.get('training_site_id')
    if not training_site_id:
        return JsonResponse({'error': 'Training site ID required'}, status=400)

    try:
        training_site = TrainingSite.objects.get(id=training_site_id)
        students_data = get_students_for_attendance(doctor, training_site, date.today())
        
        students_list = []
        for student_data in students_data:
            student = student_data['student']
            group = student_data['group']
            existing_attendance = student_data['existing_attendance']
            
            students_list.append({
                'id': student.id,
                'name': student.user.get_full_name() or student.user.username,
                'student_id': student.student_id,
                'group': group.group_name,
                'existing_status': existing_attendance.status if existing_attendance else None,
                'existing_notes': existing_attendance.notes if existing_attendance else '',
            })

        return JsonResponse({'students': students_list})

    except TrainingSite.DoesNotExist:
        return JsonResponse({'error': 'Training site not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def attendance_summary(request):
    """View attendance summary and statistics"""
    # Check if attendance tracking is enabled
    settings = DateRestrictionSettings.objects.first()
    if settings and not settings.attendance_tracking_enabled:
        messages.error(request, "Student attendance tracking is currently disabled by the administrator.")
        return redirect('doctor_section:doctor_dash')

    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "You must be a doctor to access this page.")
        return redirect('doctor_section:doctor_dash')

    # Get summary statistics
    total_attendances = StudentAttendance.objects.filter(doctor=doctor).count()
    present_count = StudentAttendance.objects.filter(doctor=doctor, status='present').count()
    absent_count = StudentAttendance.objects.filter(doctor=doctor, status='absent').count()

    # Get recent attendance by training site
    training_sites_stats = []
    training_sites = TrainingSite.objects.filter(
        mapped_attendances__doctors=doctor,
        mapped_attendances__is_active=True
    ).distinct()

    for site in training_sites:
        site_attendances = StudentAttendance.objects.filter(
            doctor=doctor,
            training_site=site
        )
        site_stats = {
            'training_site': site,
            'total': site_attendances.count(),
            'present': site_attendances.filter(status='present').count(),
            'absent': site_attendances.filter(status='absent').count(),
        }
        training_sites_stats.append(site_stats)

    context = {
        'total_attendances': total_attendances,
        'present_count': present_count,
        'absent_count': absent_count,
        'training_sites_stats': training_sites_stats,
    }

    return render(request, 'doctor_section/attendance_summary.html', context)


@login_required
def debug_doctor_status(request):
    """Debug view to check doctor status and mappings"""
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

        # Check mapped attendances
        mapped_attendances = MappedAttendance.objects.filter(doctors=doctor)
        active_mappings = mapped_attendances.filter(is_active=True)

        debug_info['total_mappings'] = mapped_attendances.count()
        debug_info['active_mappings'] = active_mappings.count()
        debug_info['mapping_details'] = [
            {
                'id': ma.id,
                'name': ma.name,
                'training_site': ma.training_site.name,
                'is_active': ma.is_active,
                'groups_count': ma.groups.count(),
                'groups': [group.group_name for group in ma.groups.all()]
            }
            for ma in mapped_attendances
        ]

        # Check all mapped attendances in system
        all_mappings = MappedAttendance.objects.all()
        debug_info['total_system_mappings'] = all_mappings.count()
        debug_info['all_doctors_in_mappings'] = list(set([
            doctor.user.username for mapping in all_mappings for doctor in mapping.doctors.all()
        ]))

    except Doctor.DoesNotExist:
        debug_info['doctor_profile_exists'] = False
        debug_info['doctor_error'] = 'Doctor profile does not exist'

        # Check if any doctor profiles exist
        all_doctors = Doctor.objects.all()
        debug_info['total_doctors_in_system'] = all_doctors.count()
        debug_info['all_doctor_usernames'] = [d.user.username for d in all_doctors]

    except AttributeError as e:
        debug_info['doctor_profile_exists'] = False
        debug_info['doctor_error'] = f'AttributeError: {str(e)}'

    return JsonResponse(debug_info, indent=2)


@login_required
def export_attendance(request):
    """Export attendance records as CSV, PDF, or Excel based on the current filters"""
    # Check if attendance tracking is enabled
    settings = DateRestrictionSettings.objects.first()
    if settings and not settings.attendance_tracking_enabled:
        messages.error(request, "Student attendance tracking is currently disabled by the administrator.")
        return redirect('doctor_section:doctor_dash')

    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "You must be a doctor to access this page.")
        return redirect('doctor_section:doctor_dash')

    # Debug: Log the request
    print(f"Export request received: format={request.GET.get('format')}, user={request.user.username}")

    export_format = request.GET.get('format', 'csv').lower()

    # Apply the same filtering logic as attendance_history view
    attendances = StudentAttendance.objects.filter(
        doctor=doctor
    ).select_related(
        'student__user', 'training_site', 'group'
    ).order_by('-date', '-marked_at')

    # Date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        try:
            start_date_obj = date.fromisoformat(start_date)
            attendances = attendances.filter(date__gte=start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = date.fromisoformat(end_date)
            attendances = attendances.filter(date__lte=end_date_obj)
        except ValueError:
            pass

    # Single date filter (for backward compatibility)
    single_date = request.GET.get('date')
    if single_date and not start_date and not end_date:
        try:
            filter_date = date.fromisoformat(single_date)
            attendances = attendances.filter(date=filter_date)
        except ValueError:
            pass

    # Training site filter
    training_site_filter = request.GET.get('training_site')
    if training_site_filter:
        attendances = attendances.filter(training_site_id=training_site_filter)

    # Student search filter
    student_search = request.GET.get('student_search', '').strip()
    if student_search:
        attendances = attendances.filter(
            Q(student__user__first_name__icontains=student_search) |
            Q(student__user__last_name__icontains=student_search) |
            Q(student__user__username__icontains=student_search) |
            Q(student__student_id__icontains=student_search)
        )

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        attendances = attendances.filter(status=status_filter)

    # Prepare filename with timestamp
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"attendance_records_{timestamp}"

    try:
        if export_format == 'csv':
            return export_attendance_csv(attendances, filename_base)
        elif export_format == 'pdf':
            return export_attendance_pdf(attendances, filename_base, doctor)
        elif export_format == 'excel':
            return export_attendance_excel(attendances, filename_base)
        else:
            # Default to CSV if format is not recognized
            return export_attendance_csv(attendances, filename_base)
    except Exception as e:
        print(f"Export error: {str(e)}")
        messages.error(request, f"Export failed: {str(e)}")
        return redirect('doctor_section:attendance_history')


def export_attendance_csv(attendances, filename_base):
    """Export attendance records as CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'

    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'Student ID', 'Student Name', 'Training Site', 'Group',
        'Date', 'Status', 'Marked At', 'Notes'
    ])

    # Write data rows
    for attendance in attendances:
        writer.writerow([
            attendance.student.student_id,
            attendance.student.user.get_full_name() or attendance.student.user.username,
            attendance.training_site.name,
            attendance.group.group_name,
            attendance.date.strftime('%Y-%m-%d'),
            attendance.status.title(),
            attendance.marked_at.strftime('%Y-%m-%d %H:%M:%S'),
            attendance.notes or ''
        ])

    return response


def export_attendance_pdf(attendances, filename_base, doctor):
    """Export attendance records as PDF file"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'

    # Create a buffer for the PDF
    buffer = io.BytesIO()

    # Create the PDF document with landscape orientation for better table fit
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    # Add AGU header with logo and university name
    elements = add_agu_header(elements, "Attendance Records Report")

    # Get custom styles
    custom_styles = get_common_styles()

    # Add doctor and export info
    doctor_name = doctor.user.get_full_name() or doctor.user.username
    elements.append(Paragraph(f"Doctor: {doctor_name}", custom_styles['subtitle']))
    elements.append(Paragraph(f"Total Records: {attendances.count()}", custom_styles['normal']))
    elements.append(Spacer(1, 0.3*inch))

    if attendances.exists():
        # Create table data
        table_data = [
            ['Student ID', 'Student Name', 'Training Site', 'Group', 'Date', 'Status', 'Marked At', 'Notes']
        ]

        for attendance in attendances:
            table_data.append([
                attendance.student.student_id,
                attendance.student.user.get_full_name() or attendance.student.user.username,
                attendance.training_site.name,
                attendance.group.group_name,
                attendance.date.strftime('%Y-%m-%d'),
                attendance.status.title(),
                attendance.marked_at.strftime('%Y-%m-%d %H:%M'),
                attendance.notes[:50] + '...' if attendance.notes and len(attendance.notes) > 50 else (attendance.notes or '')
            ])

        # Create table
        table = Table(table_data)

        # Define table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        table.setStyle(table_style)
        elements.append(table)
    else:
        elements.append(Paragraph("No attendance records found for the selected criteria.", custom_styles['normal']))

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


def export_attendance_excel(attendances, filename_base):
    """Export attendance records as Excel file"""
    # Create a new dataset
    data = tablib.Dataset()

    # Add headers
    data.headers = [
        'Student ID', 'Student Name', 'Training Site', 'Group',
        'Date', 'Status', 'Marked At', 'Notes'
    ]

    # Add data rows
    for attendance in attendances:
        data.append([
            attendance.student.student_id,
            attendance.student.user.get_full_name() or attendance.student.user.username,
            attendance.training_site.name,
            attendance.group.group_name,
            attendance.date.strftime('%Y-%m-%d'),
            attendance.status.title(),
            attendance.marked_at.strftime('%Y-%m-%d %H:%M:%S'),
            attendance.notes or ''
        ])

    # Create HTTP response with Excel content type
    response = HttpResponse(
        data.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'

    return response


@login_required
def test_export(request):
    """Test export functionality with sample data"""
    # Create a simple CSV response for testing
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="test_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Test', 'Export', 'Working'])
    writer.writerow(['This', 'is', 'a test'])

    return response
