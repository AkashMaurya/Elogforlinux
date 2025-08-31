from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .adding_forms import CoreDiaProSessionForm
from admin_section.models import CoreDiaProSession
from ..models import ActivityType
import logging
from django.http import JsonResponse
from django.db.models import Q

logger = logging.getLogger(__name__)

@login_required
def core_dia_pro_session_list(request):
    try:
        logger.debug("Fetching sessions...")
        sessions = CoreDiaProSession.objects.all().order_by("name")
        logger.debug(f"Found {sessions.count()} sessions")
        
        # Get search query if any
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
            "form": CoreDiaProSessionForm(),
            "editing": False,
            "search_query": search_query,
        }
        logger.debug("Rendering template with context: %s", context)
        return render(request, "admin_section/core_dia_pro_session_list.html", context)
    except Exception as e:
        logger.error(f"Error in core_dia_pro_session_list: {e}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("admin_section:admin_dash")

@login_required
def core_dia_pro_session_create(request):
    form = None
    try:
        if request.method == "POST":
            form = CoreDiaProSessionForm(request.POST)
            if form.is_valid():
                session = form.save(commit=False)
                session.save()
                messages.success(request, f'Session "{session.name}" created successfully!')
                return redirect("admin_section:core_dia_pro_session_list")
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = CoreDiaProSessionForm()
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        messages.error(request, "An error occurred while creating the session.")

    sessions = CoreDiaProSession.objects.all().order_by("name")
    # Preserve search query in pagination
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
        "form": form or CoreDiaProSessionForm(),
        "editing": False,
        "search_query": search_query,
    }
    return render(request, "admin_section/core_dia_pro_session_list.html", context)

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
