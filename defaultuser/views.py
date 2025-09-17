from django.shortcuts import render

# Create your views here.
def default_user_view(request):
    return render(request, 'default_user.html')