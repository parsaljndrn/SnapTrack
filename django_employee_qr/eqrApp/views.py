from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from .models import Event, Member, Attendance, QRCode
from .forms import EventForm, MemberForm, AttendanceForm
import qrcode
import io
import os
from django.conf import settings
from django.contrib.auth.hashers import make_password
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import random
import string
from django.db import transaction, IntegrityError
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
import json
from io import BytesIO
from django.core.files.base import ContentFile
import base64
from PIL import Image
#GAWA NI PARIS
import csv
from django.http import HttpResponse
from .models import Attendance
import re

def sanitize_filename(name):
    return re.sub(r'[^A-Za-z0-9_-]', '_', name)

def export_csv(request, event_id):
    from .models import Attendance, Event

    event = Event.objects.get(pk=event_id) 
    safe_event_name = sanitize_filename(event.name)  

    event = Event.objects.get(pk=event_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{safe_event_name}_attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Event', 'Member', 'Timestamp', 'Status'])

    for obj in Attendance.objects.filter(event=event).select_related('member'):
        writer.writerow([
            event.name,  # or event.name depending on your model
            f"{obj.member.first_name} {obj.member.last_name}",
            obj.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            obj.get_status_display()
        ])

    return response
#GAWA N PARIS

def facilitator_required(view_func):
    def check_facilitator(user):
        return user.is_authenticated and user.is_staff
    return user_passes_test(check_facilitator, login_url='eqrApp:attendee_dashboard')(view_func)

from django.views.decorators.csrf import csrf_protect

@csrf_protect
def custom_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('eqrApp:home')
        return redirect('eqrApp:attendee_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', '')
            if next_url:
                return redirect(next_url)
            if user.is_staff:
                return redirect('eqrApp:home')
            return redirect('eqrApp:attendee_dashboard')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('eqrApp:login')
    
    # Pass the next parameter to template
    next_param = request.GET.get('next', '')
    return render(request, 'myloginpage.html', {
        'next': next_param
    })

def custom_logout(request):
    logout(request)
    return redirect('eqrApp:login')

@login_required
def attendee_dashboard(request):
    # Ensure only non-staff users can access this
    if request.user.is_staff:
        return redirect('eqrApp:home')
    
    try:
        member = Member.objects.get(member_id=request.user.username)
    except Member.DoesNotExist:
        logout(request)
        messages.error(request, "Member account not found")
        return redirect('eqrApp:login')
    
    # Get the most recent event with a QR code for this member
    current_event_qr = QRCode.objects.filter(member=member).select_related('event').order_by('-event__date').first()
    
    # Check if member is already marked present for the current event
    is_present = False
    if current_event_qr:
        is_present = Attendance.objects.filter(
            event=current_event_qr.event,
            member=member,
            status__in=['present', 'late']
        ).exists()
    
    # Get upcoming events (next 7 days) where member is absent
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(
        date__gte=today,
        date__lte=today + timedelta(days=7)
    ).order_by('date', 'start_time')
    
    # Filter for events where member is absent
    absent_events = []
    for event in upcoming_events:
        if not Attendance.objects.filter(event=event, member=member, status__in=['present', 'late']).exists():
            absent_events.append(event)
    
    # Get attendance history (last 10 records)
    attendance_history = Attendance.objects.filter(
        member=member
    ).select_related('event').order_by('-event__date')[:10]
    
    context = {
        'member': member,
        'current_event_qr': current_event_qr,
        'is_present': is_present,  # Add this flag
        'upcoming_events': absent_events,
        'attendance_history': attendance_history,
        'page_title': 'Attendee Dashboard'
    }
    
    return render(request, 'attendee_dashboard.html', context)

@login_required
def home(request):
    # Redirect non-staff users to attendee dashboard
    if not request.user.is_staff:
        return redirect('eqrApp:attendee_dashboard')
    
    today = timezone.now().date()
    
    # Get recent events for the activity section
    recent_events = Event.objects.order_by('-date')[:5]
    
    # Add stats to each event
    for event in recent_events:
        total = Member.objects.count()
        present = Attendance.objects.filter(event=event, status='present').count()
        late = Attendance.objects.filter(event=event, status='late').count()
        absent = total - present - late
        
        event.present_count = present
        event.late_count = late
        event.absent_count = absent
        event.total_members = total
    
    # Calculate attendance stats for the most recent event
    if recent_events:
        latest_event = recent_events[0]
        total_members = Member.objects.count()
        present_count = Attendance.objects.filter(event=latest_event, status='present').count()
        late_count = Attendance.objects.filter(event=latest_event, status='late').count()
        absent_count = total_members - present_count - late_count
    else:
        present_count = late_count = absent_count = 0
    
    context = {
        'page_title': 'Facilitator Dashboard',
        'members_count': Member.objects.count(),
        'events_count': Event.objects.count(),
        'active_events': Event.objects.filter(date__gte=today).count(),
        'recent_events': recent_events,
        'recent_members': Member.objects.order_by('-date_created')[:5],
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'total_members': Member.objects.count(),
    }
    return render(request, 'home.html', context)


class CustomLoginView(LoginView):
    template_name = 'myloginpage.html'  # Use your custom login template

    def form_valid(self, form):
        # Check if user is logging in as admin/facilitator
        user = form.get_user()
        if user.username == 'admin' and user.check_password('admin123'):
            return super().form_valid(form)

        # For attendees, check if username matches member_id format
        if Member.objects.filter(member_id=user.username).exists():
            return redirect('eqrApp:attendee_dashboard')  # Redirect to attendee dashboard
            
        return super().form_valid(form)

def logout_user(request):
    logout(request)
    return redirect('login')


@login_required
@require_http_methods(["GET", "POST"])
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=True)
            event.created_by = request.user
            event.save()
            messages.success(request, f'Event "{event.name}" created successfully!')
            return redirect('eqrApp:event_detail', pk=event.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm()
    
    return render(request, 'create_event.html', {
        'form': form,
        'page_title': 'Create New Event'
    })

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    attendances = Attendance.objects.filter(
        event=event, 
        status__in=['present', 'late']
    ).select_related('member').order_by('-timestamp')
    
    total_members = Member.objects.count()
    present_count = Attendance.objects.filter(event=event, status='present').count()
    late_count = Attendance.objects.filter(event=event, status='late').count()
    absent_count = total_members - present_count - late_count
    
    present_percentage = round((present_count / total_members) * 100) if total_members > 0 else 0
    late_percentage = round((late_count / total_members) * 100) if total_members > 0 else 0
    absent_percentage = round((absent_count / total_members) * 100) if total_members > 0 else 0
    
    if request.method == 'POST':
        scan_data = request.POST.get('scan_data', '').strip()
        if not scan_data:
            return HttpResponseBadRequest("No scan data provided")
        
        try:
            qr_data = json.loads(scan_data)
            member_id = qr_data.get('member_id')
            event_id = qr_data.get('event_id')
            
            if not member_id or not event_id or int(event_id) != event.id:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid QR code for this event'
                }, status=400)
            
            member = Member.objects.get(member_id=member_id)
            attendance, created = Attendance.objects.update_or_create(
                event=event,
                member=member,
                defaults={
                    'status': 'present',
                    'timestamp': timezone.now()  # Update timestamp on each scan
                }
            )
            return JsonResponse({'status': 'success'})
        except (Member.DoesNotExist, json.JSONDecodeError) as e:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid QR code data'
            }, status=400)
    
    return render(request, 'event_detail.html', {
        'event': event,
        'attendances': attendances,
        'page_title': f'{event.name} Details',
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'total_members': total_members,
        'present_percentage': present_percentage,
        'late_percentage': late_percentage,
        'absent_percentage': absent_percentage,
    })

@login_required
def member_list(request):
    members = Member.objects.annotate(
        attendance_count=Count('attendance')
    ).order_by('last_name', 'first_name')
    return render(request, 'member_list.html', {
        'members': members,
        'page_title': 'Member Directory'
    })

@login_required
@require_http_methods(["POST"])
def mass_delete_members(request):
    member_ids = request.POST.getlist('member_ids')
    if not member_ids:
        return JsonResponse({'success': False, 'message': 'No members selected'}, status=400)
    
    try:
        with transaction.atomic():
            # Get members to be deleted
            members = Member.objects.filter(member_id__in=member_ids)
            
            # Delete associated User accounts
            User.objects.filter(username__in=member_ids).delete()
            
            # Delete members
            count = members.delete()[0]
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully deleted {count} members'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error deleting members'
        }, status=500)

@login_required
@facilitator_required
def manage_member(request, member_id=None):
    if member_id:
        member = get_object_or_404(Member, member_id=member_id)
        action = 'Edit'
    else:
        member = None
        action = 'Add'
    
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            try:
                with transaction.atomic():
                    member = form.save(commit=False)
                    if form.cleaned_data['email'] == "":
                        member.email = None
                    member.save()
                    
                    if action == 'Add':
                        # Generate random password
                        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                        
                        # Create user account or update existing one
                        user, created = User.objects.get_or_create(
                            username=member.member_id,
                            defaults={
                                'password': make_password(password),
                                'email': member.email or '',
                                'first_name': member.first_name,
                                'last_name': member.last_name,
                                'is_staff': False,
                                'is_active': True
                            }
                        )
                        
                        if not created:
                            # Update existing user
                            user.set_password(password)
                            user.email = member.email or ''
                            user.first_name = member.first_name
                            user.last_name = member.last_name
                            user.save()
                        
                        # Store the temporary password
                        member.temp_password = password
                        member.password_generated_at = timezone.now()
                        member.save()
                        
                        messages.success(request, f'Member created successfully!')
                        messages.info(request, f'Generated password: {password}')
                    
                    return redirect('eqrApp:member_list')
                    
            except IntegrityError as e:
                messages.error(request, f'Error saving member: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MemberForm(instance=member)
    
    return render(request, 'manage_member.html', {
        'form': form,
        'action': action,
        'page_title': f'{action} Member'
    })

from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def get_member(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    return JsonResponse({
        'member_id': member.member_id,
        'first_name': member.first_name,
        'last_name': member.last_name,
        'email': member.email,
        'section': member.section
    })

@require_http_methods(["POST"])
def update_member(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    form = MemberForm(request.POST, instance=member)
    
    if form.is_valid():
        try:
            member = form.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': form.errors.as_json()})
    
@login_required
@require_http_methods(["POST"])
def delete_member(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    member.delete()
    return JsonResponse({'status': 'success'})

@login_required
def event_list(request):
    events = Event.objects.order_by('-date')
    return render(request, 'event_list.html', {
        'events': events,
        'page_title': 'All Events'
    })

@login_required
def bulk_edit_attendance(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    
    # Get all members and their attendance status for this event
    members = Member.objects.all().order_by('last_name', 'first_name')
    
    # Get existing attendance records for this event
    attendances = {
        attendance.member_id: attendance.status 
        for attendance in Attendance.objects.filter(event=event)
    }
    
    # Add attendance status to each member
    for member in members:
        member.attendance_status = attendances.get(member.id, 'absent')
    
    return render(request, 'bulk_edit_attendance.html', {
        'event': event,
        'members': members,
        'page_title': f'Edit Attendance - {event.name}'
    })

# In views.py - update save_bulk_attendance
@login_required
@require_http_methods(["POST"])
def save_bulk_attendance(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    members = Member.objects.all()
    count_updated = 0
    
    for member in members:
        status_key = f'status_{member.member_id}'
        if status_key in request.POST:
            status = request.POST.get(status_key)

            if status in ['present', 'absent', 'late']:
                # For manual updates, we'll use the current time as timestamp
                attendance, created = Attendance.objects.update_or_create(
                    event=event,
                    member=member,
                    defaults={
                        'status': status,
                        'timestamp': timezone.now()  # Use current time for manual updates
                    }
                )
                count_updated += 1
    
    messages.success(request, f'Successfully updated attendance for {count_updated} members!')
    return redirect('eqrApp:event_detail', pk=event_id)

# In views.py - update event_attendance_stats
@login_required
def event_attendance_stats(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    total_members = Member.objects.count()
    
    present_count = Attendance.objects.filter(event=event, status='present').count()
    late_count = Attendance.objects.filter(event=event, status='late').count()
    absent_count = total_members - present_count - late_count
    
    data = {
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'total_members': total_members,
        'present_percentage': round((present_count / total_members) * 100) if total_members > 0 else 0,
        'late_percentage': round((late_count / total_members) * 100) if total_members > 0 else 0,
        'absent_percentage': round((absent_count / total_members) * 100) if total_members > 0 else 0
    }
    
    return JsonResponse(data)

@login_required
def view_credentials(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    
    # Generate new password if needed
    if request.user.is_staff and not member.get_current_password():
        member.generate_temp_password()
    
    context = {
        'member': member,
        'is_staff': request.user.is_staff,
        'current_password': member.get_current_password() or 'Not available'
    }
    return render(request, 'view_credentials.html', context)

@login_required
def generate_event_qr(request, event_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    event = get_object_or_404(Event, pk=event_id)
    members = Member.objects.all()
    
    try:
        qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes', str(event_id))
        os.makedirs(qr_dir, exist_ok=True)
        
        counter = 0
        for member in members:
            # Create QR data with event ID, member ID, and event details
            qr_data = {
                'event_id': event.id,
                'member_id': member.member_id,
                'event_name': event.name,
                'event_date': event.date.strftime('%Y-%m-%d'),
                'event_start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
                'event_end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
             # Use encrypted data
            qr.add_data(json.dumps(qr_data))  # Encode as JSON string
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            filename = f"{member.member_id}.png"
            filepath = os.path.join(qr_dir, filename)
            img.save(filepath)
            
            relative_path = f'qr_codes/{event_id}/{filename}'
            qr_code, created = QRCode.objects.update_or_create(
                member=member,
                event=event,
                defaults={'image': relative_path}
            )
            
            counter += 1
        
        return JsonResponse({
            'success': True, 
            'message': f'Generated QR codes for {counter} members'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error generating QR codes: {str(e)}'
        }, status=500)

@login_required
def get_member_event_qr(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    
    if request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Not available for staff users'}, status=403)
    
    try:
        member = Member.objects.get(member_id=request.user.username)
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)
    
    try:
        # Try to get existing QR code
        qr_code = QRCode.objects.get(member=member, event=event)
    except QRCode.DoesNotExist:
        # Generate QR code on-the-fly if it doesn't exist
        try:
            qr_data = {
                'member_id': member.member_id,
                'event_id': event.id,
                'event_name': event.name,
                'event_date': event.date.strftime('%Y-%m-%d'),
                'event_start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
                'event_end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
            }

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(f"MEMBER: {member.member_id}")
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Create directory if it doesn't exist
            qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes', str(event_id))
            os.makedirs(qr_dir, exist_ok=True)
            
            # Save to file
            filename = f"{member.member_id}.png"
            filepath = os.path.join(qr_dir, filename)
            img.save(filepath)
            
            # Store the path in the QRCode model
            relative_path = f'qr_codes/{event_id}/{filename}'
            qr_code = QRCode.objects.create(
                member=member,
                event=event,
                image=relative_path
            )
            
            # Make sure the image field is saved properly
            if not qr_code.image:
                # If image field is empty, set it manually
                qr_code.image = relative_path
                qr_code.save()
                
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'Error generating QR code: {str(e)}'
            }, status=500)
    
    try:
        # Ensure the file exists
        if not os.path.exists(qr_code.image.path):
            return JsonResponse({
                'success': False, 
                'error': 'QR code file not found'
            }, status=404)
            
        with open(qr_code.image.path, 'rb') as f:
            image_data = f.read()
            qr_data_uri = f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
            
        return JsonResponse({
            'success': True, 
            'qr_code': qr_data_uri,
            'member_id': member.member_id,
            'event_id': event.id,
            'event_name': event.name,
            'event_date': event.date.strftime('%Y-%m-%d'),
            'event_time': f"{event.start_time.strftime('%H:%M')} - {event.end_time.strftime('%H:%M')}" if event.start_time and event.end_time else "All day",
            'event_start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
            'event_end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error processing QR code: {str(e)}'
        }, status=500)

#edited 052525-1043
@login_required
@require_http_methods(["POST"])
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    event.delete()
    return JsonResponse({'success': True, 'message': "Event deleted successfully"})