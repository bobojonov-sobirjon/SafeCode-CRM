from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import UserObject
from .serializers import (
    UserObjectSerializer, UserObjectCreateSerializer, UserObjectUpdateSerializer,
    UserObjectWorkersAddSerializer, WorkerSerializer, UserObjectDocumentCreateSerializer
)
from apps.v1.accounts.error_handlers import get_error_message
from apps.v1.accounts.models import CustomUser
from django.contrib.auth.models import Group
from .utils import get_user_objects_queryset, apply_user_objects_filters


class UserObjectListCreateAPIView(APIView):
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
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except (ValueError, TypeError):
                page = 1
                limit = 10
            
            if limit > 100:
                limit = 100
            if limit < 1:
                limit = 10
            
            paginator = Paginator(queryset, limit)
            total_items = paginator.count
            total_pages = paginator.num_pages
            
            try:
                objects_page = paginator.page(page)
            except PageNotAnInteger:
                objects_page = paginator.page(1)
                page = 1
            except EmptyPage:
                objects_page = paginator.page(total_pages)
                page = total_pages
            
            serializer = UserObjectSerializer(objects_page, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список объектов получен успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_items': total_items,
                    'limit': limit,
                    'has_next': objects_page.has_next(),
                    'has_previous': objects_page.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
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
    Создание документов для объекта пользователя
    """
    permission_classes = [IsAuthenticated]
    
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
                description='Комментарий к документам',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'document_list',
                openapi.IN_FORM,
                description='Список документов (файлы). Можно загрузить несколько файлов, используя одно и то же имя поля document_list.',
                type=openapi.TYPE_FILE,
                required=True
            ),
        ],
        responses={201: 'Created', 400: 'Bad Request', 401: 'Unauthorized'},
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


class UserObjectAllListAPIView(APIView):
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
            queryset = UserObject.objects.filter(is_deleted=False).select_related('user')
            
            # Применяем фильтры
            queryset = apply_user_objects_filters(queryset, request)
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except (ValueError, TypeError):
                page = 1
                limit = 10
            
            if limit > 100:
                limit = 100
            if limit < 1:
                limit = 10
            
            paginator = Paginator(queryset, limit)
            total_items = paginator.count
            total_pages = paginator.num_pages
            
            try:
                objects_page = paginator.page(page)
            except PageNotAnInteger:
                objects_page = paginator.page(1)
                page = 1
            except EmptyPage:
                objects_page = paginator.page(total_pages)
                page = total_pages
            
            serializer = UserObjectSerializer(objects_page, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список всех объектов получен успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_items': total_items,
                    'limit': limit,
                    'has_next': objects_page.has_next(),
                    'has_previous': objects_page.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
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
