from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Product, ProductImage, ProductSizes, FavoriteProduct, Category
from .serializers import (
    ProductSerializer, ProductCreateUpdateSerializer,
    ProductImageSerializer, FavoriteProductSerializer, CategorySerializer
)
from apps.v1.accounts.error_handlers import get_error_message
from apps.v1.documents.mixins import PaginationMixin


class CategoryListAPIView(APIView):
    """
    Список всех категорий
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех категорий",
        tags=['Categories'],
    )
    def get(self, request):
        try:
            categories = Category.objects.all()
            serializer = CategorySerializer(categories, many=True)
            return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': get_error_message('server_error'), 'errors': {'detail': str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductListCreateAPIView(PaginationMixin, APIView):
    """
    Список и создание продуктов
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех продуктов с фильтрацией по name и article, с пагинацией",
        tags=['Products'],
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description='Фильтр по категории',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'name',
                openapi.IN_QUERY,
                description='Фильтр по названию продукта',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'article',
                openapi.IN_QUERY,
                description='Фильтр по артикулу',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description='Номер страницы (начиная с 1)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Количество элементов на странице',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                'Успешное получение списка продуктов',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'pagination': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'current_page': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'total_items': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'has_next': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'has_previous': openapi.Schema(type=openapi.TYPE_BOOLEAN),
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
            queryset = Product.objects.filter(is_deleted=False)
            
            # Фильтрация по category
            category = request.query_params.get('category', None)
            if category:
                queryset = queryset.select_related("category").filter(category=category)
            else:
                queryset = queryset.select_related("category")
            
            # Фильтрация по name
            name = request.query_params.get('name', None)
            if name:
                queryset = queryset.filter(name__icontains=name)
            
            # Фильтрация по article
            article = request.query_params.get('article', None)
            if article:
                queryset = queryset.filter(article__icontains=article)
            
            # prefetch_related qo'shildi - N+1 query muammosini hal qilish uchun
            queryset = queryset.prefetch_related('productimage_set', 'productsizes_set')
            
            # Pagination Mixin ishlatilmoqda
            products_page, paginator = self.paginate_queryset(queryset, request)
            
            serializer = ProductSerializer(products_page, many=True, context={'request': request})
            
            return self.get_paginated_response(
                products_page,
                paginator,
                serializer.data,
                'Список продуктов получен успешно'
            )
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового продукта. Используйте multipart/form-data для загрузки изображений. Поле images_list может содержать несколько файлов.",
        tags=['Products'],
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_FORM, description='Название продукта', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('description', openapi.IN_FORM, description='Описание продукта', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('price', openapi.IN_FORM, description='Цена продукта', type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('category', openapi.IN_FORM, description='ID категории', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('stock', openapi.IN_FORM, description='Количество на складе', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('article', openapi.IN_FORM, description='Артикул', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_active', openapi.IN_FORM, description='Активен', type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('images_list', openapi.IN_FORM, description='Изображения для загрузки (можно загрузить несколько файлов, используйте images_list[0], images_list[1] и т.д. или просто images_list для нескольких файлов)', type=openapi.TYPE_FILE, required=False),
            openapi.Parameter('width', openapi.IN_FORM, description='Ширина (мм)', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('height', openapi.IN_FORM, description='Высота (мм)', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('depth', openapi.IN_FORM, description='Глубина (мм)', type=openapi.TYPE_INTEGER, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response(
                'Успешное создание продукта',
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
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            # DRF MultiPartParser уже объединяет request.data и request.FILES
            # Не копируем request.data, чтобы избежать ошибки pickling файлов
            # Передаем request.data напрямую, так как он уже содержит все данные
            serializer = ProductCreateUpdateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                product = serializer.save()
                
                # Возвращаем полные данные продукта
                response_serializer = ProductSerializer(product, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Продукт создан успешно',
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


class ProductDetailAPIView(APIView):
    """
    Детали, обновление и удаление продукта
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о продукте по ID",
        tags=['Products'],
        responses={
            200: openapi.Response(
                'Успешное получение продукта',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            404: openapi.Response('Продукт не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            product = Product.objects.filter(pk=pk, is_deleted=False).first()
            
            if not product:
                return Response({
                    'success': False,
                    'message': 'Продукт не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ProductSerializer(product, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Продукт получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление продукта (PUT - полное обновление)",
        tags=['Products'],
        request_body=ProductCreateUpdateSerializer,
        responses={200: 'OK', 400: 'Bad Request', 404: 'Not Found', 401: 'Unauthorized'},
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            product = Product.objects.filter(pk=pk, is_deleted=False).first()
            
            if not product:
                return Response({
                    'success': False,
                    'message': 'Продукт не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # DRF MultiPartParser уже объединяет request.data и request.FILES
            # Не копируем request.data, чтобы избежать ошибки pickling файлов
            # Передаем request.data напрямую, так как он уже содержит все данные
            serializer = ProductCreateUpdateSerializer(product, data=request.data, context={'request': request})
            
            if serializer.is_valid():
                product = serializer.save()
                
                # Возвращаем полные данные продукта
                response_serializer = ProductSerializer(product, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Продукт обновлен успешно',
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
        operation_description="Удаление продукта (мягкое удаление)",
        tags=['Products'],
        responses={
            200: openapi.Response('Успешное удаление продукта'),
            404: openapi.Response('Продукт не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            product = Product.objects.filter(pk=pk, is_deleted=False).first()
            
            if not product:
                return Response({
                    'success': False,
                    'message': 'Продукт не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Мягкое удаление
            product.is_deleted = True
            product.save()
            
            return Response({
                'success': True,
                'message': 'Продукт удален успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductImageDeleteAPIView(APIView):
    """
    Удаление изображения продукта по ID
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Удаление изображения продукта по ID",
        tags=['Products'],
        responses={
            200: openapi.Response('Успешное удаление изображения'),
            404: openapi.Response('Изображение не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, image_id):
        try:
            image = ProductImage.objects.filter(pk=image_id).first()
            
            if not image:
                return Response({
                    'success': False,
                    'message': 'Изображение не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            image.delete()
            
            return Response({
                'success': True,
                'message': 'Изображение удалено успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FavoriteProductListCreateAPIView(APIView):
    """
    Список и создание избранных продуктов
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка всех избранных продуктов текущего пользователя",
        tags=['Favorite Products'],
        responses={
            200: openapi.Response(
                'Успешное получение списка избранных продуктов',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
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
            user = request.user
            favorites = FavoriteProduct.objects.filter(user=user).select_related('product')
            serializer = FavoriteProductSerializer(favorites, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список избранных продуктов получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Добавление продукта в избранное",
        tags=['Favorite Products'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'product_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID продукта для добавления в избранное'
                ),
            },
            required=['product_id']
        ),
        responses={
            201: openapi.Response(
                'Успешное добавление в избранное',
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
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = FavoriteProductSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                favorite = serializer.save()
                
                response_serializer = FavoriteProductSerializer(favorite, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': 'Продукт добавлен в избранное',
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


class FavoriteProductDeleteAPIView(APIView):
    """
    Удаление избранного продукта
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Удаление избранного продукта по ID",
        tags=['Favorite Products'],
        responses={
            200: openapi.Response('Успешное удаление из избранного'),
            404: openapi.Response('Избранный продукт не найден'),
            403: openapi.Response('Доступ запрещен'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            user = request.user
            favorite = FavoriteProduct.objects.filter(pk=pk, user=user).first()
            
            if not favorite:
                return Response({
                    'success': False,
                    'message': 'Избранный продукт не найден или у вас нет доступа'
                }, status=status.HTTP_404_NOT_FOUND)
            
            favorite.delete()
            
            return Response({
                'success': True,
                'message': 'Продукт удален из избранного'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
