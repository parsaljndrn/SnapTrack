from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from .models import Event, Member, Attendance
from .forms import EventForm, MemberForm, AttendanceForm
import qrcode
import io
from io import BytesIO
from django.core.files import File
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from django.db.models import Count
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.urls import reverse


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
    }
    return render(request, 'home.html', context)

def logout_user(request):
    logout(request)
    return redirect('login')


@login_required
@require_http_methods(["GET", "POST"])
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
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
        messages.error(request, "No members selected for deletion")
        return redirect('eqrApp:member_list')
    
    try:
        with transaction.atomic():
            count = Member.objects.filter(member_id__in=member_ids).count()
            Member.objects.filter(member_id__in=member_ids).delete()
        messages.success(request, f"Successfully deleted {count} members")
    except Exception as e:
        messages.error(request, f"Error deleting members: {str(e)}")
    
    return redirect('eqrApp:member_list')

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
                    # Ensure email is None if empty
                    if form.cleaned_data['email'] == "":
                        member.email = None
                    member.save()
                    messages.success(request, f'Member {member.get_full_name()} saved successfully!')
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
