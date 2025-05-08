from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import qrcode
import random
import string
from io import BytesIO
from django.core.files import File
from PIL import Image
import os
from django.contrib.auth.hashers import make_password
import secrets
from datetime import timedelta

class Member(models.Model):
    member_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    email = models.EmailField(unique=True, null=True, blank=True)
    section = models.CharField(max_length=100, blank=True, null=True)    
    avatar = models.ImageField(upload_to='member_avatars/', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    def create_user_account(self):
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # Check if user already exists
        if not User.objects.filter(username=self.member_id).exists():
            user = User.objects.create_user(
                username=self.member_id,
                password=password,
                email=self.email or '',
                is_staff=False,
                is_superuser=False
            )
            return password
        return None
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.member_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_member_id(self):
        return f"{self.member_id}"

    def get_section(self):
        return f"{self.section}"
    
    def save(self, *args, **kwargs):
        # Convert empty email to None before saving
        if self.email == "":
            self.email = None
        
        creating = self._state.adding
        
        super().save(*args, **kwargs)
        
        if creating:
            # Generate a random password for new members
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            User.objects.create_user(
                username=self.member_id,
                password=password,
                email=self.email or '',
                first_name=self.first_name,
                last_name=self.last_name,
                is_staff=False
            )
            # Store the password temporarily (optional)
            self.temp_password = password

    temp_password = models.CharField(max_length=6, blank=True, null=True)
    password_generated_at = models.DateTimeField(null=True, blank=True)
    
    def get_current_password(self):
        """Get current valid password if not expired"""
        if self.password_generated_at and \
           (timezone.now() - self.password_generated_at) < timedelta(minutes=5):
            return self.temp_password
        return None
    
    def generate_temp_password(self):
        """Generate a new temporary password"""
        self.temp_password = ''.join(random.choices(
            string.ascii_letters + string.digits, 
            k=6
        ))
        self.password_generated_at = timezone.now()
        self.save()
        
        # Update user account password if exists
        if User.objects.filter(username=self.member_id).exists():
            user = User.objects.get(username=self.member_id)
            user.set_password(self.temp_password)
            user.save()
            
        return self.temp_password

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)  # Temporary
    end_time = models.TimeField(null=True, blank=True)    # Temporary
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"
    
    def get_time_slot(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('late', 'Late')
        ],
        default='absent'
    )
    
    class Meta:
        unique_together = ('event', 'member')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.member} attended {self.event}"