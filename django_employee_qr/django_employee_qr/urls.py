from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from eqrApp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('eqrApp.urls', 'eqrApp'), namespace='eqrApp')),
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # App URLs
    path('', views.home, name='home'),
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.manage_member, name='add_member'),
    path('members/edit/<str:member_id>/', views.manage_member, name='edit_member'),
    path('members/mass-delete/', views.mass_delete_members, name='mass_delete_members'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/bulk-edit-attendance/', views.bulk_edit_attendance, name='bulk_edit_attendance'),
    path('events/<int:event_id>/save-bulk-attendance/', views.save_bulk_attendance, name='save_bulk_attendance'),
    
    
    # Include auth URLs for password reset etc.
    path('accounts/', include('django.contrib.auth.urls')),
]