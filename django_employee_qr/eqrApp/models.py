from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import os

class Member(models.Model):
    member_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    email = models.EmailField(unique=True)
    section = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='member_avatars/', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.member_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"

class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('event', 'member')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.member} attended {self.event}"