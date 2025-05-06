from django.contrib import admin
from .models import Event, Member, Attendance

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'created_by', 'created_at')
    search_fields = ('name',)
    list_filter = ('date', 'created_by')
    date_hierarchy = 'date'

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'first_name', 'last_name', 'email', 'section')
    search_fields = ('member_id', 'first_name', 'last_name', 'email')
    list_filter = ('section',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'event', 'timestamp')
    search_fields = ('member__member_id', 'member__first_name', 'member__last_name')
    list_filter = ('event', 'timestamp')
    date_hierarchy = 'timestamp'