from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import UserObject, UserObjectDocuments, UserObjectDocuments
from .serializers import (
    UserObjectSerializer, UserObjectCreateSerializer, UserObjectUpdateSerializer,
    UserObjectWorkersAddSerializer, WorkerSerializer, UserObjectDocumentCreateSerializer,
    UserObjectDocumentSerializer
)
from apps.v1.accounts.error_handlers import get_error_message
from apps.v1.accounts.models import CustomUser
from django.contrib.auth.models import Group
from .utils import get_user_objects_queryset, apply_user_objects_filters
from apps.v1.documents.mixins import PaginationMixin


class UserObjectListCreateAPIView(PaginationMixin, APIView):
    """
    Список и создание объектов пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка объектов текущего пользователя с фильтрацией и пагинацией",
        tags=['User Objects'],
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description='Фильтр по названию', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('address', openapi.IN_QUERY, description='Фильтр по адресу', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('size', openapi.IN_QUERY, description='Фильтр по размеру', type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('number_of_fire_extinguishing_systems', openapi.IN_QUERY, description='Фильтр по количеству систем', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('status', openapi.IN_QUERY, description='Фильтр по статусу', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            
            # Получаем queryset в зависимости от роли пользователя
            queryset = get_user_objects_queryset(user)
            
            # Применяем фильтры
            queryset = apply_user_objects_filters(queryset, request)
            
            # Pagination Mixin ishlatilmoqda
            objects_page, paginator = self.paginate_queryset(queryset, request)
            
            serializer = UserObjectSerializer(objects_page, many=True, context={'request': request})
            
            return self.get_paginated_response(
                objects_page,
                paginator,
                serializer.data,
                'Список объектов получен успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового объекта пользователя (только для группы Заказчик)",
        tags=['User Objects'],
        request_body=UserObjectCreateSerializer,
        responses={201: 'Created', 400: 'Bad Request', 403: 'Forbidden', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Проверка группы Заказчик
            user = request.user
            if not user.groups.filter(name='Заказчик').exists():
                return Response({
                    'success': False,
                    'message': 'Только пользователи с группой "Заказчик" могут создавать объекты'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = UserObjectCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                user_object = serializer.save()
                
                response_serializer = UserObjectSerializer(user_object, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Объект создан успешно',
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


class UserObjectDocumentCreateAPIView(APIView):
    """
    Создание документов для объекта пользователя.
    Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Создание документов для объекта пользователя. Файлы загружаются через form-data. Используйте multipart/form-data для загрузки файлов.",
        tags=['User Objects'],
        manual_parameters=[
            openapi.Parameter(
                'user_object_id',
                openapi.IN_FORM,
                description='ID объекта пользователя',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'comment',
                openapi.IN_FORM,
                description='Комментарий (необязательно)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'document_list',
                openapi.IN_FORM,
                description='Файлы для загрузки (можно загрузить несколько файлов, используйте document_list[0], document_list[1] и т.д.)',
                type=openapi.TYPE_FILE,
                required=True
            ),
        ],
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response(
                'Успешное создание документов',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'document_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'items_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Передаем request.data и request.FILES в контекст для обработки multipart/form-data
            serializer = UserObjectDocumentCreateSerializer(
                data=request.data,
                context={'request': request, 'files': request.FILES}
            )
            
            if serializer.is_valid():
                result = serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Документы успешно созданы',
                    'data': {
                        'document_id': result['user_object_document'].id,
                        'items_count': len(result['document_items'])
                    }
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


class UserObjectAllListAPIView(PaginationMixin, APIView):
    """
    Список всех объектов пользователей (для админов)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех объектов пользователей с фильтрацией и пагинацией",
        tags=['User Objects'],
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description='Фильтр по названию', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('address', openapi.IN_QUERY, description='Фильтр по адресу', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('size', openapi.IN_QUERY, description='Фильтр по размеру', type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('number_of_fire_extinguishing_systems', openapi.IN_QUERY, description='Фильтр по количеству систем', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('status', openapi.IN_QUERY, description='Фильтр по статусу', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            queryset = UserObject.objects.filter(is_deleted=False)\
                .select_related('user')\
                .prefetch_related('user_object_workers', 'user_object_documents')
            
            # Применяем фильтры
            queryset = apply_user_objects_filters(queryset, request)
            
            # Pagination Mixin ishlatilmoqda
            objects_page, paginator = self.paginate_queryset(queryset, request)
            
            serializer = UserObjectSerializer(objects_page, many=True, context={'request': request})
            
            return self.get_paginated_response(
                objects_page,
                paginator,
                serializer.data,
                'Список всех объектов получен успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserObjectDeletedListAPIView(APIView):
    """
    Список удаленных объектов пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка удаленных объектов текущего пользователя",
        tags=['User Objects'],
        responses={200: 'OK', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            queryset = UserObject.objects.filter(user=user, is_deleted=True).select_related('user')
            serializer = UserObjectSerializer(queryset, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список удаленных объектов получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserObjectDetailAPIView(APIView):
    """
    Детали, обновление и удаление объекта пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации об объекте по ID",
        tags=['User Objects'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            user_object = UserObject.objects.filter(pk=pk, is_deleted=False).select_related('user').first()
            
            if not user_object:
                return Response({
                    'success': False,
                    'message': 'Объект не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Проверяем доступ: Заказчик видит только свои объекты, другие роли - где они работники
            is_customer = user.groups.filter(name='Заказчик').exists()
            if is_customer:
                if user_object.user != user:
                    return Response({
                        'success': False,
                        'message': 'Объект не найден'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Для других ролей проверяем, является ли пользователь работником этого объекта
                from .models import UserObjectWorkers
                if not UserObjectWorkers.objects.filter(user_object=user_object, user=user).exists():
                    return Response({
                        'success': False,
                        'message': 'Объект не найден'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = UserObjectSerializer(user_object, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Объект получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление объекта пользователя (PUT - полное обновление)",
        tags=['User Objects'],
        request_body=UserObjectUpdateSerializer,
        responses={200: 'OK', 400: 'Bad Request', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            user = request.user
            user_object = UserObject.objects.filter(pk=pk, is_deleted=False).select_related('user').first()
            
            if not user_object:
                return Response({
                    'success': False,
                    'message': 'Объект не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Проверяем доступ: только Заказчик может обновлять свои объекты
            is_customer = user.groups.filter(name='Заказчик').exists()
            if not is_customer or user_object.user != user:
                return Response({
                    'success': False,
                    'message': 'Объект не найден или у вас нет прав на обновление'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = UserObjectUpdateSerializer(user_object, data=request.data)
            
            if serializer.is_valid():
                user_object = serializer.save()
                
                response_serializer = UserObjectSerializer(user_object, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Объект обновлен успешно',
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
    
    @swagger_auto_schema(
        operation_description="Частичное обновление объекта пользователя (PATCH)",
        tags=['User Objects'],
        request_body=UserObjectUpdateSerializer,
        responses={200: 'OK', 400: 'Bad Request', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def patch(self, request, pk):
        try:
            user = request.user
            user_object = UserObject.objects.filter(pk=pk, is_deleted=False).select_related('user').first()
            
            if not user_object:
                return Response({
                    'success': False,
                    'message': 'Объект не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Проверяем доступ: только Заказчик может обновлять свои объекты
            is_customer = user.groups.filter(name='Заказчик').exists()
            if not is_customer or user_object.user != user:
                return Response({
                    'success': False,
                    'message': 'Объект не найден или у вас нет прав на обновление'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = UserObjectUpdateSerializer(user_object, data=request.data, partial=True)
            
            if serializer.is_valid():
                user_object = serializer.save()
                
                response_serializer = UserObjectSerializer(user_object, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Объект обновлен успешно',
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
    
    @swagger_auto_schema(
        operation_description="Удаление объекта пользователя (мягкое удаление)",
        tags=['User Objects'],
        responses={200: 'OK', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            user = request.user
            user_object = UserObject.objects.filter(pk=pk, is_deleted=False).select_related('user').first()
            
            if not user_object:
                return Response({
                    'success': False,
                    'message': 'Объект не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Проверяем доступ: только Заказчик может удалять свои объекты
            is_customer = user.groups.filter(name='Заказчик').exists()
            if not is_customer or user_object.user != user:
                return Response({
                    'success': False,
                    'message': 'Объект не найден или у вас нет прав на удаление'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Мягкое удаление
            user_object.is_deleted = True
            user_object.save()
            
            return Response({
                'success': True,
                'message': 'Объект удален успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserObjectWorkersAddAPIView(APIView):
    """
    Добавление работников к объекту пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Добавление работников к объекту пользователя. Статус объекта изменится на PENDING.",
        tags=['User Objects'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_objects_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID объекта пользователя'
                ),
                'worker_list': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='Список ID пользователей (работников)'
                ),
            },
            required=['user_objects_id', 'worker_list']
        ),
        responses={
            201: openapi.Response(
                'Успешное добавление работников',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            400: openapi.Response('Ошибка валидации данных'),
            404: openapi.Response('Объект не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = UserObjectWorkersAddSerializer(data=request.data)
            
            if serializer.is_valid():
                result = serializer.save()
                user_object = result['user_object']
                workers = result['workers']
                
                # Возвращаем информацию об объекте
                user_object_serializer = UserObjectSerializer(user_object)
                
                return Response({
                    'success': True,
                    'message': f'Добавлено {len(workers)} работников. Статус объекта изменен на PENDING.',
                    'data': {
                        'user_object': user_object_serializer.data,
                        'added_workers_count': len(workers)
                    }
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


class WorkersListAPIView(APIView):
    """
    Получение списка работников, сгруппированных по ролям
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Получение списка работников, сгруппированных по ролям (Дежурный инженер, Инспектор МЧС, Менеджер, Обслуживающий инженер, Исполнителя)",
        tags=['User Objects'],
        responses={
            200: openapi.Response(
                'Успешное получение списка работников',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'Дежурный инженер': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'Инспектор МЧС': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'Менеджер': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'Обслуживающий инженер': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                                'Исполнителя': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                                ),
                            }
                        ),
                    }
                )
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            # Список ролей для получения работников
            worker_roles = [
                'Дежурный инженер',
                'Инспектор МЧС',
                'Менеджер',
                'Обслуживающий инженер',
                'Исполнителя'
            ]
            
            # Словарь для хранения работников по ролям
            workers_by_role = {}
            
            # Получаем работников для каждой роли
            for role_name in worker_roles:
                try:
                    group = Group.objects.get(name=role_name)
                    # Получаем всех активных пользователей этой группы
                    users = CustomUser.objects.filter(
                        groups=group,
                        is_active=True
                    ).order_by('first_name', 'last_name')
                    
                    # Сериализуем пользователей
                    serializer = WorkerSerializer(users, many=True)
                    workers_by_role[role_name] = serializer.data
                except Group.DoesNotExist:
                    # Если группа не существует, возвращаем пустой список
                    workers_by_role[role_name] = []
            
            return Response({
                'success': True,
                'message': 'Список работников получен успешно',
                    'data': workers_by_role
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserObjectStatusUpdateAPIView(APIView):
    """
    Обновление статуса объекта пользователя (закрытие проекта)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Обновление статуса объекта пользователя. Доступно только для администраторов. Статусы: completed, on_hold, cancelled",
        tags=['User Objects'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'object_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID объекта пользователя'
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['completed', 'on_hold', 'cancelled'],
                    description='Новый статус объекта'
                ),
            },
            required=['object_id', 'status']
        ),
        responses={
            200: openapi.Response('Успешное обновление статуса'),
            400: openapi.Response('Ошибка валидации данных'),
            403: openapi.Response('Доступ запрещен'),
            404: openapi.Response('Объект не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            user = request.user
            
            # Проверяем, является ли пользователь администратором
            if not user.groups.filter(name='Администратор').exists():
                return Response({
                    'success': False,
                    'message': 'Только администраторы могут изменять статус объекта'
                }, status=status.HTTP_403_FORBIDDEN)
            
            object_id = request.data.get('object_id')
            new_status = request.data.get('status')
            
            if not object_id:
                return Response({
                    'success': False,
                    'message': 'object_id обязателен'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not new_status:
                return Response({
                    'success': False,
                    'message': 'status обязателен'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем валидность статуса
            valid_statuses = [
                UserObject.Status.COMPLETED,
                UserObject.Status.ON_HOLD,
                UserObject.Status.CANCELLED
            ]
            
            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'message': f'Неверный статус. Допустимые значения: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Получаем объект
            try:
                user_object = UserObject.objects.get(id=object_id, is_deleted=False)
            except UserObject.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Объект не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Обновляем статус
            old_status = user_object.status
            user_object.status = new_status
            user_object.save()
            
            # Отправляем уведомление создателю объекта
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            from apps.v1.notification.models import Notification
            
            channel_layer = get_channel_layer()
            
            # Статусы на русском
            status_messages = {
                UserObject.Status.COMPLETED: 'Завершенный',
                UserObject.Status.ON_HOLD: 'На паузе',
                UserObject.Status.CANCELLED: 'Отмененный'
            }
            
            status_text = status_messages.get(new_status, new_status)
            message = f"Администратор изменил статус объекта '{user_object.name}' на {status_text}"
            
            # Создаем уведомление
            notification = Notification.objects.create(
                recipient=user_object.user,
                actor=user,
                verb="object_status_changed",
                message=message,
                user_object=user_object,
                category='user_object'
            )
            
            # Отправляем через WebSocket
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"user_{user_object.user.id}",
                    {
                        "type": "notification_message",
                        "notification": {
                            "id": notification.id,
                            "message": message,
                            "verb": "object_status_changed",
                            "actor": {
                                "id": user.id,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                            },
                            "user_object": {
                                "id": user_object.id,
                                "name": user_object.name,
                            },
                            "created_at": notification.created_at.isoformat(),
                            "is_read": notification.is_read,
                        }
                    }
                )
            
            # Возвращаем обновленный объект
            serializer = UserObjectSerializer(user_object, context={'request': request})
            
            return Response({
                'success': True,
                'message': f'Статус объекта успешно изменен на {status_text}',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserObjectDocumentsListAPIView(APIView):
    """
    Список документов объектов пользователя (фильтруется по текущему пользователю)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка документов объектов пользователя текущего пользователя с пагинацией. Возвращает: object (информация об объекте), comment, file_datas (список файлов с URL), created_at",
        tags=['User Objects'],
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
            queryset = UserObjectDocuments.objects.filter(user=user)\
                .select_related('user_object', 'user')\
                .prefetch_related('user_object_document_items')\
                .order_by('-created_at')
            
            # Pagination Mixin ishlatilmoqda
            documents, paginator = self.paginate_queryset(queryset, request)
            
            serializer = UserObjectDocumentSerializer(documents, many=True, context={'request': request})
            
            return self.get_paginated_response(
                documents,
                paginator,
                serializer.data,
                'Документы получены успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)