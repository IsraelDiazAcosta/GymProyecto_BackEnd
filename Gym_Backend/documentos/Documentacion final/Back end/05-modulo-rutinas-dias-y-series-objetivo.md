# 05. Módulo de Rutinas, Días y Series Objetivo — Apex Gym Hub

---

## 1. Propósito

Este documento explica el módulo de planificación de entrenamientos (**`apps/routines`**) en **Apex Gym Hub**. Detalla la jerarquía de cuatro niveles (`Routine` → `RoutineDay` → `RoutineExercise` → `RoutineSet`), la visibilidad mixta entre rutinas personales y plantillas públicas (`Q(user=user) | Q(is_template=True)`), la creación automática de `'Día 1'` con carga opcional inmediata de ejercicios (`perform_create`), las acciones personalizadas `add_exercise` y `clone_routine`, el algoritmo de reconciliación *in-place* de series en `RoutineExerciseSerializer.update()`, y el permiso por objeto `IsRoutineExerciseOwner`.

---

## 2. Ubicación

Rutas exactas bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `apps/routines/models.py` — Modelos `Routine`, `RoutineDay`, `RoutineExercise`, `RoutineSet`.
- `apps/routines/serializers.py` — `RoutineSetSerializer`, `RoutineExerciseSerializer`, `RoutineDaySerializer`, `RoutineListSerializer`, `RoutineDetailSerializer`.
- `apps/routines/views.py` — `RoutineViewSet`, `RoutineDayViewSet`, `IsRoutineExerciseOwner`, `RoutineExerciseViewSet`, `RoutineSetViewSet`.
- `apps/routines/urls.py` — `DefaultRouter` registrando `routines`, `days`, `exercises` y `sets` bajo `/api/v1/routines/`.
- `apps/routines/admin.py` — `RoutineAdmin`, `RoutineDayAdmin` (con `RoutineExerciseInline`), `RoutineExerciseAdmin` (con `RoutineSetInline`), `RoutineSetAdmin`.

---

## 3. Cómo se conecta

1. **Entrada de URL:** `Gym_Backend/urls.py` monta `apps/routines/urls.py` en `/api/v1/routines/`.
2. **Dependencia del catálogo:** `RoutineExercise.exercise` apunta por `ForeignKey` a `apps.catalog.models.Exercise`, y `RoutineExerciseSerializer` reutiliza `ExerciseListSerializer` para incluir `exercise_detail` (nombre, máquina, músculo principal, URL de imagen) dentro de la rutina.
3. **Integración con `tracking`:** `WorkoutSession` (en `apps/tracking`) referencia a `Routine` y `RoutineDay` (`on_delete=SET_NULL`), permitiendo iniciar sesiones ligadas a una rutina y, cuando aún no se registran series reales, mostrar los ejercicios y series planificados como respaldo en el detalle de la sesión.
4. **Propiedad y aislamiento:** Todas las vistas exigen `IsAuthenticated`. `RoutineViewSet` muestra las rutinas del usuario autenticado más plantillas públicas (`is_template=True`), mientras que `RoutineDayViewSet`, `RoutineExerciseViewSet` y `RoutineSetViewSet` restringen sus querysets a objetos propiedad de `request.user`.

---

## 4. Componentes, funciones y variables clave

| Archivo | Símbolo | Rol |
| :--- | :--- | :--- |
| `routines/models.py` | `Routine`, `RoutineDay`, `RoutineExercise`, `RoutineSet` | Jerarquía Plan → Día → Ejercicio programado → Serie objetivo (`warmup`, `feeder`, `working`, `drop_set`, `to_failure`). |
| `routines/views.py` | `RoutineViewSet.get_queryset()` | Filtra con `Q(user=user) | Q(is_template=True)` y precarga `days__exercises__target_sets` y `days__exercises__exercise`. |
| `routines/views.py` | `RoutineViewSet._extract_exercise_ids(data)` | Normaliza la entrada aceptando `exercise_ids` (lista), `exercise_id` o `exercise`. |
| `routines/views.py` | `RoutineViewSet._add_exercises_to_day(day, ids_to_add, data)` | Inserta `RoutineExercise` incrementando `order` y genera sus `RoutineSet` (default: 4 series, 8-12 reps, 90s descanso). |
| `routines/views.py` | `RoutineViewSet.perform_create(serializer)` | Crea la rutina, crea automáticamente `'Día 1'` y añade ejercicios iniciales si se enviaron, todo en `transaction.atomic()`. |
| `routines/views.py` | `RoutineViewSet.add_exercise` (`add-exercise/`) | `@action` POST para añadir uno o varios ejercicios al primer día de una rutina existente. |
| `routines/views.py` | `RoutineViewSet.clone_routine` (`clone/`) | `@action` POST que clona profundamente una rutina (días, ejercicios y series) a la cuenta del usuario (`is_template=False`). |
| `routines/views.py` | `IsRoutineExerciseOwner` | Permiso por objeto (`has_object_permission`) que exige `obj.routine_day.routine.user_id == request.user.id`. |
| `routines/serializers.py` | `RoutineSetSerializer` | Valida `min_reps >= 1`, `max_reps >= 1` y `min_reps <= max_reps`. |
| `routines/serializers.py` | `RoutineExerciseSerializer` | Permite crear/editar series mediante lista explícita `target_sets` o parámetros abreviados (`sets_count`, `min_reps`, `max_reps`). |
| `routines/serializers.py` | `RoutineExerciseSerializer.update()` | Algoritmo atómico que actualiza series existentes *in-place*, agrega faltantes heredando de la última serie o recorta sobrantes. |
| `routines/serializers.py` | `RoutineListSerializer` / `RoutineDetailSerializer` | Exponen la rutina anidando `days` → `exercises` → `target_sets`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1 Consulta de rutinas propias + plantillas y carga masiva (`apps/routines/views.py`, líneas 25-78)

```python
class RoutineViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return RoutineListSerializer
        return RoutineDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # Muestra rutinas del usuario y plantillas públicas
        return Routine.objects.filter(
            Q(user=user) | Q(is_template=True)
        ).prefetch_related('days__exercises__target_sets', 'days__exercises__exercise')
```

- **`Q(user=user) | Q(is_template=True)`:** Construye un `OR` SQL para devolver tanto las rutinas creadas por el usuario como las plantillas oficiales/públicas (`is_template=True`).
- **`prefetch_related(...)`:** Precarga en lotes los días, los ejercicios de cada día, sus `Exercise` relacionados y sus `target_sets`, evitando consultas N+1 al serializar rutinas completas.
- **Observación de seguridad importante:** `RoutineViewSet` define `permission_classes = [permissions.IsAuthenticated]` pero **no** valida en un permiso de objeto que en métodos `PUT`/`PATCH`/`DELETE`/`add-exercise` la rutina pertenezca a `request.user` y no sea una plantilla ajena (`is_template=True`). Un usuario autenticado que conozca el UUID de una plantilla podría modificarla o eliminarla si no se añade un permiso `IsOwnerOrReadOnly`.

```python
    @staticmethod
    def _extract_exercise_ids(data):
        """Obtiene la lista de UUIDs de ejercicios aceptando exercise_ids, exercise_id o exercise."""
        raw_ids = data.get('exercise_ids')
        single_id = data.get('exercise_id') or data.get('exercise')
        if isinstance(raw_ids, list) and raw_ids:
            return [eid for eid in raw_ids if eid]
        if single_id:
            return [single_id]
        return []

    @staticmethod
    def _add_exercises_to_day(day, ids_to_add, data):
        """Crea RoutineExercise y RoutineSet para los ejercicios indicados en un día de rutina."""
        sets_count = int(data.get('sets_count', 4) or 4)
        min_reps = int(data.get('min_reps', 8) or 8)
        max_reps = int(data.get('max_reps', 12) or 12)
        rest_seconds = int(data.get('rest_seconds', 90) or 90)
        notes = data.get('notes', '') or ''
        next_order = day.exercises.count() + 1

        for eid in ids_to_add:
            exercise = get_object_or_404(Exercise, pk=eid)
            routine_ex = RoutineExercise.objects.create(
                routine_day=day,
                exercise=exercise,
                order=next_order,
                rest_seconds=rest_seconds,
                notes=notes,
            )
            next_order += 1
            for s in range(1, sets_count + 1):
                RoutineSet.objects.create(
                    routine_exercise=routine_ex,
                    set_number=s,
                    min_reps=min_reps,
                    max_reps=max_reps,
                )

    def perform_create(self, serializer):
        with transaction.atomic():
            routine = serializer.save(user=self.request.user)
            day = RoutineDay.objects.create(routine=routine, name='Día 1', order=1)
            ids_to_add = self._extract_exercise_ids(self.request.data)
            if ids_to_add:
                self._add_exercises_to_day(day, ids_to_add, self.request.data)
```

- **`perform_create`:** Garantiza que toda rutina nueva nazca lista para usarse con al menos un `RoutineDay` llamado `'Día 1'` (`order=1`). Si el cliente además envía `exercise_ids` (o `exercise_id` / `exercise`) al crear la rutina, los inserta en ese día junto con sus series objetivo dentro de una transacción atómica (`with transaction.atomic():`).
- En `_add_exercises_to_day`, `sets_count` toma por defecto `4`, `min_reps` `8`, `max_reps` `12` y `rest_seconds` `90` si el cliente omite dichos valores.

---

### 5.2 Acciones `add_exercise` y `clone_routine` (`apps/routines/views.py`, líneas 79-135)

```python
    @action(detail=True, methods=['post'], url_path='add-exercise')
    def add_exercise(self, request, pk=None):
        """Agrega uno o más ejercicios del catálogo a la rutina con sus series y repeticiones objetivo."""
        with transaction.atomic():
            routine = self.get_object()
            day = routine.days.first()
            if not day:
                day = RoutineDay.objects.create(routine=routine, name='Día 1', order=1)

            ids_to_add = self._extract_exercise_ids(request.data) or [None]
            self._add_exercises_to_day(day, ids_to_add, request.data)

        routine = self.get_queryset().get(pk=routine.pk)
        return Response(RoutineDetailSerializer(routine, context={'request': request}).data, status=status.HTTP_201_CREATED)
```

- Obtiene el primer día (`routine.days.first()`) o crea `'Día 1'` si la rutina quedó sin días.
- Si el cliente no envía ningún ID de ejercicio, `ids_to_add` toma `[None]` y `get_object_or_404(Exercise, pk=None)` aborta la transacción devolviendo `404`.
- Al finalizar la transacción, recarga la rutina mediante `self.get_queryset().get(pk=routine.pk)` para asegurar el `prefetch_related` actualizado y retorna el detalle completo con HTTP `201 Created`.

```python
    @action(detail=True, methods=['post'], url_path='clone')
    def clone_routine(self, request, pk=None):
        """Permite a un usuario clonar una plantilla a su cuenta personal."""
        original = self.get_object()
        new_routine = Routine.objects.create(
            user=request.user,
            title=f"{original.title} (Mi copia)",
            description=original.description,
            is_template=False,
            is_active=True,
        )

        for day in original.days.all():
            new_day = RoutineDay.objects.create(
                routine=new_routine,
                name=day.name,
                order=day.order
            )
            for ex in day.exercises.all():
                new_ex = RoutineExercise.objects.create(
                    routine_day=new_day,
                    exercise=ex.exercise,
                    order=ex.order,
                    rest_seconds=ex.rest_seconds,
                    tempo=ex.tempo,
                    notes=ex.notes
                )
                for s in ex.target_sets.all():
                    RoutineSet.objects.create(
                        routine_exercise=new_ex,
                        set_number=s.set_number,
                        set_type=s.set_type,
                        min_reps=s.min_reps,
                        max_reps=s.max_reps,
                        target_rpe=s.target_rpe,
                        target_rir=s.target_rir,
                        target_weight=s.target_weight,
                    )

        serializer = RoutineDetailSerializer(new_routine, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

- Realiza una **copia profunda** (*deep copy*) en los 4 niveles (`Routine` → `RoutineDay` → `RoutineExercise` → `RoutineSet`) asignando `user=request.user`, `is_template=False` y el sufijo `" (Mi copia)"` al título, para que el alumno pueda personalizar pesos, descansos y series sobre su propia copia sin tocar la plantilla original. *(Nota: a diferencia de `perform_create` y `add_exercise`, `clone_routine` no está envuelta en `transaction.atomic()`).*

---

### 5.3 Algoritmo de `RoutineExerciseSerializer.update()` (`apps/routines/serializers.py`, líneas 69-135)

```python
    @transaction.atomic
    def update(self, instance, validated_data):
        sets_count = validated_data.pop('sets_count', None)
        min_reps = validated_data.pop('min_reps', None)
        max_reps = validated_data.pop('max_reps', None)
        target_sets_data = validated_data.pop('target_sets', None)

        instance = super().update(instance, validated_data)
        existing_sets = list(instance.target_sets.order_by('set_number', 'id'))
```

Primero actualiza los campos propios de `RoutineExercise` (`order`, `rest_seconds`, `tempo`, `notes`, `exercise`) y carga las series actuales ordenadas en memoria (`existing_sets`). Luego maneja dos estrategias mutuamente excluyentes:

#### Rama A: El cliente envió la lista detallada `target_sets`

```python
        if target_sets_data is not None:
            common_len = min(len(existing_sets), len(target_sets_data))
            for idx in range(common_len):
                s_obj = existing_sets[idx]
                s_data = target_sets_data[idx]
                s_obj.set_number = s_data.get('set_number', idx + 1)
                for field in ('set_type', 'min_reps', 'max_reps', 'target_rpe', 'target_rir', 'target_weight'):
                    if field in s_data:
                        setattr(s_obj, field, s_data[field])
                s_obj.save()
            if len(target_sets_data) > len(existing_sets):
                for idx in range(len(existing_sets), len(target_sets_data)):
                    s_data = dict(target_sets_data[idx])
                    s_data.setdefault('set_number', idx + 1)
                    RoutineSet.objects.create(routine_exercise=instance, **s_data)
            elif len(target_sets_data) < len(existing_sets):
                ids_to_delete = [s.id for s in existing_sets[len(target_sets_data):]]
                instance.target_sets.filter(id__in=ids_to_delete).delete()
```

- **Actualización *in-place*:** En vez de borrar todas las series y recrearlas, reutiliza los objetos existentes hasta `min(len(existing_sets), len(target_sets_data))`, preservando sus `id`. Si sobran elementos en la petición los crea; si faltan, elimina solo las series sobrantes por `id__in`.

#### Rama B: El cliente envió parámetros rápidos (`sets_count`, `min_reps`, `max_reps`)

```python
        elif any(v is not None for v in (sets_count, min_reps, max_reps)):
            ref_set = existing_sets[-1] if existing_sets else None
            final_sets = sets_count if sets_count is not None else (len(existing_sets) or 3)
            final_min = min_reps if min_reps is not None else (ref_set.min_reps if ref_set else 8)
            final_max = max_reps if max_reps is not None else (ref_set.max_reps if ref_set else final_min)
            if final_min > final_max:
                raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})

            common_len = min(len(existing_sets), final_sets)
            for idx in range(common_len):
                s_obj = existing_sets[idx]
                s_obj.set_number = idx + 1
                if min_reps is not None:
                    s_obj.min_reps = final_min
                if max_reps is not None:
                    s_obj.max_reps = final_max
                if s_obj.min_reps > s_obj.max_reps:
                    raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})
                s_obj.save()

            if final_sets > len(existing_sets):
                for s_num in range(len(existing_sets) + 1, final_sets + 1):
                    RoutineSet.objects.create(
                        routine_exercise=instance,
                        set_number=s_num,
                        set_type=ref_set.set_type if ref_set else 'working',
                        min_reps=final_min,
                        max_reps=final_max,
                        target_rpe=ref_set.target_rpe if ref_set else None,
                        target_rir=ref_set.target_rir if ref_set else None,
                        target_weight=ref_set.target_weight if ref_set else None,
                    )
            elif final_sets < len(existing_sets):
                ids_to_delete = [s.id for s in existing_sets[final_sets:]]
                instance.target_sets.filter(id__in=ids_to_delete).delete()
```

- Toma la última serie (`ref_set = existing_sets[-1]`) como plantilla de referencia para conservar `set_type`, `target_rpe`, `target_rir` y `target_weight` si se añaden nuevas series (ej. subir de 3 a 4 series).
- Valida tanto la consistencia global (`final_min > final_max`) como la de cada serie individual si solo se actualizó uno de los extremos (`s_obj.min_reps > s_obj.max_reps`).
- Si se reduce `sets_count`, recorta únicamente las últimas series excedentes.

---

### 5.4 Permiso `IsRoutineExerciseOwner` y ViewSets hijos (`apps/routines/views.py`, líneas 137-166)

```python
class RoutineDayViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineDaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineDay.objects.filter(routine__user=self.request.user)


class IsRoutineExerciseOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.routine_day.routine.user_id == request.user.id


class RoutineExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineExerciseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoutineExerciseOwner]

    def get_queryset(self):
        return RoutineExercise.objects.filter(
            routine_day__routine__user=self.request.user
        ).select_related('exercise', 'routine_day__routine').prefetch_related('target_sets')


class RoutineSetViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineSet.objects.filter(routine_exercise__routine_day__routine__user=self.request.user)
```

- `IsRoutineExerciseOwner` actúa como segunda barrera explícita a nivel de objeto (`has_object_permission`) comprobando `obj.routine_day.routine.user_id == request.user.id` (además del filtro de `get_queryset()`).
- **Observación arquitectónica:** Aunque los endpoints `days/`, `exercises/` y `sets/` están registrados como `ModelViewSet`, sus serializers no aceptan el ID padre en `POST` (`RoutineDaySerializer` marca `routine` en `read_only_fields` y `RoutineDayViewSet` no define `perform_create`; `RoutineExerciseSerializer` no incluye `routine_day` en `Meta.fields`; `RoutineSetSerializer` no incluye `routine_exercise` en `Meta.fields`). Por tanto, en la práctica están diseñados para consultar, actualizar (`PATCH`/`PUT`) o eliminar (`DELETE`) recursos existentes, mientras la creación se realiza desde `RoutineViewSet` (`POST /routines/` y `POST /routines/{id}/add-exercise/`).

---

## 6. Flujo paso a paso (Crear rutina, agregar ejercicios y editar series)

1. El usuario envía `POST /api/v1/routines/routines/` con `{"title": "Pecho y Tríceps", "exercise_ids": ["<uuid-1>", "<uuid-2>"], "sets_count": 3, "min_reps": 8, "max_reps": 12}`.
2. `RoutineViewSet.perform_create` crea la `Routine` asociada a `request.user`, crea `RoutineDay(name='Día 1', order=1)` y ejecuta `_add_exercises_to_day`, creando 2 `RoutineExercise` (`order=1, 2`) con 3 `RoutineSet` cada uno.
3. Si después el usuario quiere agregar otro ejercicio, envía `POST /api/v1/routines/routines/{id}/add-exercise/` con `{"exercise_id": "<uuid-3>"}` (toma defaults `4` series, `8-12` reps, `90s` descanso).
4. Si el usuario desea cambiar un ejercicio existente de 4 a 5 series o ajustar su rango de repeticiones, envía `PATCH /api/v1/routines/exercises/{routine_exercise_id}/` con `{"sets_count": 5, "min_reps": 6, "max_reps": 10}` (o el arreglo completo `target_sets`).
5. `IsRoutineExerciseOwner` confirma que `obj.routine_day.routine.user_id == request.user.id` y `RoutineExerciseSerializer.update()` reconcilia las series en base de datos dentro de `@transaction.atomic`.

---

## 7. Conceptos y términos técnicos

- **Consulta `Q(...) | Q(...)`:** Objeto `Q` de Django ORM que permite combinar condiciones SQL con operadores lógicos `OR` (`|`), `AND` (`&`) y `NOT` (`~`).
- **`transaction.atomic()`:** Bloque o decorador que agrupa múltiples operaciones SQL (`INSERT`, `UPDATE`, `DELETE`) en una sola transacción; si ocurre cualquier excepción, se ejecuta un `ROLLBACK` automático para no dejar datos a medias.
- **Actualización *in-place* vs reemplazo destructivo:** En lugar de borrar todos los registros hijos y reinsertarlos con nuevos IDs en cada `PATCH`, la actualización *in-place* modifica los registros existentes en su posición y solo inserta o elimina la diferencia.
- **Deep Copy (Clonación profunda):** Duplicar no solo la entidad raíz (`Routine`), sino recorrer recursivamente todos sus hijos (`RoutineDay`, `RoutineExercise`, `RoutineSet`) generando registros independientes en base de datos.
- **Permiso por objeto (`has_object_permission`):** Verificación de DRF que se ejecuta después de recuperar la instancia específica (`get_object()`), garantizando que el usuario sea dueño del recurso antes de permitir modificarlo o borrarlo.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo logra `RoutineViewSet` mostrar tanto las rutinas privadas del usuario como las plantillas públicas sin mezclar rutinas privadas de otros usuarios?**
   - *Respuesta modelo:* En `get_queryset()` filtra con `Routine.objects.filter(Q(user=user) | Q(is_template=True))`. Esto equivale en SQL a `WHERE user_id = <mi_id> OR is_template = TRUE`, por lo que ningún usuario puede ver las rutinas privadas (`is_template=False`) de otra persona.

2. **¿Qué hace el backend automáticamente cuando el usuario crea una rutina mediante `POST /api/v1/routines/routines/`?**
   - *Respuesta modelo:* `perform_create()` abre una transacción atómica, guarda la rutina asignándole `user=self.request.user`, crea automáticamente un primer `RoutineDay` llamado `'Día 1'` (`order=1`) y, si el cuerpo incluye `exercise_ids`, `exercise_id` o `exercise`, crea los `RoutineExercise` y sus `RoutineSet` iniciales en ese mismo paso.

3. **¿Por qué existe un método `clone_routine` si el usuario ya puede ver las plantillas (`is_template=True`)?**
   - *Respuesta modelo:* Porque las plantillas públicas sirven como catálogo base compartido, pero cada usuario necesita personalizar cargas, descansos, repeticiones o ejercicios sin alterar la plantilla original. `clone_routine` realiza una copia profunda de los 4 niveles (`Routine`, `RoutineDay`, `RoutineExercise`, `RoutineSet`) asignando `user=request.user` e `is_template=False`.

4. **Explica cómo funciona el algoritmo de `RoutineExerciseSerializer.update()` cuando el frontend modifica solo `sets_count` o `min_reps`/`max_reps`.**
   - *Respuesta modelo:* Primero guarda los campos propios del `RoutineExercise` y recupera las series actuales ordenadas por `set_number` e `id`. Luego toma la última serie existente como referencia (`ref_set`) para no perder metadatos como `set_type`, `target_rpe` o `target_weight`. Actualiza *in-place* las series comunes validando `min_reps <= max_reps`; si aumentó `sets_count`, crea las series adicionales copiando la configuración de `ref_set`; si disminuyó, elimina únicamente las series sobrantes al final.

5. **¿Qué valida `IsRoutineExerciseOwner` y qué riesgo residual detectaste en `RoutineViewSet`?**
   - *Respuesta modelo:* `IsRoutineExerciseOwner` valida `obj.routine_day.routine.user_id == request.user.id` en `RoutineExerciseViewSet`, impidiendo que un usuario edite o borre ejercicios de rutinas ajenas. En cambio, `RoutineViewSet` expone las plantillas `is_template=True` dentro de `get_queryset()` usando solo `IsAuthenticated`, sin un permiso de objeto que bloquee `PATCH`/`DELETE`/`add-exercise` sobre plantillas que no pertenecen al usuario; esa es una mejora de seguridad recomendada.

6. **¿Qué ocurre si un usuario intenta crear directamente un día en `POST /api/v1/routines/days/` o una serie en `POST /api/v1/routines/sets/`?**
   - *Respuesta modelo:* Fallaría la creación porque `RoutineDaySerializer` tiene `routine` en `read_only_fields` sin `perform_create` que la asigne, y `RoutineSetSerializer` ni siquiera expone el campo `routine_exercise` en `Meta.fields` (lo mismo pasa con `routine_day` en `RoutineExerciseSerializer`). Esos tres endpoints secundarios están pensados en la arquitectura actual para consultar, editar o borrar elementos ya creados desde `RoutineViewSet`.

---

## 9. Resumen para repasar

- El módulo `routines` modela **4 niveles anidados**: `Routine` → `RoutineDay` → `RoutineExercise` → `RoutineSet`.
- `RoutineViewSet.get_queryset()` combina rutinas propias y plantillas públicas con `Q(user=user) | Q(is_template=True)` y precarga profunda (`prefetch_related`).
- `perform_create()` y `add_exercise()` automatizan `'Día 1'` y la creación en lote de ejercicios/series dentro de `transaction.atomic()`.
- `clone_routine()` duplica completamente una plantilla hacia la cuenta del usuario (`"(Mi copia)"`, `is_template=False`).
- `RoutineExerciseSerializer.update()` reconcilia series *in-place* aceptando tanto `target_sets` completos como parámetros rápidos (`sets_count`, `min_reps`, `max_reps`), y `RoutineExerciseViewSet` protege la propiedad con `IsRoutineExerciseOwner`.
