# 01. Estructura, Configuración y Arquitectura Django — Apex Gym Hub

---

## 1. Propósito

Este documento explica la arquitectura general, el punto de entrada y la configuración global del Back End de **Apex Gym Hub** construido con **Django** y **Django REST Framework (DRF)**. Permite comprender cómo arranca el servidor, cómo se estructuran las cuatro aplicaciones de dominio (`users`, `catalog`, `routines`, `tracking`), cómo se configuran la seguridad, la base de datos, los tokens JWT, el soporte CORS, la subida de archivos multimedia y cómo se enrutan las peticiones HTTP hacia cada módulo o hacia el prototipo funcional en `templates/index.html`.

---

## 2. Ubicación

Todos los archivos analizados en este documento residen bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `manage.py` — Utilidad de línea de comandos de Django (`runserver`, `migrate`, `seed_catalog`, etc.).
- `Gym_Backend/settings.py` — Configuración central del proyecto (apps, middleware, base de datos, DRF, JWT, CORS, multimedia, idioma y zona horaria).
- `Gym_Backend/urls.py` — Enrutador raíz (`ROOT_URLCONF`) que conecta `/`, `/admin/`, `/api/v1/*` y los archivos estáticos/media en desarrollo.
- `Gym_Backend/wsgi.py` — Punto de entrada estándar WSGI para servidores de aplicaciones síncronos en producción (Gunicorn, uWSGI).
- `Gym_Backend/asgi.py` — Punto de entrada estándar ASGI para servidores asíncronos (Uvicorn, Daphne).
- `templates/index.html` — Prototipo web autocontenido (HTML/CSS/JS) para probar en vivo los endpoints `/api/v1/`.
- `apps/` — Carpeta contenedora de las aplicaciones de dominio:
  - `apps/__init__.py`
  - `apps/users/` (`apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`)
  - `apps/catalog/` (`apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `permissions.py`, `management/commands/seed_catalog.py`, `migrations/`)
  - `apps/routines/` (`apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`)
  - `apps/tracking/` (`apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`)

> **Nota sobre la estructura observada:** En la raíz también existen `README.md`, `DOCUMENTACION_CAMBIOS_CATALOGO.md`, `.gitignore`, `db.sqlite3`, `media/`, `.postman/resources.yaml` y `postman/globals/workspace.globals.yaml`. El proyecto **no** cuenta actualmente con un archivo `requirements.txt` ni con archivos de pruebas automatizadas (`tests.py`) dentro de las apps.

### Árbol real de carpetas de `Gym_Backend`

```text
Gym_Backend/
├── manage.py
├── db.sqlite3
├── README.md
├── DOCUMENTACION_CAMBIOS_CATALOGO.md
├── .gitignore
├── Gym_Backend/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── templates/
│   └── index.html
├── media/
├── .postman/
│   └── resources.yaml
├── postman/
│   └── globals/
│       └── workspace.globals.yaml
└── apps/
    ├── __init__.py
    ├── users/
    │   ├── __init__.py, admin.py, apps.py, models.py, serializers.py, urls.py, views.py
    │   └── migrations/ (0001_initial.py, 0002_user_training_goal_bodyweightlog.py)
    ├── catalog/
    │   ├── __init__.py, admin.py, apps.py, models.py, permissions.py, serializers.py, urls.py, views.py
    │   ├── management/commands/seed_catalog.py
    │   └── migrations/ (0001_initial.py, 0002_..., 0003_userfavoriteexercise.py)
    ├── routines/
    │   ├── __init__.py, admin.py, apps.py, models.py, serializers.py, urls.py, views.py
    │   └── migrations/ (0001_initial.py, 0002_initial.py)
    └── tracking/
        ├── __init__.py, admin.py, apps.py, models.py, serializers.py, urls.py, views.py
        └── migrations/ (0001_initial.py, 0002_initial.py, 0003_workoutsession_routine_status_duration.py)
```

---

## 3. Cómo se conecta

El proyecto sigue una **arquitectura modular orientada a dominios** sobre el patrón **MVT/REST** de Django + DRF:

1. **Arranque (`manage.py` / `wsgi.py` / `asgi.py`)**: Todos establecen `DJANGO_SETTINGS_MODULE = 'Gym_Backend.settings'`.
2. **Carga de configuración (`Gym_Backend/settings.py`)**:
   - Agrega `BASE_DIR / 'apps'` al `sys.path` para facilitar importaciones.
   - Registra las 4 apps locales usando sus clases `AppConfig` (`apps.users.apps.UsersConfig`, etc.). Cada `AppConfig` define `name = 'apps.<app>'` y `label = '<app>'`, lo cual permite que `AUTH_USER_MODEL = 'users.User'` y las referencias entre apps usen la etiqueta corta (`users`, `catalog`, `routines`, `tracking`).
   - Conecta DRF con `SimpleJWT` como mecanismo global de autenticación y exige por defecto `IsAuthenticatedOrReadOnly`.
3. **Enrutamiento (`Gym_Backend/urls.py`)**:
   - La raíz `/` sirve directamente `templates/index.html` mediante `TemplateView`.
   - `/admin/` habilita el panel administrativo nativo de Django.
   - `/api/v1/auth/`, `/api/v1/catalog/`, `/api/v1/routines/` y `/api/v1/tracking/` delegan mediante `include(...)` a los `urls.py` internos de cada aplicación.
   - Cuando `DEBUG = True`, Django sirve los archivos subidos (`/media/`) y estáticos (`/static/`).
4. **Cliente de prueba (`templates/index.html`)**: Se conecta vía `fetch()` contra `/api/v1/...`, almacena el token JWT en `localStorage` y demuestra en un solo lugar login, auditoría de usuarios admin, catálogo multimedia, creación de rutinas y registro de marcas/1RM.

```text
Cliente (App Móvil / Web / templates/index.html)
       │  HTTP + Header "Authorization: Bearer <JWT>"
       ▼
Gym_Backend/urls.py  (Middleware: CorsMiddleware -> Auth -> ...)
  ├── ""                  ──▶ templates/index.html (TemplateView)
  ├── "admin/"            ──▶ Django Admin
  ├── "api/v1/auth/"      ──▶ apps/users/urls.py
  ├── "api/v1/catalog/"   ──▶ apps/catalog/urls.py
  ├── "api/v1/routines/"  ──▶ apps/routines/urls.py
  └── "api/v1/tracking/"  ──▶ apps/tracking/urls.py
```

---

## 4. Componentes, funciones y variables clave

| Archivo | Elemento / Variable | Rol en el sistema |
| :--- | :--- | :--- |
| `manage.py` | `main()` | Fija `DJANGO_SETTINGS_MODULE` y ejecuta `execute_from_command_line(sys.argv)`. |
| `settings.py` | `BASE_DIR` | Ruta raíz absoluta (`Gym_Backend/`) calculada con `pathlib.Path`. |
| `settings.py` | `sys.path.insert(0, str(BASE_DIR / 'apps'))` | Inserta el directorio `apps/` en la ruta de búsqueda de módulos de Python. |
| `settings.py` | `INSTALLED_APPS` | Lista las 6 apps nativas, `corsheaders`, `rest_framework`, `rest_framework_simplejwt` y las 4 `AppConfig` locales. |
| `settings.py` | `MIDDLEWARE` | Cadena de procesamiento HTTP; destaca `CorsMiddleware` en primera posición. |
| `settings.py` | `AUTH_USER_MODEL` | Define `'users.User'` como modelo de autenticación en sustitución de `auth.User`. |
| `settings.py` | `REST_FRAMEWORK` | Configura `JWTAuthentication`, `IsAuthenticatedOrReadOnly` y `PageNumberPagination` (`PAGE_SIZE = 20`). |
| `settings.py` | `SIMPLE_JWT` | Define vigencia de tokens (`7` días access, `30` días refresh), rotación (`True`) y prefijo `Bearer`. |
| `settings.py` | `CORS_ALLOW_ALL_ORIGINS` | Permite peticiones desde cualquier origen (`True`, orientado a desarrollo). |
| `settings.py` | `MEDIA_URL` / `MEDIA_ROOT` | Mapea `/media/` a `BASE_DIR / 'media'` para imágenes y videos. |
| `settings.py` | `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` | Eleva el límite de subida en memoria a `10 MB` (`10 * 1024 * 1024` bytes). |
| `urls.py` | `urlpatterns` | Tabla principal de rutas HTTP incluyendo la vista raíz y los 4 prefijos `/api/v1/*`. |
| `wsgi.py` / `asgi.py` | `application` | Objeto callable estándar que exponen los servidores web en despliegue. |
| `apps/*/apps.py` | `UsersConfig`, `CatalogConfig`, `RoutinesConfig`, `TrackingConfig` | Metadatos `name = 'apps.<nombre>'` y `label = '<nombre>'` para cada app modular. |
| `templates/index.html` | `API_URL`, `login()`, `cargarEjercicios()`, `crearRutina()`, `guardarMarca()` | Funciones JS que consumen la API REST en tiempo real para demostración funcional. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1 `manage.py` (líneas 1-22)

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gym_Backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

- **Línea 9:** `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gym_Backend.settings')` asigna qué archivo de configuración usará Django si la variable de entorno aún no existe.
- **Líneas 10-17:** Intenta importar el despachador de comandos de Django; si falla (por ejemplo, entorno virtual no activado), lanza un `ImportError` descriptivo.
- **Línea 18:** Pasa los argumentos de consola (`sys.argv`, como `runserver`, `migrate` o `seed_catalog`) a Django para ejecutarlos.

---

### 5.2 `Gym_Backend/settings.py` (bloques clave, líneas 1-138)

#### Rutas, sys.path y seguridad básica (líneas 1-18)

```python
from datetime import timedelta
from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Enable importing directly from apps folder
sys.path.insert(0, str(BASE_DIR / 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-5m43kyk4deh94s)#j#nj#3mr$izcb1x=m86(1vof6%j$a6x_@h'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
```

- `BASE_DIR` sube dos niveles desde `Gym_Backend/settings.py` hasta la carpeta raíz del backend (`Gym_Backend/`).
- `sys.path.insert(0, str(BASE_DIR / 'apps'))` permite importaciones cortas dentro de `apps/`, aunque en el código real se mantienen importaciones explícitas como `from apps.catalog.models import Exercise`.
- `SECRET_KEY`, `DEBUG = True` y `ALLOWED_HOSTS = ['*']` corresponden a un perfil de desarrollo local/red local (por ejemplo, pruebas desde dispositivos móviles Expo en la misma red), pero constituyen un riesgo si se despliegan sin variables de entorno en producción.

#### Aplicaciones instaladas y AppConfigs (líneas 20-38)

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',

    # Local Domain Apps
    'apps.users.apps.UsersConfig',
    'apps.catalog.apps.CatalogConfig',
    'apps.routines.apps.RoutinesConfig',
    'apps.tracking.apps.TrackingConfig',
]
```

Cada clase `*Config` en `apps/<modulo>/apps.py` sigue el mismo patrón (por ejemplo `apps/catalog/apps.py`):

```python
from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.catalog'
    label = 'catalog'
    verbose_name = 'Catálogo de Ejercicios y Máquinas'
```

- Definir `name = 'apps.catalog'` indica la ruta del paquete Python, mientras `label = 'catalog'` fija el identificador lógico que Django utiliza para nombrar tablas (`catalog_exercise`) y resolver referencias entre modelos sin incluir el prefijo `apps.`.

#### Middleware, Templates, Base de Datos y Modelo de Usuario (líneas 40-95)

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Gym_Backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Gym_Backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'users.User'
```

- `CorsMiddleware` está ubicado al inicio (línea 41) para interceptar peticiones `OPTIONS` (preflight CORS) y añadir cabeceras `Access-Control-Allow-*` antes de que `CommonMiddleware` o las vistas generen respuestas o redirecciones.
- `DIRS: [BASE_DIR / 'templates']` habilita que `TemplateView(template_name='index.html')` localice `templates/index.html`.
- `DATABASES` apunta a SQLite (`db.sqlite3`) en desarrollo.
- `AUTH_USER_MODEL = 'users.User'` reemplaza el modelo estándar de Django desde la migración inicial.
- Las líneas 82-95 configuran los 4 validadores estándar de contraseñas de Django (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`).

#### DRF, SimpleJWT, CORS, Internacionalización y Archivos Multimedia (líneas 98-138)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOW_ALL_ORIGINS = True

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
```

- `REST_FRAMEWORK`: Cualquier endpoint que no sobreescriba `permission_classes` permite lectura anónima y exige JWT para escritura; además pagina automáticamente de 20 en 20 elementos.
- `SIMPLE_JWT`: El token de acceso dura 7 días y el de refresco 30 días. `ROTATE_REFRESH_TOKENS = True` emite un nuevo `refresh` token al renovar, aunque `BLACKLIST_AFTER_ROTATION = False` (el token anterior no se invalida en una lista negra).
- `TIME_ZONE = 'America/Mexico_City'` con `USE_TZ = True`: Django almacena fechas en UTC en base de datos y convierte a hora de Ciudad de México cuando se llama a `timezone.localtime(...)` (clave en el módulo de `tracking` para agrupar entrenamientos por fecha local).
- `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` en 10 MB permiten recibir payloads JSON grandes con imágenes en Base64 o archivos multipart sin que Django arroje `RequestDataTooBig`.

---

### 5.3 `Gym_Backend/urls.py` (líneas 1-23)

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Vista Frontend Rápida (Prototipo funcional)
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')),
    path('api/v1/routines/', include('apps.routines.urls')),
    path('api/v1/tracking/', include('apps.tracking.urls')),
]

# Servir archivos estáticos y multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

- **Versionado de API:** Todas las rutas de negocio cuelgan del prefijo `/api/v1/`, facilitando futuras versiones (`/api/v2/`) sin romper clientes actuales.
- **Servido multimedia local:** El bloque `if settings.DEBUG:` expone `/media/...` directamente desde el servidor de desarrollo de Django.

---

### 5.4 `Gym_Backend/wsgi.py` y `Gym_Backend/asgi.py`

```python
# Gym_Backend/wsgi.py
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gym_Backend.settings')

application = get_wsgi_application()
```

```python
# Gym_Backend/asgi.py
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gym_Backend.settings')

application = get_asgi_application()
```

- Ambos archivos exponen el objeto `application` necesario para servidores de producción. `wsgi.py` está conectado explícitamente en `settings.py` mediante `WSGI_APPLICATION = 'Gym_Backend.wsgi.application'`; `asgi.py` queda disponible si en el futuro se incorporan WebSockets o servidores ASGI como Uvicorn.

---

### 5.5 `templates/index.html` (fragmentos clave del prototipo funcional)

`templates/index.html` (717 líneas) es un panel interactivo de pruebas sin frameworks externos que consume los 4 módulos de la API:

```javascript
const API_URL = '/api/v1';
let accessToken = localStorage.getItem('token') || '';
// ...
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    };
}
```

- **Sección 1 (Usuario / Sesión):** Llama a `POST /api/v1/auth/login/`, guarda `access`, `email` y `user.is_staff` en `localStorage`, muestra la insignia `🛡️ Administrador` o `👤 Usuario Estándar` y, si es admin, habilita `GET /api/v1/auth/users/`.
- **Sección 2 (Catálogo):** Consulta `equipment/`, `muscles/` y `exercises/`; si es admin permite publicar ejercicios vía `POST /api/v1/catalog/exercises/` e incrusta iframes de YouTube, `<video>` o `<img>` al consultar el detalle `GET /api/v1/catalog/exercises/${id}/`.
- **Sección 3 (Rutinas):** Lista (`GET /api/v1/routines/routines/`), crea (`POST /api/v1/routines/routines/`) y añade ejercicios (`POST /api/v1/routines/routines/${rutinaId}/add-exercise/`).
- **Sección 4 (Registro de Marcas):** Crea una sesión (`POST /api/v1/tracking/sessions/`), vincula el ejercicio (`POST /api/v1/tracking/exercises/`), registra la serie (`POST /api/v1/tracking/sets/`) y refresca el historial con cálculo de 1RM desde `GET /api/v1/tracking/progression/${exerciseId}/`.

---

## 6. Flujo paso a paso (Ciclo de vida de una petición HTTP)

1. El cliente (app móvil React Native/Expo o `templates/index.html`) envía una petición HTTP, por ejemplo `GET /api/v1/routines/routines/`, incluyendo `Authorization: Bearer <access_token>`.
2. El servidor recibe la petición a través de `wsgi.py` (o `runserver`).
3. Django pasa la petición por la lista `MIDDLEWARE` de `settings.py`: `CorsMiddleware` evalúa cabeceras CORS, luego pasan `SecurityMiddleware`, sesiones, CSRF y `AuthenticationMiddleware`.
4. `ROOT_URLCONF` (`Gym_Backend/urls.py`) hace coincidir el prefijo `api/v1/routines/` y delega el resto de la URL a `apps/routines/urls.py`.
5. DRF ejecuta `JWTAuthentication`, valida la firma del token usando `SECRET_KEY` y asigna `request.user`.
6. DRF evalúa `permission_classes` de la vista (o `DEFAULT_PERMISSION_CLASSES` si la vista no define propios).
7. La vista ejecuta consultas sobre SQLite (`db.sqlite3`) mediante el ORM, serializa la respuesta a JSON, aplica `PageNumberPagination` (`PAGE_SIZE = 20`) si corresponde, y retorna la respuesta HTTP atravesando de vuelta `MIDDLEWARE` (donde `CorsMiddleware` inyecta `Access-Control-Allow-Origin: *`).

---

## 7. Conceptos y términos técnicos

- **WSGI / ASGI:** Interfaces estándar de Python que conectan un servidor web (Nginx + Gunicorn/Uvicorn) con un framework Python como Django. WSGI es síncrono (una petición por hilo/worker) y ASGI soporta concurrencia asíncrona.
- **AppConfig (`name` vs `label`):** Clase de configuración de cada app Django. Cuando las apps se guardan dentro de una subcarpeta `apps/`, `name` indica la ruta Python (`apps.users`) y `label` mantiene el nombre corto (`users`) para modelos y migraciones.
- **Middleware:** Capa intermedia de funciones/clases por la que pasan todas las peticiones entrantes y respuestas salientes de Django antes de llegar a la vista.
- **CORS (Cross-Origin Resource Sharing):** Mecanismo de seguridad de los navegadores que bloquea peticiones AJAX/fetch hacia un dominio o puerto distinto al del frontend si el servidor no responde con las cabeceras permitidas (`django-cors-headers`).
- **JWT (JSON Web Token):** Estándar de autenticación sin estado (*stateless*). El cliente recibe un token firmado criptográficamente al iniciar sesión y lo envía en cada petición sin necesitar sesiones en servidor.
- **Paginación (`PageNumberPagination`):** Técnica para dividir listados grandes en páginas de tamaño fijo (`PAGE_SIZE = 20`) devolviendo `count`, `next`, `previous` y `results`.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué las aplicaciones locales están dentro de `apps/` y cada `apps.py` define tanto `name` como `label`?**
   - *Respuesta modelo:* Se agrupan en `apps/` para mantener limpia la raíz del proyecto y separar la configuración global (`Gym_Backend/`) de la lógica de dominio (`users`, `catalog`, `routines`, `tracking`). En cada `AppConfig`, `name = 'apps.<modulo>'` le indica a Python la ruta de importación real, mientras `label = '<modulo>'` preserva identificadores cortos como `'users.User'` o `'catalog.exercise'` en `AUTH_USER_MODEL`, claves foráneas y tablas SQL.

2. **¿Qué hace `CorsMiddleware` y por qué es el primer elemento de `MIDDLEWARE` en `settings.py`?**
   - *Respuesta modelo:* `CorsMiddleware` añade las cabeceras HTTP `Access-Control-Allow-*` necesarias para que clientes externos (web o emuladores en otro puerto/origen) puedan consumir la API. Se coloca al principio para interceptar solicitudes preflight `OPTIONS` y añadir cabeceras incluso antes de que otros middlewares como `CommonMiddleware` generen redirecciones o respuestas tempranas.

3. **¿Cuál es la diferencia entre `STATIC_URL`/`STATIC_ROOT` y `MEDIA_URL`/`MEDIA_ROOT`?**
   - *Respuesta modelo:* Los archivos **estáticos** (`STATIC_*`) pertenecen al código fuente del proyecto (CSS/JS del panel `/admin/` recopilados con `collectstatic` en `staticfiles/`). Los archivos **multimedia** (`MEDIA_*`) son archivos subidos dinámicamente por administradores o usuarios (fotos de máquinas, ejercicios, miniaturas o avatares) almacenados en `media/` y servidos bajo `/media/` cuando `DEBUG = True`.

4. **¿Qué implicaciones de seguridad tiene la configuración actual de `settings.py` si se quisiera pasar a producción?**
   - *Respuesta modelo:* Existen cuatro parámetros inseguros para producción: `SECRET_KEY` está expuesta en el código fuente, `DEBUG = True` mostraría trazas de error detalladas, `ALLOWED_HOSTS = ['*']` desactiva la validación del encabezado `Host`, y `CORS_ALLOW_ALL_ORIGINS = True` abre la API a cualquier dominio. Antes de desplegar deben moverse a variables de entorno y restringirse a los dominios reales, además de migrar de SQLite a un motor cliente-servidor como PostgreSQL y generar un `requirements.txt`.

5. **¿Por qué `SIMPLE_JWT` tiene `ACCESS_TOKEN_LIFETIME` en 7 días y qué ocurre al rotar refresh tokens si `BLACKLIST_AFTER_ROTATION` es `False`?**
   - *Respuesta modelo:* Un access token de 7 días reduce la frecuencia de renovación en el cliente móvil durante desarrollo/uso continuo, a costa de una ventana mayor si el token fuera robado. Con `ROTATE_REFRESH_TOKENS = True` y `BLACKLIST_AFTER_ROTATION = False`, cada llamada a `/api/v1/auth/token/refresh/` entrega un nuevo `refresh` token, pero el `refresh` anterior no queda invalidado en base de datos hasta que expire naturalmente a los 30 días.

6. **¿Para qué sirven `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` configurados a 10 MB?**
   - *Respuesta modelo:* Por defecto Django limita el cuerpo de peticiones en memoria a 2.5 MB (`DATA_UPLOAD_MAX_MEMORY_SIZE`). Como el catálogo soporta carga de imágenes codificadas en Base64 dentro de JSON (lo que aumenta su tamaño ~33% respecto al binario) además de `multipart/form-data`, elevar ambos límites a 10 MB evita errores `400/RequestDataTooBig` antes de que actúe el validador propio de 5 MB de `validate_image`.

---

## 9. Resumen para repasar

- El proyecto se organiza en un núcleo de configuración (`Gym_Backend/`) y **4 apps de dominio** dentro de `apps/`: `users`, `catalog`, `routines` y `tracking`, todas enrutadas bajo `/api/v1/`.
- La autenticación es **stateless con JWT** (`SimpleJWT`, `Bearer`, access de 7 días, refresh de 30 días) y `AUTH_USER_MODEL = 'users.User'` sustituye al usuario por defecto desde el inicio.
- La política global de DRF es `IsAuthenticatedOrReadOnly` con paginación de **20 elementos por página**, aunque cada módulo refina sus permisos según su rol.
- `templates/index.html` sirve en `/` como cliente web de demostración en tiempo real conectado a los 4 módulos de la API.
- Como deuda técnica de configuración destacan: `SECRET_KEY` hardcoded, `DEBUG = True`, `CORS_ALLOW_ALL_ORIGINS = True`, ausencia de `requirements.txt` y ausencia de suite de tests (`tests.py`).
