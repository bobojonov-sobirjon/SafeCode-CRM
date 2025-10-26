from django.shortcuts import render, get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.v1.website.models import Services, ServiceItems, Contacts
from apps.v1.website.serializers import ServicesSerializer, ServiceItemsSerializer, ContactsSerializer


class ServicesListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Services"],
        operation_id="get_services",
        operation_summary="Get all services",
        operation_description="Get all services",
        responses={200: ServicesSerializer(many=True), 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
    )
    def get(self, request):
        services = Services.objects.all().order_by('-created_at')
        serializer = ServicesSerializer(services, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Services"],
        operation_id="get_service_detail",
        operation_summary="Get service detail",
        operation_description="Get service detail",
        operation_parameters=[
            openapi.Parameter(
                name="pk",
                in_="path",
                type=openapi.TYPE_INTEGER,
                required=True,
                description="Service ID"
            )
        ],
        responses={200: ServicesSerializer, 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
    )
    def get(self, request, *args, **kwargs):
        service = get_object_or_404(Services, pk=kwargs.get('pk'))
        serializer = ServicesSerializer(service, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContactsListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Contacts"],
        operation_id="get_contacts",
        operation_summary="Get all contacts",
        operation_description="Get all contacts",
        responses={200: ContactsSerializer(many=True), 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
    )
    def get(self, request):
        contacts = Contacts.objects.all().order_by('-created_at')
        serializer = ContactsSerializer(contacts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
