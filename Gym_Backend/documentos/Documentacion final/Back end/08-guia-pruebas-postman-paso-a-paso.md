# 08 — Guía Completa de Pruebas en Postman (Paso a Paso)

Esta guía documenta **las 68 peticiones** de la API de **GymProyecto** incluidas en la colección:
`Gym_Backend/postman/GymProyecto_API_Completa.postman_collection.json`

Explica **qué hace cada consulta**, **qué método HTTP usa**, **qué permisos requiere**, **en qué orden ejecutarlas** y **qué JSON enviar** para probar toda la API de principio a fin sin errores.

---

## 1. Preparación rápida en Postman

1. **Enciende Django** en tu terminal:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
2. **Importa la colección en Postman:**
   - Abre Postman → botón **Import** → selecciona `GymProyecto_API_Completa.postman_collection.json`.
3. **Variables automáticas:**
   - `{{base_url}}` ya apunta a `http://127.0.0.1:8000/api/v1`.
   - `{{access_token}}` y `{{refresh_token}}` se guardan **solos** al ejecutar **Registrar** o **Login**, y Postman los manda automáticamente como `Authorization: Bearer {{access_token}}` en todas las rutas protegidas.
   - Los IDs (`{{muscle_id}}`, `{{equipment_id}}`, `{{exercise_id}}`, `{{routine_id}}`, `{{session_id}}`, `{{log_exercise_id}}`, `{{set_log_id}}`) también se guardan automáticamente al listar o crear registros.

### Significado rápido de los métodos HTTP
| Método | ¿Qué significa? | Código esperado al funcionar |
| :--- | :--- | :--- |
| **`GET`** | **Consultar / Leer** datos (no modifica nada) | `200 OK` |
| **`POST`** | **Crear** un registro nuevo o ejecutar una acción (login, favorito, iniciar/finalizar sesión) | `201 Created` o `200 OK` |
| **`PATCH`** | **Editar / Actualizar** parcialmente un registro existente | `200 OK` |
| **`DELETE`** | **Eliminar** un registro de la base de datos | `204 No Content` |

### Permisos
- **Público:** No necesita token.
- **Autenticado:** Necesita token JWT (cualquier usuario logueado).
- **Solo Admin:** Necesita token JWT de un usuario con `is_staff = True` (creado con `createsuperuser` o marcado como staff en `/admin/`).

> **Tip de orden:** En cada bloque, si quieres seguir usando el ID recién creado en los pasos siguientes, **deja el `DELETE` hasta el final** de tus pruebas (o vuelve a ejecutar el `GET` para recargar otro ID válido).

---

## Fase 1 — Auth y Usuarios (`/api/v1/auth/`)
> **Empieza SIEMPRE aquí** para obtener tu token JWT. Si vas a probar creación/edición de máquinas y ejercicios (Fases 2, 3 y 4), inicia sesión en el paso 2 con tu cuenta **Admin**.

### Paso 1.1 — Registrar Usuario
- **Tipo:** `POST` *(Crear cuenta)* | **Permiso:** Público
- **URL:** `{{base_url}}/auth/register/`
- **Qué hace:** Crea un usuario nuevo en la tabla `User` y devuelve sus tokens JWT. Guarda automáticamente `{{access_token}}` y `{{refresh_token}}`.
- **Body (JSON):**
  ```json
  {
    "email": "nuevo_atleta@gym.com",
    "username": "NuevoAtleta",
    "password": "Password123!",
    "password_confirm": "Password123!",
    "experience_level": "beginner",
    "training_goal": "hypertrophy",
    "current_weight": "75.50",
    "height": "1.78"
  }
  ```
- **Esperado:** `201 Created` con `user` y `tokens`.

### Paso 1.2 — Login (Obtener Token JWT)
- **Tipo:** `POST` *(Autenticación)* | **Permiso:** Público
- **URL:** `{{base_url}}/auth/login/`
- **Qué hace:** Valida correo y contraseña, y devuelve `access` (válido 7 días) y `refresh` (válido 30 días). Guarda ambos tokens automáticamente.
- **Body (JSON):**
  ```json
  {
    "email": "nuevo_atleta@gym.com",
    "password": "Password123!"
  }
  ```
  *(Cambia el email y password por tu cuenta Admin si vas a probar los `POST`/`PATCH`/`DELETE` del catálogo).*
- **Esperado:** `200 OK`.

### Paso 1.3 — Refrescar Token JWT
- **Tipo:** `POST` *(Renovar sesión)* | **Permiso:** Público (usa `refresh_token`)
- **URL:** `{{base_url}}/auth/token/refresh/`
- **Qué hace:** Genera un nuevo `access_token` sin volver a escribir la contraseña.
- **Body (JSON):** `{ "refresh": "{{refresh_token}}" }`
- **Esperado:** `200 OK`.

### Paso 1.4 — Ver Mi Perfil
- **Tipo:** `GET` *(Consultar)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/profile/`
- **Qué hace:** Devuelve todos los datos del usuario dueño del token (email, peso, estatura, objetivo, si es admin, etc.).
- **Esperado:** `200 OK`.

### Paso 1.5 — Editar Mi Perfil
- **Tipo:** `PATCH` *(Actualizar)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/profile/`
- **Qué hace:** Modifica los campos que envíes del perfil del usuario actual.
- **Body (JSON):**
  ```json
  {
    "username": "AtletaPro",
    "experience_level": "intermediate",
    "training_goal": "strength",
    "current_weight": "76.20",
    "height": "1.78",
    "bio": "Entrenando fuerza e hipertrofia 4 días a la semana."
  }
  ```
- **Esperado:** `200 OK`.

### Paso 1.6 — Ver Mis Preferencias (Settings)
- **Tipo:** `GET` *(Consultar)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/settings/`
- **Qué hace:** Obtiene las preferencias persistidas del usuario autenticado (`theme_mode`, `accent_color`, `language`). Si aún no existen en el servidor, las crea automáticamente con sus valores por defecto (`dark`, `emerald`, `es`).
- **Esperado:** `200 OK`.

### Paso 1.7 — Editar Mis Preferencias (Settings)
- **Tipo:** `PATCH` *(Actualizar)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/settings/`
- **Qué hace:** Guarda en el servidor el modo de tema, color de acento o idioma elegidos por el usuario.
- **Valores válidos:**
  - `theme_mode`: `dark`, `light`, `system`
  - `accent_color`: `emerald`, `ocean`, `amber`, `violet`, `crimson`
  - `language`: `es`, `en`, `system`
- **Body (JSON):**
  ```json
  {
    "theme_mode": "light",
    "accent_color": "ocean",
    "language": "en"
  }
  ```
- **Esperado:** `200 OK`.

### Paso 1.8 — Listar Historial de Peso Corporal
- **Tipo:** `GET` *(Consultar)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/weight-logs/`
- **Qué hace:** Trae el historial de registros de peso corporal del usuario ordenados del más reciente al más antiguo.
- **Esperado:** `200 OK`.

### Paso 1.9 — Registrar Peso Corporal
- **Tipo:** `POST` *(Crear)* | **Permiso:** Autenticado
- **URL:** `{{base_url}}/auth/weight-logs/`
- **Qué hace:** Agrega un nuevo peso al historial y actualiza automáticamente `current_weight` en el perfil.
- **Body (JSON):** `{ "weight": "76.40", "date": "2026-11-23" }`
- **Esperado:** `201 Created`.

### Paso 1.10 — Listar Todos los Usuarios (Panel Admin)
- **Tipo:** `GET` *(Consultar)* | **Permiso:** Solo Admin
- **URL:** `{{base_url}}/auth/users/`
- **Qué hace:** Lista todos los usuarios registrados junto con su conteo de rutinas y entrenamientos.
- **Esperado:** `200 OK` (si no eres admin devuelve `403 Forbidden`).

---

## Fase 2 — Catálogo: Grupos Musculares (`/api/v1/catalog/muscles/`)
> Ejecuta primero el `GET` para guardar un `{{muscle_id}}` real antes de crear ejercicios.

| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **2.1** | `GET` | `/catalog/muscles/?page=1&page_size=20` | Público | Lista grupos musculares (soporta `?search=` y `?body_part=`). Guarda el primer `{{muscle_id}}`. |
| **2.2** | `GET` | `/catalog/muscles/{{muscle_id}}/` | Público | Muestra el detalle de un grupo muscular específico. |
| **2.3** | `POST` | `/catalog/muscles/` | Solo Admin | Crea un grupo muscular nuevo (`{ "name": "Antebrazo", "body_part": "Brazo" }`). Guarda su `{{muscle_id}}`. |
| **2.4** | `PATCH` | `/catalog/muscles/{{muscle_id}}/` | Solo Admin | Edita el nombre o zona anatómica del grupo muscular. |
| **2.5** | `DELETE` | `/catalog/muscles/{{muscle_id}}/` | Solo Admin | Elimina el grupo muscular *(ejecutar al final o sobre uno de prueba)*. |

---

## Fase 3 — Catálogo: Máquinas y Equipos (`/api/v1/catalog/equipment/`)
> Ejecuta el `GET` o el `POST` para tener un `{{equipment_id}}` válido antes de pasar a Ejercicios.

| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **3.1** | `GET` | `/catalog/equipment/?page=1&page_size=10` | Público | Lista máquinas paginadas (soporta `?search=`, `?type=plate_loaded`, `?page=`, `?page_size=`). Guarda el primer `{{equipment_id}}`. |
| **3.2** | `GET` | `/catalog/equipment/{{equipment_id}}/` | Público | Muestra la ficha completa de una máquina (marca, guía de ajuste, foto, si es favorita). |
| **3.3** | `POST` | `/catalog/equipment/` | Solo Admin | Crea una máquina nueva (acepta imagen opcional en Base64 o multipart). Guarda `{{equipment_id}}`. |
| **3.4** | `PATCH` | `/catalog/equipment/{{equipment_id}}/` | Solo Admin | Actualiza datos o foto de la máquina (borra la foto vieja y optimiza la nueva a WebP). |
| **3.5** | `POST` | `/catalog/equipment/{{equipment_id}}/favorite/` | Autenticado | **Toggle favorito:** si no era favorita la agrega (`201`); si ya era favorita la quita (`200`). |
| **3.6** | `GET` | `/catalog/equipment/favorites/` | Autenticado | Devuelve solo las máquinas marcadas como favoritas por el usuario actual. |
| **3.7** | `DELETE` | `/catalog/equipment/{{equipment_id}}/` | Solo Admin | Elimina la máquina y su foto del disco *(ejecutar al final o sobre una máquina de prueba)*. |

**Ejemplo de Body para Paso 3.3 (`POST /catalog/equipment/`):**
```json
{
  "name": "Prensa Hack 45",
  "equipment_type": "plate_loaded",
  "brand": "Hammer Strength",
  "description": "Máquina guiada para enfoque de cuádriceps.",
  "setup_guide": "Coloca los pies al ancho de hombros en la parte media-baja."
}
```
*(Valores válidos de `equipment_type`: `plate_loaded`, `pin_selected`, `cable`, `smith`, `free_weight`, `bodyweight`, `cardio`, `accessory`).*

---

## Fase 4 — Catálogo: Ejercicios y Multimedia (`/api/v1/catalog/exercises/` y `/media/`)
> Usa `{{equipment_id}}` y `{{muscle_id}}` de las fases anteriores, y guarda `{{exercise_id}}` para Rutinas y Tracking.

| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **4.1** | `GET` | `/catalog/exercises/?page=1&page_size=10` | Público | Lista ejercicios paginados (soporta `?search=`, `?equipment=`, `?muscle=`, `?difficulty=`, `?page=`, `?page_size=`). Guarda `{{exercise_id}}`. |
| **4.2** | `GET` | `/catalog/exercises/{{exercise_id}}/` | Público | Devuelve la ficha completa: máquina, músculos, instrucciones, multimedia, `image` y `own_image`. |
| **4.3** | `POST` | `/catalog/exercises/` | Solo Admin | Crea un ejercicio nuevo, asigna su músculo principal (`muscle_id`) y crea el video (`video_url`) automáticamente. Guarda `{{exercise_id}}`. |
| **4.4** | `PATCH` | `/catalog/exercises/{{exercise_id}}/` | Solo Admin | Edita el ejercicio (nombre, máquina, músculo, instrucciones, video o foto). |
| **4.5** | `POST` | `/catalog/exercises/{{exercise_id}}/favorite/` | Autenticado | **Toggle favorito:** marca o desmarca el ejercicio como favorito del usuario. |
| **4.6** | `GET` | `/catalog/exercises/favorites/` | Autenticado | Lista solo los ejercicios favoritos del usuario autenticado. |
| **4.7** | `DELETE` | `/catalog/exercises/{{exercise_id}}/` | Solo Admin | Elimina el ejercicio y limpia sus referencias en rutinas y sesiones *(dejar al final o usar un ejercicio de prueba)*. |
| **4.8** | `GET` | `/catalog/media/?exercise={{exercise_id}}` | Público | Lista el material multimedia (videos/fotos/GIFs) de ejercicios. |
| **4.9** | `POST` | `/catalog/media/` | Solo Admin | Agrega un nuevo video/foto/GIF a un ejercicio (`exercise` UUID requerido). Guarda `{{media_id}}`. |
| **4.10** | `PATCH` | `/catalog/media/{{media_id}}/` | Solo Admin | Edita título u orden de un archivo multimedia. |
| **4.11** | `DELETE` | `/catalog/media/{{media_id}}/` | Solo Admin | Elimina un elemento multimedia. |

**Ejemplo de Body para Paso 4.3 (`POST /catalog/exercises/`):**
```json
{
  "name": "Sentadilla Hack en Máquina",
  "equipment_id": "{{equipment_id}}",
  "muscle_id": "{{muscle_id}}",
  "mechanics": "compound",
  "difficulty": "intermediate",
  "instructions": "1. Apoya la espalda firme.\n2. Baja a 90 grados.\n3. Empuja sin bloquear rodillas.",
  "tips": "Mantén los talones pegados a la plataforma.",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

---

## Fase 5 — Rutinas (`/api/v1/routines/`)
> Requiere estar autenticado y tener un `{{exercise_id}}` de la Fase 4.

| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **5.1** | `GET` | `/routines/routines/` | Autenticado | Lista tus rutinas y plantillas públicas. Guarda `{{routine_id}}`, `{{routine_day_id}}` y `{{routine_exercise_id}}`. |
| **5.2** | `POST` | `/routines/routines/` | Autenticado | Crea una rutina nueva junto con `Day 1`, los ejercicios en `exercise_ids` y sus series objetivo. Guarda `{{routine_id}}`, `{{routine_day_id}}` y `{{routine_exercise_id}}`. |
| **5.3** | `GET` | `/routines/routines/{{routine_id}}/` | Autenticado | Obtiene el detalle completo de una rutina con sus días, ejercicios y sets. |
| **5.4** | `PATCH` | `/routines/routines/{{routine_id}}/` | Autenticado | Edita título o descripción de la rutina. |
| **5.5** | `POST` | `/routines/routines/{{routine_id}}/add-exercise/` | Autenticado | Agrega uno o más ejercicios con sus series (`sets_count`), `min_reps`, `max_reps` y `rest_seconds` *(rechaza ejercicios duplicados en la misma rutina con `400`)*. |
| **5.6** | `POST` | `/routines/routines/{{routine_id}}/clone/` | Autenticado | Crea una copia personal completa de una rutina o plantilla. |
| **5.7** | `DELETE` | `/routines/routines/{{routine_id}}/` | Autenticado | Elimina la rutina completa *(requiere que no tenga una sesión activa en curso → `400`; dejar para el final si la vas a usar en Tracking)*. |
| **5.8** | `GET` | `/routines/days/` | Autenticado | Lista los días de tus rutinas. |
| **5.9** | `PATCH` | `/routines/days/{{routine_day_id}}/` | Autenticado | Cambia el nombre u orden de un día de rutina. |
| **5.10** | `GET` | `/routines/exercises/` | Autenticado | Lista todos los ejercicios asignados a tus rutinas. Guarda `{{routine_exercise_id}}`. |
| **5.11** | `PATCH` | `/routines/exercises/{{routine_exercise_id}}/` | Autenticado | Actualiza `sets_count`, `min_reps` y `max_reps` de un ejercicio dentro de la rutina. |
| **5.12** | `DELETE` | `/routines/exercises/{{routine_exercise_id}}/` | Autenticado | Quita ese ejercicio de la rutina. |
| **5.13** | `GET` | `/routines/sets/` | Autenticado | Lista las configuraciones de series objetivo. Guarda `{{routine_set_id}}`. |
| **5.14** | `PATCH` | `/routines/sets/{{routine_set_id}}/` | Autenticado | Edita una serie individual (`min_reps`, `max_reps`, `target_rpe`, `target_weight`). |
| **5.15** | `DELETE` | `/routines/sets/{{routine_set_id}}/` | Autenticado | Elimina una serie objetivo. |

---

## Fase 6 — Tracking: Sesiones, Marcas y Progreso (`/api/v1/tracking/`)
> Simula un entrenamiento real completo: **Iniciar sesión → Registrar ejercicio → Registrar serie/marca → Finalizar → Consultar historial y gráficas 1RM**.

### Flujo de entrenamiento en vivo (en este orden)
| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **6.1** | `POST` | `/tracking/sessions/start/` | Autenticado | Inicia una sesión con cronómetro vinculada a `{{routine_id}}` *(requiere rutina con ≥1 ejercicio → `400`, y devuelve `409` si ya hay otra rutina activa)*. Guarda `{{session_id}}`. |
| **6.2** | `GET` | `/tracking/sessions/active/` | Autenticado | Consulta si hay una sesión activa en curso (devuelve la sesión o `null`). |
| **6.3** | `POST` | `/tracking/exercises/` | Autenticado | Vincula `{{exercise_id}}` dentro de `{{session_id}}` *(debe pertenecer a la rutina activa)*. Guarda `{{log_exercise_id}}`. |
| **6.4** | `POST` | `/tracking/sets/` | Autenticado | Registra una serie real (`weight`, `reps`, `rpe`). Calcula automáticamente `estimated_1rm` y actualiza el récord personal (PR). Guarda `{{set_log_id}}`. |
| **6.5** | `PATCH` | `/tracking/sets/{{set_log_id}}/` | Autenticado | Edita el peso, repeticiones o RPE de una serie registrada y recalcula el PR. |
| **6.6** | `DELETE` | `/tracking/sets/{{set_log_id}}/` | Autenticado | Elimina una serie registrada y recalcula el PR *(opcional; si borras todas, vuelve a correr 6.4 antes de finalizar)*. |
| **6.7** | `POST` | `/tracking/sessions/finish/` | Autenticado | Finaliza la sesión activa, calcula `duration_seconds` y la marca como `completed` *(exige ≥1 serie registrada → `400`)*. |

### Acciones extra de sesiones, historial y gráficas
| Orden | Tipo | URL | Permiso | Qué hace |
| :--- | :--- | :--- | :--- | :--- |
| **6.8** | `POST` | `/tracking/sessions/{{session_id}}/finish/` | Autenticado | Finaliza una sesión específica activa pasándole su UUID *(exige ≥1 serie registrada → `400`)*. |
| **6.9** | `POST` | `/tracking/sessions/cancel/` | Autenticado | Descarta la sesión activa marcándola como `cancelled`. |
| **6.10** | `GET` | `/tracking/sessions/` | Autenticado | Lista todas las sesiones del usuario (activas, completadas o canceladas). |
| **6.11** | `POST` | `/tracking/sessions/` | Autenticado | Crea una sesión manual directamente. Guarda `{{session_id}}`. |
| **6.12** | `GET` | `/tracking/sessions/{{session_id}}/` | Autenticado | Detalle completo de una sesión (incluye ejercicios planeados vs registrados). |
| **6.13** | `GET` | `/tracking/sessions/{{session_id}}/detail/` | Autenticado | Alias del detalle completo de sesión. |
| **6.14** | `GET` | `/tracking/sessions/history/?page=1&page_size=20` | Autenticado | Historial paginado de sesiones completadas con resumen (`total_sessions`, duración total y promedio) y filtros `?from=`, `?to=`, `?routine_id=` *(compatible también con `?desde=` y `?hasta=`)*. |
| **6.15** | `GET` | `/tracking/sessions/routine-summary/` | Autenticado | Resumen agrupado por rutina (cuántas veces hiciste cada rutina y duración promedio); soporta `?from=` y `?to=` *(y legacy `?desde=` / `?hasta=`)*. |
| **6.16** | `DELETE` | `/tracking/sessions/{{session_id}}/` | Autenticado | Elimina una sesión del historial. |
| **6.17** | `GET` | `/tracking/exercises/` | Autenticado | Lista todos los ejercicios registrados en tus sesiones. |
| **6.18** | `GET` | `/tracking/sets/` | Autenticado | Lista todas tus series/marcas registradas. |
| **6.19** | `GET` | `/tracking/progression/{{exercise_id}}/` | Autenticado | Historial cronológico de fuerza de un ejercicio (`estimated_1rm`, peso corporal, fuerza relativa y `records` PRs). |
| **6.20** | `GET` | `/tracking/progress/weight-1rm/?exercise_id={{exercise_id}}` | Autenticado | Datos para la gráfica que cruza tu peso corporal con tu 1RM estimado por fecha. |

---

## Resumen del flujo mínimo recomendado para demostrar en revisión (2 minutos)
Si en tu revisión quieres demostrar que toda la API funciona de punta a punta en pocos clics, corre solo estos **11 pasos en orden**:
1. `1.2 Login` *(con Admin → guarda token)*
2. `1.4 Ver Mi Perfil`
3. `1.7 Editar Mis Preferencias (Settings)`
4. `2.1 Listar Grupos Musculares` *(guarda `muscle_id`)*
5. `3.3 Crear Máquina` *(guarda `equipment_id`)*
6. `4.3 Crear Ejercicio` *(usa `muscle_id` y `equipment_id`, guarda `exercise_id`)*
7. `4.1 Listar Ejercicios (?page=1&page_size=10)` *(demuestra paginación)*
8. `5.2 Crear Rutina` *(usa `exercise_id`, guarda `routine_id`)*
9. `6.1 Iniciar Sesión` → `6.3 Vincular Ejercicio` → `6.4 Registrar Marca`
10. `6.7 Finalizar Sesión Activa`
11. `6.14 Historial Paginado` y `6.19 Progresión 1RM`
