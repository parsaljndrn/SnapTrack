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
        
        # Check if user already exists
            user_exists = User.objects.filter(username=self.member_id).exists()
        
            if user_exists:
            # Update existing user
                user = User.objects.get(username=self.member_id)
                user.set_password(password)
                user.email = self.email or ''
                user.first_name = self.first_name
                user.last_name = self.last_name
                user.save()
            else:
            # Create new user
                User.objects.create_user(
                    username=self.member_id,
                    password=password,
                    email=self.email or '',
                    first_name=self.first_name,
                    last_name=self.last_name,
                    is_staff=False,
                    is_active=True
                )
        
        # Store the password temporarily
            self.temp_password = password
            self.password_generated_at = timezone.now()
        
        # Save again to store password info
            super().save(update_fields=['temp_password', 'password_generated_at'])
    
    temp_password = models.CharField(max_length=6, blank=True, null=True)
    password_generated_at = models.DateTimeField(null=True, blank=True)
    
    def generate_temp_password(self):
        """Generate a new temporary password"""
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        self.temp_password = password
        self.password_generated_at = timezone.now()
        
        # Create or update user account
        user, created = User.objects.get_or_create(
            username=self.member_id,
            defaults={
                'password': make_password(password),
                'email': self.email or '',
                'first_name': self.first_name,
                'last_name': self.last_name,
                'is_staff': False,
                'is_active': True
            }
        )
        
        if not created:
            user.set_password(password)
            user.save()
            
        self.save()
        return password
    
    def get_current_password(self):
        """Get current valid password if not expired"""
        if self.password_generated_at and \
           (timezone.now() - self.password_generated_at) < timedelta(hours=1):
            return self.temp_password
        return None

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
    timestamp = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add
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
        return f"{self.member} attended {self.event} at {self.timestamp}"

    # In models.py - enhance the save method
def save(self, *args, **kwargs):
    # Only auto-set status if it's not being manually set
    if not self.status or self.status == 'absent':
        if self.event.start_time:
            from django.utils.timezone import make_aware
            from datetime import datetime, time
            
            # Create aware datetime objects for comparison
            event_date = self.event.date
            event_start_time = self.event.start_time
            event_start = make_aware(datetime.combine(event_date, event_start_time))
            
            arrival_time = self.timestamp
            
            # Calculate time difference in minutes
            time_difference = (arrival_time - event_start).total_seconds() / 60
            
            if time_difference <= 10:  # On time or less than 10 mins late
                self.status = 'present'
            else:  # More than 10 mins late
                self.status = 'late'
        else:  # No start time specified, default to present
            self.status = 'present'
    
    super().save(*args, **kwargs)
    
class QRCode(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='qr_codes/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('member', 'event')