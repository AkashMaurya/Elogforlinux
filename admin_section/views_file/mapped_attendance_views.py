from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import MappedAttendance, TrainingSite, Group, LogYear, LogYearSection, Department
from ..forms import MappedAttendanceForm
from accounts.models import Doctor


@login_required
def mapped_attendance_list(request):
    """List all mapped attendance records with search and filtering"""
    search_query = request.GET.get('search', '')
    log_year_filter = request.GET.get('log_year', '')
    training_site_filter = request.GET.get('training_site', '')
    is_active_filter = request.GET.get('is_active', '')

    # Base queryset
    mappings = MappedAttendance.objects.select_related(
        'training_site', 'log_year', 'log_year_section'
    ).prefetch_related('doctors', 'groups')

    # Apply filters
    if search_query:
        mappings = mappings.filter(
            Q(name__icontains=search_query) |
            Q(training_site__name__icontains=search_query)
        )

    if log_year_filter:
        mappings = mappings.filter(log_year_id=log_year_filter)

    if training_site_filter:
        mappings = mappings.filter(training_site_id=training_site_filter)

    if is_active_filter:
        mappings = mappings.filter(is_active=is_active_filter == 'true')

    # Pagination
    paginator = Paginator(mappings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    log_years = LogYear.objects.all().order_by('-year_name')
    training_sites = TrainingSite.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'log_years': log_years,
        'training_sites': training_sites,
        'selected_log_year': log_year_filter,
        'selected_training_site': training_site_filter,
        'selected_is_active': is_active_filter,
    }

    return render(request, 'admin_section/mapped_attendance_list.html', context)


@login_required
def mapped_attendance_create(request):
    """Create a new mapped attendance record"""
    if request.method == 'POST':
        form = MappedAttendanceForm(request.POST)
        if form.is_valid():
            mapping = form.save()
            messages.success(request, f'Mapped attendance "{mapping.name}" created successfully!')
            return redirect('admin_section:mapped_attendance_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MappedAttendanceForm()

    # Get all departments for the filter dropdown
    departments = Department.objects.all().order_by('name')

    context = {
        'form': form,
        'departments': departments,
        'title': 'Create Mapped Attendance',
        'submit_text': 'Create Mapping'
    }

    return render(request, 'admin_section/mapped_attendance_form.html', context)


@login_required
def mapped_attendance_edit(request, pk):
    """Edit an existing mapped attendance record"""
    mapping = get_object_or_404(MappedAttendance, pk=pk)

    if request.method == 'POST':
        form = MappedAttendanceForm(request.POST, instance=mapping)
        if form.is_valid():
            mapping = form.save()
            messages.success(request, f'Mapped attendance "{mapping.name}" updated successfully!')
            return redirect('admin_section:mapped_attendance_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MappedAttendanceForm(instance=mapping)

    # Get all departments for the filter dropdown
    departments = Department.objects.all().order_by('name')

    context = {
        'form': form,
        'mapping': mapping,
        'departments': departments,
        'title': f'Edit Mapped Attendance: {mapping.name}',
        'submit_text': 'Update Mapping'
    }

    return render(request, 'admin_section/mapped_attendance_form.html', context)


@login_required
def mapped_attendance_delete(request, pk):
    """Delete a mapped attendance record"""
    mapping = get_object_or_404(MappedAttendance, pk=pk)

    if request.method == 'POST':
        mapping_name = mapping.name
        mapping.delete()
        messages.success(request, f'Mapped attendance "{mapping_name}" deleted successfully!')
        return redirect('admin_section:mapped_attendance_list')

    context = {
        'mapping': mapping,
        'title': f'Delete Mapped Attendance: {mapping.name}'
    }

    return render(request, 'admin_section/mapped_attendance_delete.html', context)


@login_required
def mapped_attendance_detail(request, pk):
    """View details of a mapped attendance record"""
    mapping = get_object_or_404(
        MappedAttendance.objects.select_related(
            'training_site', 'log_year', 'log_year_section'
        ).prefetch_related('doctors__user', 'groups'),
        pk=pk
    )

    # Get students in mapped groups
    students = []
    for group in mapping.groups.all():
        group_students = group.students.select_related('user').all()
        students.extend(group_students)

    context = {
        'mapping': mapping,
        'students': students,
        'title': f'Mapped Attendance Details: {mapping.name}'
    }

    return render(request, 'admin_section/mapped_attendance_detail.html', context)


@login_required
def get_groups_by_year(request):
    """AJAX endpoint to get groups filtered by log year"""
    log_year_id = request.GET.get('log_year_id')
    groups = []

    if log_year_id:
        groups_queryset = Group.objects.filter(log_year_id=log_year_id).order_by('group_name')
        groups = [{'id': group.id, 'name': group.group_name} for group in groups_queryset]

    return JsonResponse({'groups': groups})


@login_required
def get_training_sites_by_year(request):
    """AJAX endpoint to get training sites filtered by log year"""
    log_year_id = request.GET.get('log_year_id')
    training_sites = []

    if log_year_id:
        sites_queryset = TrainingSite.objects.filter(log_year_id=log_year_id).order_by('name')
        training_sites = [{'id': site.id, 'name': site.name} for site in sites_queryset]

    return JsonResponse({'training_sites': training_sites})


@login_required
def get_doctors_by_department(request):
    """AJAX endpoint to get doctors filtered by department"""
    department_id = request.GET.get('department_id')
    doctors = []

    if department_id:
        # Get doctors mapped to the selected department
        doctors_queryset = Doctor.objects.filter(
            departments__id=department_id
        ).select_related('user').order_by('user__first_name', 'user__last_name')

        doctors = [
            {
                'id': doctor.id,
                'name': doctor.user.get_full_name() or doctor.user.username,
                'username': doctor.user.username,
                'email': doctor.user.email
            }
            for doctor in doctors_queryset
        ]
    else:
        # If no department selected, return all doctors
        doctors_queryset = Doctor.objects.select_related('user').order_by('user__first_name', 'user__last_name')
        doctors = [
            {
                'id': doctor.id,
                'name': doctor.user.get_full_name() or doctor.user.username,
                'username': doctor.user.username,
                'email': doctor.user.email
            }
            for doctor in doctors_queryset
        ]

    return JsonResponse({'doctors': doctors})
