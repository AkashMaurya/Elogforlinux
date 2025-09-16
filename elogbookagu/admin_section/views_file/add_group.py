from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from admin_section.models import Group, LogYear, LogYearSection
from admin_section.forms import GroupForm


def add_group(request):
    # Handle form submission for adding a group
    if request.method == 'POST':
        # Check if it's a batch delete operation
        if 'delete_ids' in request.POST:
            delete_ids_str = request.POST.get('delete_ids', '')
            if delete_ids_str:
                delete_ids = delete_ids_str.split(',')
                deleted_count = 0
                for group_id in delete_ids:
                    try:
                        group = Group.objects.get(id=group_id)
                        group.delete()
                        deleted_count += 1
                    except Group.DoesNotExist:
                        pass

                if deleted_count > 0:
                    messages.success(request, f'{deleted_count} groups deleted successfully!')
                return redirect('admin_section:add_group')

        # Regular form submission for adding a group
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group added successfully!')
            return redirect('admin_section:add_group')
    else:
        form = GroupForm()

    # Get filter parameters
    year_section_id = request.GET.get('year_section')
    search_query = request.GET.get('q', '').strip()

    # Get all year sections for the filter dropdown
    year_sections = LogYearSection.objects.filter(is_deleted=False).order_by('year_name__year_name', 'year_section_name')

    # Base queryset
    groups = Group.objects.all()

    # Apply filter if selected
    if year_section_id:
        groups = groups.filter(log_year_section_id=year_section_id)

    # Apply search if provided
    if search_query:
        groups = groups.filter(
            Q(group_name__icontains=search_query) |
            Q(log_year__year_name__icontains=search_query) |
            Q(log_year_section__year_section_name__icontains=search_query)
        )

    # Order the groups
    groups = groups.order_by('log_year_section__year_section_name', 'group_name')

    # Pagination
    paginator = Paginator(groups, 10)  # Show 10 groups per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'groups': page_obj,
        'year_sections': year_sections,
        'selected_year_section': year_section_id,
        'search_query': search_query,
    }

    return render(request, "admin_section/add_group.html", context)


def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group updated successfully!')
            return redirect('admin_section:add_group')
    else:
        form = GroupForm(instance=group)

    context = {
        'form': form,
        'group': group,
        'is_edit': True,
    }

    return render(request, "admin_section/add_group.html", context)


def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group.delete()
    messages.success(request, 'Group deleted successfully!')
    return redirect('admin_section:add_group')


def get_year_sections(request, year_id):
    """API endpoint to get year sections for a specific year"""
    year_sections = LogYearSection.objects.filter(year_name_id=year_id, is_deleted=False).values('id', 'year_section_name')
    return JsonResponse(list(year_sections), safe=False)
