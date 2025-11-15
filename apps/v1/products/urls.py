from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # CRUD операции для продуктов
    path('', views.ProductListCreateAPIView.as_view(), name='product_list_create'),
    path('<int:pk>/', views.ProductDetailAPIView.as_view(), name='product_detail'),
    
    # Удаление изображения
    path('images/<int:image_id>/delete/', views.ProductImageDeleteAPIView.as_view(), name='product_image_delete'),
    
    # Избранные продукты
    path('favorites/', views.FavoriteProductListCreateAPIView.as_view(), name='favorite_product_list_create'),
    path('favorites/<int:pk>/delete/', views.FavoriteProductDeleteAPIView.as_view(), name='favorite_product_delete'),
]