import os
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Storage, StorageFile
from .serializers import (
    StorageSerializer, StorageCreateSerializer, StorageUpdateSerializer,
    StorageFileSerializer, StorageFileCreateSerializer
)
from .error_handlers import get_error_message


class StorageListCreateAPIView(APIView):
    """
    Список и создание хранилищ текущего пользователя
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение списка хранилищ текущего пользователя",
        tags=['Storage'],
        responses={
            200: openapi.Response('Список хранилищ', StorageSerializer(many=True)),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            user = request.user
            storages = Storage.objects.filter(user=user).select_related('object', 'user').prefetch_related('files').order_by('-created_at')
            serializer = StorageSerializer(storages, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список хранилищ получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового хранилища с возможностью загрузки файлов",
        tags=['Storage'],
        manual_parameters=[
            openapi.Parameter(
                name='object_id',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=False,
                description='ID объекта (необязательно)'
            ),
            openapi.Parameter(
                name='name',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description='Название хранилища'
            ),
            openapi.Parameter(
                name='date',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True,
                description='Дата хранилища (формат: YYYY-MM-DD)'
            ),
            openapi.Parameter(
                name='files_data',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=False,
                description="Файлы (можно выбрать несколько)"
            ),
        ],
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response('Хранилище создано', StorageSerializer),
            400: openapi.Response('Ошибка валидации'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # Подготавливаем данные для serializer
            data = request.data.copy()
            
            serializer = StorageCreateSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                storage = serializer.save()
                
                # Получаем files_data из request.FILES и создаем StorageFile объекты
                files_data = request.FILES.getlist('files_data', [])
                import os
                for uploaded_file in files_data:
                    original_filename = uploaded_file.name
                    file_name_without_ext = os.path.splitext(original_filename)[0]
                    generated_name = file_name_without_ext if file_name_without_ext else original_filename
                    
                    # Создаем StorageFile объект
                    # Django автоматически обработает временный файл
                    storage_file = StorageFile(
                        storage=storage,
                        file=uploaded_file,
                        name=generated_name
                    )
                    storage_file.save()
                
                # Перезагружаем storage с файлами для корректного отображения
                storage.refresh_from_db()
                response_serializer = StorageSerializer(storage)
                
                return Response({
                    'success': True,
                    'message': 'Хранилище создано успешно',
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


class StorageDetailAPIView(APIView):
    """
    Детали, обновление и удаление хранилища
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о хранилище",
        tags=['Storage'],
        responses={
            200: openapi.Response('Хранилище', StorageSerializer),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            try:
                storage = Storage.objects.filter(user=user, pk=pk).select_related('object', 'user').prefetch_related('files').first()
            except Storage.DoesNotExist:
                storage = None
            
            if not storage:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageSerializer(storage)
            
            return Response({
                'success': True,
                'message': 'Хранилище получено успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление хранилища",
        tags=['Storage'],
        request_body=StorageUpdateSerializer,
        responses={
            200: openapi.Response('Хранилище обновлено', StorageSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=pk)
            except Storage.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageUpdateSerializer(storage, data=request.data)
            
            if serializer.is_valid():
                storage = serializer.save()
                response_serializer = StorageSerializer(storage)
                
                return Response({
                    'success': True,
                    'message': 'Хранилище обновлено успешно',
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
        operation_description="Частичное обновление хранилища",
        tags=['Storage'],
        request_body=StorageUpdateSerializer,
        responses={
            200: openapi.Response('Хранилище обновлено', StorageSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, pk):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=pk)
            except Storage.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageUpdateSerializer(storage, data=request.data, partial=True)
            
            if serializer.is_valid():
                storage = serializer.save()
                response_serializer = StorageSerializer(storage)
                
                return Response({
                    'success': True,
                    'message': 'Хранилище обновлено успешно',
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
        operation_description="Удаление хранилища",
        tags=['Storage'],
        responses={
            200: openapi.Response('Хранилище удалено'),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=pk)
            except Storage.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            storage.delete()
            
            return Response({
                'success': True,
                'message': 'Хранилище удалено успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StorageFileListCreateAPIView(APIView):
    """
    Список и создание файлов хранилища
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение списка файлов хранилища",
        tags=['Storage Files'],
        responses={
            200: openapi.Response('Список файлов', StorageFileSerializer(many=True)),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, storage_id):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=storage_id)
            except Storage.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            files = StorageFile.objects.filter(storage=storage).order_by('-created_at')
            serializer = StorageFileSerializer(files, many=True)
            
            return Response({
                'success': True,
                'message': 'Список файлов получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание файла для хранилища",
        tags=['Storage Files'],
        manual_parameters=[
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                description='Файл для загрузки',
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'name',
                openapi.IN_FORM,
                description='Название файла (необязательно)',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response('Файл создан', StorageFileSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Хранилище не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request, storage_id):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=storage_id)
            except Storage.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Хранилище не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageFileCreateSerializer(data=request.data)
            
            if serializer.is_valid():
                storage_file = serializer.save(storage=storage)
                response_serializer = StorageFileSerializer(storage_file)
                
                return Response({
                    'success': True,
                    'message': 'Файл создан успешно',
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


class StorageFileDetailAPIView(APIView):
    """
    Детали, обновление и удаление файла хранилища
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о файле",
        tags=['Storage Files'],
        responses={
            200: openapi.Response('Файл', StorageFileSerializer),
            404: openapi.Response('Файл не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, storage_id, file_id):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=storage_id)
                storage_file = StorageFile.objects.get(storage=storage, pk=file_id)
            except (Storage.DoesNotExist, StorageFile.DoesNotExist):
                return Response({
                    'success': False,
                    'message': 'Файл не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageFileSerializer(storage_file)
            
            return Response({
                'success': True,
                'message': 'Файл получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление файла хранилища",
        tags=['Storage Files'],
        manual_parameters=[
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                description='Новый файл (необязательно)',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'name',
                openapi.IN_FORM,
                description='Название файла (необязательно)',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        consumes=['multipart/form-data'],
        responses={
            200: openapi.Response('Файл обновлен', StorageFileSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Файл не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, storage_id, file_id):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=storage_id)
                storage_file = StorageFile.objects.get(storage=storage, pk=file_id)
            except (Storage.DoesNotExist, StorageFile.DoesNotExist):
                return Response({
                    'success': False,
                    'message': 'Файл не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = StorageFileCreateSerializer(storage_file, data=request.data, partial=True)
            
            if serializer.is_valid():
                storage_file = serializer.save()
                response_serializer = StorageFileSerializer(storage_file)
                
                return Response({
                    'success': True,
                    'message': 'Файл обновлен успешно',
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
        operation_description="Удаление файла хранилища",
        tags=['Storage Files'],
        responses={
            200: openapi.Response('Файл удален'),
            404: openapi.Response('Файл не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, storage_id, file_id):
        try:
            user = request.user
            try:
                storage = Storage.objects.get(user=user, pk=storage_id)
                storage_file = StorageFile.objects.get(storage=storage, pk=file_id)
            except (Storage.DoesNotExist, StorageFile.DoesNotExist):
                return Response({
                    'success': False,
                    'message': 'Файл не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            storage_file.delete()
            
            return Response({
                'success': True,
                'message': 'Файл удален успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

