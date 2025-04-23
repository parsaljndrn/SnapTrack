from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class UserAttendee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=11, unique=True)
    section = models.CharField(max_length=4)
    is_admin = models.BooleanField(default=False)


class UserFacilitator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=11, unique=True)
    is_admin = models.BooleanField(default=True)

class Events(models.Model):
    facilitator = models.ForeignKey(UserFacilitator, on_delete=models.CASCADE)
    event_name = models.CharField(max_length=200)
    event_date = models.DateField()

class AttendanceRecord(models.Model):
    event = models.ForeignKey(Events, on_delete=models.CASCADE)
    attendee = models.ForeignKey(UserAttendee, on_delete=models.CASCADE)
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ['event', 'attendee']

    