from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import JournalsAndActs, Bills
from .serializers import (
    JournalsAndActsSerializer, JournalsAndActsCreateSerializer,
    BillsSerializer, BillsCreateSerializer
)
from apps.v1.accounts.error_handlers import get_error_message
from apps.v1.user_objects.models import UserObject


class JournalsAndActsListCreateAPIView(APIView):
    """
    Список и создание журналов и актов
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка журналов и актов текущего пользователя с пагинацией",
        tags=['Journals and Acts'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            
            # Фильтруем только по текущему пользователю
            queryset = JournalsAndActs.objects.filter(user=user).select_related('object_id', 'user').order_by('-created_at')
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except ValueError:
                page = 1
                limit = 10
            
            paginator = Paginator(queryset, limit)
            
            try:
                journals_and_acts = paginator.page(page)
            except EmptyPage:
                journals_and_acts = paginator.page(paginator.num_pages)
            except PageNotAnInteger:
                journals_and_acts = paginator.page(1)
            
            serializer = JournalsAndActsSerializer(journals_and_acts, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Журналы и акты получены успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': journals_and_acts.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'items_per_page': limit,
                    'has_next': journals_and_acts.has_next(),
                    'has_previous': journals_and_acts.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового журнала/акта. Поле type может принимать значения: 'estimate' (Смета), 'act' (Акт), 'form' (Форма)",
        tags=['Journals and Acts'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['object_id'],
            properties={
                'object_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID объекта пользователя'),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['estimate', 'act', 'form'],
                    description='Тип: estimate (Смета), act (Акт), form (Форма)',
                    default=None
                ),
                'date': openapi.Schema(type=openapi.FORMAT_DATE, description='Дата (YYYY-MM-DD)', default=None)
            }
        ),
        responses={201: 'Created', 400: 'Bad Request', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = JournalsAndActsCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                journal_or_act = serializer.save()
                
                response_serializer = JournalsAndActsSerializer(journal_or_act, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Журнал/акт создан успешно',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JournalsAndActsDetailAPIView(APIView):
    """
    Детали журнала/акта
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о журнале/акте по ID",
        tags=['Journals and Acts'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            journal_or_act = JournalsAndActs.objects.filter(pk=pk, user=user).select_related('object_id', 'user').first()
            
            if not journal_or_act:
                return Response({
                    'success': False,
                    'message': 'Журнал/акт не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = JournalsAndActsSerializer(journal_or_act, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Журнал/акт получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillsListCreateAPIView(APIView):
    """
    Список и создание счетов
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка счетов текущего пользователя с пагинацией",
        tags=['Bills'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            
            # Фильтруем только по текущему пользователю
            queryset = Bills.objects.filter(user=user).select_related('object_id', 'user').order_by('-created_at')
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except ValueError:
                page = 1
                limit = 10
            
            paginator = Paginator(queryset, limit)
            
            try:
                bills = paginator.page(page)
            except EmptyPage:
                bills = paginator.page(paginator.num_pages)
            except PageNotAnInteger:
                bills = paginator.page(1)
            
            serializer = BillsSerializer(bills, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Счета получены успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': bills.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'items_per_page': limit,
                    'has_next': bills.has_next(),
                    'has_previous': bills.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового счета",
        tags=['Bills'],
        request_body=BillsCreateSerializer,
        responses={201: 'Created', 400: 'Bad Request', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = BillsCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                bill = serializer.save()
                
                response_serializer = BillsSerializer(bill, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Счет создан успешно',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': get_error_message('validation_error'),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillsDetailAPIView(APIView):
    """
    Детали счета
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о счете по ID",
        tags=['Bills'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            bill = Bills.objects.filter(pk=pk, user=user).select_related('object_id', 'user').first()
            
            if not bill:
                return Response({
                    'success': False,
                    'message': 'Счет не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = BillsSerializer(bill, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Счет получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillsByObjectUserListAPIView(APIView):
    """
    Список счетов, отфильтрованных по пользователю объекта (не по создателю счета)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка счетов, отфильтрованных по пользователю объекта (UserObject.user)",
        tags=['Bills'],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            
            # Фильтруем по пользователю объекта (UserObject.user), а не по создателю счета
            queryset = Bills.objects.filter(object_id__user=user).select_related('object_id', 'user', 'object_id__user').order_by('-created_at')
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except ValueError:
                page = 1
                limit = 10
            
            paginator = Paginator(queryset, limit)
            
            try:
                bills = paginator.page(page)
            except EmptyPage:
                bills = paginator.page(paginator.num_pages)
            except PageNotAnInteger:
                bills = paginator.page(1)
            
            serializer = BillsSerializer(bills, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Счета получены успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': bills.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'items_per_page': limit,
                    'has_next': bills.has_next(),
                    'has_previous': bills.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
