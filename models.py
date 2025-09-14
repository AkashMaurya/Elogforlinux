from django.db import models

class DoctorConfig(models.Model):
    enable_attendance_tracking = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Doctor Configuration'
        verbose_name_plural = 'Doctor Configurations'

    def __str__(self):
        return 'Doctor Configuration Settings'