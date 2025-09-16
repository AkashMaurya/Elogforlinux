from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from admin_section.models import LogYearSection, LogYear
from admin_section.forms import LogYearSectionForm


def add_elogyear(request):
    # Handle form submission
    if request.method == 'POST':
        form = LogYearSectionForm(request.POST)
        if form.is_valid():
            year_section = form.save()
            messages.success(request, 'Year Section added successfully!')

            # Add a message about departments if Year 5 or Year 6 was created
            if year_section.year_section_name in ['Year 5', 'Year 6']:
                messages.info(request, f'Departments for {year_section.year_section_name} have been automatically created.')

            return redirect('admin_section:add_elogyear')
    else:
        form = LogYearSectionForm()

    # Get all year sections for the table
    year_sections = LogYearSection.objects.filter(is_deleted=False).order_by('year_name__year_name', 'year_section_name')

    # Pagination
    paginator = Paginator(year_sections, 10)  # Show 10 year sections per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'year_sections': page_obj,
    }

    return render(request, "admin_section/add_elogyear.html", context)


def edit_elogyear(request, section_id):
    year_section = get_object_or_404(LogYearSection, id=section_id)

    if request.method == 'POST':
        form = LogYearSectionForm(request.POST, instance=year_section)
        if form.is_valid():
            form.save()
            messages.success(request, 'Year Section updated successfully!')
            return redirect('admin_section:add_elogyear')
    else:
        form = LogYearSectionForm(instance=year_section)

    context = {
        'form': form,
        'year_section': year_section,
        'is_edit': True,
    }

    return render(request, "admin_section/add_elogyear.html", context)


def delete_elogyear(request, section_id):
    year_section = get_object_or_404(LogYearSection, id=section_id)

    if request.method == 'POST':
        try:
            # Soft delete - set is_deleted to True instead of actually deleting
            year_section.is_deleted = True
            year_section.save()
            messages.success(request, 'Year Section deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting year section: {str(e)}')
        return redirect('admin_section:add_elogyear')

    # If it's an AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Otherwise, redirect to the year section list
    return redirect('admin_section:add_elogyear')
