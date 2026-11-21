# 07. Catálogo Completo de Endpoints, Validaciones, Errores y Auditoría Técnica — Apex Gym Hub

---

## 1. Propósito

Este documento reúne la referencia transversal completa de toda la API REST de **Apex Gym Hub**: la tabla maestra de **todos los endpoints** expuestos en `Gym_Backend` (método HTTP, ruta completa, vista/acción, permisos, parámetros/cuerpo, respuesta y códigos de estado), el **catálogo consolidado de validaciones y manejo de errores**, y una **auditoría técnica honesta de riesgos y deuda técnica** verificada directamente sobre el código fuente real para que los alumnos puedan responder con solvencia preguntas críticas durante la defensa oral.

---

## 2. Ubicación

Este documento consolida todos los archivos de enrutamiento, serialización, vistas y configuración bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `Gym_Backend/settings.py` y `Gym_Backend/urls.py`
- `apps/users/urls.py`, `apps/users/serializers.py`, `apps/users/views.py`, `apps/users/models.py`
- `apps/catalog/urls.py`, `apps/catalog/serializers.py`, `apps/catalog/views.py`, `apps/catalog/models.py`, `apps/catalog/permissions.py`
- `apps/routines/urls.py`, `apps/routines/serializers.py`, `apps/routines/views.py`, `apps/routines/models.py`
- `apps/tracking/urls.py`, `apps/tracking/serializers.py`, `apps/tracking/views.py`, `apps/tracking/models.py`
- `templates/index.html` y `DOCUMENTACION_CAMBIOS_CATALOGO.md`

---

## 3. Cómo se conecta

Todos los endpoints siguen el flujo unificado:

`Gym_Backend/urls.py` → `apps/<modulo>/urls.py` → `ViewSet / APIView` (autenticación global `JWTAuthentication` + permisos por vista) → `Serializer` (validación y transformación) → `Model / ORM` (`db.sqlite3`).

- **Prefijo base de API:** `/api/v1/`
- **Cabecera de autenticación:** `Authorization: Bearer <access_token>`
- **Paginación global por defecto (`settings.py`):** `PageNumberPagination` con `PAGE_SIZE = 20` (formato `{count, next, previous, results}`) en listados estándar de `ViewSet` (`ListModelMixin`) y vistas genéricas `ListAPIView`.

---

## 4. Componentes, funciones y variables clave — Tabla Maestra Completa de Endpoints

### 4.1 Rutas raíz del proyecto (`Gym_Backend/urls.py`)

| Método | URL completa | Vista | Permisos | Descripción / Respuesta | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | `TemplateView` (`index.html`) | Público | Prototipo web HTML/JS conectado a `/api/v1/`. | `200` |
| `GET` / `POST` | `/admin/` | Django Admin | Staff (`is_staff=True`) | Panel administrativo web de Django. | `200`, `302` |
| `GET` | `/media/<path>` | `static()` (solo `DEBUG=True`) | Público | Sirve archivos subidos (`equipment/`, `exercises/`, `avatars/`). | `200`, `404` |
| `GET` | `/static/<path>` | `static()` (solo `DEBUG=True`) | Público | Sirve archivos estáticos recopilados. | `200`, `404` |

---

### 4.2 Módulo Usuarios y Autenticación (`/api/v1/auth/` — `apps/users/urls.py`)

| Método | URL completa | Vista / Clase | Permisos | Parámetros / Body | Respuesta | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register/` | `RegisterView` | `AllowAny` | Body: `email`, `password` (min 6), `password_confirm`, opc: `username`, `experience_level`, `training_goal`, `current_weight`, `height`. | `{user, tokens: {refresh, access}}` | `201`, `400` |
| `POST` | `/api/v1/auth/login/` | `CustomTokenObtainPairView` | `AllowAny` | Body: `email`, `password`. | `{refresh, access, user: {id, email, username, experience_level, is_staff}}` | `200`, `400`, `401` |
| `POST` | `/api/v1/auth/token/refresh/` | `TokenRefreshView` | `AllowAny` | Body: `refresh`. | `{access, refresh}` (rota refresh token) | `200`, `400`, `401` |
| `GET` | `/api/v1/auth/profile/` | `UserProfileView` | `IsAuthenticated` | Header `Bearer`. | Perfil del usuario autenticado (`UserProfileSerializer`). | `200`, `401` |
| `PUT` / `PATCH` | `/api/v1/auth/profile/` | `UserProfileView` | `IsAuthenticated` | Body: `username`, `avatar`, `experience_level`, `training_goal`, `current_weight`, `height`, `bio`. | Perfil actualizado (`id`, `email`, `is_staff`, `date_joined` read-only). | `200`, `400`, `401` |
| `GET` | `/api/v1/auth/weight-logs/` | `BodyWeightLogListCreateView` | `IsAuthenticated` | Paginado (`?page=`). | Lista paginada ordenada por `-date, -id`. | `200`, `401` |
| `POST` | `/api/v1/auth/weight-logs/` | `BodyWeightLogListCreateView` | `IsAuthenticated` | Body: `weight` (>= 1), opc: `date` (`YYYY-MM-DD`). | `{id, weight, date, created_at}` y actualiza `user.current_weight`. | `201`, `400`, `401` |
| `GET` | `/api/v1/auth/users/` | `AdminUserListView` | `IsAdminUser` (`is_staff=True`) | Paginado (`?page=`). | Lista paginada con `routines_count` y `workouts_count`. | `200`, `401`, `403` |

---

### 4.3 Módulo Catálogo (`/api/v1/catalog/` — `apps/catalog/urls.py`)

| Método | URL completa | ViewSet / Acción | Permisos | Parámetros / Body | Respuesta | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/catalog/equipment/` | `EquipmentViewSet.list` | Público (`IsAdminOrReadOnly`) | Query: `?search=`, `?type=`, `?page=`. | Lista paginada de máquinas con `is_favorite` anotado. | `200` |
| `POST` | `/api/v1/catalog/equipment/` | `EquipmentViewSet.create` | Admin (`is_staff=True`) | Multipart/JSON: `name`, `equipment_type`, `brand`, `image` (archivo o Base64), `description`, `setup_guide`. | Máquina creada (imagen optimizada a WebP). | `201`, `400`, `401`, `403` |
| `GET` | `/api/v1/catalog/equipment/{id}/` | `EquipmentViewSet.retrieve` | Público (`IsAdminOrReadOnly`) | `id` (int). | Detalle de la máquina con `is_favorite`. | `200`, `404` |
| `PUT` / `PATCH` | `/api/v1/catalog/equipment/{id}/` | `EquipmentViewSet.update` / `partial_update` | Admin (`is_staff=True`) | Campos de máquina (`image` reemplaza y borra archivo previo). | Máquina actualizada. | `200`, `400`, `401`, `403`, `404` |
| `DELETE` | `/api/v1/catalog/equipment/{id}/` | `EquipmentViewSet.destroy` | Admin (`is_staff=True`) | `id` (int). | Sin cuerpo (`post_delete` borra imagen física). | `204`, `401`, `403`, `404` |
| `POST` | `/api/v1/catalog/equipment/{id}/favorite/` | `EquipmentViewSet.toggle_favorite` | `IsAuthenticated` | `id` (int). Sin body requerido. | `{is_favorite: true/false, equipment_id}`. | `201` (añadido), `200` (quitado), `401`, `404` |
| `GET` | `/api/v1/catalog/equipment/favorites/` | `EquipmentViewSet.list_favorites` | `IsAuthenticated` | — | Arreglo directo (sin paginar) de máquinas favoritas. | `200`, `401` |
| `GET` | `/api/v1/catalog/muscles/` | `MuscleGroupViewSet.list` | Público (`IsAdminOrReadOnly`) | Query: `?search=`, `?body_part=`, `?page=`. | Lista paginada de grupos musculares. | `200` |
| `POST` | `/api/v1/catalog/muscles/` | `MuscleGroupViewSet.create` | Admin (`is_staff=True`) | Body: `name`, `body_part`. | Grupo muscular creado. | `201`, `400`, `401`, `403` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/catalog/muscles/{id}/` | `MuscleGroupViewSet` detalle | GET público / escritura Admin | `id` (int). | Objeto músculo o `204`. | `200`, `204`, `400`, `401`, `403`, `404` |
| `GET` | `/api/v1/catalog/exercises/` | `ExerciseViewSet.list` | Público (`IsAdminOrReadOnly`) | Query: `?search=`, `?equipment=`, `?muscle=`, `?difficulty=`, `?page=`. | Lista paginada (`ExerciseListSerializer`) con `is_favorite` y cascada de imagen. | `200` |
| `POST` | `/api/v1/catalog/exercises/` | `ExerciseViewSet.create` | Admin (`is_staff=True`) | Multipart/JSON: `name`, `instructions`, opc: `equipment_id`, `muscle_id`, `video_url`, `image` (archivo/Base64), `mechanics`, `difficulty`, `tips`. | Detalle completo (`ExerciseDetailSerializer`). | `201`, `400`, `401`, `403` |
| `GET` | `/api/v1/catalog/exercises/{id}/` | `ExerciseViewSet.retrieve` | Público (`IsAdminOrReadOnly`) | `id` (UUID). | Detalle completo con `equipment`, `muscles`, `media`, `is_favorite`. | `200`, `404` |
| `PUT` / `PATCH` | `/api/v1/catalog/exercises/{id}/` | `ExerciseViewSet.update` / `partial_update` | Admin (`is_staff=True`) | Campos de ejercicio, `equipment_id`, `muscle_id`, `video_url`, `image`. | Ejercicio actualizado. | `200`, `400`, `401`, `403`, `404` |
| `DELETE` | `/api/v1/catalog/exercises/{id}/` | `ExerciseViewSet.destroy` | Admin (`is_staff=True`) | `id` (UUID). | Borrado atómico en cascada (`routine_placements`, `logged_workouts`, ejercicio + archivo). | `204`, `401`, `403`, `404` |
| `POST` | `/api/v1/catalog/exercises/{id}/favorite/` | `ExerciseViewSet.toggle_favorite` | `IsAuthenticated` | `id` (UUID). | `{is_favorite: true/false, exercise_id: "<uuid>"}`. | `201` (añadido), `200` (quitado), `401`, `404` |
| `GET` | `/api/v1/catalog/exercises/favorites/` | `ExerciseViewSet.list_favorites` | `IsAuthenticated` | — | Arreglo directo (sin paginar) de ejercicios favoritos. | `200`, `401` |
| `GET` | `/api/v1/catalog/media/` | `ExerciseMediaViewSet.list` | Público (`IsAdminOrReadOnly`) | Query: `?exercise=<uuid>`, `?page=`. | Lista paginada de multimedia. | `200` |
| `POST` | `/api/v1/catalog/media/` | `ExerciseMediaViewSet.create` | Admin (`is_staff=True`) | `media_type`, `title`, `file`, `external_url`, `thumbnail`, `order` *(nota: `exercise` falta en `fields` del serializer)*. | Material multimedia creado o error DB por `exercise_id` nulo. | `201`, `400`, `401`, `403` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/catalog/media/{id}/` | `ExerciseMediaViewSet` detalle | GET público / escritura Admin | `id` (int). | Objeto multimedia o `204`. | `200`, `204`, `400`, `401`, `403`, `404` |

---

### 4.4 Módulo Rutinas (`/api/v1/routines/` — `apps/routines/urls.py`)

| Método | URL completa | ViewSet / Acción | Permisos | Parámetros / Body | Respuesta | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/routines/routines/` | `RoutineViewSet.list` | `IsAuthenticated` | `?page=`. | Lista paginada (`RoutineListSerializer`) de rutinas propias + `is_template=True`. | `200`, `401` |
| `POST` | `/api/v1/routines/routines/` | `RoutineViewSet.create` | `IsAuthenticated` | Body: `title`, opc: `description`, `is_template`, `is_active`, `exercise_ids`/`exercise_id`/`exercise`, `sets_count`, `min_reps`, `max_reps`, `rest_seconds`, `notes`. | Rutina creada con `'Día 1'` y ejercicios iniciales (`RoutineDetailSerializer`). | `201`, `400`, `401`, `404` |
| `GET` | `/api/v1/routines/routines/{id}/` | `RoutineViewSet.retrieve` | `IsAuthenticated` | `id` (UUID). | Detalle completo de rutina (`days` → `exercises` → `target_sets`). | `200`, `401`, `404` |
| `PUT` / `PATCH` / `DELETE` | `/api/v1/routines/routines/{id}/` | `RoutineViewSet` edición/borrado | `IsAuthenticated` | `id` (UUID), campos de `Routine`. | Rutina actualizada (`200`) o eliminada (`204`). | `200`, `204`, `400`, `401`, `404` |
| `POST` | `/api/v1/routines/routines/{id}/add-exercise/` | `RoutineViewSet.add_exercise` | `IsAuthenticated` | Body: `exercise_ids`/`exercise_id`/`exercise`, opc: `sets_count` (4), `min_reps` (8), `max_reps` (12), `rest_seconds` (90), `notes`. | Rutina completa actualizada (`RoutineDetailSerializer`). | `201`, `401`, `404` |
| `POST` | `/api/v1/routines/routines/{id}/clone/` | `RoutineViewSet.clone_routine` | `IsAuthenticated` | `id` (UUID). Sin body requerido. | Nueva rutina clonada para el usuario (`"<titulo> (Mi copia)"`). | `201`, `401`, `404` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/routines/days/` y `/days/{id}/` | `RoutineDayViewSet` | `IsAuthenticated` (filtrado `routine__user`) | `id` (UUID); `name`, `order`. *(Nota: `POST` falla porque `routine` es read-only).* | Lista paginada / detalle / `204`. | `200`, `204`, `400`, `401`, `404` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/routines/exercises/` y `/exercises/{id}/` | `RoutineExerciseViewSet` | `IsAuthenticated` + `IsRoutineExerciseOwner` | `id` (UUID); `exercise`, `order`, `rest_seconds`, `tempo`, `notes`, `target_sets` o `sets_count`/`min_reps`/`max_reps`. *(Nota: `POST` directo falla por faltar `routine_day` en serializer).* | Lista paginada / detalle actualizado con reconciliación *in-place* / `204`. | `200`, `204`, `400`, `401`, `404` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/routines/sets/` y `/sets/{id}/` | `RoutineSetViewSet` | `IsAuthenticated` (filtrado `routine__user`) | `id` (int); `set_number`, `set_type`, `min_reps`, `max_reps`, `target_rpe`, `target_rir`, `target_weight`. *(Nota: `POST` directo falla por faltar `routine_exercise` en serializer).* | Lista paginada / detalle / `204`. | `200`, `204`, `400`, `401`, `404` |

---

### 4.5 Módulo Tracking (`/api/v1/tracking/` — `apps/tracking/urls.py`)

| Método | URL completa | ViewSet / Vista | Permisos | Parámetros / Body | Respuesta | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/tracking/sessions/finish/` | `WorkoutSessionViewSet.finish_active` | `IsAuthenticated` | Opc: `perceived_effort_rpe`, `notes`. | Sesión activa finalizada (`status='completed'`, `duration_seconds`). | `200`, `401`, `404` |
| `GET` | `/api/v1/tracking/sessions/` | `WorkoutSessionViewSet.list` | `IsAuthenticated` | `?page=`. | Lista paginada (`WorkoutSessionListSerializer`) del usuario. | `200`, `401` |
| `POST` | `/api/v1/tracking/sessions/` | `WorkoutSessionViewSet.create` | `IsAuthenticated` | Body (`WorkoutSessionDetailSerializer`): `routine`, `routine_day`, `title`, `start_time`, etc. | Sesión creada (si `routine=None` y `title='Entrenamiento Móvil'` -> `'cancelled'`). | `201`, `400`, `401` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/v1/tracking/sessions/{id}/` | `WorkoutSessionViewSet` detalle | `IsAuthenticated` (filtrado `user`) | `id` (UUID). | Detalle (`WorkoutSessionDetailSerializer`) / `204`. | `200`, `204`, `400`, `401`, `404` |
| `POST` | `/api/v1/tracking/sessions/start/` | `WorkoutSessionViewSet.start_session` | `IsAuthenticated` | Body opc: `routine_id`/`routine`, `title`. | Sesión activa existente (`200`) o nueva sesión creada (`201`). | `200`, `201`, `401`, `404` |
| `GET` | `/api/v1/tracking/sessions/active/` | `WorkoutSessionViewSet.active_session` | `IsAuthenticated` | — | Sesión activa (`WorkoutSessionDetailSerializer`) o `null`. | `200`, `401` |
| `POST` | `/api/v1/tracking/sessions/{id}/finish/` | `WorkoutSessionViewSet.finish_session` | `IsAuthenticated` | `id` (UUID); opc: `perceived_effort_rpe`, `notes`. | Sesión especificada marcada como `'completed'`. | `200`, `401`, `404` |
| `POST` | `/api/v1/tracking/sessions/cancel/` | `WorkoutSessionViewSet.cancel_session` | `IsAuthenticated` | — | `{status: "cancelled", id: "<uuid>" | null}`. | `200`, `401` |
| `GET` | `/api/v1/tracking/sessions/history/` | `WorkoutSessionViewSet.history` | `IsAuthenticated` | Query: `?desde`/`from`/`start_date`, `?hasta`/`to`/`end_date`, `?routine_id`/`routine`, `?page=`, `?page_size=` (max 100). | `{count, next, previous, summary: {...}, results: [...]}`. | `200`, `401` |
| `GET` | `/api/v1/tracking/sessions/{id}/detail/` | `WorkoutSessionViewSet.session_detail` | `IsAuthenticated` | `id` (UUID). | Detalle completo con cache `_build_session_exercises_data`. | `200`, `401`, `404` |
| `GET` | `/api/v1/tracking/sessions/routine-summary/` | `WorkoutSessionViewSet.routine_summary` | `IsAuthenticated` | Mismos filtros de fecha/rutina que `history/`. | Arreglo agrupado por rutina (`sessions_count`, duración total y promedio, `last_session_at`). | `200`, `401` |
| `GET` / `POST` / `PUT` / `PATCH` / `DELETE` | `/api/v1/tracking/exercises/` y `/exercises/{id}/` | `WorkoutLogExerciseViewSet` | `IsAuthenticated` (queryset filtrado `session__user`) | `session`, `exercise`, `order`, `notes`. | Ejercicios vinculados a sesiones del usuario. | `200`, `201`, `204`, `400`, `401`, `404` |
| `GET` / `POST` / `PUT` / `PATCH` / `DELETE` | `/api/v1/tracking/sets/` y `/sets/{id}/` | `WorkoutSetLogViewSet` | `IsAuthenticated` (queryset filtrado `log_exercise__session__user`) | `log_exercise`, `set_number`, `set_type`, `weight`, `reps`, `rpe`, `rir`, `is_completed`. | Serie con `estimated_1rm` (en `POST` actualiza PR `max_weight`). | `200`, `201`, `204`, `400`, `401`, `404` |
| `GET` | `/api/v1/tracking/progression/<uuid:exercise_id>/` | `ExerciseProgressionView` | `IsAuthenticated` | `exercise_id` (UUID en URL). | `{exercise_id, history, body_weight_history, records}`. | `200`, `401` |
| `GET` | `/api/v1/tracking/progress/weight-1rm/` | `Weight1RMProgressView` | `IsAuthenticated` | Query opc: `?exercise_id=<uuid>`. | `{exercise_id, weight_logs, progress}`. | `200`, `401` |

---

## 5. Explicación del código línea por línea o bloque por bloque (Catálogo de Validaciones y Códigos de Error)

### 5.1 Validaciones implementadas en Serializers y Modelos

1. **Autenticación y Usuarios (`apps/users/`):**
   - `CustomUserManager.create_user`: lanza `ValueError("El email es obligatorio")` si falta `email`.
   - `UserRegistrationSerializer`: `password` exige `min_length=6`; `validate()` exige `attrs['password'] == attrs['password_confirm']` o responde `400 Bad Request` con `{"password": "Las contraseñas no coinciden."}`.
   - `BodyWeightLogSerializer`: exige `weight` con `min_value=1` (`max_digits=5, decimal_places=2`, máximo `999.99`).
   - `User.email` es `unique=True`: correos repetidos producen `400 Bad Request` en el serializador.

2. **Catálogo y Multimedia (`apps/catalog/`):**
   - `validate_image`: máximo `5 MB` (`5 * 1024 * 1024` bytes) y extensión estricta `.jpg`, `.jpeg`, `.png`, `.webp`.
   - `FlexibleImageField`: valida Base64 estricto con `validate=True`; si está malformado, vacío o Pillow no reconoce la imagen, dispara `self.fail('invalid_image')` (`400 Bad Request`).
   - `Equipment.name`, `MuscleGroup.name`, `Exercise.name` y `Exercise.slug` son `unique=True`.
   - `ExerciseDetailSerializer`: `video_url` usa `serializers.URLField` (`400` si no tiene esquema HTTP/HTTPS válido); `equipment_id` y `muscle_id` usan `PrimaryKeyRelatedField` (`400` si el ID no existe).
   - `settings.py`: `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` limitan la carga a `10 MB`.

3. **Rutinas (`apps/routines/`):**
   - `RoutineSetSerializer`: `min_reps` y `max_reps` con `min_value=1`; `validate()` exige `min_reps <= max_reps` (`400` con `{'min_reps': 'min_reps no puede ser mayor que max_reps.'}`).
   - `RoutineExerciseSerializer`: `sets_count`, `min_reps`, `max_reps` con `min_value=1`; `validate()` y `update()` verifican `min_reps <= max_reps` tanto globalmente como por cada serie existente.
   - `RoutineViewSet.add_exercise`: si `exercise_id` no existe en `catalog.Exercise`, `get_object_or_404` devuelve `404 Not Found`.

4. **Tracking (`apps/tracking/`):**
   - `WorkoutSessionViewSet.start_session`: si `routine_id` no existe o es rutina privada de otro usuario, devuelve `404` (`{'detail': 'Rutina no encontrada.'}`).
   - `WorkoutSessionViewSet.finish_active`: si el usuario no tiene sesión activa, devuelve `404` (`{'detail': 'No hay sesión activa.'}`).
   - `CompletedSessionPagination`: acota `page_size` a un máximo de `100` (`max_page_size = 100`).
   - `WorkoutSetLog`: `reps` y `set_number` son `PositiveSmallIntegerField` (no negativos). `WorkoutSetLog.estimated_1rm` restringe Brzycki a `0 < reps < 37`.

### 5.2 Guía rápida de códigos HTTP en el proyecto

| Código | Significado en Apex Gym Hub | Causas típicas |
| :--- | :--- | :--- |
| `200 OK` | Lectura o actualización exitosa | `GET`, `PUT`, `PATCH`, login, refresh, `finish`, `cancel`, `favorite` al quitar. |
| `201 Created` | Recurso creado | `register`, `POST` estándar, `add-exercise`, `clone`, `start` (nueva sesión), `favorite` al añadir. |
| `204 No Content` | Eliminación exitosa | `DELETE` en cualquier `ModelViewSet`. |
| `400 Bad Request` | Error de validación | Contraseñas distintas, `min_reps > max_reps`, Base64 inválido, imagen > 5 MB, JSON malformado. |
| `401 Unauthorized` | No autenticado / JWT inválido | Token faltante, malformado o expirado, o credenciales erróneas en `/login/`. |
| `403 Forbidden` | Sin permisos suficientes | Usuario normal (`is_staff=False`) intentando `GET /auth/users/` o escribir en `/catalog/*`. |
| `404 Not Found` | Recurso inexistente o ajeno | UUID no encontrado, ejercicio inexistente en `add-exercise`, no hay sesión activa en `sessions/finish/`, o recurso filtrado por otro usuario. |

---

## 6. Flujo paso a paso (Auditoría Técnica: Riesgos, Bugs y Deuda Técnica Real)

A continuación se documentan los hallazgos reales verificados directamente en el código fuente del proyecto (útiles para demostrar pensamiento crítico y criterio de ingeniero senior ante el jurado):

### A. Riesgos Críticos de Seguridad y Configuración (`settings.py` y vistas)
1. **Secretos y modo debug expuestos (`Gym_Backend/settings.py`):** `SECRET_KEY` está codificada en texto plano (`django-insecure-...`), `DEBUG = True`, `ALLOWED_HOSTS = ['*']` y `CORS_ALLOW_ALL_ORIGINS = True`. En `templates/index.html` y `README.md` aparecen credenciales de prueba (`admin@gym.com` / `Admin123!`).
2. **Permisos faltantes sobre plantillas en `RoutineViewSet` (`apps/routines/views.py`):** `get_queryset()` incluye `Q(user=user) | Q(is_template=True)` y la clase solo exige `IsAuthenticated`. Sin una clase `has_object_permission` que bloquee mutaciones cuando `obj.user_id != request.user.id`, cualquier usuario autenticado podría modificar (`PATCH`/`PUT`), agregar ejercicios o eliminar una plantilla pública (`is_template=True`).
3. **Falta de validación de propiedad en creación de `tracking` (`apps/tracking/views.py`):**
   - `WorkoutSessionViewSet` permite `POST /api/v1/tracking/sessions/` directamente: un usuario podría crear múltiples sesiones `'active'` saltándose `start_session`, o pasar el UUID de una `routine` privada de otro usuario.
   - `WorkoutLogExerciseViewSet` y `WorkoutSetLogViewSet` filtran `get_queryset()` por usuario para lectura/edición, pero no validan en `perform_create()` ni en `validate()` que la `session` o `log_exercise` enviada en el `POST` pertenezca a `request.user`.
4. **Tokens JWT de larga duración sin lista negra (`settings.py`):** `ACCESS_TOKEN_LIFETIME` dura 7 días y `BLACKLIST_AFTER_ROTATION = False`, impidiendo revocar tokens comprometidos antes de su expiración natural.
5. **Validadores de contraseña omitidos en registro API (`apps/users/serializers.py`):** `UserRegistrationSerializer` solo valida `min_length=6`, sin invocar `AUTH_PASSWORD_VALIDATORS` definidos en `settings.py`.

### B. Deuda Técnica de Base de Datos y Migraciones
6. **Migraciones desincronizadas en `routines` y `tracking`:** En `apps/routines/models.py` (`RoutineExercise.exercise`) y `apps/tracking/models.py` (`WorkoutLogExercise.exercise`) se cambió `on_delete=models.PROTECT` a `on_delete=models.CASCADE`, pero las migraciones existentes (`0002_initial.py`) siguen registrando `PROTECT`. No se han generado las migraciones pendientes.
7. **Migración en tiempo de petición (`_ensure_tracking_migrations()` en `apps/tracking/views.py`):** Ejecuta introspección de esquema y `call_command('migrate', ...)` dentro de `WorkoutSessionViewSet.initial()` tragándose errores con `except Exception: pass`. En producción debe eliminarse.
8. **Endpoints `POST` secundarios bloqueados por omisión de FK en serializers:**
   - `POST /api/v1/routines/days/` falla porque `RoutineDaySerializer` tiene `routine` en `read_only_fields` y `RoutineDayViewSet` no tiene `perform_create`.
   - `POST /api/v1/routines/exercises/` falla porque `RoutineExerciseSerializer` omite `routine_day` en `Meta.fields`.
   - `POST /api/v1/routines/sets/` falla porque `RoutineSetSerializer` omite `routine_exercise` en `Meta.fields`.
   - `POST /api/v1/catalog/media/` falla porque `ExerciseMediaSerializer` omite `exercise` en `Meta.fields`.

### C. Deuda Técnica de Mantenibilidad, Rendimiento y Datos
9. **Ausencia de `requirements.txt` y de pruebas (`tests.py`):** No existe archivo de dependencias fijadas (`Django 6.1+`, `DRF`, `SimpleJWT`, `django-cors-headers`, `Pillow`) ni tests unitarios o de integración en ninguna de las 4 apps.
10. **`PersonalRecord` incompleto (`apps/tracking/views.py`):** `WorkoutSetLogViewSet.perform_create` solo actualiza `record_type='max_weight'`, nunca calcula ni guarda automáticamente `record_type='1rm'`, y no recalcula los récords cuando el usuario edita o borra una serie errónea.
11. **Consultas N+1 en `AdminUserListSerializer` (`apps/users/serializers.py`):** `source='routines.count'` y `source='workout_sessions.count'` disparan 2 consultas SQL extra por usuario en `GET /api/v1/auth/users/` en lugar de usar `.annotate(Count(...))` en `AdminUserListView.queryset`.
12. **Limpieza parcial de archivos multimedia e inconsistencias menores:**
    - `ExerciseMedia` (`file`, `thumbnail`) y `User.avatar` no ejecutan `validate_image`, `optimize_image` ni limpieza `post_delete`.
    - `Exercise.save()` no actualiza el `slug` si cambia el nombre ni maneja colisiones de `slugify` (lo que arrojaría `IntegrityError` 500 en lugar de 400).
    - `User.height` tiene `verbose_name='Estatura (cm)'` con `DecimalField(max_digits=5, decimal_places=2)` sin validadores de rango mínimo/máximo.
    - `DOCUMENTACION_CAMBIOS_CATALOGO.md` en la raíz del proyecto describe contratos antiguos (`id`/`order` en `ExerciseMuscleSerializer`, `{"status": "added"}` en `toggle_favorite`) que no coinciden con la implementación vigente de `apps/catalog/`.
    - `BodyWeightLog`, `UserFavoriteEquipment` y `UserFavoriteExercise` no están registrados en `admin.py`.

---

## 7. Conceptos y términos técnicos

- **Deuda técnica:** Compromisos o atajos en diseño, configuración, pruebas o sincronización (como omitir `requirements.txt`, `tests.py` o migraciones pendientes) que aceleraron el desarrollo inicial pero requieren corrección antes de escalar a producción.
- **IDOR / Broken Object Level Authorization (BOLA):** Vulnerabilidad en APIs cuando un usuario autenticado puede acceder o modificar un recurso perteneciente a otro usuario o público solo por conocer su ID (por ejemplo, mutar una plantilla pública en `RoutineViewSet` o insertar sets en una sesión ajena).
- **Problema N+1:** Patrón ineficiente donde para listar $N$ objetos se ejecuta 1 consulta principal más $N$ (o $2N$) consultas adicionales en el serializador (como en `AdminUserListSerializer`).
- **Idempotencia:** Capacidad de repetir la misma operación obteniendo el mismo resultado controlado (como `sessions/start/` devolviendo la sesión activa existente o `seed_catalog`).
- **Integración Referencial (`IntegrityError`):** Error de base de datos cuando una operación intenta dejar una columna `NOT NULL` vacía (como `POST /catalog/media/` sin `exercise`) o violar una restricción `UNIQUE`.

---

## 8. Posibles preguntas del profesor

1. **Si te pidieran pasar este backend a producción mañana mismo, ¿cuáles son los 3 cambios obligatorios que harías primero?**
   - *Respuesta modelo:* Primero, externalizar `SECRET_KEY`, poner `DEBUG = False`, restringir `ALLOWED_HOSTS` y `CORS_ALLOW_ALL_ORIGINS`, y migrar de SQLite a PostgreSQL creando un `requirements.txt`. Segundo, cerrar las brechas de autorización por objeto (`IsOwnerOrReadOnly` en `RoutineViewSet` para proteger `is_template=True`, y validar propiedad de `session`/`log_exercise` al crear registros en `tracking`). Tercero, generar las migraciones pendientes de `routines`/`tracking` y retirar `_ensure_tracking_migrations()` de la vista.

2. **¿Por qué algunos endpoints de `DefaultRouter` como `POST /api/v1/routines/days/` o `POST /api/v1/catalog/media/` no funcionan directamente aunque usan `ModelViewSet`?**
   - *Respuesta modelo:* Porque aunque los `ViewSet` habilitan `POST` al heredar de `ModelViewSet`, los serializers (`RoutineDaySerializer`, `RoutineExerciseSerializer`, `RoutineSetSerializer`, `ExerciseMediaSerializer`) omiten o marcan como `read_only` la clave foránea hacia su modelo padre. Sin asignar esa relación en `perform_create` o exponerla validada en el serializer, SQLite rechaza el `INSERT` por restricción `NOT NULL`.

3. **¿Qué diferencia hay entre el error `401 Unauthorized` y `403 Forbidden` en esta API?**
   - *Respuesta modelo:* `401` ocurre cuando no hay credenciales válidas (falta el header `Authorization: Bearer ...` o el JWT expiró/es inválido). `403` ocurre cuando el usuario **sí** está autenticado correctamente con un JWT válido, pero su rol no tiene permiso para esa acción, por ejemplo un usuario con `is_staff=False` intentando acceder a `GET /api/v1/auth/users/` o crear un ejercicio en `POST /api/v1/catalog/exercises/`.

4. **¿Qué sucede en `AdminUserListView` si hay 500 usuarios registrados y cómo lo optimizarías?**
   - *Respuesta modelo:* Actualmente `AdminUserListSerializer` usa `source='routines.count'` y `source='workout_sessions.count'`, lo que dispara 2 consultas SQL por cada usuario de la página (41 consultas para una página de 20 usuarios). Lo optimizaría anotando los conteos directamente en `AdminUserListView.queryset` con `User.objects.annotate(routines_count=Count('routines', distinct=True), workouts_count=Count('workout_sessions', distinct=True))`.

5. **¿Qué pasa actualmente con los récords personales (`PersonalRecord`) si un usuario se equivoca y edita o borra una serie de 200 kg que había anotado por error?**
   - *Respuesta modelo:* El récord `max_weight` de 200 kg permanecería guardado en `PersonalRecord` porque `WorkoutSetLogViewSet` solo verifica y actualiza el récord en `perform_create` (`POST`), no en `perform_update` (`PATCH`/`PUT`) ni `perform_destroy` (`DELETE`). Además, el campo `record_type='1rm'` aún no se actualiza automáticamente.

6. **¿Cómo garantizarías calidad continua si el equipo sigue ampliando Apex Gym Hub?**
   - *Respuesta modelo:* Añadiendo una suite de pruebas automatizadas en los `tests.py` de las 4 apps usando `APITestCase` de DRF (cubriendo permisos admin vs usuario, aislamiento multiusuario, cálculo de Brzycki, clonación de rutinas y subida Base64), junto con un `requirements.txt` fijado y verificación de `makemigrations --check` en CI.

---

## 9. Resumen para repasar

- La API expone recursos bajo 4 prefijos (`/api/v1/auth/`, `/api/v1/catalog/`, `/api/v1/routines/`, `/api/v1/tracking/`) más `/`, `/admin/` y `/media/`.
- El manejo de errores sigue estándares REST/DRF (`400` validación, `401` JWT inválido/ausente, `403` falta de privilegios `is_staff`, `404` recurso inexistente o fuera del queryset del usuario).
- Las fortalezas arquitectónicas clave incluyen autenticación JWT con email, optimización WebP + Base64, subconsultas `Exists` sin N+1 en catálogo, reconciliación *in-place* de series y analítica de 1RM/fuerza relativa.
- Las principales áreas de mejora para producción son: variables de entorno (`SECRET_KEY`, `DEBUG`, CORS), permisos por objeto en `RoutineViewSet` y `tracking` `POST`, sincronización de migraciones pendientes, eliminación de `_ensure_tracking_migrations()`, `requirements.txt` y pruebas automatizadas.
