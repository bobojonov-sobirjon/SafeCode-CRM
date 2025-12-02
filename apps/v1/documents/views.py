from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import JournalsAndActs, Bills
from .serializers import (
    JournalsAndActsSerializer, JournalsAndActsCreateSerializer, JournalsAndActsUpdateSerializer,
    BillsSerializer, BillsCreateSerializer, BillsUpdateSerializer
)
from apps.v1.accounts.error_handlers import get_error_message
from apps.v1.user_objects.models import UserObject
from .mixins import PaginationMixin


class JournalsAndActsListCreateAPIView(PaginationMixin, APIView):
    """
    Список и создание журналов и актов
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
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
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            queryset = JournalsAndActs.objects.filter(user=user)\
                .select_related('object_id', 'user')\
                .prefetch_related('journal_and_act_documents')\
                .order_by('-created_at')
            
            # Pagination Mixin ishlatilmoqda
            journals_and_acts, paginator = self.paginate_queryset(queryset, request)
            
            serializer = JournalsAndActsSerializer(journals_and_acts, many=True, context={'request': request})
            
            return self.get_paginated_response(
                journals_and_acts, 
                paginator, 
                serializer.data, 
                'Журналы и акты получены успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового журнала/акта с документами. Поле type может принимать значения: 'estimate' (Смета), 'act' (Акт), 'form' (Форма). Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов.",
        tags=['Journals and Acts'],
        manual_parameters=[
            openapi.Parameter('object_id', openapi.IN_FORM, description='ID объекта пользователя', type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('type', openapi.IN_FORM, description='Тип: estimate (Смета), act (Акт), form (Форма)', type=openapi.TYPE_STRING, enum=['estimate', 'act', 'form'], required=False),
            openapi.Parameter('date', openapi.IN_FORM, description='Дата (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('document_list', openapi.IN_FORM, description='Файлы для загрузки (можно загрузить несколько файлов, используйте document_list[0], document_list[1] и т.д.)', type=openapi.TYPE_FILE, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={201: 'Created', 400: 'Bad Request', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Передаем request.data и request.FILES в контекст для обработки multipart/form-data
            serializer = JournalsAndActsCreateSerializer(
                data=request.data,
                context={'request': request, 'files': request.FILES}
            )
            
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
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о журнале/акте по ID",
        tags=['Journals and Acts'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            journal_or_act = JournalsAndActs.objects.filter(pk=pk, user=user)\
                .select_related('object_id', 'user')\
                .prefetch_related('journal_and_act_documents')\
                .first()
            
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
    
    @swagger_auto_schema(
        operation_description="Обновление журнала/акта с документами. Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов. Если передаете document_list, старые документы будут удалены и заменены новыми.",
        tags=['Journals and Acts'],
        manual_parameters=[
            openapi.Parameter('object_id', openapi.IN_FORM, description='ID объекта пользователя', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('type', openapi.IN_FORM, description='Тип: estimate (Смета), act (Акт), form (Форма)', type=openapi.TYPE_STRING, enum=['estimate', 'act', 'form'], required=False),
            openapi.Parameter('date', openapi.IN_FORM, description='Дата', type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, required=False),
            openapi.Parameter('document_list', openapi.IN_FORM, description='Файлы для загрузки (можно загрузить несколько файлов). Если передаете, старые документы будут удалены.', type=openapi.TYPE_FILE, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 404: 'Not Found'},
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            user = request.user
            journal_or_act = JournalsAndActs.objects.filter(pk=pk, user=user).first()
            
            if not journal_or_act:
                return Response({
                    'success': False,
                    'message': 'Журнал/акт не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = JournalsAndActsUpdateSerializer(
                journal_or_act,
                data=request.data,
                context={'request': request, 'files': request.FILES},
                partial=True
            )
            
            if serializer.is_valid():
                updated_journal_or_act = serializer.save()
                
                response_serializer = JournalsAndActsSerializer(updated_journal_or_act, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Журнал/акт обновлен успешно',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            
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
    
    def patch(self, request, pk):
        """PATCH использует тот же метод, что и PUT"""
        return self.put(request, pk)


class BillsListCreateAPIView(PaginationMixin, APIView):
    """
    Список и создание счетов
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
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
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            queryset = Bills.objects.filter(user=user)\
                .select_related('object_id', 'user')\
                .prefetch_related('bill_documents')\
                .order_by('-created_at')
            
            # Pagination Mixin ishlatilmoqda
            bills, paginator = self.paginate_queryset(queryset, request)
            
            serializer = BillsSerializer(bills, many=True, context={'request': request})
            
            return self.get_paginated_response(
                bills, 
                paginator, 
                serializer.data, 
                'Счета получены успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового счета с документами. Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов.",
        tags=['Bills'],
        manual_parameters=[
            openapi.Parameter('object_id', openapi.IN_FORM, description='ID объекта пользователя', type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('comment', openapi.IN_FORM, description='Комментарий', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('price', openapi.IN_FORM, description='Цена', type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('status', openapi.IN_FORM, description='Статус: pending, paid, cancelled', type=openapi.TYPE_STRING, enum=['pending', 'paid', 'cancelled'], required=False),
            openapi.Parameter('document_list', openapi.IN_FORM, description='Файлы для загрузки (можно загрузить несколько файлов, используйте document_list[0], document_list[1] и т.д.)', type=openapi.TYPE_FILE, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={201: 'Created', 400: 'Bad Request', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Передаем request.data и request.FILES в контекст для обработки multipart/form-data
            serializer = BillsCreateSerializer(
                data=request.data,
                context={'request': request, 'files': request.FILES}
            )
            
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
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о счете по ID",
        tags=['Bills'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            bill = Bills.objects.filter(pk=pk, user=user)\
                .select_related('object_id', 'user')\
                .prefetch_related('bill_documents')\
                .first()
            
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
    
    @swagger_auto_schema(
        operation_description="Обновление счета с документами. Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов. Если передаете document_list, старые документы будут удалены и заменены новыми.",
        tags=['Bills'],
        manual_parameters=[
            openapi.Parameter('object_id', openapi.IN_FORM, description='ID объекта пользователя', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('comment', openapi.IN_FORM, description='Комментарий', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('price', openapi.IN_FORM, description='Цена', type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('status', openapi.IN_FORM, description='Статус: pending, paid, cancelled', type=openapi.TYPE_STRING, enum=['pending', 'paid', 'cancelled'], required=False),
            openapi.Parameter('document_list', openapi.IN_FORM, description='Файлы для загрузки (можно загрузить несколько файлов). Если передаете, старые документы будут удалены.', type=openapi.TYPE_FILE, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 404: 'Not Found'},
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            user = request.user
            bill = Bills.objects.filter(pk=pk, user=user).first()
            
            if not bill:
                return Response({
                    'success': False,
                    'message': 'Счет не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = BillsUpdateSerializer(
                bill,
                data=request.data,
                context={'request': request, 'files': request.FILES},
                partial=True
            )
            
            if serializer.is_valid():
                updated_bill = serializer.save()
                
                response_serializer = BillsSerializer(updated_bill, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Счет обновлен успешно',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            
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
    
    def patch(self, request, pk):
        """PATCH использует тот же метод, что и PUT"""
        return self.put(request, pk)


class JournalsAndActsByObjectUserListAPIView(PaginationMixin, APIView):
    """
    Список журналов и актов, отфильтрованных по пользователю объекта (не по создателю)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка журналов и актов, отфильтрованных по пользователю объекта (UserObject.user)",
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
            
            # Фильтруем по пользователю объекта (UserObject.user), а не по создателю
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            queryset = JournalsAndActs.objects.filter(object_id__user=user)\
                .select_related('object_id', 'user', 'object_id__user')\
                .prefetch_related('journal_and_act_documents')\
                .order_by('-created_at')
            
            # Pagination Mixin ishlatilmoqda
            journals_and_acts, paginator = self.paginate_queryset(queryset, request)
            
            serializer = JournalsAndActsSerializer(journals_and_acts, many=True, context={'request': request})
            
            return self.get_paginated_response(
                journals_and_acts, 
                paginator, 
                serializer.data, 
                'Журналы и акты получены успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillsByObjectUserListAPIView(PaginationMixin, APIView):
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
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            queryset = Bills.objects.filter(object_id__user=user)\
                .select_related('object_id', 'user', 'object_id__user')\
                .prefetch_related('bill_documents')\
                .order_by('-created_at')
            
            # Pagination Mixin ishlatilmoqda
            bills, paginator = self.paginate_queryset(queryset, request)
            
            serializer = BillsSerializer(bills, many=True, context={'request': request})
            
            return self.get_paginated_response(
                bills, 
                paginator, 
                serializer.data, 
                'Счета получены успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
