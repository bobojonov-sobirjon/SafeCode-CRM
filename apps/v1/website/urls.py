from django.urls import path

from apps.v1.website.views import ServicesListView, ServiceDetailView, ContactsListView

urlpatterns = [
    path('services/', ServicesListView.as_view(), name='services_list'),
    path('services/<int:pk>/', ServiceDetailView.as_view(), name='service_detail'),
    path('contacts/', ContactsListView.as_view(), name='contacts_list'),
]
