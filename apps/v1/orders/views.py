from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Order, DeliveryMethod, PaymentMethod
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    DeliveryMethodSerializer, DeliveryMethodCreateSerializer,
    PaymentMethodSerializer, PaymentMethodCreateSerializer
)
from apps.v1.accounts.error_handlers import get_error_message


class OrderListCreateAPIView(APIView):
    """
    Список и создание заказов текущего пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="""
        Получение списка всех заказов текущего пользователя (my orders).
        
        **Описание:**
        - Возвращает список всех заказов, созданных текущим авторизованным пользователем
        - Заказы отсортированы по дате создания (новые первыми)
        - Каждый заказ включает полную информацию: номер заказа, адрес доставки, статус оплаты, способ доставки и оплаты, список товаров, общую стоимость
        
        **Доступ:**
        - Только авторизованные пользователи
        - Пользователь видит только свои заказы
        
        **Ответ включает:**
        - order_number: Уникальный номер заказа (автоматически генерируется при создании)
        - user: Информация о пользователе
        - city, street, house, apartment, postal_index: Адрес доставки
        - status: Статус оплаты (pending, paid, failed, cancelled)
        - delivery_method: Способ доставки с ценой
        - payment_method: Способ оплаты
        - total_price: Общая стоимость заказа (включая стоимость товаров и доставки)
        - items: Список товаров в заказе с количеством
        - created_at, updated_at: Даты создания и обновления
        """,
        tags=['Orders'],
        responses={
            200: openapi.Response(
                'Список заказов получен успешно',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
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
            orders = Order.objects.filter(user=user).select_related(
                'user', 'delivery_method', 'payment_method'
            ).prefetch_related('items__product').order_by('-created_at')
            
            serializer = OrderSerializer(orders, many=True)
            
            return Response({
                'success': True,
                'message': 'Список заказов получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="""
        Создание нового заказа.
        
        **Описание:**
        Создает новый заказ для текущего авторизованного пользователя. Номер заказа генерируется автоматически (формат: 4 заглавные буквы + 6 цифр, например: ABCD123456).
        
        **Обязательные поля:**
        - city: Город доставки (строка, максимум 255 символов)
        - street: Улица доставки (строка, максимум 255 символов)
        - house: Номер дома (строка, максимум 50 символов)
        - items: Список товаров в заказе (массив, минимум 1 товар)
          - product_id: ID продукта (целое число, обязательное)
          - quantity: Количество товара (целое число, обязательное, минимум 1)
        
        **Необязательные поля:**
        - apartment: Номер квартиры (строка, максимум 50 символов)
        - postal_index: Почтовый индекс (строка, максимум 20 символов)
        - delivery_method_id: ID способа доставки (целое число)
        - payment_method_id: ID способа оплаты (целое число)
        
        **Автоматический расчет:**
        - order_number: Генерируется автоматически при создании заказа
        - total_price: Рассчитывается автоматически как сумма:
          * Стоимость всех товаров (цена товара × количество)
          * Стоимость доставки (если указан delivery_method)
        
        **Пример запроса:**
        ```json
        {
            "city": "Москва",
            "street": "Ленина",
            "house": "10",
            "apartment": "5",
            "postal_index": "123456",
            "delivery_method_id": 1,
            "payment_method_id": 1,
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 2, "quantity": 1}
            ]
        }
        ```
        
        **Валидация:**
        - Все обязательные поля должны быть заполнены
        - product_id должен существовать и продукт должен быть активным
        - delivery_method_id и payment_method_id должны существовать (если указаны)
        - items должен содержать минимум один товар
        """,
        tags=['Orders'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'city': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Город доставки',
                    max_length=255,
                    example='Москва'
                ),
                'street': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Улица доставки',
                    max_length=255,
                    example='Ленина'
                ),
                'house': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Номер дома',
                    max_length=50,
                    example='10'
                ),
                'apartment': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Номер квартиры (необязательно)',
                    max_length=50,
                    example='5'
                ),
                'postal_index': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Почтовый индекс (необязательно)',
                    max_length=20,
                    example='123456'
                ),
                'delivery_method_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID способа доставки (необязательно)',
                    example=1
                ),
                'payment_method_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID способа оплаты (необязательно)',
                    example=1
                ),
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='Список товаров в заказе (минимум 1 товар)',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'product_id': openapi.Schema(
                                type=openapi.TYPE_INTEGER,
                                description='ID продукта',
                                example=1
                            ),
                            'quantity': openapi.Schema(
                                type=openapi.TYPE_INTEGER,
                                description='Количество товара',
                                example=2,
                                minimum=1
                            ),
                        },
                        required=['product_id', 'quantity']
                    ),
                    min_items=1
                ),
            },
            required=['city', 'street', 'house', 'items']
        ),
        responses={
            201: openapi.Response(
                'Заказ успешно создан',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
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
            serializer = OrderCreateSerializer(data=request.data, context={'request': request})
            
            if serializer.is_valid():
                order = serializer.save()
                response_serializer = OrderSerializer(order)
                
                return Response({
                    'success': True,
                    'message': 'Заказ создан успешно',
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


class OrderDetailAPIView(APIView):
    """
    Детали заказа
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="""
        Получение детальной информации о заказе по ID.
        
        **Описание:**
        Возвращает полную информацию о конкретном заказе по его ID. Пользователь может получить доступ только к своим заказам.
        
        **Параметры:**
        - pk (path parameter): ID заказа (целое число)
        
        **Ответ включает:**
        - id: Уникальный идентификатор заказа
        - order_number: Номер заказа (автоматически сгенерированный при создании)
        - user: Информация о пользователе, создавшем заказ
          - id: ID пользователя
          - email: Email пользователя
          - first_name: Имя пользователя
          - last_name: Фамилия пользователя
        - city: Город доставки
        - street: Улица доставки
        - house: Номер дома
        - apartment: Номер квартиры (если указан)
        - postal_index: Почтовый индекс (если указан)
        - status: Статус оплаты заказа
          - pending: Ожидание оплаты
          - paid: Оплачен
          - failed: Ошибка оплаты
          - cancelled: Отменен
        - delivery_method: Информация о способе доставки (если указан)
          - id: ID способа доставки
          - name: Название способа доставки
          - details: Детали доставки
          - price: Стоимость доставки
        - payment_method: Информация о способе оплаты (если указан)
          - id: ID способа оплаты
          - name: Название способа оплаты
          - details: Детали оплаты
        - total_price: Общая стоимость заказа (включая товары и доставку)
        - items: Список товаров в заказе
          - id: ID элемента заказа
          - product: Информация о продукте
            - id: ID продукта
            - name: Название продукта
            - price: Цена продукта
            - article: Артикул продукта
          - quantity: Количество товара
          - created_at: Дата создания элемента заказа
        - created_at: Дата создания заказа
        - updated_at: Дата последнего обновления заказа
        
        **Ошибки:**
        - 404: Заказ не найден или не принадлежит текущему пользователю
        - 401: Требуется авторизация
        """,
        tags=['Orders'],
        manual_parameters=[
            openapi.Parameter(
                'pk',
                openapi.IN_PATH,
                description='ID заказа',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                'Заказ получен успешно',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            404: openapi.Response('Заказ не найден или не принадлежит текущему пользователю'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            user = request.user
            try:
                order = Order.objects.filter(user=user, pk=pk).select_related(
                    'user', 'delivery_method', 'payment_method'
                ).prefetch_related('items__product').first()
            except Order.DoesNotExist:
                order = None
            
            if not order:
                return Response({
                    'success': False,
                    'message': 'Заказ не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = OrderSerializer(order)
            
            return Response({
                'success': True,
                'message': 'Заказ получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
