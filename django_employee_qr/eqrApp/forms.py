from django import forms
from .models import Event, Member

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['member_id', 'first_name', 'last_name', 'email', 'section']