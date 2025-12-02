from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Journals and Acts endpoints
    path('journals-and-acts/', views.JournalsAndActsListCreateAPIView.as_view(), name='journals_and_acts_list_create'),
    path('journals-and-acts/<int:pk>/', views.JournalsAndActsDetailAPIView.as_view(), name='journals_and_acts_detail'),
    path('journals-and-acts/by-object-user/', views.JournalsAndActsByObjectUserListAPIView.as_view(), name='journals_and_acts_by_object_user_list'),
    
    # Bills endpoints
    path('bills/', views.BillsListCreateAPIView.as_view(), name='bills_list_create'),
    path('bills/<int:pk>/', views.BillsDetailAPIView.as_view(), name='bills_detail'),
    path('bills/by-object-user/', views.BillsByObjectUserListAPIView.as_view(), name='bills_by_object_user_list'),
]