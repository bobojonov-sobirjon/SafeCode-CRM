from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Product, ProductImage, ProductSizes, FavoriteProduct, Category
from .serializers import (
    ProductSerializer, ProductCreateUpdateSerializer,
    ProductImageSerializer, FavoriteProductSerializer, CategorySerializer
)
from apps.v1.accounts.error_handlers import get_error_message


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


class ProductListCreateAPIView(APIView):
    """
    Список и создание продуктов
    """
    permission_classes = [AllowAny]
    
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
            
            # Фильтрация по name
            name = request.query_params.get('name', None)
            if name:
                queryset = queryset.filter(name__icontains=name)
            
            # Фильтрация по article
            article = request.query_params.get('article', None)
            if article:
                queryset = queryset.filter(article__icontains=article)
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except (ValueError, TypeError):
                page = 1
                limit = 10
            
            # Ограничиваем максимальный limit
            if limit > 100:
                limit = 100
            if limit < 1:
                limit = 10
            
            paginator = Paginator(queryset, limit)
            total_items = paginator.count
            total_pages = paginator.num_pages
            
            try:
                products_page = paginator.page(page)
            except PageNotAnInteger:
                products_page = paginator.page(1)
                page = 1
            except EmptyPage:
                products_page = paginator.page(total_pages)
                page = total_pages
            
            serializer = ProductSerializer(products_page, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Список продуктов получен успешно',
                'data': serializer.data,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_items': total_items,
                    'limit': limit,
                    'has_next': products_page.has_next(),
                    'has_previous': products_page.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Создание нового продукта. Используйте multipart/form-data для загрузки изображений. Поле images_list может содержать несколько файлов.",
        tags=['Products'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название продукта'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание продукта'),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER, description='Цена продукта'),
                'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID категории'),
                'stock': openapi.Schema(type=openapi.TYPE_INTEGER, description='Количество на складе'),
                'article': openapi.Schema(type=openapi.TYPE_STRING, description='Артикул'),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Активен'),
                'images_list': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_FILE),
                    description='Список изображений (файлы)'
                ),
                'width': openapi.Schema(type=openapi.TYPE_INTEGER, description='Ширина'),
                'height': openapi.Schema(type=openapi.TYPE_INTEGER, description='Высота'),
                'depth': openapi.Schema(type=openapi.TYPE_INTEGER, description='Глубина'),
            }
        ),
        consumes=['application/json'],
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
            # Объединяем данные из request.data и request.FILES для form-data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            serializer = ProductCreateUpdateSerializer(data=data, context={'request': request})
            
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
            
            # Объединяем данные из request.data и request.FILES для form-data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            serializer = ProductCreateUpdateSerializer(product, data=data, context={'request': request})
            
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
