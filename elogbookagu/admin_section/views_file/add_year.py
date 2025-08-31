from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from admin_section.models import LogYear
from admin_section.forms import LogYearForm


def add_year(request):
    # Handle form submission
    if request.method == 'POST':
        form = LogYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Year added successfully!')
            return redirect('admin_section:add_year')
    else:
        form = LogYearForm()

    # Get all years for the table
    years = LogYear.objects.all().order_by('-year_name')

    # Pagination
    paginator = Paginator(years, 10)  # Show 10 years per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'years': page_obj,
    }

    return render(request, "admin_section/add_year.html", context)


def edit_year(request, year_id):
    year = get_object_or_404(LogYear, id=year_id)

    if request.method == 'POST':
        form = LogYearForm(request.POST, instance=year)
        if form.is_valid():
            form.save()
            messages.success(request, 'Year updated successfully!')
            return redirect('admin_section:add_year')
    else:
        form = LogYearForm(instance=year)

    context = {
        'form': form,
        'year': year,
        'is_edit': True,
    }

    return render(request, "admin_section/add_year.html", context)


def delete_year(request, year_id):
    year = get_object_or_404(LogYear, id=year_id)

    if request.method == 'POST':
        try:
            year.delete()
            messages.success(request, 'Year deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting year: {str(e)}')
        return redirect('admin_section:add_year')

    # If it's an AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    # Otherwise, redirect to the year list
    return redirect('admin_section:add_year')
