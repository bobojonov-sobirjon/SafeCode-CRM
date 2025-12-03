from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg import generators

from rest_framework import permissions
from config.libraries.swagger_auth import SwaggerTokenView


class CustomOpenAPISchemaGenerator(generators.OpenAPISchemaGenerator):
    """Custom schema generator that adds security definitions"""
    
    def get_security_definitions(self):
        """Add Bearer token security definitions"""
        return {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'JWT Bearer token. Для получения токена используйте endpoint логина: /api/v1/accounts/login/'
            },
        }


schema_view = get_schema_view(
    openapi.Info(
        title="SafeCode CRM APIs",
        default_version='v1',
        description="""
        SafeCode CRM APIs - Система управления для SafeCode CRM
        
        ### 📌 Аутентификация (Вход в систему)
        
        **Способ 1: Через Bearer token**
        1. Отправьте email и пароль на endpoint `POST /api/v1/accounts/login/`
        2. Скопируйте полученный `access` токен
        3. Нажмите кнопку "Authorize"
        4. Введите токен в следующем формате: `Bearer YOUR_TOKEN_HERE`
        5. Нажмите кнопку "Authorize" и можете использовать все API! ✅
        
        **Примечание:** Токен действителен в течение 1 часа. После истечения срока выполните повторный вход.
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
    patterns=[
        path('api/v1/accounts/', include('apps.v1.accounts.urls')),
        path('api/v1/website/', include('apps.v1.website.urls')),
        path('api/v1/notification/', include('apps.v1.notification.urls')),
        path('api/v1/products/', include('apps.v1.products.urls')),
        path('api/v1/user_objects/', include('apps.v1.user_objects.urls')),
        path('api/v1/documents/', include('apps.v1.documents.urls')),
        path('api/v1/orders/', include('apps.v1.orders.urls')),
    ],
    generator_class=CustomOpenAPISchemaGenerator,
    url='https://api.safecode.flowersoptrf.ru',  # Production URL
)

urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Swagger OAuth2 token endpoint
urlpatterns += [
    path('api/v1/swagger/token/', SwaggerTokenView.as_view(), name='swagger-token'),
]

urlpatterns += [
    path('api/v1/accounts/', include('apps.v1.accounts.urls')),
    path('api/v1/website/', include('apps.v1.website.urls')),
    path('api/v1/notification/', include('apps.v1.notification.urls')),
    path('api/v1/products/', include('apps.v1.products.urls')),
    path('api/v1/user_objects/', include('apps.v1.user_objects.urls')),
    path('api/v1/documents/', include('apps.v1.documents.urls')),
    path('api/v1/orders/', include('apps.v1.orders.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT, }, ), ]