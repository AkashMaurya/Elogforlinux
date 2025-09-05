from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .adding_forms import CoreDiaProSessionForm
from admin_section.models import CoreDiaProSession, Department
from ..models import ActivityType
import logging
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
import io
import csv
import tablib

logger = logging.getLogger(__name__)


@login_required
def core_dia_pro_session_list(request):
    """List CoreDiaProSession objects, support CSV/XLSX template download and bulk upload.

    Expected upload columns (case-insensitive): name, department, activity_type
    department is matched by Department.name (case-insensitive)
    activity_type is matched by ActivityType.name within the department (case-insensitive)
    """
    # Template download
    if request.method == 'GET' and request.GET.get('download') == 'session_template':
        fmt = request.GET.get('format', 'csv').lower()
        headers = ['name', 'department', 'activity_type']
        sample = [['Example Session', 'Example Department', 'Example Activity Type']]
        if fmt == 'xlsx':
            dataset = tablib.Dataset(*sample, headers=headers)
            data = dataset.export('xlsx')
            resp = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename="core_sessions_template.xlsx"'
            return resp
        # default CSV
        csv_content = 'name,department,activity_type\nExample Session,Example Department,Example Activity Type\n'
        resp = HttpResponse(csv_content, content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="core_sessions_template.csv"'
        return resp

    # Bulk upload
    if request.method == 'POST' and request.FILES.get('bulk_file'):
        bulk_file = request.FILES['bulk_file']
        filename = bulk_file.name.lower()
        try:
            content = bulk_file.read()
            rows = []
            if filename.endswith('.csv'):
                text = content.decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(text))
                rows = list(reader)
            elif filename.endswith(('.xls', '.xlsx')):
                dataset = tablib.Dataset().load(content, format='xlsx')
                rows = list(dataset.dict)
            else:
                messages.error(request, 'Unsupported file type. Upload a .csv, .xls, or .xlsx file.')
                return redirect('admin_section:core_dia_pro_session_list')

            if not rows:
                messages.error(request, 'Uploaded file contains no rows.')
                return redirect('admin_section:core_dia_pro_session_list')

            # Normalize headers from first row
            first_row = rows[0]
            headers = [str(h).strip().lower() for h in first_row.keys()]
            required = ['name', 'department', 'activity_type']
            missing = [c for c in required if c not in headers]
            if missing:
                messages.error(request, f'Missing required columns: {", ".join(missing)}. Expected columns: name, department, activity_type')
                return redirect('admin_section:core_dia_pro_session_list')

            create_objs = []
            errors = []
            for idx, raw_row in enumerate(rows, start=1):
                # Normalize each row: keys lowercased
                row = {str(k).strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items()}
                name = row.get('name')
                dept_name = row.get('department')
                activity_name = row.get('activity_type')

                if not name:
                    errors.append(f'Row {idx}: missing session name')
                    continue
                if not dept_name:
                    errors.append(f'Row {idx}: missing department')
                    continue
                if not activity_name:
                    errors.append(f'Row {idx}: missing activity_type')
                    continue

                dept = Department.objects.filter(name__iexact=str(dept_name).strip()).first()
                if not dept:
                    errors.append(f'Row {idx}: department "{dept_name}" not found')
                    continue

                activity = ActivityType.objects.filter(name__iexact=str(activity_name).strip(), department=dept).first()
                if not activity:
                    errors.append(f'Row {idx}: activity_type "{activity_name}" not found for department "{dept.name}"')
                    continue

                # Skip if duplicate exists
                if CoreDiaProSession.objects.filter(name__iexact=str(name).strip(), department=dept, activity_type=activity).exists():
                    errors.append(f'Row {idx}: session "{name}" already exists for department "{dept.name}" and activity "{activity.name}"')
                    continue

                create_objs.append(CoreDiaProSession(name=str(name).strip(), department=dept, activity_type=activity))

            if create_objs:
                CoreDiaProSession.objects.bulk_create(create_objs)
                messages.success(request, f'Created {len(create_objs)} session(s)')

            if errors:
                for err in errors[:30]:
                    messages.error(request, err)
                if len(errors) > 30:
                    messages.error(request, f'...and {len(errors)-30} more errors')

        except Exception as exc:
            messages.error(request, f'Error processing upload: {str(exc)}')

        return redirect('admin_section:core_dia_pro_session_list')

    # Normal listing with search and pagination
    sessions = CoreDiaProSession.objects.all().order_by('name')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        sessions = sessions.filter(
            Q(name__icontains=search_query) |
            Q(activity_type__name__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )

    paginator = Paginator(sessions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'core_sessions': page_obj,
        'form': CoreDiaProSessionForm(),
        'editing': False,
        'search_query': search_query,
    }
    return render(request, 'admin_section/core_dia_pro_session_list.html', context)


@login_required
def core_dia_pro_session_create(request):
    """Handle creation of a single CoreDiaProSession via the form on the list page."""
    try:
        if request.method != 'POST':
            return redirect('admin_section:core_dia_pro_session_list')

        form = CoreDiaProSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'Session "{session.name}" created successfully!')
            return redirect('admin_section:core_dia_pro_session_list')
        else:
            # If invalid, re-render the list view with the form errors visible
            sessions = CoreDiaProSession.objects.all().order_by('name')
            paginator = Paginator(sessions, 10)
            page_obj = paginator.get_page(request.GET.get('page'))
            context = {
                'core_sessions': page_obj,
                'form': form,
                'editing': False,
                'search_query': request.GET.get('q', '').strip(),
            }
            return render(request, 'admin_section/core_dia_pro_session_list.html', context)
    except Exception as exc:
        logger.error(f'Error creating session: {exc}')
        messages.error(request, 'An error occurred while creating the session.')
        return redirect('admin_section:core_dia_pro_session_list')


@login_required
def core_dia_pro_session_update(request, pk):
    try:
        session = get_object_or_404(CoreDiaProSession, pk=pk)
        if request.method == 'POST':
            form = CoreDiaProSessionForm(request.POST, instance=session)
            if form.is_valid():
                updated = form.save()
                messages.success(request, f'Session "{updated.name}" updated successfully!')
                return redirect('admin_section:core_dia_pro_session_list')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = CoreDiaProSessionForm(instance=session)

        sessions = CoreDiaProSession.objects.all().order_by('name')
        search_query = request.GET.get('q', '').strip()
        if search_query:
            sessions = sessions.filter(
                Q(name__icontains=search_query) |
                Q(activity_type__name__icontains=search_query) |
                Q(department__name__icontains=search_query)
            )
        paginator = Paginator(sessions, 10)
        page_obj = paginator.get_page(request.GET.get('page'))

        context = {
            'core_sessions': page_obj,
            'form': form,
            'editing': True,
            'editing_session': session,
            'search_query': search_query,
        }
        return render(request, 'admin_section/core_dia_pro_session_list.html', context)
    except Exception as exc:
        logger.error(f'Error updating session with pk {pk}: {exc}')
        messages.error(request, 'An error occurred while updating the session.')
        return redirect('admin_section:core_dia_pro_session_list')


@login_required
def core_dia_pro_session_delete(request, pk):
    try:
        session = get_object_or_404(CoreDiaProSession, pk=pk)
        name = session.name
        session.delete()
        messages.success(request, f'Session "{name}" deleted successfully!')
        logger.info(f"Session {name} deleted by user {request.user.username}")
    except CoreDiaProSession.DoesNotExist:
        messages.error(request, 'Session not found.')
    except Exception as exc:
        logger.error(f'Error deleting session with pk {pk}: {exc}')
        messages.error(request, 'An error occurred while deleting the session.')
    return redirect('admin_section:core_dia_pro_session_list')


@login_required
def get_activity_types_by_department(request, department_id):
    try:
        activity_types = ActivityType.objects.filter(department_id=department_id)
        data = list(activity_types.values('id', 'name'))
        return JsonResponse(data, safe=False)
    except Exception as exc:
        logger.error(f'Error fetching activity types for department {department_id}: {exc}')
        return JsonResponse({'error': str(exc)}, status=400)

@login_required
def core_dia_pro_session_update(request, pk):
    try:
        session = get_object_or_404(CoreDiaProSession, pk=pk)
        
        if request.method == "POST":
            form = CoreDiaProSessionForm(request.POST, instance=session)
            if form.is_valid():
                updated_session = form.save()
                messages.success(request, f'Session "{updated_session.name}" updated successfully!')
                return redirect("admin_section:core_dia_pro_session_list")
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = CoreDiaProSessionForm(instance=session)

        # Get all sessions for the list
        sessions = CoreDiaProSession.objects.all().order_by("name")
        search_query = request.GET.get('q', '').strip()
        if search_query:
            sessions = sessions.filter(
                Q(name__icontains=search_query) |
                Q(activity_type__name__icontains=search_query) |
                Q(department__name__icontains=search_query)
            )
        
        paginator = Paginator(sessions, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "core_sessions": page_obj,
            "form": form,
            "editing": True,
            "editing_session": session,
            "search_query": search_query,
        }
        return render(request, "admin_section/core_dia_pro_session_list.html", context)
    except Exception as e:
        logger.error(f"Error updating session with pk {pk}: {e}")
        messages.error(request, "An error occurred while updating the session.")
        return redirect("admin_section:core_dia_pro_session_list")



@login_required
def core_dia_pro_session_delete(request, pk):
    try:
        session = get_object_or_404(CoreDiaProSession, pk=pk)
        session_name = session.name
        session.delete()
        messages.success(request, f'Session "{session_name}" deleted successfully!')
        logger.info(f"Session {session_name} deleted by user {request.user.username}")
    except CoreDiaProSession.DoesNotExist:
        messages.error(request, "Session not found.")
        logger.warning(f"Attempted to delete non-existent session with pk {pk}")
    except Exception as e:
        logger.error(f"Error deleting session with pk {pk}: {e}")
        messages.error(request, "An error occurred while deleting the session.")
    return redirect("admin_section:core_dia_pro_session_list")

@login_required
def get_activity_types_by_department(request, department_id):
    try:
        # Get all activity types for the given department
        activity_types = ActivityType.objects.filter(department_id=department_id)
        
        # Convert to list of dictionaries
        data = list(activity_types.values('id', 'name'))
        
        logger.debug(f"Fetched {len(data)} activity types for department {department_id}")
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error fetching activity types for department {department_id}: {e}")
        return JsonResponse(
            {'error': str(e)}, 
            status=400
        )
