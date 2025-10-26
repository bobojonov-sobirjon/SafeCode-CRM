from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Регистрация и вход
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('roles/', views.GetRolesAPIView.as_view(), name='get_roles'),
    
    # Восстановление пароля
    path('forgot-password/', views.ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordAPIView.as_view(), name='reset_password'),
    
    # Профиль пользователя
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('profile/change-password/', views.ChangePasswordAPIView.as_view(), name='change_password'),
    path('profile/simple-change-password/', views.SimpleChangePasswordAPIView.as_view(), name='simple_change_password'),
    path('user-info/', views.UserInfoAPIView.as_view(), name='user_info'),
]