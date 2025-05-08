from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from .models import Event, Member, Attendance
from .forms import EventForm, MemberForm, AttendanceForm
import qrcode
import io
from django.contrib.auth.hashers import make_password
from django.core.files import File
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from django.db.models import Count
from django.utils import timezone
import random
import string
from django.db import transaction, IntegrityError
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.utils import timezone

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # First try authenticating normally
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            # Check if this is a member ID that exists
            if Member.objects.filter(member_id=username).exists():
                messages.error(request, 'Invalid password')
            else:
                messages.error(request, 'Invalid credentials')
            return render(request, 'myloginpage.html')
        
        login(request, user)
        if user.is_staff:
            return redirect('home')
        return redirect('attendee_dashboard')
    
    return render(request, 'myloginpage.html')

@login_required
def attendee_dashboard(request):
    context = {
        'page_title': 'Dashboard',
        'members_count': Member.get_full_name(),
        'member_id': Member.get_member_id(),
        'section': Member.get_section(),
    }
    return render(request, 'attendee_dashboard.html', context)

@login_required
def home(request):
    today = timezone.now().date()
    context = {
        'page_title': 'Dashboard',
        'members_count': Member.objects.count(),
        'events_count': Event.objects.count(),
        'active_events': Event.objects.filter(date__gte=today).count(),
        'recent_events': Event.objects.order_by('-date')[:5],
        'recent_attendances': Attendance.objects.select_related('member', 'event')
                              .order_by('-timestamp')[:10],
        'events': Event.objects.order_by('-date')  # Add all events for the dropdown
    }
    return render(request, 'home.html', context)

class CustomLoginView(LoginView):
    def form_valid(self, form):
        # Check if user is logging in as admin/facilitator
        user = form.get_user()
        if user.username == 'admin' and user.check_password('admin123'):
            return super().form_valid(form)
        
        # For attendees, check if username matches member_id format
        if Member.objects.filter(member_id=user.username).exists():
            return redirect('attendee_dashboard')  # Redirect to empty page for now
            
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
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            messages.success(request, f'Event "{event.name}" created successfully!')
            return redirect('event_detail', pk=event.pk)
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
            member_id = scan_data.replace('MEMBER:', '')
            member = Member.objects.get(member_id=member_id)
            attendance, created = Attendance.objects.get_or_create(
                event=event,
                member=member,
                defaults={'status': 'present'} 
            )
            if not created:
                attendance.status = 'present'
                attendance.save()
                messages.info(request, f'{member.get_full_name()} marked as present!')
            else:
                messages.success(request, f'{member.get_full_name()} marked as present!')
        except Member.DoesNotExist:
            messages.error(request, f'Member ID {member_id} not found!')
        return redirect('event_detail', pk=event.pk)
    
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
def generate_all_qr(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    attendees = Attendance.objects.filter(event=event).select_related('member').order_by('member__last_name')
    if not attendees.exists():
        messages.warning(request, "No attendees found for this event")
        return redirect('event_detail', pk=event_id)
    
    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{event.name}_attendees_qr_codes.pdf"'
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        x, y = 50, height - 100
        for i, attendee in enumerate(attendees, 1):
            if i > 1 and i % 3 == 1:
                p.showPage()
                x, y = 50, height - 100
            
            p.setFont("Helvetica-Bold", 12)
            p.drawString(x, y, f"ID: {attendee.member.member_id}")
            p.drawString(x, y-20, f"Name: {attendee.member.get_full_name()}")
            if attendee.member.section:
                p.drawString(x, y-40, f"Section: {attendee.member.section}")
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=2,
            )
            qr.add_data(f"MEMBER:{attendee.member.member_id}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            p.drawImage(ImageReader(img_buffer), x, y-140, width=100, height=100)
            x += 180
        
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('event_detail', pk=event_id)

@login_required
def generate_qr(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"MEMBER:{member.member_id}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        response = HttpResponse(content_type="image/png")
        response['Cache-Control'] = 'max-age=86400'
        img.save(response, "PNG")
        return response
    
    except Exception as e:
        return HttpResponseBadRequest(f"Error generating QR code: {str(e)}")

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
@require_http_methods(["GET", "POST"])
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
                        # Generate random 6-digit alphanumeric password
                        password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                        
                        # Create or update user account
                        user, created = User.objects.get_or_create(
                            username=member.member_id,
                            defaults={
                                'password': make_password(password),
                                'email': member.email or '',
                                'is_staff': False,
                                'is_active': True
                            }
                        )
                        
                        if not created:
                            # Update existing user if member ID already has an account
                            user.set_password(password)
                            user.save()
                        
                        messages.success(request, f'Member created successfully!')
                        messages.info(request, f'Temporary password: {password}')
                    
                    return redirect('eqrApp:member_list')
                    
            except IntegrityError as e:
                if 'email' in str(e) and form.cleaned_data.get('email'):
                    form.add_error('email', 'This email is already registered')
                elif 'member_id' in str(e):
                    form.add_error('member_id', 'This member ID already exists')
                else:
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
                attendance, created = Attendance.objects.update_or_create(
                    event=event,
                    member=member,
                    defaults={'status': status}
                )
                count_updated += 1
    
    messages.success(request, f'Successfully updated attendance for {count_updated} members!')
    return redirect('event_detail', pk=event_id)

@login_required
def event_attendance_stats(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    total_members = Member.objects.count()
    
    data = {
        'present': Attendance.objects.filter(event=event, status='present').count(),
        'late': Attendance.objects.filter(event=event, status='late').count(),
        'absent': total_members - Attendance.objects.filter(
            event=event, 
            status__in=['present', 'late']
        ).count()
    }
    
    return JsonResponse(data)

@login_required
def view_credentials(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    
    # Auto-generate new password if expired or doesn't exist
    if request.user.is_staff and not member.get_current_password():
        member.generate_temp_password()
    
    context = {
        'member': member,
        'is_staff': request.user.is_staff,
        'current_password': member.get_current_password()
    }
    return render(request, 'view_credentials.html', context)

# def delete_event(request, pk):
#     event = get_object_or_404(Event, pk=pk)
    
#     if request.method == 'POST':
#         event.delete()
#         messages.success(request, "Event deleted successfully")
#         return redirect('eqrApp:event_list')

#     return redirect('eqrApp:event_list')
