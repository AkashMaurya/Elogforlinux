# Generated migration for soft delete functionality
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_create_ssoauditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_deleted',
            field=models.BooleanField(default=False, help_text='Soft delete flag - user is hidden but data preserved'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When the user was soft deleted', null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='deleted_by',
            field=models.ForeignKey(blank=True, help_text='Admin who performed the soft delete', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_users', to=settings.AUTH_USER_MODEL),
        ),
    ]
