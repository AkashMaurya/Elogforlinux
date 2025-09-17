from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from ..models import TrainingSite
from ..forms import TrainingSiteForm


def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


@login_required
@user_passes_test(is_admin)
def add_training_site(request):
    """
    View for adding a new training site and listing all existing training sites
    """
    # Handle form submission
    if request.method == 'POST':
        form = TrainingSiteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Training site added successfully!')
            return redirect('admin_section:add_training_site')
    else:
        form = TrainingSiteForm()

    # Get all training sites for the table
    training_sites = TrainingSite.objects.all().order_by('name')

    # Pagination
    paginator = Paginator(training_sites, 10)  # Show 10 training sites per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'training_sites': page_obj,
    }

    return render(request, "admin_section/add_training_site.html", context)


@login_required
@user_passes_test(is_admin)
def edit_training_site(request, training_site_id):
    """
    View for editing an existing training site
    """
    training_site = get_object_or_404(TrainingSite, id=training_site_id)
    
    if request.method == 'POST':
        form = TrainingSiteForm(request.POST, instance=training_site)
        if form.is_valid():
            form.save()
            messages.success(request, 'Training site updated successfully!')
            return redirect('admin_section:add_training_site')
    else:
        form = TrainingSiteForm(instance=training_site)
    
    context = {
        'form': form,
        'training_site': training_site,
    }
    
    return render(request, "admin_section/edit_training_site.html", context)


@login_required
@user_passes_test(is_admin)
def delete_training_site(request, training_site_id):
    """
    View for deleting a training site
    """
    training_site = get_object_or_404(TrainingSite, id=training_site_id)
    
    # Check if this training site is being used by any student logs
    if hasattr(training_site, 'studentlogformmodel_set') and training_site.studentlogformmodel_set.exists():
        messages.error(request, f"Cannot delete '{training_site.name}' because it is being used in student logs.")
        return redirect('admin_section:add_training_site')
    
    # If not being used, delete it
    training_site_name = training_site.name
    training_site.delete()
    messages.success(request, f"Training site '{training_site_name}' deleted successfully!")
    
    return redirect('admin_section:add_training_site')
