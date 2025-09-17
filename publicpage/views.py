from django.shortcuts import render, get_object_or_404, redirect
from admin_section.models import Department, TrainingSite
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import time
import datetime
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Student, Staff, Doctor
import os  # Moved os import here
from django.http import FileResponse
from django.conf import settings
from django.db import models
from django.core.paginator import Paginator
from django.db.models import Sum
from student_section.models import StudentLogFormModel


def get_site_statistics():
    """
    Helper function to calculate and format site statistics
    Returns a dictionary with formatted statistics
    """
    # Count users by role (only active users)
    doctor_count = CustomUser.objects.filter(role='doctor', is_active=True).count()
    staff_count = CustomUser.objects.filter(role='staff', is_active=True).count()
    student_count = CustomUser.objects.filter(role='student', is_active=True).count()
    admin_count = CustomUser.objects.filter(role='admin', is_active=True).count()

    # Total active users
    total_users = doctor_count + staff_count + student_count + admin_count

    # Count institutions/departments (more comprehensive)
    total_training_sites = TrainingSite.objects.count()
    total_departments = Department.objects.count()
    total_institutions = total_training_sites + total_departments

    # Calculate real resources accessed
    log_entries = StudentLogFormModel.objects.count()

    # Add attendance records from doctor section
    try:
        from doctor_section.models import DoctorAttendance
        attendance_records = DoctorAttendance.objects.count()
    except ImportError:
        attendance_records = 0

    # Add emergency attendance records from staff section
    try:
        from staff_section.models import StaffEmergencyAttendance
        emergency_attendance_records = StaffEmergencyAttendance.objects.count()
    except ImportError:
        emergency_attendance_records = 0

    # Add blog posts and other content
    try:
        from admin_section.models import Blog
        blog_posts = Blog.objects.filter(is_published=True).count()
    except ImportError:
        blog_posts = 0

    # Add page visits tracking
    try:
        from .models import PageVisit
        total_page_visits = PageVisit.objects.count()
        unique_visitors = PageVisit.objects.filter(is_unique=True).count()
    except ImportError:
        total_page_visits = 0
        unique_visitors = 0

    # Calculate total logs (focus on actual log entries)
    total_logs = log_entries  # Use actual student log entries

    # Ensure minimum display values for better presentation
    display_users = max(total_users, 8)  # Minimum 8 for demo
    display_institutions = max(total_institutions, 1)  # Minimum 1 for demo
    display_logs = max(total_logs, 30)  # Minimum 30 for demo to look professional

    # Format numbers with commas for thousands
    formatted_users = f"{display_users:,}+"
    formatted_institutions = f"{display_institutions:,}+"
    formatted_logs = f"{display_logs:,}+"

    return {
        'active_users': formatted_users,
        'institutions': formatted_institutions,
        'total_logs': formatted_logs,  # Changed from resources_accessed to total_logs
        'support_available': '24/7',  # This is a static value
        'doctor_count': f"{doctor_count:,}",
        'staff_count': f"{staff_count:,}",
        'student_count': f"{student_count:,}",
        'admin_count': f"{admin_count:,}",
        'total_users': f"{total_users:,}",
        # Additional detailed stats
        'log_entries': f"{log_entries:,}",  # Raw log entries count
        'total_attendance': f"{attendance_records + emergency_attendance_records:,}",
        'total_blogs': f"{blog_posts:,}",
        'training_sites': f"{total_training_sites:,}",
        'departments': f"{total_departments:,}",
        'page_visits': f"{total_page_visits:,}",
        'unique_visitors': f"{unique_visitors:,}",
        # Raw numbers for calculations
        'raw_users': total_users,
        'raw_institutions': total_institutions,
        'raw_logs': total_logs,
    }

# Create your views here.


def home(request):
    # Track page visit
    try:
        from .models import PageVisit
        PageVisit.record_visit('home', request)
    except Exception:
        pass  # Silently fail if tracking doesn't work

    # Get statistics from helper function
    context = get_site_statistics()
    return render(request, "home.html", context)


# def about(request):
#     # Track page visit
#     try:
#         from .models import PageVisit
#         PageVisit.record_visit('about', request)
#     except Exception:
#         pass  # Silently fail if tracking doesn't work

#     # Get statistics from helper function
#     context = get_site_statistics()
#     return render(request, "about.html", context)


# def resources(request):
#     return render(request, "resources.html")


def update(request):
    # Get filter parameters
    category = request.GET.get('category', '')
    search_query = request.GET.get('q', '').strip()

    # Import the Blog model from admin_section
    from admin_section.models import Blog

    # Base queryset - only published blogs
    blogs = Blog.objects.filter(is_published=True)

    # Apply filters
    if category:
        blogs = blogs.filter(category=category)

    if search_query:
        blogs = blogs.filter(
            models.Q(title__icontains=search_query) |
            models.Q(summary__icontains=search_query) |
            models.Q(content__icontains=search_query)
        )

    # Order by most recent first
    blogs = blogs.order_by('-created_at')

    # Pagination
    paginator = Paginator(blogs, 9)  # 9 items per page for grid layout
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'blogs': page_obj,
        'selected_category': category,
        'search_query': search_query,
        'categories': Blog.CATEGORY_CHOICES,
    }

    return render(request, "update.html", context)


def blog_detail(request, blog_id):
    """View for displaying a single blog post to the public"""
    # Import the Blog model from admin_section
    from admin_section.models import Blog

    # Get the blog post - only published blogs are visible to the public
    blog = get_object_or_404(Blog, id=blog_id, is_published=True)

    # Get related blogs (same category, excluding current blog)
    related_blogs = Blog.objects.filter(
        category=blog.category,
        is_published=True
    ).exclude(id=blog.id).order_by('-created_at')[:3]

    context = {
        'blog': blog,
        'related_blogs': related_blogs,
        'categories': Blog.CATEGORY_CHOICES,
    }

    return render(request, "blog_detail.html", context)


def ebookjournals(request, pdf_name=None):
    if pdf_name:  # If a specific PDF is requested
        pdf_path = os.path.join(settings.MEDIA_ROOT, f"{pdf_name}.pdf")
        try:
            pdf_file = open(pdf_path, "rb")
            response = FileResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{pdf_name}.pdf"'
            return response
        except FileNotFoundError:
            # Optionally handle the error differently
            pass

    # If no PDF requested or file not found, return the template
    return render(request, "ebookjournals.html")


def login(request):
    # Agar user pehle se login hai to redirect karen
    # if request.user.is_authenticated:
    #     return redirect("dashboard")

    # Agar request method POST hai, to form se data handle karen
    if request.method == "POST":
        email = (
            request.POST.get("email").strip().lower()
        )  # Email ko strip aur lower case mein convert karen
        password = request.POST.get("password")  # Password le rahe hain

        # Agar email ya password nahi hai, to error message dikhayein
        if not email or not password:
            messages.error(request, "Email and  Password are both required!")  # Error message
            return redirect("login")  # Login page par redirect karein

        # Authenticate karen: user ko email aur password se check karen
        user = authenticate(request, username=email, password=password)

        # Agar user valid nahi hai, to error message dikhayein aur brute-force attack se bachne ke liye thodi der wait karen
        if user is None:
            messages.error(request, "Invalid email or password.")
            time.sleep(2)  # Brute-force attack se bachne ke liye
            return redirect("login")

        # Agar user authenticate ho gaya hai, to user ko login karayein
        auth_login(request, user)
        messages.success(
            request, f"Welcome {user.email}!"
        )  # Login hone par success message dikhayein

        # Seesion mein user ki details save karen
        request.session["username"] = (
            user.username.upper()
        )  # Username ko uppercase mein store karen
        request.session["first_name"] = user.first_name  # First name store karen
        request.session["last_name"] = user.last_name  # Last name store karen
        request.session["profile_photo"] = (
            user.profile_photo.url
            if user.profile_photo and user.profile_photo.url
            else "/media/profiles/default.jpg"
        )  # Profile photo ko store karen, agar photo nahi hai to default image ka path set karen
        request.session["role"] = user.role  # Role ko session mein save karen
        request.session["city"] = user.city  # City ko session mein save karen
        request.session["country"] = user.country  # Country ko session mein save karen
        request.session["phone_no"] = (
            user.phone_no
        )  # Phone number ko session mein save karen
        request.session["bio"] = user.bio  # Bio ko session mein save karen
        request.session["speciality"] = (
            user.speciality
        )  # Speciality ko session mein save karen
        request.session["email"] = user.email  # Email ko session mein save karen

        # Add student group data if user is a student
        if user.role == "student":
            try:
                student = Student.objects.get(user=user)
                if student.group:
                    request.session["group_name"] = student.group.group_name
                    request.session["log_year"] = (
                        student.group.log_year.year_name
                        if student.group.log_year
                        else None
                    )
                    request.session["log_year_section"] = (
                        student.group.log_year_section.year_section_name
                        if student.group.log_year_section
                        else None
                    )
                    # Add debug prints
                    print("Group Name:", student.group.group_name)
                    print(
                        "Log Year:",
                        (
                            student.group.log_year.year_name
                            if student.group.log_year
                            else None
                        ),
                    )
                    print(
                        "Section:",
                        (
                            student.group.log_year_section.year_section_name
                            if student.group.log_year_section
                            else None
                        ),
                    )
            except Student.DoesNotExist:
                print(f"No student profile found for user: {user.email}")
                request.session["group_name"] = None
                request.session["log_year"] = None
                request.session["log_year_section"] = None

        # Staff data handling
        if user.role == "staff":
            try:
                staff = Staff.objects.select_related('user').get(user=user)
                departments = staff.get_departments()
                request.session["departments"] = departments
            except Staff.DoesNotExist:
                print(f"No staff profile found for user: {user.email}")
                request.session["departments"] = []
                messages.warning(request, "Staff profile not found. Please contact administrator.")
            except Exception as e:
                print(f"Error fetching staff departments: {str(e)}")
                request.session["departments"] = []

        request.session.save()  # Session ko explicitly save karen

        # User ke role ke hisaab se redirection
        role_redirects = {
            "defaultuser": "defaultuser:default_home",
            "admin": "admin_section:admin_dash",  # Admin role ke liye dashboard redirect
            "doctor": "doctor_section:doctor_dash",  # Doctor role ke liye dashboard redirect
            "student": "student_section:student_dash",  # Student role ke liye dashboard redirect
            "staff": "staff_section:staff_dash",  # Staff role ke liye dashboard redirect
        }

        # Agar role valid hai to uss role ke dashboard par redirect karen, warna default "dashboard" par
        return redirect(role_redirects.get(user.role, "dashboard"))

    # Agar GET request hai, to login page render karen
    current_year = datetime.datetime.now().year
    return render(request, "login.html", {"current_year": current_year})


def logout(request):
    logout(request)
    messages.success(request, "Successfully logged out!")
    return redirect("login")
