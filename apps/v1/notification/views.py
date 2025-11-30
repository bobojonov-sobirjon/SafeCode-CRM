from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from apps.v1.notification.models import Notification
from apps.v1.accounts.models import PurchasedService, CustomUser
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import NotificationSerializer
from apps.v1.accounts.error_handlers import get_error_message


@shared_task
def notify_expiring_services():
    now = timezone.now()
    for days_left in [10, 7, 4, 1]:
        target_date = now + timedelta(days=days_left)
        purchases = PurchasedService.objects.filter(is_active=True, finished_date__date=target_date.date())
        for purchase in purchases.select_related('user', 'service'):
            # In-app notification
            Notification.objects.create(
                recipient=purchase.user,
                actor=None,
                verb='service_expiry_reminder',
                message=f"Услуга '{purchase.service.title}' истекает через {days_left} дней. Пожалуйста, продлите.",
                target=purchase,
                category='service'
            )
            # Email
            try:
                send_mail(
                    'Напоминание: срок услуги истекает',
                    f"Здравствуйте, {purchase.user.get_full_name()}!\n\nУслуга '{purchase.service.title}' истекает через {days_left} дней. Пожалуйста, проверьте и продлите при необходимости.",
                    settings.DEFAULT_FROM_EMAIL,
                    [purchase.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass


class NotificationListAPIView(APIView):
    """
    Получение списка уведомлений текущего пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получение списка уведомлений текущего пользователя. Можно фильтровать по is_read параметру.",
        tags=['Notifications'],
        manual_parameters=[
            openapi.Parameter('is_read', openapi.IN_QUERY, description='Фильтр по статусу прочтения (true/false). Если не указан, возвращаются все уведомления.', type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('page', openapi.IN_QUERY, description='Номер страницы', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('limit', openapi.IN_QUERY, description='Количество элементов на странице', type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={
            200: openapi.Response(
                'Список уведомлений',
                NotificationSerializer(many=True)
            ),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def get(self, request):
        try:
            from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
            
            user = request.user
            
            # Получаем все уведомления пользователя
            queryset = Notification.objects.filter(recipient=user, is_read=False)
            
            # Фильтр по is_read, если указан
            is_read_param = request.query_params.get('is_read')
            if is_read_param is not None:
                is_read_value = is_read_param.lower() in ('true', '1', 'yes')
                queryset = queryset.filter(is_read=is_read_value)
            
            queryset = queryset.select_related('actor', 'user_object', 'target_content_type').prefetch_related('target').order_by('-created_at')
            
            # Пагинация
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 20)
            
            try:
                page = int(page)
                limit = int(limit)
            except ValueError:
                page = 1
                limit = 20
            
            paginator = Paginator(queryset, limit)
            
            try:
                notifications = paginator.page(page)
            except EmptyPage:
                notifications = paginator.page(paginator.num_pages)
            except PageNotAnInteger:
                notifications = paginator.page(1)
            
            serializer = NotificationSerializer(notifications, many=True)
            
            return Response({
                'success': True,
                'message': 'Список уведомлений получен успешно',
                'data': serializer.data,
                'count': paginator.count,
                'unread_count': Notification.objects.filter(recipient=user, is_read=False).count(),
                'pagination': {
                    'current_page': notifications.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'items_per_page': limit,
                    'has_next': notifications.has_next(),
                    'has_previous': notifications.has_previous(),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationMarkAsReadAPIView(APIView):
    """
    Отметка уведомления как прочитанного
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Отметка уведомления как прочитанного (is_read=True)",
        tags=['Notifications'],
        responses={
            200: openapi.Response(
                'Уведомление отмечено как прочитанное',
                NotificationSerializer
            ),
            404: openapi.Response('Уведомление не найдено'),
            401: openapi.Response('Требуется авторизация')
        },
        security=[{'Bearer': []}]
    )
    def patch(self, request, notification_id):
        try:
            user = request.user
            
            # Получаем уведомление
            try:
                notification = Notification.objects.get(
                    id=notification_id,
                    recipient=user
                )
            except Notification.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Уведомление не найдено'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Отмечаем как прочитанное
            notification.is_read = True
            notification.save()
            
            serializer = NotificationSerializer(notification)
            
            return Response({
                'success': True,
                'message': 'Уведомление отмечено как прочитанное',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': get_error_message('server_error'),
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
