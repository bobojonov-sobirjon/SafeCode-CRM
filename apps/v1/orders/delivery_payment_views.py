from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import DeliveryMethod, PaymentMethod
from .serializers import (
    DeliveryMethodSerializer, DeliveryMethodCreateSerializer,
    PaymentMethodSerializer, PaymentMethodCreateSerializer
)
from apps.v1.accounts.error_handlers import get_error_message


class DeliveryMethodListCreateAPIView(APIView):
    """
    Список и создание способов доставки
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="""
        Получение списка всех способов доставки.
        
        **Описание:**
        Возвращает список всех доступных способов доставки. Способы доставки отсортированы по дате создания (новые первыми).
        
        **Ответ включает:**
        - id: Уникальный идентификатор способа доставки
        - name: Название способа доставки
        - details: Детали способа доставки
        - price: Стоимость доставки
        - created_at: Дата создания
        - updated_at: Дата обновления
        """,
        tags=['Delivery Methods'],
        responses={
            200: openapi.Response(
                'Список способов доставки',
                DeliveryMethodSerializer(many=True)
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            delivery_methods = DeliveryMethod.objects.all().order_by('-created_at')
            serializer = DeliveryMethodSerializer(delivery_methods, many=True)
            
            return Response({
                'success': True,
                'message': 'Список способов доставки получен успешно',
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
        Создание нового способа доставки.
        
        **Описание:**
        Создает новый способ доставки с указанными параметрами.
        
        **Обязательные поля:**
        - name: Название способа доставки (строка, максимум 255 символов)
        
        **Необязательные поля:**
        - details: Детали способа доставки (текст)
        - price: Стоимость доставки (десятичное число, по умолчанию 0)
        
        **Пример запроса:**
        ```json
        {
            "name": "Курьерская доставка",
            "details": "Доставка курьером в течение 1-2 дней",
            "price": 500.00
        }
        ```
        """,
        tags=['Delivery Methods'],
        request_body=DeliveryMethodCreateSerializer,
        responses={
            201: openapi.Response('Способ доставки создан', DeliveryMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = DeliveryMethodCreateSerializer(data=request.data)
            
            if serializer.is_valid():
                delivery_method = serializer.save()
                response_serializer = DeliveryMethodSerializer(delivery_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ доставки создан успешно',
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


class DeliveryMethodDetailAPIView(APIView):
    """
    Детали, обновление и удаление способа доставки
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о способе доставки по ID",
        tags=['Delivery Methods'],
        responses={
            200: openapi.Response('Способ доставки', DeliveryMethodSerializer),
            404: openapi.Response('Способ доставки не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            try:
                delivery_method = DeliveryMethod.objects.get(pk=pk)
            except DeliveryMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ доставки не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = DeliveryMethodSerializer(delivery_method)
            
            return Response({
                'success': True,
                'message': 'Способ доставки получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление способа доставки",
        tags=['Delivery Methods'],
        request_body=DeliveryMethodCreateSerializer,
        responses={
            200: openapi.Response('Способ доставки обновлен', DeliveryMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Способ доставки не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            try:
                delivery_method = DeliveryMethod.objects.get(pk=pk)
            except DeliveryMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ доставки не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = DeliveryMethodCreateSerializer(delivery_method, data=request.data)
            
            if serializer.is_valid():
                delivery_method = serializer.save()
                response_serializer = DeliveryMethodSerializer(delivery_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ доставки обновлен успешно',
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
        operation_description="Частичное обновление способа доставки",
        tags=['Delivery Methods'],
        request_body=DeliveryMethodCreateSerializer,
        responses={
            200: openapi.Response('Способ доставки обновлен', DeliveryMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Способ доставки не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, pk):
        try:
            try:
                delivery_method = DeliveryMethod.objects.get(pk=pk)
            except DeliveryMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ доставки не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = DeliveryMethodCreateSerializer(delivery_method, data=request.data, partial=True)
            
            if serializer.is_valid():
                delivery_method = serializer.save()
                response_serializer = DeliveryMethodSerializer(delivery_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ доставки обновлен успешно',
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
        operation_description="Удаление способа доставки",
        tags=['Delivery Methods'],
        responses={
            200: openapi.Response('Способ доставки удален'),
            404: openapi.Response('Способ доставки не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            try:
                delivery_method = DeliveryMethod.objects.get(pk=pk)
            except DeliveryMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ доставки не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            delivery_method.delete()
            
            return Response({
                'success': True,
                'message': 'Способ доставки удален успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodListCreateAPIView(APIView):
    """
    Список и создание способов оплаты
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="""
        Получение списка всех способов оплаты.
        
        **Описание:**
        Возвращает список всех доступных способов оплаты. Способы оплаты отсортированы по дате создания (новые первыми).
        
        **Ответ включает:**
        - id: Уникальный идентификатор способа оплаты
        - name: Название способа оплаты
        - details: Детали способа оплаты
        - created_at: Дата создания
        - updated_at: Дата обновления
        """,
        tags=['Payment Methods'],
        responses={
            200: openapi.Response(
                'Список способов оплаты',
                PaymentMethodSerializer(many=True)
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            payment_methods = PaymentMethod.objects.all().order_by('-created_at')
            serializer = PaymentMethodSerializer(payment_methods, many=True)
            
            return Response({
                'success': True,
                'message': 'Список способов оплаты получен успешно',
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
        Создание нового способа оплаты.
        
        **Описание:**
        Создает новый способ оплаты с указанными параметрами.
        
        **Обязательные поля:**
        - name: Название способа оплаты (строка, максимум 255 символов)
        
        **Необязательные поля:**
        - details: Детали способа оплаты (текст)
        
        **Пример запроса:**
        ```json
        {
            "name": "Банковская карта",
            "details": "Оплата банковской картой онлайн"
        }
        ```
        """,
        tags=['Payment Methods'],
        request_body=PaymentMethodCreateSerializer,
        responses={
            201: openapi.Response('Способ оплаты создан', PaymentMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = PaymentMethodCreateSerializer(data=request.data)
            
            if serializer.is_valid():
                payment_method = serializer.save()
                response_serializer = PaymentMethodSerializer(payment_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ оплаты создан успешно',
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


class PaymentMethodDetailAPIView(APIView):
    """
    Детали, обновление и удаление способа оплаты
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о способе оплаты по ID",
        tags=['Payment Methods'],
        responses={
            200: openapi.Response('Способ оплаты', PaymentMethodSerializer),
            404: openapi.Response('Способ оплаты не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request, pk):
        try:
            try:
                payment_method = PaymentMethod.objects.get(pk=pk)
            except PaymentMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ оплаты не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = PaymentMethodSerializer(payment_method)
            
            return Response({
                'success': True,
                'message': 'Способ оплаты получен успешно',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Обновление способа оплаты",
        tags=['Payment Methods'],
        request_body=PaymentMethodCreateSerializer,
        responses={
            200: openapi.Response('Способ оплаты обновлен', PaymentMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Способ оплаты не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def put(self, request, pk):
        try:
            try:
                payment_method = PaymentMethod.objects.get(pk=pk)
            except PaymentMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ оплаты не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = PaymentMethodCreateSerializer(payment_method, data=request.data)
            
            if serializer.is_valid():
                payment_method = serializer.save()
                response_serializer = PaymentMethodSerializer(payment_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ оплаты обновлен успешно',
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
        operation_description="Частичное обновление способа оплаты",
        tags=['Payment Methods'],
        request_body=PaymentMethodCreateSerializer,
        responses={
            200: openapi.Response('Способ оплаты обновлен', PaymentMethodSerializer),
            400: openapi.Response('Ошибка валидации'),
            404: openapi.Response('Способ оплаты не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, pk):
        try:
            try:
                payment_method = PaymentMethod.objects.get(pk=pk)
            except PaymentMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ оплаты не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = PaymentMethodCreateSerializer(payment_method, data=request.data, partial=True)
            
            if serializer.is_valid():
                payment_method = serializer.save()
                response_serializer = PaymentMethodSerializer(payment_method)
                
                return Response({
                    'success': True,
                    'message': 'Способ оплаты обновлен успешно',
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
        operation_description="Удаление способа оплаты",
        tags=['Payment Methods'],
        responses={
            200: openapi.Response('Способ оплаты удален'),
            404: openapi.Response('Способ оплаты не найден'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def delete(self, request, pk):
        try:
            try:
                payment_method = PaymentMethod.objects.get(pk=pk)
            except PaymentMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Способ оплаты не найден'
                }, status=status.HTTP_404_NOT_FOUND)
            
            payment_method.delete()
            
            return Response({
                'success': True,
                'message': 'Способ оплаты удален успешно'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

