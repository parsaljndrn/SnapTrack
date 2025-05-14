from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from eqrApp import views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('eqrApp.urls')),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    # Authentication URLs
]