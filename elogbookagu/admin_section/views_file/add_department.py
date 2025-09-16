from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from admin_section.models import Department, LogYear, LogYearSection
from admin_section.forms import DepartmentForm
from accounts.models import Student


def add_department(request):
    # Handle form submission for adding a department
    if request.method == 'POST':
        # Check if it's a batch delete operation
        if 'delete_ids' in request.POST:
            delete_ids_str = request.POST.get('delete_ids', '')
            if delete_ids_str:
                delete_ids = delete_ids_str.split(',')
                deleted_count = 0
                for dept_id in delete_ids:
                    try:
                        dept = Department.objects.get(id=dept_id)
                        dept.delete()
                        deleted_count += 1
                    except Department.DoesNotExist:
                        pass

                if deleted_count > 0:
                    messages.success(request, f'{deleted_count} departments deleted successfully!')
                return redirect('admin_section:add_department')

        # Regular form submission for adding a department
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully!')
            return redirect('admin_section:add_department')
    else:
        form = DepartmentForm()

    # Get filter parameters
    year_section_id = request.GET.get('year_section')
    search_query = request.GET.get('q', '').strip()

    # Get all year sections for the filter dropdown
    year_sections = LogYearSection.objects.filter(is_deleted=False).order_by('year_name__year_name', 'year_section_name')

    # Base queryset
    departments = Department.objects.all()

    # Apply filter if selected
    if year_section_id:
        departments = departments.filter(log_year_section_id=year_section_id)

    # Apply search if provided
    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(log_year__year_name__icontains=search_query) |
            Q(log_year_section__year_section_name__icontains=search_query)
        ).distinct()

    # Order the departments
    departments = departments.order_by('log_year_section__year_section_name', 'name')

    # Pagination
    paginator = Paginator(departments, 10)  # Show 10 departments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'departments': page_obj,
        'year_sections': year_sections,
        'selected_year_section': year_section_id,
        'search_query': search_query,
    }

    return render(request, "admin_section/add_department.html", context)


def edit_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully!')
            return redirect('admin_section:add_department')
    else:
        form = DepartmentForm(instance=department)

    context = {
        'form': form,
        'department': department,
        'is_edit': True,
    }

    return render(request, "admin_section/add_department.html", context)


def delete_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        try:
            department.delete()
            messages.success(request, 'Department deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting department: {str(e)}')
        return redirect('admin_section:add_department')

    # If it's an AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Otherwise, redirect to the department list
    return redirect('admin_section:add_department')


def get_year_sections(request, year_id):
    """API endpoint to get year sections for a specific year"""
    year_sections = LogYearSection.objects.filter(year_name_id=year_id, is_deleted=False)
    sections_data = [{'id': section.id, 'name': section.year_section_name} for section in year_sections]

    return JsonResponse({'success': True, 'sections': sections_data})
