from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/',  auth_views.LoginView.as_view(template_name='bourse/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('bourse.urls')),
    
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='bourse/password_change.html',
        success_url='/profil/'
    ), name='password_change'),
]