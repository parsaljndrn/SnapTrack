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
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('qr/<str:member_id>/', views.generate_qr, name='generate_qr'),
    path('events/<int:event_id>/qr/all/', views.generate_all_qr, name='generate_qr_all'),
    
    # Include auth URLs for password reset etc.
    path('accounts/', include('django.contrib.auth.urls')),
]