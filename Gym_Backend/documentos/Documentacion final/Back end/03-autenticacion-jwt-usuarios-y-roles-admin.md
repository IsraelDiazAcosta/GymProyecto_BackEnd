# 03. Autenticación JWT, Usuarios y Roles de Administrador — Apex Gym Hub

---

## 1. Propósito

Este documento explica el módulo de identidad, autenticación, perfil biométrico, historial de peso corporal y control de acceso por roles en **Apex Gym Hub**. Cubre cómo se sustituyó el modelo de usuario por defecto de Django para autenticar por correo electrónico (`email`), cómo se generan y renuevan tokens JWT en el registro y el login, cómo se sincroniza automáticamente el peso actual (`current_weight`) del usuario al registrar un pesaje y cómo se restringen las operaciones administrativas mediante `IsAdminUser` e `IsAdminOrReadOnly`.

---

## 2. Ubicación

Rutas exactas bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `apps/users/models.py` — `CustomUserManager`, `User` (`AbstractUser`), `BodyWeightLog`.
- `apps/users/serializers.py` — `UserRegistrationSerializer`, `UserProfileSerializer`, `BodyWeightLogSerializer`, `AdminUserListSerializer`, `CustomTokenObtainPairSerializer`.
- `apps/users/views.py` — `CustomTokenObtainPairView`, `AdminUserListView`, `RegisterView`, `UserProfileView`, `BodyWeightLogListCreateView`.
- `apps/users/urls.py` — Rutas bajo `/api/v1/auth/`.
- `apps/users/admin.py` — `CustomUserCreationForm`, `CustomUserChangeForm`, `UserAdmin`.
- `apps/catalog/permissions.py` — Permiso personalizado `IsAdminOrReadOnly` reutilizado en todo el catálogo.

---

## 3. Cómo se conecta

1. `Gym_Backend/settings.py` declara `AUTH_USER_MODEL = 'users.User'` y configura `JWTAuthentication` como clase de autenticación global en DRF.
2. `Gym_Backend/urls.py` monta `apps/users/urls.py` bajo `/api/v1/auth/`.
3. Al registrarse (`POST /api/v1/auth/register/`) o iniciar sesión (`POST /api/v1/auth/login/`), el cliente obtiene tokens `access` y `refresh` junto con información del usuario incluyendo `is_staff`.
4. En peticiones autenticadas posteriores, el middleware/DRF decodifica el `Bearer <access>` e inyecta el objeto `User` en `request.user`.
5. Las vistas restringen acceso según permisos:
   - `AllowAny`: registro, login y refresh.
   - `IsAuthenticated`: perfil propio (`/profile/`) e historial de peso (`/weight-logs/`).
   - `IsAdminUser`: auditoría completa de usuarios (`GET /api/v1/auth/users/`), que exige `user.is_staff == True`.
   - `IsAdminOrReadOnly` (`apps/catalog/permissions.py`): lectura pública/autenticada y escritura exclusiva para `is_staff=True` en el módulo de catálogo.

---

## 4. Componentes, funciones y variables clave

| Archivo | Símbolo | Responsabilidad |
| :--- | :--- | :--- |
| `users/models.py` | `CustomUserManager` | Sobreescribe `create_user` y `create_superuser` para usar `email` en lugar de `username`. |
| `users/models.py` | `User.USERNAME_FIELD = 'email'` | Establece el correo como credencial de inicio de sesión (`REQUIRED_FIELDS = []`). |
| `users/models.py` | `BodyWeightLog` | Historial cronológico de pesajes vinculados al usuario. |
| `users/serializers.py` | `UserRegistrationSerializer` | Valida coincidencia `password == password_confirm`, exige `min_length=6` y crea usuarios estándar (`is_staff=False`). |
| `users/serializers.py` | `CustomTokenObtainPairSerializer` | Extiende SimpleJWT para adjuntar `user` (`id`, `email`, `username`, `experience_level`, `is_staff`) en la respuesta de login. |
| `users/serializers.py` | `UserProfileSerializer` | Expone perfil protegiendo `id`, `email`, `is_staff` y `date_joined` como `read_only_fields`. |
| `users/serializers.py` | `BodyWeightLogSerializer` | Valida `weight` (`min_value=1`) para registros de peso. |
| `users/serializers.py` | `AdminUserListSerializer` | Serializa usuarios para el administrador agregando `routines_count` y `workouts_count`. |
| `users/views.py` | `RegisterView` | Crea usuario y genera par de tokens JWT mediante `RefreshToken.for_user(user)`. |
| `users/views.py` | `CustomTokenObtainPairView` | Login JWT usando `CustomTokenObtainPairSerializer`. |
| `users/views.py` | `UserProfileView` | `RetrieveUpdateAPIView` cuyo `get_object()` siempre retorna `self.request.user`. |
| `users/views.py` | `BodyWeightLogListCreateView` | Lista/crea pesajes del usuario y sincroniza `user.current_weight` con el más reciente. |
| `users/views.py` | `AdminUserListView` | `ListAPIView` protegido con `IsAdminUser` para auditar todos los usuarios. |
| `users/admin.py` | `UserAdmin` | Configura formularios y `fieldsets` en `/admin/` adaptados a `email` sin requerir `username`. |
| `catalog/permissions.py` | `IsAdminOrReadOnly` | Permite `SAFE_METHODS` (`GET`, `HEAD`, `OPTIONS`) a todos y escritura solo a `is_staff=True`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1 `CustomUserManager` y `User` (`apps/users/models.py`, líneas 6-91)

```python
class CustomUserManager(BaseUserManager):
    """Gestor personalizado de usuarios con email como identificador único."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
```

- **Líneas 10-12:** Verifica que el correo exista y normaliza la parte del dominio a minúsculas (`normalize_email`).
- **Líneas 14-17:** Hashea la contraseña con `set_password` (PBKDF2 por defecto en Django) o asigna contraseña inutilizable si no se proveyó ninguna.
- **Líneas 21-31:** En `create_superuser` garantiza que `is_staff`, `is_superuser` e `is_active` sean `True` y delega en `create_user`.

```python
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField('correo electrónico', unique=True)
    # ... campos biométricos y de objetivo ...
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
```

- **Línea 36:** `username` deja de ser único u obligatorio (a diferencia de `AbstractUser` estándar) y pasa a ser un alias opcional.
- **Línea 82-83:** `USERNAME_FIELD = 'email'` instruye a Django, SimpleJWT y al panel `/admin/` a autenticar por correo. `REQUIRED_FIELDS = []` evita que `createsuperuser` pida `username` en consola.

---

### 5.2 Serializadores de registro, perfil, auditoría y login (`apps/users/serializers.py`, líneas 5-66)

```python
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password_confirm', 'experience_level', 'training_goal', 'current_weight', 'height')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user
```

- **Seguridad por diseño:** Ni `is_staff` ni `is_superuser` figuran en `Meta.fields`, de modo que ningún usuario puede enviarlo en el payload de registro; `AbstractUser` inicializa ambos en `False`.
- **`password_confirm`:** Existe solo para validación (`write_only=True`) y se extrae con `.pop()` antes de invocar `User.objects.create_user(...)` (de lo contrario `User()` fallaría al no existir esa columna en el modelo).
- **Observación técnica:** `UserRegistrationSerializer` valida únicamente `min_length=6`, sin llamar a `django.contrib.auth.password_validation.validate_password`, por lo que los `AUTH_PASSWORD_VALIDATORS` de `settings.py` aplican en `/admin/` o formularios Django, pero no bloquean registros simples vía API.

```python
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'avatar', 'experience_level', 'training_goal', 'current_weight', 'height', 'bio', 'is_staff', 'date_joined')
        read_only_fields = ('id', 'email', 'is_staff', 'date_joined')
```

- **Protección contra escalamiento de privilegios:** Aunque `is_staff` se expone en lectura para que el cliente sepa si mostrar herramientas de administración, al estar en `read_only_fields` cualquier `PATCH /api/v1/auth/profile/` con `{"is_staff": true}` es ignorado por DRF.

```python
class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer para que el administrador pueda auditar a todos los usuarios."""
    routines_count = serializers.IntegerField(source='routines.count', read_only=True)
    workouts_count = serializers.IntegerField(source='workout_sessions.count', read_only=True)
```

- Reutiliza los `related_name` definidos en `Routine` (`routines`) y `WorkoutSession` (`workout_sessions`) para mostrar métricas de actividad por usuario. *(Nota de rendimiento: al usar `.count` en el serializer en vez de `annotate(Count(...))` en el queryset, dispara 2 consultas SQL extra por cada usuario listado).*

```python
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'username': self.user.username,
            'experience_level': self.user.experience_level,
            'is_staff': self.user.is_staff,
        }
        return data
```

- `super().validate(attrs)` autentica usando `USERNAME_FIELD` (`email`) + `password` y produce `{'refresh': '...', 'access': '...'}`. Luego añade la clave `'user'` con los datos mínimos de sesión y rol (`is_staff`).

---

### 5.3 Vistas de autenticación, perfil, peso corporal y auditoría admin (`apps/users/views.py`, líneas 15-69)

```python
class AdminUserListView(generics.ListAPIView):
    """Permite al administrador ver la lista de todos los usuarios registrados y sus métricas."""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAdminUser]
```

- **`IsAdminUser`** verifica `bool(request.user and request.user.is_staff)`. Si un usuario estándar (`is_staff=False`) consulta `GET /api/v1/auth/users/`, DRF devuelve **403 Forbidden**. Si es anónimo, devuelve **401 Unauthorized**.

```python
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generar tokens automáticamente al registrarse
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
```

- Sobreescribe `create()` para evitar que el usuario recién registrado tenga que hacer una segunda petición a `/login/`: instancia un `RefreshToken` manualmente con `RefreshToken.for_user(user)` y devuelve el perfil junto con ambos tokens bajo la clave `tokens` y HTTP `201 Created`.

```python
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
```

- No requiere `<pk>` en la URL porque `get_object()` retorna directamente el usuario dueño del JWT (`self.request.user`), impidiendo consultar o editar perfiles ajenos.

```python
class BodyWeightLogListCreateView(generics.ListCreateAPIView):
    serializer_class = BodyWeightLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BodyWeightLog.objects.filter(user=self.request.user).order_by('-date', '-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        latest = BodyWeightLog.objects.filter(user=self.request.user).order_by('-date', '-id').first()
        if latest:
            self.request.user.current_weight = latest.weight
            self.request.user.save(update_fields=['current_weight'])
```

- **Sincronización inteligente:** Tras guardar el nuevo `BodyWeightLog` asignando `user=self.request.user`, consulta el registro más reciente por `order_by('-date', '-id').first()`. De este modo, si el usuario registra un peso retroactivo de hace dos semanas, su `User.current_weight` **no** se sobrescribe con un dato viejo, sino que conserva el peso de la fecha más actual (y en empates del mismo día, el de `id` más alto). Usa `update_fields=['current_weight']` para hacer un `UPDATE` SQL mínimo.

---

### 5.4 Enrutamiento, Admin y Permiso `IsAdminOrReadOnly`

```python
# apps/users/urls.py
urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('weight-logs/', BodyWeightLogListCreateView.as_view(), name='user_weight_logs'),
    path('users/', AdminUserListView.as_view(), name='admin_user_list'),
]
```

```python
# apps/catalog/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    """
    Permite lectura (GET, HEAD, OPTIONS) a cualquier usuario,
    pero requiere permisos de administrador (is_staff=True) para crear, editar o eliminar.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
```

- **`IsAdminOrReadOnly`** protege los `ViewSet` del catálogo (`Equipment`, `MuscleGroup`, `Exercise`, `ExerciseMedia`): cualquier cliente puede consultar el catálogo (`GET`), pero solo administradores autenticados (`is_staff=True`) pueden ejecutar `POST`, `PUT`, `PATCH` o `DELETE`.
- **`apps/users/admin.py`:** Adapta `BaseUserAdmin` con `CustomUserCreationForm` y `CustomUserChangeForm` para que el panel administrativo muestre y edite usuarios por `email` (incluyendo `experience_level`, `current_weight`, `height`, `avatar`, `bio` y permisos). *(Nota: `BodyWeightLog` no está registrado en `apps/users/admin.py`).*

---

## 6. Flujo paso a paso (Registro, Login y Sincronización de Peso)

### Flujo de Registro (`POST /api/v1/auth/register/`)
1. El cliente envía `email`, `password`, `password_confirm` y campos opcionales (`username`, `experience_level`, `training_goal`, `current_weight`, `height`).
2. `UserRegistrationSerializer.validate()` comprueba que ambas contraseñas coincidan y tengan al menos 6 caracteres.
3. `UserRegistrationSerializer.create()` elimina `password_confirm` y llama `User.objects.create_user(...)`, creando el usuario con `is_staff=False`.
4. `RegisterView.create()` invoca `RefreshToken.for_user(user)` y responde `201 Created` con `user` y `tokens: {refresh, access}`.

### Flujo de Login (`POST /api/v1/auth/login/`)
1. El cliente envía `{"email": "...", "password": "..."}`.
2. `CustomTokenObtainPairSerializer.validate()` verifica la contraseña contra el hash almacenado mediante el backend de autenticación usando `USERNAME_FIELD = 'email'`.
3. Emite `refresh`, `access` y el bloque `user` (incluyendo `is_staff`).
4. El cliente guarda `access` (vigente 7 días) y `is_staff` para habilitar vistas de administrador (como el botón `👥 Ver Todos los Usuarios` en `templates/index.html`).

### Flujo de Registro de Peso (`POST /api/v1/auth/weight-logs/`)
1. El usuario autenticado envía `{"weight": 78.5, "date": "2026-11-20"}` (fecha opcional, por defecto `timezone.localdate`).
2. `BodyWeightLogSerializer` valida `weight >= 1`.
3. `BodyWeightLogListCreateView.perform_create()` asocia `user=request.user`, busca el registro con mayor `date` (y mayor `id` en caso de empate) y actualiza `User.current_weight`.

---

## 7. Conceptos y términos técnicos

- **`AbstractUser` vs `AbstractBaseUser`:** `AbstractUser` hereda toda la funcionalidad lista de Django (permisos, grupos, `is_staff`, `is_active`, `date_joined`), permitiendo añadir campos y cambiar `USERNAME_FIELD` sin reescribir el sistema completo de permisos.
- **`USERNAME_FIELD` y `REQUIRED_FIELDS`:** Configuración del modelo de usuario que indica qué campo identifica al usuario al autenticarse y qué campos adicionales solicita el comando `createsuperuser`.
- **`write_only` y `read_only_fields`:** Atributos de DRF. `write_only` (como `password`) acepta datos de entrada pero jamás los devuelve en JSON; `read_only_fields` (como `is_staff` en `UserProfileSerializer`) se muestra en JSON pero se ignora si alguien intenta alterarlo vía API.
- **Token Access vs Refresh:** El *access token* viaja en cada petición y permite acceso rápido; el *refresh token* sirve exclusivamente para solicitar un nuevo *access token* cuando este expira sin pedir contraseña nuevamente.
- **`SAFE_METHODS`:** En HTTP/DRF corresponde a `('GET', 'HEAD', 'OPTIONS')`, métodos considerados de solo lectura que no modifican el estado del servidor.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo logró el proyecto que el usuario inicie sesión con `email` en lugar de `username`?**
   - *Respuesta modelo:* Se heredó de `AbstractUser` en `apps/users/models.py`, se marcó `email` con `unique=True`, se hizo `username` opcional/no único, se fijó `USERNAME_FIELD = 'email'` y `REQUIRED_FIELDS = []`, se implementó `CustomUserManager` (`create_user` y `create_superuser`) validando el correo, y se declaró `AUTH_USER_MODEL = 'users.User'` en `settings.py`.

2. **¿Por qué un usuario recién registrado en `/api/v1/auth/register/` nunca puede auto-asignarse rol administrador?**
   - *Respuesta modelo:* Porque `UserRegistrationSerializer.Meta.fields` no incluye `is_staff` ni `is_superuser`, y `User.objects.create_user()` solo promueve esos campos en `create_superuser()`. Además, al editar su perfil en `UserProfileView`, `is_staff` está protegido en `read_only_fields`.

3. **¿Qué diferencia hay en el formato JSON que devuelven `/auth/register/` y `/auth/login/`?**
   - *Respuesta modelo:* `/auth/register/` retorna `{'user': <perfil completo>, 'tokens': {'refresh': ..., 'access': ...}}` con código `201`, mientras que `/auth/login/` (`CustomTokenObtainPairSerializer`) retorna en el nivel raíz `{'refresh': ..., 'access': ..., 'user': {'id', 'email', 'username', 'experience_level', 'is_staff'}}` con código `200`. El cliente debe contemplar ambas estructuras.

4. **¿Por qué `BodyWeightLogListCreateView.perform_create` vuelve a consultar `BodyWeightLog.objects...order_by('-date', '-id').first()` en lugar de copiar directamente el peso recién guardado a `user.current_weight`?**
   - *Respuesta modelo:* Porque el endpoint permite enviar una `date` personalizada. Si un usuario registra hoy un pesaje histórico de hace un mes, copiarlo ciegamente dañaría su `current_weight` real. Ordenar descendentemente por `-date` y `-id` asegura que `User.current_weight` siempre refleje el dato cronológicamente más reciente.

5. **¿Cuál es la diferencia entre el permiso `IsAdminUser` usado en `/api/v1/auth/users/` y `IsAdminOrReadOnly` usado en `/api/v1/catalog/`?**
   - *Respuesta modelo:* `IsAdminUser` bloquea incluso las lecturas (`GET`) a usuarios no administradores (solo un usuario con `is_staff=True` puede ver el directorio completo de usuarios). `IsAdminOrReadOnly`, en cambio, permite lecturas (`GET`, `HEAD`, `OPTIONS`) a cualquier usuario (incluso anónimo) para consultar máquinas y ejercicios, restringiendo únicamente `POST`, `PUT`, `PATCH` y `DELETE` a `is_staff=True`.

6. **¿Cómo sabe `UserProfileView` qué perfil devolver si la URL `/api/v1/auth/profile/` no lleva un `<id>`?**
   - *Respuesta modelo:* Porque `UserProfileView` sobreescribe el método `get_object(self)` de `RetrieveUpdateAPIView` para devolver directamente `self.request.user`, el cual fue resuelto previamente por `JWTAuthentication` a partir del token `Bearer`.

---

## 9. Resumen para repasar

- La autenticación se basa en **correo electrónico** (`USERNAME_FIELD = 'email'`) con UUID como clave primaria y gestión mediante `CustomUserManager`.
- `RegisterView` registra usuarios estándar (`is_staff=False`) y genera JWT al instante con `RefreshToken.for_user(user)`.
- `CustomTokenObtainPairSerializer` enriquece el login devolviendo `is_staff` para que el frontend adapte su interfaz (panel admin vs usuario).
- `BodyWeightLogListCreateView` sincroniza automáticamente `User.current_weight` con el registro más reciente por fecha.
- La autorización separa estrictamente `IsAdminUser` (auditoría de usuarios en `/auth/users/`) de `IsAdminOrReadOnly` (gestión del catálogo).
