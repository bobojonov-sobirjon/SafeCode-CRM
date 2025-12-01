from django.urls import path
from . import views

app_name = 'user_objects'

urlpatterns = [
    # CRUD операции для объектов пользователя
    path('', views.UserObjectListCreateAPIView.as_view(), name='user_object_list_create'),
    path('all/', views.UserObjectAllListAPIView.as_view(), name='user_object_all_list'),
    path('archived/', views.UserObjectDeletedListAPIView.as_view(), name='user_object_deleted_list'),
    path('<int:pk>/', views.UserObjectDetailAPIView.as_view(), name='user_object_detail'),
    
    # Добавление работников к объекту
    path('workers/add/', views.UserObjectWorkersAddAPIView.as_view(), name='user_object_workers_add'),
    path('workers/', views.WorkersListAPIView.as_view(), name='workers_list'),
    path('documents/create/', views.UserObjectDocumentCreateAPIView.as_view(), name='user_object_document_create'),
    path('documents/', views.UserObjectDocumentsListAPIView.as_view(), name='user_object_documents_list'),
    
    # Обновление статуса объекта
    path('status/update/', views.UserObjectStatusUpdateAPIView.as_view(), name='user_object_status_update'),
]