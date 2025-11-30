from django.urls import path
from . import views
from . import delivery_payment_views

app_name = 'orders'

urlpatterns = [
    # Orders
    path('', views.OrderListCreateAPIView.as_view(), name='order_list_create'),
    path('<int:pk>/', views.OrderDetailAPIView.as_view(), name='order_detail'),
    
    # Delivery Methods
    path('delivery-methods/', delivery_payment_views.DeliveryMethodListCreateAPIView.as_view(), name='delivery_method_list_create'),
    path('delivery-methods/<int:pk>/', delivery_payment_views.DeliveryMethodDetailAPIView.as_view(), name='delivery_method_detail'),
    
    # Payment Methods
    path('payment-methods/', delivery_payment_views.PaymentMethodListCreateAPIView.as_view(), name='payment_method_list_create'),
    path('payment-methods/<int:pk>/', delivery_payment_views.PaymentMethodDetailAPIView.as_view(), name='payment_method_detail'),
]

