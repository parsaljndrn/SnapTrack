from django.urls import path, include
from . import views
from .views import custom_login, attendee_dashboard
from django.contrib.auth.views import LoginView, LogoutView

app_name = 'eqrApp'

urlpatterns = [
    path('home/', views.home, name='home'), #issue dito pre automatic sa homepage dumideretso imbis na log in
    #members page (actions)
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.manage_member, name='add_member'),
    path('members/edit/<str:member_id>/', views.manage_member, name='edit_member'),
    path('members/delete/<str:member_id>/', views.delete_member, name='delete_member'),
    path('members/mass-delete/', views.mass_delete_members, name='mass_delete_members'),
    path('members/manage/<str:member_id>/', views.manage_member, name='manage_member'),
    path('api/members/<str:member_id>/', views.get_member, name='get_member'),
    path('api/members/<str:member_id>/update/', views.update_member, name='update_member'),
    path('api/events/<int:event_id>/attendance/', views.event_attendance_stats, name='event_attendance_stats'),
    path('accounts/login/', views.custom_login, name='login'),
    path('accounts/logout/', LogoutView.as_view(next_page='login'), name='logout'),

    
    #path('accounts/login/', views.custom_login, name='login'),
    path('members/manage/<str:member_id>/', views.manage_member, name='manage_member'),
    path('members/view/<str:member_id>/', views.view_credentials, name='view_credentials'),
    path('members/mass_delete/', views.mass_delete_members, name='mass_delete_members'),
    #member dashboard (member logging in, not redirecting here: check views)
    path('attendee_dashboard/', attendee_dashboard, name='attendee_dashboard'),
    #path('accounts/attendee/', attendee_dashboard, name='attendee_dashboard'),
    #log out url
    path('accounts/logout/', views.logout_user, name='logout'),
    #path('accounts/logout/', LogoutView.as_view(), name='logout'),
    #event page (actions)
    path('events/', views.event_list, name='event_list'),  
    path('events/create/', views.create_event, name='create_event'),
    # path('event/<int:pk>/delete/', views.delete_event, name='delete_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/bulk-edit-attendance/', views.bulk_edit_attendance, name='bulk_edit_attendance'),
    path('events/<int:event_id>/save-bulk-attendance/', views.save_bulk_attendance, name='save_bulk_attendance'),
] 
