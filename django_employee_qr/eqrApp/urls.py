from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    path('', views.home, name='home'),
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.manage_member, name='add_member'),
    path('members/edit/<str:member_id>/', views.manage_member, name='edit_member'),
    path('members/delete/<str:member_id>/', views.delete_member, name='delete_member'),
    path('members/mass-delete/', views.mass_delete_members, name='mass_delete_members'),
    path('accounts/login/', LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('members/manage/<str:member_id>/', views.manage_member, name='manage_member'),
    path('api/members/<str:member_id>/', views.get_member, name='get_member'),
    path('api/members/<str:member_id>/update/', views.update_member, name='update_member'),
    path('api/events/<int:event_id>/attendance/', views.event_attendance_stats, name='event_attendance_stats'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('events/', views.event_list, name='event_list'),  
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/bulk-edit-attendance/', views.bulk_edit_attendance, name='bulk_edit_attendance'),
    path('events/<int:event_id>/save-bulk-attendance/', views.save_bulk_attendance, name='save_bulk_attendance'),
]