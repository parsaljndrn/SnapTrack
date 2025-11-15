from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.manage_member, name='add_member'),
    path('members/edit/<str:member_id>/', views.manage_member, name='edit_member'),
    path('accounts/login/', LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('events/', views.event_list, name='event_list'),  # This is the critical line
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('qr/<str:member_id>/', views.generate_qr, name='generate_qr'),
    path('events/<int:event_id>/qr/all/', views.generate_all_qr, name='generate_qr_all'),
]