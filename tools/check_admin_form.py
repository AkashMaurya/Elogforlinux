import os
import django
from django.test.client import RequestFactory

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elogbookagu.settings')
django.setup()

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from accounts.admin import CustomUserAdmin

User = get_user_model()
# create admin and user instances
admin_user = User.objects.create_superuser(username='admintestscript', email='admintestscript@example.com', password='adminpass')
user = User.objects.create(username='targetscript', email='targetscript@example.com')
user.set_password('pass')
user.save()

site = AdminSite()
admin = CustomUserAdmin(User, site)

# Build a request with POST data similar to the test
rf = RequestFactory()
request = rf.post('/')
request.user = admin_user

# Prepare POST data from the actual admin change page would contain many fields.
post_data = {
    'username': user.username,
    'email': user.email,
    'role': 'doctor',
    '_save': 'Save',
}

# Get the form class for change
FormClass = admin.get_form(request, obj=user)
form = FormClass(post_data, instance=user)
print('Form fields:', list(form.fields.keys()))
print('Form is_bound:', form.is_bound)
print('Form is_valid:', form.is_valid())
print('Form errors:', form.errors)
print('Cleaned data keys:', list(getattr(form, 'cleaned_data', {}).keys()))

# If invalid, print which fields are required or have errors
for name, field in form.fields.items():
    print(name, 'required=', field.required)

# Also try including initial values for non-primitive fields set to empty
# e.g., ensure profile_photo present
post_data2 = post_data.copy()
post_data2.setdefault('profile_photo', '')
form2 = FormClass(post_data2, instance=user)
print('Form2 is_valid:', form2.is_valid())
print('Form2 errors:', form2.errors)
print('Done')
