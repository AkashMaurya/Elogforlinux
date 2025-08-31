from django.shortcuts import render, redirect
from .adding_forms import ActivityTypeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from admin_section.models import ActivityType  # Assuming you have this model
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect

@login_required
def add_activity_type(request):
    # Handle form submission
    if request.method == 'POST':
        form = ActivityTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Activity type added successfully.")
            return redirect('admin_section:add_activity_type')
        else:
            messages.error(request, "An error occurred. Please try again.")
    else:
        form = ActivityTypeForm()

    # Handle table display with search and pagination
    search_query = request.GET.get('q', '').strip()  # Get search query, default to empty string
    activity_types = ActivityType.objects.all().order_by('name')  # Base queryset

    if search_query:
        # Filter by name or department (case-insensitive)
        activity_types = activity_types.filter(
            name__icontains=search_query
        ) | activity_types.filter(
            department__icontains=search_query
        )

    paginator = Paginator(activity_types, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'activity_types': page_obj,
        'search_query': search_query,  # Pass search query to template for persistence
    }
    return render(request, 'admin_section/add_activity_type.html', context)

@login_required
def edit_activity_type(request, activity_type_id):
    activity_type = ActivityType.objects.get(id=activity_type_id)
    if request.method == 'POST':
        form = ActivityTypeForm(request.POST, instance=activity_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Activity type updated successfully.")
            return redirect('admin_section:add_activity_type')
        else:
            messages.error(request, "Error updating activity type.")
    else:
        form = ActivityTypeForm(instance=activity_type)
    
    # Still show the table with pagination
    activity_types = ActivityType.objects.all().order_by('name')
    paginator = Paginator(activity_types, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'activity_types': page_obj,
        'editing': True,  # To indicate we're in edit mode
        'activity_type_id': activity_type_id,
    }
    return render(request, 'admin_section/add_activity_type.html', context)

@login_required
def delete_activity_type(request, activity_type_id):
    if request.method == 'POST':  # Optional: Add confirmation via POST
        try:
            activity_type = ActivityType.objects.get(id=activity_type_id)
            activity_type.delete()
            messages.success(request, "Activity type deleted successfully.")
        except ActivityType.DoesNotExist:
            messages.error(request, "Activity type not found.")
        except Exception as e:
            messages.error(request, f"Error deleting activity type: {str(e)}")
    return redirect('admin_section:add_activity_type')