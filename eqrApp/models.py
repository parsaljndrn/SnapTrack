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
from django.core.exceptions import ValidationError
import base64

class Member(models.Model):
    member_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    email = models.EmailField(unique=True, null=True, blank=True)
    section = models.CharField(max_length=100, blank=True, null=True)    
    avatar = models.ImageField(upload_to='member_avatars/', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    temp_password = models.CharField(max_length=50, blank=True, null=True)  # Increased length
    password_generated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.member_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_member_id(self):
        return f"{self.member_id}"

    def get_section(self):
        return f"{self.section}"
    
    def set_default_password(self):
        """Set the exact last name as password"""
        last_name = self.last_name.strip()
        if not last_name:
            last_name = "TempPass123"  # Fallback if last name is empty
        
        self.temp_password = last_name
        self.password_generated_at = timezone.now()
        return last_name
    
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

    def clean(self):
        """Validate that last name meets minimum password requirements"""
        super().clean()
        if len(self.last_name.strip()) < 1:  # At least 1 character
            raise ValidationError({'last_name': 'Last name must not be empty'})

    def create_user_account(self):
        """Create or update user account with last name as password"""
        password = self.set_default_password()
        
        try:
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
                user.email = self.email or ''
                user.first_name = self.first_name
                user.last_name = self.last_name
                user.save()
                
            print(f"Created/Updated user account for {self.member_id} with password: {password}")
            return password
            
        except Exception as e:
            print(f"Error creating user account for {self.member_id}: {e}")
            return None

    def save(self, *args, **kwargs):
        # Convert empty email to None before saving
        if self.email == "":
            self.email = None
        
        self.clean()  # Run validation
        
        creating = self._state.adding
        super().save(*args, **kwargs)
        
        if creating:
            self.create_user_account()
            super().save(update_fields=['temp_password', 'password_generated_at'])
        
        # Update user account if name changed
        elif self.pk:
            try:
                old_member = Member.objects.get(pk=self.pk)
                if (self.first_name != old_member.first_name or 
                    self.last_name != old_member.last_name or
                    self.email != old_member.email):
                    
                    try:
                        user = User.objects.get(username=self.member_id)
                        user.first_name = self.first_name
                        user.last_name = self.last_name
                        user.email = self.email or ''
                        
                        # Update password if last name changed
                        if self.last_name != old_member.last_name:
                            new_password = self.set_default_password()
                            user.set_password(new_password)
                            print(f"Updated password for {self.member_id} to: {new_password}")
                        
                        user.save()
                    except User.DoesNotExist:
                        # Create user account if it doesn't exist
                        self.create_user_account()
            except Member.DoesNotExist:
                pass
        
class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"
    
    def get_time_slot(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10,
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

    def save(self, *args, **kwargs):
        # Only auto-set status if it's not being manually set
        # FIXED: Only auto-calculate for truly empty status, not manually set 'absent'
        if not self.status:  # Only when status is None/empty, not when it's explicitly 'absent'
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
    encrypted_data = models.TextField()  # Store encrypted QR data instead of image
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('member', 'event')
    
    def generate_qr_image_data_uri(self):
        """Generate QR code image as base64 data URI from encrypted data"""
        try:
            # Import crypto functions
            from .utils.crypto import decrypt_qr_data
            
            # Decrypt the data
            decrypted_data = decrypt_qr_data(self.encrypted_data)
            if not decrypted_data:
                return None
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.encrypted_data)  # Use encrypted data for QR
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 data URI
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"Error generating QR image: {e}")
            return None
    
    def get_decrypted_data(self):
        """Get decrypted QR data"""
        from .utils.crypto import decrypt_qr_data
        return decrypt_qr_data(self.encrypted_data)