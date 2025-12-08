from django.urls import path
from . import views
from . import storage_views

app_name = 'accounts'

urlpatterns = [
    # Регистрация и вход
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('verify-email/', views.VerifyEmailAPIView.as_view(), name='verify_email'),
    path('resend-verification-email/', views.ResendVerificationEmailAPIView.as_view(), name='resend_verification_email'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('roles/', views.GetRolesAPIView.as_view(), name='get_roles'),
    
    # Восстановление пароля
    path('forgot-password/', views.ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordAPIView.as_view(), name='reset_password'),
    
    # Профиль пользователя
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('profile/change-password/', views.ChangePasswordAPIView.as_view(), name='change_password'),
    
    # Purchased services
    path('purchased-services/', views.PurchasedServiceListCreateAPIView.as_view(), name='purchased_service_list_create'),
    path('purchased-services/<int:pk>/', views.PurchasedServiceDetailAPIView.as_view(), name='purchased_service_detail'),
    
    # User management
    path('users/', views.ListUsersAPIView.as_view(), name='list_users'),
    path('users/create/', views.CreateUserAPIView.as_view(), name='create_user'),
    path('users/<int:pk>/', views.UserDetailAPIView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', views.UpdateUserAPIView.as_view(), name='update_user'),
    path('users/<int:pk>/delete/', views.DeleteUserAPIView.as_view(), name='delete_user'),
    path('users/<int:pk>/password/', views.UpdateUserPasswordAPIView.as_view(), name='update_user_password'),
    
    # Group management
    path('groups/', views.GroupListAPIView.as_view(), name='group_list'),
    
    # Storage management
    path('storage/', storage_views.StorageListCreateAPIView.as_view(), name='storage_list_create'),
    path('storage/<int:pk>/', storage_views.StorageDetailAPIView.as_view(), name='storage_detail'),
    path('storage/<int:storage_id>/files/', storage_views.StorageFileListCreateAPIView.as_view(), name='storage_file_list_create'),
    path('storage/<int:storage_id>/files/<int:file_id>/', storage_views.StorageFileDetailAPIView.as_view(), name='storage_file_detail'),
]