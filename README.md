# SafeCodeCRM

SafeCodeCRM is a Django REST Framework-based Customer Relationship Management (CRM) system designed to manage user accounts, services, contacts, and business data.

## Features

- **User Authentication**: Custom user model with JWT-based authentication
- **API Documentation**: Integrated Swagger/OpenAPI documentation
- **Service Management**: Manage services, service items, and pricing
- **Contact Management**: Store and manage contact information
- **CORS Support**: Configured for cross-origin requests
- **Data Import/Export**: Built-in import/export functionality
- **Email Support**: Email configuration for notifications and communications

## Project Structure

```
SafeCodeCRM/
├── apps/
│   └── v1/
│       ├── accounts/          # User authentication and management
│       │   ├── models.py       # CustomUser model
│       │   ├── views.py        # API views
│       │   ├── serializers.py  # API serializers
│       │   └── urls.py         # URL routing
│       └── website/            # Website content management
│           ├── models.py       # Services, ServiceItems, Contacts models
│           ├── views.py        # API views
│           ├── serializers.py  # API serializers
│           └── urls.py         # URL routing
├── config/                     # Project configuration
│   ├── settings.py            # Django settings
│   ├── libraries/              # Configuration libraries
│   │   ├── jwt.py             # JWT settings
│   │   ├── swagger.py         # Swagger settings
│   │   ├── cors.py            # CORS settings
│   │   ├── email.py           # Email configuration
│   │   ├── cache.py           # Cache configuration
│   │   ├── logging.py         # Logging configuration
│   │   └── rest_framework.py  # DRF settings
│   ├── middleware/            # Custom middleware
│   └── urls.py               # Root URL configuration
├── env/                       # Virtual environment
├── logs/                      # Log files
├── manage.py                 # Django management script
└── requirements.txt          # Python dependencies
```

## Requirements

- Python 3.x
- Django 5.2.7
- Django REST Framework 3.16.1
- SQLite database (default)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SafeCodeCRM
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv env
   env\Scripts\activate
   
   # Linux/Mac
   python -m venv env
   source env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**
   Create a `.env` file in the root directory with the following variables:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=*
   
   # Database (optional, defaults to SQLite)
   DB_NAME=db.sqlite3
   
   # Email Configuration (optional)
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-password
   
   # CORS Settings (optional)
   CORS_ALLOW_ALL_ORIGINS=True
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/`

## API Documentation

### Swagger UI
Visit `http://localhost:8000/swagger/` to access the interactive API documentation.

### ReDoc
Visit `http://localhost:8000/redoc/` for an alternative documentation view.

## Key Models

### CustomUser
- Email (unique identifier)
- Phone number
- Date of birth
- Avatar
- Address
- Position
- Organization ID

### Services
- Title
- Image
- Description
- Why this service
- For whom
- Price

### ServiceItems
- Related to Services
- Content

### Contacts
- Address
- Phone
- Email
- Working hours (Mon-Thu, Fri, Sat-Sun)
- Map iframe

## API Endpoints

### Authentication
- `POST /api/v1/accounts/register/` - Register new user
- `POST /api/v1/accounts/login/` - Login
- `POST /api/v1/accounts/logout/` - Logout
- `POST /api/v1/accounts/token/refresh/` - Refresh JWT token

### User Profile
- `GET /api/v1/accounts/profile/` - Get user profile
- `PUT /api/v1/accounts/profile/` - Update user profile
- `PATCH /api/v1/accounts/profile/` - Partial update

### Services
- `GET /api/v1/website/services/` - List all services
- `POST /api/v1/website/services/` - Create new service
- `GET /api/v1/website/services/{id}/` - Get service details
- `PUT /api/v1/website/services/{id}/` - Update service
- `DELETE /api/v1/website/services/{id}/` - Delete service

### Contacts
- `GET /api/v1/website/contacts/` - Get contact information
- `POST /api/v1/website/contacts/` - Create contact information

## Configuration

### JWT Authentication
JWT tokens are configured with the following default settings:
- Access token lifetime: 5 minutes
- Refresh token lifetime: 1 day
- Token blacklisting enabled

### CORS
CORS is configured to allow cross-origin requests. Modify settings in `config/libraries/cors.py` for production.

### Logging
Logs are configured to write to `logs/django.log`. Modify settings in `config/libraries/logging.py`.

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
```

### Applying Migrations
```bash
python manage.py migrate
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

## Production Deployment

Before deploying to production:

1. Set `DEBUG = False` in `config/settings.py`
2. Change `SECRET_KEY` to a secure random value
3. Set proper `ALLOWED_HOSTS`
4. Configure proper database (PostgreSQL, MySQL, etc.)
5. Set up proper media/static file serving
6. Configure SSL/HTTPS
7. Update CORS settings for production domains
8. Configure email settings
9. Set up proper logging and monitoring

## Dependencies

- Django 5.2.7
- Django REST Framework 3.16.1
- djangorestframework-simplejwt 5.5.1
- drf-yasg 1.21.11 (Swagger documentation)
- django-cors-headers 4.9.0
- django-filter 25.2
- django-import-export 4.3.12
- PyJWT 2.10.1
- pillow 12.0.0
- python-dotenv 1.1.1

## License

This project is proprietary software.

## Support

For questions or issues, please contact the development team.

## Authors

SafeCodeCRM Development Team

