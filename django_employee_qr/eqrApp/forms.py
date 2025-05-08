from django import forms
from django.core.validators import RegexValidator
from .models import Event, Member, Attendance

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'date', 'start_time', 'end_time']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control-events mb-3', 'placeholder': 'Enter event name'}),
            'date': forms.DateInput(attrs={'class': 'form-control-events mb-3', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'required': 'required'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'required': 'required'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if not start_time:
            raise forms.ValidationError("Start time is required")
        if not end_time:
            raise forms.ValidationError("End time is required")
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("End time must be after start time")
        
        return cleaned_data

class MemberForm(forms.ModelForm):
    member_id = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^\d{11}$',
                message='Member ID must be exactly 11 digits',
                code='invalid_member_id'
            )
        ],
        widget=forms.TextInput(attrs={
            'required': True,
            'pattern': r'\d{11}',
            'title': 'Must be exactly 11 digits'
        }))
    
    section = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'pattern': r'^[a-zA-Z0-9]{4,6}$',
            'title': 'Please enter your designated section'
        }))
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'pattern': r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$|^$',
            'title': 'Please enter a valid email address or leave blank'
        }))

    class Meta:
        model = Member
        fields = ['member_id', 'first_name', 'last_name', 'email', 'section']
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        return None if email == "" else email
    
class AttendanceForm(forms.ModelForm):
    status = forms.ChoiceField(
        required=True,
        choices=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('late', 'Late'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Attendance
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'})
        } 
