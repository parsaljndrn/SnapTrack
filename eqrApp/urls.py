from django.urls import path, include
from . import views
from .views import custom_login, attendee_dashboard, CustomLoginView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.shortcuts import redirect
from .views import home 

app_name = 'eqrApp'

urlpatterns = [
    path('', views.home, name='home'),  # Root URL
    path('home/', views.home, name='home'),
    #issue dito pre automatic sa homepage dumideretso imbis na log in
    #members page (actions)
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.manage_member, name='add_member'),
    path('members/edit/<str:member_id>/', views.manage_member, name='edit_member'),
    path('members/delete/<str:member_id>/', views.delete_member, name='delete_member'),
    path('members/mass-delete/', views.mass_delete_members, name='mass_delete_members'),
    path('members/manage/<str:member_id>/', views.manage_member, name='manage_member'),
    path('api/members/<str:member_id>/', views.get_member, name='get_member'),
    path('api/members/<str:member_id>/update/', views.update_member, name='update_member'),
    #path('api/events/<int:event_id>/attendance/', views.event_attendance_stats, name='event_attendance_stats'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('attendee/dashboard/', views.attendee_dashboard, name='attendee_dashboard'),
    path('events/<int:event_id>/generate-qr/', views.generate_event_qr, name='generate_event_qr'),
    path('events/<int:event_id>/get-qr/', views.get_member_event_qr, name='get_member_event_qr'),

    
    #path('accounts/login/', views.custom_login, name='login'),
    path('members/manage/<str:member_id>/', views.manage_member, name='manage_member'),
    path('members/mass_delete/', views.mass_delete_members, name='mass_delete_members'),
    #member dashboard (member logging in, not redirecting here: check views)
    #log out url
    #path('accounts/logout/', LogoutView.as_view(), name='logout'),
    #event page (actions)
    path('events/', views.event_list, name='event_list'),  
    path('events/create/', views.create_event, name='create_event'),
    path('event/<int:pk>/delete/', views.delete_event, name='delete_event'), #edited 052525-1045
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/bulk-edit-attendance/', views.bulk_edit_attendance, name='bulk_edit_attendance'),
    path('events/<int:event_id>/save-bulk-attendance/', views.save_bulk_attendance, name='save_bulk_attendance'),

    #GAWA NI PARIS
    path('events/<int:event_id>/export-csv/', views.export_csv, name='export_csv'),
]
