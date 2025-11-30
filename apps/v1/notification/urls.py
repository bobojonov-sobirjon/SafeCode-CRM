from django.urls import path
from . import views

app_name = 'notification'

urlpatterns = [
    path('', views.NotificationListAPIView.as_view(), name='notification_list'),
    path('<int:notification_id>/read/', views.NotificationMarkAsReadAPIView.as_view(), name='notification_mark_as_read'),
]