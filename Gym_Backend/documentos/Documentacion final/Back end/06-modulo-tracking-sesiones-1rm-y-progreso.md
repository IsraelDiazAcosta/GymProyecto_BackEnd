# 06. Módulo de Tracking: Sesiones, 1RM y Progreso — Apex Gym Hub

---

## 1. Propósito

Este documento explica el módulo de seguimiento de entrenamientos reales (**`apps/tracking`**) en **Apex Gym Hub**. Cubre la función de autoverificación de migraciones `_ensure_tracking_migrations()`, el ciclo de vida completo de una sesión en `WorkoutSessionViewSet` (`start`, `active`, `finish`, `finish_active`, `cancel`, `history` paginado con `summary`, `detail` con caché `_build_session_exercises_data` y `routine-summary`), el cálculo del **1RM estimado** con la fórmula de Brzycki, la actualización automática de récords personales (`PersonalRecord`) en `WorkoutSetLogViewSet.perform_create`, y las vistas analíticas de progresión (`ExerciseProgressionView` y `Weight1RMProgressView`).

---

## 2. Ubicación

Rutas exactas bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `apps/tracking/models.py` — `WorkoutSession`, `WorkoutLogExercise`, `WorkoutSetLog` (propiedad `estimated_1rm`), `PersonalRecord`.
- `apps/tracking/serializers.py` — `WorkoutSetLogSerializer`, `WorkoutLogExerciseSerializer`, `_WorkoutSessionCommonMixin`, `WorkoutSessionListSerializer`, `CompletedWorkoutSessionSerializer`, `WorkoutSessionDetailSerializer`, `PersonalRecordSerializer`.
- `apps/tracking/views.py` — `_ensure_tracking_migrations`, `_parse_query_datetime`, `CompletedSessionPagination`, `WorkoutSessionViewSet`, `WorkoutLogExerciseViewSet`, `WorkoutSetLogViewSet`, `ExerciseProgressionView`, `Weight1RMProgressView`.
- `apps/tracking/urls.py` — Ruta explícita `sessions/finish/` + `DefaultRouter` (`sessions`, `exercises`, `sets`) + rutas analíticas `progression/<uuid:exercise_id>/` y `progress/weight-1rm/`.
- `apps/tracking/admin.py` — `WorkoutSessionAdmin` (con `WorkoutLogExerciseInline`), `WorkoutSetLogAdmin`, `PersonalRecordAdmin`.

---

## 3. Cómo se conecta

1. **Enrutamiento (`apps/tracking/urls.py`):** Se monta bajo `/api/v1/tracking/`. Destaca que `path('sessions/finish/', WorkoutSessionViewSet.as_view({'post': 'finish_active'}))` está registrado **antes** de `include(router.urls)` para que la palabra literal `finish` no sea interceptada como `<pk>` por el router de `WorkoutSessionViewSet`.
2. **Conexión con `routines` y `catalog`:** Cada `WorkoutSession` enlaza opcionalmente con `Routine` y `RoutineDay` (`SET_NULL`); cada `WorkoutLogExercise` enlaza con `catalog.Exercise`. Si una sesión finaliza sin series registradas, `WorkoutSessionDetailSerializer` consulta la rutina planificada para mostrar los ejercicios previstos con estado `'sin registro'`.
3. **Conexión con `users` (`BodyWeightLog`):** `ExerciseProgressionView` y `Weight1RMProgressView` importan `BodyWeightLog` desde `apps.users.models` para cruzar cada serie registrada con el peso corporal histórico del usuario en esa fecha y calcular la **fuerza relativa** (`estimated_1rm / body_weight`).

---

## 4. Componentes, funciones y variables clave

| Archivo | Símbolo | Rol |
| :--- | :--- | :--- |
| `tracking/views.py` | `_ensure_tracking_migrations()` | Verifica en `WorkoutSessionViewSet.initial()` si faltan columnas de la migración `0003` y ejecuta `call_command('migrate', 'tracking')` si es necesario. |
| `tracking/views.py` | `_parse_query_datetime(raw_value, end_of_day)` | Convierte parámetros ISO datetime o `YYYY-MM-DD` en `DateTime` *timezone-aware*. |
| `tracking/views.py` | `CompletedSessionPagination` | Paginador específico para `history/` (`page_size = 20`, `page_size_query_param = 'page_size'`, `max_page_size = 100`). |
| `tracking/views.py` | `WorkoutSessionViewSet` | Gestiona CRUD y ciclo de vida (`start`, `active`, `finish`, `finish_active`, `cancel`, `history`, `detail`, `routine-summary`). |
| `tracking/views.py` | `WorkoutSessionViewSet._get_active_session(user)` | Busca la sesión activa más reciente excluyendo registros fantasma `'Entrenamiento Móvil'`. |
| `tracking/views.py` | `WorkoutSessionViewSet._filter_completed_sessions_qs(request)` | Filtro reutilizado por `history` y `routine-summary` (soporta `desde`/`from`/`start_date`, `hasta`/`to`/`end_date`, `routine_id`/`routine`). |
| `tracking/views.py` | `WorkoutSetLogViewSet.perform_create` | Guarda la serie y actualiza `PersonalRecord` (`record_type='max_weight'`) si `set_log.weight > current_max.value`. |
| `tracking/views.py` | `ExerciseProgressionView` | Historial cronológico de un ejercicio con `estimated_1rm`, peso corporal y `relative_strength`, más PRs. |
| `tracking/views.py` | `Weight1RMProgressView` | Cruce global (o filtrado por `?exercise_id=`) entre `BodyWeightLog` y `estimated_1rm` por fecha local. |
| `tracking/models.py` | `WorkoutSetLog.estimated_1rm` | Propiedad calculada mediante fórmula de Brzycki: `weight * (36 / (37 - reps))`. |
| `tracking/serializers.py` | `_WorkoutSessionCommonMixin` | Resuelve `routine_id`, `routine_title`, `routine_detail`, `started_at`, `ended_at`, `duration_seconds` y `date` en hora local. |
| `tracking/serializers.py` | `WorkoutSessionDetailSerializer._build_session_exercises_data()` | Consolida y cachea por `obj.pk` el resumen completo de ejercicios/series o el respaldo de rutina planificada. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1 Autoverificación de migraciones en runtime: `_ensure_tracking_migrations()` (`apps/tracking/views.py`, líneas 40-67 y 88-90)

```python
_MIGRATIONS_CHECKED = False


def _ensure_tracking_migrations():
    global _MIGRATIONS_CHECKED
    if _MIGRATIONS_CHECKED:
        return
    try:
        with connection.cursor() as cursor:
            columns = [
                col.name
                for col in connection.introspection.get_table_description(
                    cursor, WorkoutSession._meta.db_table
                )
            ]
        if (
            'status' not in columns
            or 'routine_id' not in columns
            or 'duration_seconds' not in columns
        ):
            call_command('migrate', 'tracking', interactive=False, verbosity=0)
        _MIGRATIONS_CHECKED = True
    except Exception:
        try:
            call_command('migrate', 'tracking', interactive=False, verbosity=0)
            _MIGRATIONS_CHECKED = True
        except Exception:
            pass
```

- Se invoca dentro de `WorkoutSessionViewSet.initial(self, request, *args, **kwargs)` justo antes de ejecutar cualquier acción.
- Usa una bandera global en memoria `_MIGRATIONS_CHECKED` para comprobar solo una vez por proceso de servidor si las columnas incorporadas en `0003_workoutsession_routine_status_duration` (`status`, `routine_id`, `duration_seconds`) existen en la tabla `tracking_workoutsession`.
- Si alguna columna falta, ejecuta programáticamente `python manage.py migrate tracking` sin interacción (`interactive=False`).
- **Crítica técnica:** Fue diseñada como salvaguarda defensiva para evitar errores `OperationalError: no such column` si alguien levantaba el servidor sin correr `migrate` tras actualizar el código; sin embargo, ejecutar migraciones dentro del ciclo de peticiones HTTP (con `except Exception: pass`) es una deuda técnica que en producción debe eliminarse en favor de migraciones explícitas en el pipeline de despliegue.

---

### 5.2 Ciclo de vida de sesiones en `WorkoutSessionViewSet` (`apps/tracking/views.py`, líneas 111-230)

#### Compatibilidad heredada (`perform_create` y `_get_active_session`)

```python
    def perform_create(self, serializer):
        title = serializer.validated_data.get('title', '')
        routine = serializer.validated_data.get('routine')
        if routine is None and title == 'Entrenamiento Móvil':
            serializer.save(user=self.request.user, status='cancelled')
        else:
            serializer.save(user=self.request.user)

    def _get_active_session(self, user):
        return (
            WorkoutSession.objects.filter(
                user=user,
                status='active',
                is_completed=False,
                end_time__isnull=True,
            )
            .exclude(routine__isnull=True, title='Entrenamiento Móvil')
            .select_related('routine', 'routine_day__routine')
            .order_by('-start_time')
            .first()
        )
```

- Cuando clientes anteriores creaban sesiones rápidas sin rutina llamadas `'Entrenamiento Móvil'` mediante `POST /sessions/`, `perform_create` las marca `status='cancelled'` y `_get_active_session` las excluye para que no bloqueen ni aparezcan como entrenamientos activos reales.

#### Iniciar, consultar activa, finalizar y cancelar (`start`, `active`, `finish_active`, `finish`, `cancel`)

```python
    @action(detail=False, methods=['post'], url_path='start')
    def start_session(self, request):
        """Inicia una sesión para la rutina indicada o devuelve la sesión activa existente."""
        existing = self._get_active_session(request.user)
        if existing:
            return Response(WorkoutSessionDetailSerializer(existing).data)

        routine_id = request.data.get('routine_id') or request.data.get('routine')
        routine = None
        if routine_id:
            routine = (
                Routine.objects.filter(
                    Q(user=request.user) | Q(is_template=True),
                    pk=routine_id,
                )
                .prefetch_related('days')
                .first()
            )
            if routine is None:
                return Response(
                    {'detail': 'Rutina no encontrada.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        session = WorkoutSession.objects.create(
            user=request.user,
            routine=routine,
            routine_day=routine.days.first() if routine else None,
            title=routine.title if routine else (request.data.get('title') or 'Entrenamiento'),
            start_time=timezone.now(),
            status='active',
            is_completed=False,
        )
        return Response(
            WorkoutSessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )
```

- **`start_session` (`POST /sessions/start/`):** Garantiza como máximo **una sesión activa por usuario**. Si ya existe una activa, la devuelve con `200 OK` (idempotente). Si no existe, valida que la rutina (si se envió) pertenezca al usuario o sea plantilla (`404` si no existe) y crea la nueva sesión con `status='active'`, retornando `201 Created`.
- **`active_session` (`GET /sessions/active/`):** Devuelve la sesión activa serializada o `null` (`Response(None)`) para que la app móvil recupere o descarte un entrenamiento en curso tras reiniciar.
- **`finish_active` (`POST /sessions/finish/`) y `finish_session` (`POST /sessions/{id}/finish/`):** Ambos fijan `end_time = now`, `is_completed = True`, `status = 'completed'`, calculan `duration_seconds = max(1, int((now - session.start_time).total_seconds()))`, y opcionalmente guardan `perceived_effort_rpe` y `notes`.
- **`cancel_session` (`POST /sessions/cancel/`):** Marca la sesión activa como `status='cancelled'`, `is_completed=False` con `end_time=timezone.now()` y responde `{'status': 'cancelled', 'id': ...}`.

---

### 5.3 Historial paginado (`history`), detalle cacheado (`detail`) y resumen por rutina (`routine-summary`)

#### `history` (`GET /api/v1/tracking/sessions/history/`, líneas 272-323)

```python
        totals = qs.aggregate(
            total_sessions=Count('id'),
            total_duration=Coalesce(Sum(Coalesce('duration_seconds', Value(0))), Value(0)),
            avg_duration=Coalesce(
                Avg(Coalesce('duration_seconds', Value(0))), Value(0.0)
            ),
        )

        annotated_qs = (
            qs.select_related('routine', 'routine_day__routine')
            .prefetch_related(
                'routine__days__exercises',
                'routine_day__routine__days__exercises',
            )
            .annotate(
                annotated_exercises=Count('logged_exercises__exercise', distinct=True),
                annotated_sets=Count('logged_exercises__logged_sets', distinct=True),
                annotated_volume=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('logged_exercises__logged_sets__weight')
                            * F('logged_exercises__logged_sets__reps'),
                            output_field=FloatField(),
                        )
                    ),
                    Value(0.0),
                ),
            )
            .order_by('-start_time', '-end_time')
        )
```

- **Doble nivel de agregación SQL:**
  1. `totals` calcula el resumen global de **todas** las sesiones filtradas (`total_sessions`, `total_duration_seconds`, `average_duration_seconds`) y lo devuelve bajo la clave `'summary'` en la respuesta paginada.
  2. `annotated_qs` anota por cada fila `annotated_exercises` (ejercicios distintos), `annotated_sets` (series distintas) y `annotated_volume` ($\sum \text{peso} \times \text{reps}$ usando `ExpressionWrapper` y `Coalesce(..., 0.0)`), evitando cálculos costosos por fila en Python.
  3. Pagina con `CompletedSessionPagination` (20 por página, configurable hasta 100 con `?page_size=`) y serializa con `CompletedWorkoutSessionSerializer`.

#### `detail` y `_build_session_exercises_data()` (`apps/tracking/serializers.py`, líneas 175-301)

```python
    def _build_session_exercises_data(self, obj):
        cache = getattr(self, '_session_exercises_cache', None)
        if cache is None:
            cache = {}
            self._session_exercises_cache = cache
        cache_key = str(obj.pk)
        if cache_key in cache:
            return cache[cache_key]
```

- `WorkoutSessionDetailSerializer` expone 5 `SerializerMethodField` derivados del mismo cómputo: `has_logged_sets`, `total_exercises`, `total_sets`, `total_volume` y `exercises`. Para no repetir el recorrido 5 veces por sesión, `_build_session_exercises_data` guarda el resultado en `self._session_exercises_cache[str(obj.pk)]` en la primera llamada y las otras 4 solo leen del diccionario.
- **Lógica bifurcada:**
  - **Con series registradas (`has_sets = True`):** Agrupa múltiples bloques `WorkoutLogExercise` del mismo `exercise_id` dentro de la sesión, ordena las series por `(set_number, logged_at, str(s.id))`, renumera secuencialmente `1..N`, acumula `total_volume` y etiqueta cada ejercicio con `unrecorded: False`, `status: 'registrado'`.
  - **Sin series registradas (`has_sets = False`):** Si la sesión está ligada a una rutina (`_resolve_routine(obj)`), recorre los días y ejercicios planificados exponiendo `planned_sets`, `planned_reps` (ej. `"8-12"` o `"10"`), `unrecorded: True` y `status: 'sin registro'`; si no tiene rutina pero sí `logged_list`, devuelve esos ejercicios vacíos con `status: 'sin registro'`.

#### `routine_summary` (`GET /api/v1/tracking/sessions/routine-summary/`, líneas 331-394)

- Agrupa en SQL las sesiones completadas por `Coalesce('routine_id', 'routine_day__routine_id')` y `Coalesce('routine__title', 'routine_day__routine__title', 'title')`, calculando `sessions_count`, `total_duration_seconds` y `last_session_at = Max('effective_date')`.
- Luego consolida en Python por clave (`rid` o `'unlinked:<rname>'`), calcula `average_duration_seconds` y ordena descendentemente por marca temporal de la última sesión.

---

### 5.4 Fórmula Brzycki (`estimated_1rm`) y Récords Personales (`PersonalRecord`)

```python
# apps/tracking/models.py (líneas 116-121)
    @property
    def estimated_1rm(self):
        """Fórmula de Brzycki: peso * (36 / (37 - reps))"""
        if self.reps > 0 and self.reps < 37:
            return round(float(self.weight) * (36 / (37 - self.reps)), 2)
        return float(self.weight)
```

- Estima la **Repetición Máxima teórica (1RM)** con la ecuación de Brzycki:
  $$\text{1RM} = \text{peso} \times \frac{36}{37 - \text{reps}}$$
- La guarda `0 < self.reps < 37` es fundamental: cuando `reps == 1`, la fracción vale `36/36 = 1` (`1RM == peso`), y evitar `reps >= 37` previene división por cero (`37 - 37 = 0`) o resultados negativos absurdos.

```python
# apps/tracking/views.py (líneas 412-429)
class WorkoutSetLogViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutSetLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutSetLog.objects.filter(log_exercise__session__user=self.request.user)

    def perform_create(self, serializer):
        set_log = serializer.save()
        # Verificar y actualizar récord personal (PR)
        exercise = set_log.log_exercise.exercise
        user = self.request.user

        # Máximo peso levantado
        current_max = PersonalRecord.objects.filter(
            user=user, exercise=exercise, record_type='max_weight'
        ).first()

        if not current_max or set_log.weight > current_max.value:
            PersonalRecord.objects.update_or_create(
                user=user,
                exercise=exercise,
                record_type='max_weight',
                defaults={'value': set_log.weight, 'achieved_at': timezone.now()}
            )
```

- Cada vez que se registra una serie (`POST /api/v1/tracking/sets/`), verifica el `PersonalRecord` actual de tipo `'max_weight'` para ese `(user, exercise)`. Si no existe o el nuevo peso es estrictamente mayor, crea o actualiza el récord usando `update_or_create`.
- **Observaciones técnicas:**
  1. Solo actualiza automáticamente `record_type='max_weight'`, no genera automáticamente el récord `'1rm'` ni recalcula si una serie se edita o borra (`PATCH`/`DELETE`).
  2. Ni `WorkoutLogExerciseViewSet` ni `WorkoutSetLogViewSet` validan en `perform_create` o en el serializer que el `session` o `log_exercise` enviado en el body pertenezca a `request.user` (un usuario malicioso que conociera el UUID de la sesión de otro usuario podría insertar registros allí).

---

### 5.5 Analítica de Progreso (`ExerciseProgressionView` y `Weight1RMProgressView`, líneas 432-546)

- **`ExerciseProgressionView` (`GET /api/v1/tracking/progression/<uuid:exercise_id>/`):**
  1. Obtiene todas las `WorkoutSetLog` completadas (`is_completed=True`) del usuario para ese `exercise_id`, ordenadas cronológicamente por `logged_at`.
  2. Obtiene los `BodyWeightLog` del usuario ordenados ascendentemente por `('date', 'id')`.
  3. Para cada serie, `get_body_weight_at(s.logged_at)` convierte la fecha a zona horaria local (`timezone.localtime(dt).date()`) y selecciona el peso corporal registrado en esa fecha o en la fecha inmediatamente anterior (`wl['date'] <= target_date`), usando `request.user.current_weight` como respaldo si no hay logs previos.
  4. Calcula `relative_strength = round(e1rm / bw, 2)` y retorna `exercise_id`, `history`, `body_weight_history` y `records` (`PersonalRecord`).
- **`Weight1RMProgressView` (`GET /api/v1/tracking/progress/weight-1rm/`):**
  - Sigue el mismo cruce temporal entre `WorkoutSetLog` completadas y `BodyWeightLog`, permitiendo filtrar opcionalmente con `?exercise_id=<uuid>` o consultar la evolución global de todos los ejercicios para graficar peso corporal vs 1RM estimado y fuerza relativa a lo largo del tiempo.

---

## 6. Flujo paso a paso (De inicio de sesión de entrenamiento a cálculo de progreso)

1. El cliente consulta `GET /api/v1/tracking/sessions/active/` al abrir la app; si recibe `null`, inicia un entrenamiento enviando `POST /api/v1/tracking/sessions/start/` con `{"routine_id": "<uuid>"}`.
2. `WorkoutSessionViewSet.initial()` verifica una vez por proceso con `_ensure_tracking_migrations()` que la tabla esté migrada; luego `start_session` crea la sesión en estado `'active'` y responde `201 Created`.
3. Por cada ejercicio ejecutado, el cliente registra el vínculo con `POST /api/v1/tracking/exercises/` (`session`, `exercise`, `order`).
4. Por cada serie completada, envía `POST /api/v1/tracking/sets/` (`log_exercise`, `set_number`, `weight`, `reps`, `rpe`). El modelo calcula `estimated_1rm` (Brzycki) al vuelo y `perform_create` actualiza `PersonalRecord` (`max_weight`) si se batió marca.
5. Al terminar, el cliente llama `POST /api/v1/tracking/sessions/finish/` (o `sessions/{id}/finish/`), que fija `status='completed'`, `is_completed=True` y calcula `duration_seconds`.
6. La pantalla de historial consulta `GET /api/v1/tracking/sessions/history/` (obteniendo `summary` global + lista paginada con volumen por sesión) y las gráficas de progreso consultan `GET /api/v1/tracking/progression/{exercise_id}/` o `GET /api/v1/tracking/progress/weight-1rm/`.

---

## 7. Conceptos y términos técnicos

- **1RM (One-Repetition Maximum) y Fórmula de Brzycki:** Estimación del peso máximo que una persona puede levantar una sola vez sin realizar pruebas máximas riesgosas, calculada a partir de cargas submáximas: $\text{peso} \times \frac{36}{37 - \text{reps}}$.
- **Fuerza Relativa (`relative_strength`):** Cociente entre la fuerza máxima estimada (`estimated_1rm`) y el peso corporal del atleta (`body_weight`). Permite comparar rendimiento real incluso cuando el usuario sube o baja de peso corporal.
- **Volumen de Entrenamiento:** Métrica estándar de carga mecánica calculada como $\sum (\text{peso} \times \text{repeticiones})$ a través de todas las series de la sesión.
- **Agregaciones ORM (`Count`, `Sum`, `Avg`, `Max`, `Coalesce`, `ExpressionWrapper`):** Funciones que delegan cálculos matemáticos y agrupamientos directamente al motor SQL en una sola consulta, devolviendo `0` o `0.0` en lugar de `NULL` gracias a `Coalesce`.
- **Caché por instancia en Serializer (`_session_exercises_cache`):** Técnica para compartir resultados calculados entre múltiples `SerializerMethodField` dentro del mismo ciclo de serialización de un objeto, evitando cómputos redundantes.
- **Orden de rutas en Django `urls.py`:** Django evalúa patrones de arriba hacia abajo. Registrar rutas estáticas como `sessions/finish/` antes de `include(router.urls)` evita que `finish` sea interpretado como un `<pk>` de sesión.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué `apps/tracking/urls.py` define manualmente `path('sessions/finish/', ...)` antes de `include(router.urls)` si ya existe `@action(detail=True, url_path='finish')`?**
   - *Respuesta modelo:* Son dos endpoints distintos: `POST /sessions/{id}/finish/` (`finish_session`) finaliza una sesión específica por su UUID, mientras que `POST /sessions/finish/` (`finish_active`) finaliza automáticamente la sesión activa del usuario sin que el frontend necesite enviar su ID. Colocar `sessions/finish/` antes de `router.urls` evita que el router intente tratar la cadena `"finish"` como el parámetro `<pk>` de detalle (`sessions/<pk>/`).

2. **¿Cómo funciona la fórmula de Brzycki en `WorkoutSetLog.estimated_1rm` y qué caso límite previene la condición `self.reps < 37`?**
   - *Respuesta modelo:* Aplica `round(float(self.weight) * (36 / (37 - self.reps)), 2)`. Si `reps` fuera `37`, el denominador `37 - 37` provocaría una excepción `ZeroDivisionError`; y si `reps > 37`, daría un 1RM negativo. Por eso la condición `0 < self.reps < 37` acota la fórmula a su dominio válido y retorna `float(self.weight)` fuera de ese rango.

3. **¿Cómo optimiza `WorkoutSessionDetailSerializer` el cálculo de `has_logged_sets`, `total_exercises`, `total_sets`, `total_volume` y `exercises`?**
   - *Respuesta modelo:* Todos esos campos son `SerializerMethodField` que delegan en `_build_session_exercises_data(obj)`. Ese método crea un diccionario `_session_exercises_cache` en la instancia del serializador indexado por `str(obj.pk)`. Así, el recorrido y agrupamiento de series (o de la rutina planificada) se ejecuta una sola vez por sesión en vez de cinco veces.

4. **¿Qué ocurre en el detalle de una sesión si el usuario la inició desde una rutina y la finalizó sin registrar ninguna serie?**
   - *Respuesta modelo:* `_build_session_exercises_data` detecta `has_sets = False` (`all_sets_count == 0`). En lugar de devolver un arreglo vacío, resuelve la rutina mediante `obj.routine` o `obj.routine_day.routine` y construye la lista de ejercicios planificados indicando `planned_sets`, `planned_reps`, `unrecorded: True` y `status: 'sin registro'`.

5. **¿Qué crítica técnica merece `_ensure_tracking_migrations()` en `apps/tracking/views.py`?**
   - *Respuesta modelo:* Aunque fue útil durante el desarrollo para prevenir caídas por columnas faltantes tras añadir `status`, `routine` y `duration_seconds` en la migración `0003`, inspeccionar el esquema de la base de datos y ejecutar `call_command('migrate')` dentro de `initial()` de una vista API viola la separación entre despliegue y ejecución, silencia excepciones con `except Exception: pass` y en entornos multiproceso podría causar condiciones de carrera. Debe retirarse en producción y ejecutarse `manage.py migrate` antes de arrancar el servidor.

6. **¿Cómo calcula `ExerciseProgressionView` la fuerza relativa histórica si el usuario se pesa en fechas distintas a sus entrenamientos?**
   - *Respuesta modelo:* Convierte la fecha `logged_at` de cada serie a fecha local (`America/Mexico_City`) y recorre el historial ordenado de `BodyWeightLog` buscando el último pesaje cuya fecha sea menor o igual a la fecha de la serie (`wl['date'] <= target_date`). Si no hay pesajes previos a esa fecha, usa `request.user.current_weight` como respaldo, y divide `estimated_1rm / bw`.

---

## 9. Resumen para repasar

- `WorkoutSessionViewSet` controla el ciclo completo de entrenamiento (`start`, `active`, `finish`, `finish_active`, `cancel`), garantizando una sola sesión activa y excluyendo sesiones heredadas `'Entrenamiento Móvil'`.
- `history/` calcula métricas globales (`summary`) y por sesión (`annotated_exercises`, `annotated_sets`, `annotated_volume`) directamente en SQL con `Count`, `Sum`, `Avg` y `Coalesce`, paginando de 20 en 20 (`CompletedSessionPagination`).
- `WorkoutSetLog.estimated_1rm` implementa **Brzycki** (`peso * 36 / (37 - reps)` para `1..36` reps) y `WorkoutSetLogViewSet.perform_create` actualiza automáticamente el `PersonalRecord` de `max_weight`.
- `ExerciseProgressionView` y `Weight1RMProgressView` cruzan series completadas con `BodyWeightLog` en hora local para entregar el historial de 1RM y fuerza relativa.
- `_ensure_tracking_migrations()` es un mecanismo defensivo de desarrollo en runtime que conviene reemplazar por migraciones previas al arranque en producción.
