from django.shortcuts import render, redirect
from .adding_forms import ActivityTypeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from admin_section.models import ActivityType, Department  # Assuming you have these models
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, HttpResponse
import io
import csv
import tablib

@login_required
def add_activity_type(request):
    # Allow downloading a CSV template for bulk uploads
    if request.method == 'GET' and request.GET.get('download') == 'activity_template':
        fmt = request.GET.get('format', 'csv').lower()
        headers = ['name', 'department']
        sample = [['Example Activity', 'Example Department']]
        if fmt == 'xlsx':
            dataset = tablib.Dataset(*sample, headers=headers)
            data = dataset.export('xlsx')
            response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="activity_type_template.xlsx"'
            return response
        else:
            # default CSV
            csv_content = 'name,department\nExample Activity,Example Department\n'
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="activity_type_template.csv"'
            return response

    # Handle bulk upload file if present
    if request.method == 'POST' and request.FILES.get('bulk_file'):
        bulk_file = request.FILES.get('bulk_file')
        filename = bulk_file.name.lower()
        try:
            content = bulk_file.read()
            # Parse CSV
            rows = []
            if filename.endswith('.csv'):
                text = content.decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(text))
                rows = list(reader)
            elif filename.endswith(('.xls', '.xlsx')):
                dataset = tablib.Dataset().load(content, format='xlsx')
                # tablib Dataset.dict returns list of OrderedDicts
                rows = list(dataset.dict)
            else:
                messages.error(request, 'Unsupported file type. Upload a .csv, .xls, or .xlsx file.')
                return redirect('admin_section:add_activity_type')

            # Normalize headers and validate required columns
            if not rows:
                messages.error(request, 'Uploaded file contains no rows.')
                return redirect('admin_section:add_activity_type')

            # Normalize first row keys to check columns
            first_row = rows[0]
            headers = [str(h).strip().lower() for h in first_row.keys()]
            required = ['name', 'department']
            missing = [c for c in required if c not in headers]
            if missing:
                messages.error(request, f'Missing required columns: {", ".join(missing)}. Expected columns: name, department')
                return redirect('admin_section:add_activity_type')

            successes = []
            errors = []
            create_objs = []
            for idx, raw_row in enumerate(rows, start=1):
                # Normalize row keys to lowercase
                row = {str(k).strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items()}
                name = row.get('name')
                dept_name = row.get('department')

                if not name:
                    errors.append(f'Row {idx}: missing activity name')
                    continue
                if not dept_name:
                    errors.append(f'Row {idx}: missing department')
                    continue

                dept = Department.objects.filter(name__iexact=str(dept_name).strip()).first()
                if not dept:
                    errors.append(f'Row {idx}: department "{dept_name}" not found')
                    continue

                # Skip duplicates
                if ActivityType.objects.filter(name__iexact=str(name).strip(), department=dept).exists():
                    errors.append(f'Row {idx}: activity "{name}" already exists for department "{dept.name}"')
                    continue

                create_objs.append(ActivityType(name=str(name).strip(), department=dept))

            if create_objs:
                ActivityType.objects.bulk_create(create_objs)
                successes.append(f'Created {len(create_objs)} activity type(s)')

            if successes:
                messages.success(request, '; '.join(successes))
            if errors:
                # Limit large error lists for UX
                for err in errors[:20]:
                    messages.error(request, err)
                if len(errors) > 20:
                    messages.error(request, f'...and {len(errors)-20} more errors')

        except Exception as e:
            messages.error(request, f'Error processing upload: {str(e)}')
        return redirect('admin_section:add_activity_type')
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