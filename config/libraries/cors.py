CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "https://api.safecode.flowersoptrf.ru",  # Production domain
    "http://api.safecode.flowersoptrf.ru",   # HTTP variant (agar kerak bo'lsa)
    "https://safecode-phi.vercel.app",       # Frontend domain
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "https://api.safecode.flowersoptrf.ru",
    "http://api.safecode.flowersoptrf.ru",
    "https://safecode-phi.vercel.app",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = True
