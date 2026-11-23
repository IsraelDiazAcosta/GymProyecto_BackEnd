# 04. Módulo de Catálogo: Máquinas, Ejercicios y Multimedia — Apex Gym Hub

---

## 1. Propósito

Este documento explica el funcionamiento técnico del catálogo maestro de **Apex Gym Hub**: equipos y máquinas de gimnasio (`Equipment`), grupos musculares (`MuscleGroup`), ejercicios (`Exercise`), relaciones anatómicas (`ExerciseMuscle`), material multimedia (`ExerciseMedia`) y favoritos del usuario (`UserFavoriteEquipment`, `UserFavoriteExercise`). Se profundiza en la validación y optimización automática de imágenes a formato **WebP** con Pillow (incluyendo corrección de rotación EXIF), la limpieza automática de archivos huérfanos en disco mediante señales `post_delete`, el campo `FlexibleImageField` para aceptar tanto `multipart/form-data` como **Base64**, las subconsultas SQL `Exists(OuterRef('pk'))` para evitar consultas N+1, el borrado atómico en `ExerciseViewSet` y el comando semilla `seed_catalog`.

---

## 2. Ubicación

Rutas exactas bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_BackEnd\Gym_Backend\`:

- `apps/catalog/models.py` — Validadores, optimización WebP, limpieza de archivos, los 7 modelos del catálogo y la señal `@receiver(post_delete)`.
- `apps/catalog/serializers.py` — `FlexibleImageField`, `_build_abs_url`, `_resolve_exercise_image_url`, y serializadores de máquinas, músculos, multimedia y ejercicios (lista y detalle).
- `apps/catalog/views.py` — `EquipmentViewSet`, `MuscleGroupViewSet`, `ExerciseViewSet`, `ExerciseMediaViewSet` con filtros, búsqueda, anotación `is_favorite` y acciones `@action` (`favorite`, `favorites`).
- `apps/catalog/urls.py` — `DefaultRouter` registrando `equipment`, `muscles`, `exercises` y `media` bajo `/api/v1/catalog/`.
- `apps/catalog/admin.py` — Registro en Django Admin con `TabularInline` para músculos y multimedia y `prepopulated_fields` para `slug`.
- `apps/catalog/permissions.py` — `IsAdminOrReadOnly`.
- `apps/catalog/management/commands/seed_catalog.py` — Comando CLI `python manage.py seed_catalog`.

---

## 3. Cómo se conecta

1. **Permisos:** Todos los `ViewSet` del catálogo aplican `IsAdminOrReadOnly` (cualquiera lee; solo `is_staff=True` crea/edita/elimina), excepto las acciones personalizadas `@action` `favorite` y `favorites`, que sobreescriben el permiso a `IsAuthenticated` para que cualquier alumno pueda gestionar sus favoritos.
2. **Parsers multimedia:** `EquipmentViewSet`, `ExerciseViewSet` y `ExerciseMediaViewSet` configuran `parser_classes = [MultiPartParser, FormParser, JSONParser]`, permitiendo subir imágenes vía formularios binarios (`multipart`) o dentro de JSON (`Base64` gracias a `FlexibleImageField`).
3. **Resolución de imágenes y cascada visual:** Si un `Exercise` no tiene imagen propia, `_resolve_exercise_image_url` recurre automáticamente a la foto de su `Equipment`, y si tampoco existe, a la miniatura (`thumbnail`) de su primer `ExerciseMedia`.
4. **Integración con otros módulos:** `apps/routines` (`RoutineExercise`) y `apps/tracking` (`WorkoutLogExercise`, `PersonalRecord`) referencian a `catalog.Exercise` y reutilizan `ExerciseListSerializer` en sus respuestas.

---

## 4. Componentes, funciones y variables clave

| Archivo | Símbolo | Rol |
| :--- | :--- | :--- |
| `catalog/models.py` | `validate_image(file)` | Valida límite máximo de `5 MB` y extensiones `.jpg`, `.jpeg`, `.png`, `.webp`. |
| `catalog/models.py` | `optimize_image(image_field)` | Corrige rotación EXIF, convierte modos de color, redimensiona a máximo `1080x1080` y recomprime a `WEBP` (`quality=75`). |
| `catalog/models.py` | `delete_old_file_on_update(instance, model_class, field_name)` | Borra el archivo anterior en disco cuando se reemplaza o elimina la imagen en una actualización. |
| `catalog/models.py` | `auto_delete_image_on_delete` | Receptor `@receiver(post_delete)` para `Equipment` y `Exercise` que borra la imagen física de `media/` al eliminar el registro. |
| `catalog/serializers.py` | `FlexibleImageField` | Subclase de `serializers.ImageField` que acepta archivos binarios, Data URIs Base64, Base64 puro o diccionarios `{base64, name}`. |
| `catalog/serializers.py` | `_build_abs_url(request, file_field)` | Construye URLs absolutas (`http://host/media/...`) usando `request.build_absolute_uri`. |
| `catalog/serializers.py` | `_resolve_exercise_image_url(obj, request)` | Resuelve la imagen efectiva del ejercicio en cascada: `obj.image` → `obj.equipment.image` → `obj.media.first().thumbnail`. |
| `catalog/serializers.py` | `ExerciseListSerializer` / `ExerciseDetailSerializer` | Listado ligero (incluye `image`, `image_url`, `thumbnail` y `primary_muscle`) y detalle completo con creación/edición de `muscle_id` y `video_url`. |
| `catalog/views.py` | `EquipmentViewSet` / `ExerciseViewSet` | Anotan `is_favorite` mediante `Exists(OuterRef('pk'))`, filtran por query params y exponen `POST .../favorite/` y `GET .../favorites/`. |
| `catalog/views.py` | `ExerciseViewSet.perform_destroy` | Borra en `transaction.atomic()` `routine_placements`, `logged_workouts` y finalmente el `Exercise`. |
| `seed_catalog.py` | `Command.handle()` | Puebla idempotente (`get_or_create`) de 12 `MuscleGroup`, 6 `Equipment` y 3 `Exercise` con sus `ExerciseMuscle`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1 Validación, optimización WebP y limpieza de imágenes (`apps/catalog/models.py`, líneas 14-65 y 262-266)

#### Validación de archivos (`validate_image`)

```python
def validate_image(file):
    if hasattr(file, 'seek'):
        file.seek(0)
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError('El tamaño máximo de imagen permitido es 5 MB.')
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Formato no válido. Usa imágenes JPG, PNG o WebP.')
```

- Posiciona el puntero del archivo al byte `0` (`seek(0)`), rechaza imágenes mayores a 5 MB (`5 * 1024 * 1024` bytes) y valida que la extensión esté permitida antes de que llegue al almacenamiento.

#### Compresión y estandarización (`optimize_image`)

```python
def optimize_image(image_field):
    if not image_field:
        return
    try:
        if hasattr(image_field, 'seek'):
            image_field.seek(0)
        img = Image.open(image_field)
        img = ImageOps.exif_transpose(img)
        if img.mode == 'P':
            img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=75, optimize=True)
        base_name = os.path.splitext(os.path.basename(image_field.name))[0]
        new_name = f"{base_name}.webp"
        image_field.save(new_name, ContentFile(buffer.getvalue()), save=False)
    except Exception:
        if hasattr(image_field, 'seek'):
            try:
                image_field.seek(0)
            except Exception:
                pass
```

- **Línea 33:** `ImageOps.exif_transpose(img)` lee metadatos EXIF (comunes en fotos tomadas verticalmente desde iPhone/Android) y rota los píxeles físicamente para evitar imágenes acostadas.
- **Líneas 34-37:** Convierte paletas indexadas (`P`) conservando transparencia (`RGBA`) si existe, y convierte otros modos incompatibles (ej. `CMYK`) a `RGB`.
- **Línea 38:** `thumbnail((1080, 1080), Image.Resampling.LANCZOS)` escala proporcionalmente sin deformar, acotando ancho y alto a un máximo de `1080px` con filtro de alta nitidez.
- **Líneas 39-43:** Guarda el resultado en memoria (`BytesIO`) como `WEBP` al 75% de calidad y reemplaza el archivo del campo con `save=False` (el `.save()` del modelo lo escribirá en disco justo después).
- **Líneas 44-49:** Si Pillow falla, rebobina el stream para permitir que Django guarde la imagen original sin bloquear la operación.

#### Eliminación de archivos obsoletos al actualizar o borrar

```python
def delete_old_file_on_update(instance, model_class, field_name='image'):
    if not instance.pk:
        return False
    old_instance = model_class.objects.filter(pk=instance.pk).first()
    if not old_instance:
        return False
    old_file = getattr(old_instance, field_name)
    new_file = getattr(instance, field_name)
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
        return True
    return bool(new_file and not old_file)
```

```python
@receiver(post_delete, sender=Equipment)
@receiver(post_delete, sender=Exercise)
def auto_delete_image_on_delete(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)
```

- `Equipment.save()` y `Exercise.save()` llaman a `delete_old_file_on_update(...)` antes de guardar: si el archivo cambió, borra el viejo del disco y devuelve `True` para indicar `is_new_image`, disparando `optimize_image` solo cuando la imagen es nueva o modificada (evitando recomprimirla innecesariamente cuando solo cambia el texto del ejercicio).
- La señal `post_delete` (`auto_delete_image_on_delete`) garantiza que al eliminar una máquina o un ejercicio en Admin o vía API, su archivo `.webp` no quede huérfano ocupando espacio en `media/`. *(Nota: `ExerciseMedia.file` y `ExerciseMedia.thumbnail` no cuentan con esta señal ni optimización).*

---

### 5.2 `FlexibleImageField` y resolución de URLs (`apps/catalog/serializers.py`, líneas 10-63)

```python
class FlexibleImageField(serializers.ImageField):
    """Acepta archivos multipart estándar o imágenes codificadas en Base64 (Data URI, string puro o dict)."""

    def to_internal_value(self, data):
        raw_name = None
        if isinstance(data, dict) and 'base64' in data:
            raw_name = data.get('name')
            data = data.get('base64')

        if isinstance(data, str):
            stripped = data.strip()
            if not stripped:
                return None
            if ';base64,' in stripped:
                header, b64_str = stripped.split(';base64,', 1)
                ext = header.split('/')[-1].split(';')[0].lower() if '/' in header else 'jpg'
            else:
                b64_str = stripped
                ext = 'jpg'

            if ext == 'jpeg':
                ext = 'jpg'
            if ext not in ('jpg', 'png', 'webp'):
                ext = 'jpg'

            try:
                decoded = base64.b64decode(''.join(b64_str.split()), validate=True)
            except (ValueError, binascii.Error, TypeError):
                self.fail('invalid_image')

            if not decoded:
                self.fail('invalid_image')

            base_name = os.path.splitext(os.path.basename(raw_name))[0] if raw_name else f"upload_{uuid.uuid4().hex[:12]}"
            data = ContentFile(decoded, name=f"{base_name}.{ext}")

        return super().to_internal_value(data)
```

- **Versatilidad para clientes móviles (React Native / Expo) y web:**
  1. Si llega un archivo `multipart/form-data`, `data` no es `dict` ni `str`, por lo que pasa directo a `super().to_internal_value(data)`.
  2. Si llega un objeto `{"base64": "...", "name": "foto.png"}`, extrae el nombre y el string.
  3. Si es un string vacío, retorna `None` (permite limpiar/omitir la imagen).
  4. Si trae cabecera Data URI (`data:image/png;base64,...`), separa el encabezado para extraer la extensión; si es Base64 puro, asume `.jpg`.
  5. Limpia saltos de línea/espacios con `''.join(b64_str.split())`, decodifica en modo estricto (`validate=True`) y construye un `ContentFile` en memoria con un nombre único (`upload_<hex>` si no traía nombre), entregándoselo finalmente al `ImageField` de DRF para que Pillow verifique que los bytes realmente corresponden a una imagen válida.

```python
def _build_abs_url(request, file_field):
    if not file_field:
        return None
    return request.build_absolute_uri(file_field.url) if request else file_field.url


def _resolve_exercise_image_url(obj, request):
    if obj.image:
        return _build_abs_url(request, obj.image)
    if obj.equipment and obj.equipment.image:
        return _build_abs_url(request, obj.equipment.image)
    media = obj.media.first()
    if media and media.thumbnail:
        return _build_abs_url(request, media.thumbnail)
    return None
```

- Proporciona **degradación elegante** de imágenes: el ejercicio siempre muestra su propia imagen si existe; de lo contrario hereda la foto de su máquina y en última instancia la miniatura de su primer elemento multimedia. Además `ExerciseListSerializer` expone esa URL bajo tres alias (`image`, `image_url`, `thumbnail`) para compatibilidad con distintas pantallas del frontend.

---

### 5.3 Creación/Edición enriquecida en `ExerciseDetailSerializer` (`apps/catalog/serializers.py`, líneas 160-211)

```python
    def create(self, validated_data):
        video_url = validated_data.pop('video_url', None)
        muscle = validated_data.pop('muscle_id', None)
        exercise = Exercise.objects.create(**validated_data)

        if muscle:
            ExerciseMuscle.objects.create(exercise=exercise, muscle=muscle, role='primary')

        if video_url:
            ExerciseMedia.objects.create(
                exercise=exercise,
                media_type='video',
                external_url=video_url,
                title='Demostración en video'
            )

        return exercise
```

- Permite que el panel administrativo cree en **una sola petición HTTP** el `Exercise`, su relación primaria en `ExerciseMuscle` (mediante `muscle_id`) y su video demostrativo en `ExerciseMedia` (mediante `video_url`).
- En `update(...)` (líneas 178-211): si el payload incluye `muscle_id`, elimina los músculos `role='primary'` anteriores y ejecuta `ExerciseMuscle.objects.update_or_create(..., defaults={'role': 'primary'})`. Si incluye `video_url`, actualiza el primer `ExerciseMedia` de tipo `'video'`, lo crea si no existía, o lo elimina si se envió vacío (`""`).

---

### 5.4 ViewSets, subconsultas `Exists(OuterRef('pk'))`, `@action` y borrado atómico (`apps/catalog/views.py`)

#### Subconsulta eficiente de favoritos (`EquipmentViewSet` y `ExerciseViewSet`)

```python
# apps/catalog/views.py (líneas 89-107)
    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            queryset = queryset.annotate(
                is_favorite=Exists(
                    UserFavoriteExercise.objects.filter(user=user, exercise=OuterRef('pk'))
                )
            )
            eq_qs = Equipment.objects.annotate(
                is_favorite=Exists(
                    UserFavoriteEquipment.objects.filter(user=user, equipment=OuterRef('pk'))
                )
            )
            queryset = queryset.prefetch_related(Prefetch('equipment', queryset=eq_qs))
        else:
            queryset = queryset.annotate(
                is_favorite=Value(False, output_field=BooleanField())
            )
```

- **Optimización SQL:** En vez de hacer una consulta `SELECT EXISTS(...)` dentro del serializador por cada uno de los 20 ejercicios de la página (problema N+1), `Exists(OuterRef('pk'))` traduce la comprobación a una única subconsulta correlacionada directamente en SQL.
- Cuando el usuario no ha iniciado sesión, `Value(False, output_field=BooleanField())` mantiene el campo `is_favorite = False` consistente en el esquema JSON sin tocar la tabla de favoritos.
- `Prefetch('equipment', queryset=eq_qs)` garantiza que el objeto `equipment` anidado dentro de `ExerciseDetailSerializer` también traiga su propio `is_favorite` anotado.
- Al final de `ExerciseViewSet.get_queryset()` se retorna `queryset.distinct()` porque `search_fields = ['name', 'equipment__name', 'muscles__name']` y el filtro `?muscle=` hacen `JOIN` sobre una relación muchos-a-muchos, lo que produciría filas repetidas sin `.distinct()`.

#### Acciones de favoritos (`@action`)

```python
# apps/catalog/views.py (líneas 121-137)
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='favorite')
    def toggle_favorite(self, request, pk=None):
        exercise = self.get_object()
        fav, created = UserFavoriteExercise.objects.get_or_create(
            user=request.user,
            exercise=exercise
        )
        if not created:
            fav.delete()
            return Response({'is_favorite': False, 'exercise_id': str(exercise.id)})
        return Response({'is_favorite': True, 'exercise_id': str(exercise.id)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='favorites')
    def list_favorites(self, request):
        queryset = self.get_queryset().filter(favorited_by__user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

- `toggle_favorite` implementa un interruptor (*toggle*) atómico con `get_or_create`: si ya existía, lo elimina y responde `200 OK` (`is_favorite: False`); si no existía, lo crea y responde `201 Created` (`is_favorite: True`). El mismo patrón aplica en `EquipmentViewSet`.
- `list_favorites` lista todos los favoritos del usuario sin paginar.

#### Borrado transaccional en `ExerciseViewSet.perform_destroy` (líneas 139-143)

```python
    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.routine_placements.all().delete()
            instance.logged_workouts.all().delete()
            instance.delete()
```

- Envuelve el borrado en `transaction.atomic()` para garantizar atomicidad todo-o-nada: primero elimina las apariciones del ejercicio en rutinas (`RoutineExercise`) y en entrenamientos registrados (`WorkoutLogExercise`) —lo cual evita errores de integridad referencial ya que las migraciones `0002_initial` de `routines` y `tracking` tienen `PROTECT`— y finalmente borra el `Exercise` (lo que a su vez dispara la señal `post_delete` para borrar su imagen `.webp`).

---

### 5.5 Comando semilla `seed_catalog` (`apps/catalog/management/commands/seed_catalog.py`)

```python
class Command(BaseCommand):
    help = 'Puebla la base de datos con grupos musculares, máquinas principales y ejercicios de ejemplo'

    def handle(self, *args, **options):
        # ... 12 MuscleGroup ...
        for name, part in muscles_data:
            m, _ = MuscleGroup.objects.get_or_create(name=name, defaults={'body_part': part})
            muscles[name] = m
        # ... 6 Equipment ...
        for eq_data in equipment_data:
            eq, _ = Equipment.objects.get_or_create(name=eq_data['name'], defaults=eq_data)
            equipments[eq.name] = eq
        # ... 3 Exercise + ExerciseMuscle ...
        for ex_info in exercises_data:
            primary = ex_info.pop('primary_muscle')
            secondary = ex_info.pop('secondary_muscle')
            ex, created = Exercise.objects.get_or_create(
                name=ex_info['name'],
                defaults=ex_info
            )
            if created:
                ExerciseMuscle.objects.create(exercise=ex, muscle=primary, role='primary')
                if secondary:
                    ExerciseMuscle.objects.create(exercise=ex, muscle=secondary, role='secondary')
```

- Hereda de `BaseCommand` y es **100% idempotente** gracias a `get_or_create(...)`: si se ejecuta varias veces, no duplica los 12 grupos musculares, las 6 máquinas ni los 3 ejercicios iniciales (`Prensa de Piernas 45°`, `Jalón al Pecho en Polea Alta`, `Extensión de Rodilla en Máquina`), y solo crea las filas de `ExerciseMuscle` cuando `created` es `True`.

---

## 6. Flujo paso a paso (Subida y renderizado de una imagen de ejercicio en Base64)

1. Un administrador envía `POST /api/v1/catalog/exercises/` (o `PATCH`) con un JSON que contiene `"image": "data:image/jpeg;base64,/9j/4AAQ..."` junto con `name`, `equipment_id`, `muscle_id`, `video_url` e `instructions`.
2. `IsAdminOrReadOnly` verifica `request.user.is_authenticated and request.user.is_staff`.
3. `JSONParser` lee el JSON y `FlexibleImageField.to_internal_value()` detecta `;base64,`, decodifica los bytes a un `ContentFile` con extensión `.jpg`, y valida que sea una imagen real.
4. El validador `validate_image` comprueba que pese ≤ 5 MB y tenga extensión permitida.
5. `Exercise.save()` calcula `slug` si es nuevo (o invoca `delete_old_file_on_update` si ya existía, eliminando la imagen previa del disco) y llama a `optimize_image(self.image)`.
6. Pillow corrige orientación EXIF, escala a máximo `1080x1080` y guarda un `.webp` ligero en `media/exercises/`.
7. `ExerciseDetailSerializer.create()` crea `ExerciseMuscle` (primary) y `ExerciseMedia` (video) si se enviaron.
8. Al responder o al consultar `GET /api/v1/catalog/exercises/`, `Exists(OuterRef('pk'))` inyecta `is_favorite` en la misma consulta SQL y `_resolve_exercise_image_url` devuelve la URL absoluta del `.webp`.

---

## 7. Conceptos y términos técnicos

- **EXIF (`ImageOps.exif_transpose`):** Metadatos que graban las cámaras móviles indicando en qué orientación se tomó la foto. Sin transponer, un servidor suele mostrar fotos verticales giradas 90 grados.
- **Formato WebP:** Formato moderno de imagen desarrollado por Google que ofrece compresión superior (con y sin pérdida) y transparencia, reduciendo drásticamente el consumo de ancho de banda en apps móviles frente a PNG/JPEG.
- **Data URI Base64:** Representación de un archivo binario en texto ASCII con el prefijo `data:<mime>;base64,<datos>`, muy usada por apps móviles o formularios JSON cuando no se desea construir peticiones `multipart/form-data`.
- **Señales de Django (`@receiver(post_delete)`):** Patrón Observador integrado en el ORM que ejecuta automáticamente una función tras ocurrir un evento sobre un modelo (en este caso, borrar la imagen física después de eliminar el registro de BD).
- **Subconsulta `Exists(OuterRef('pk'))`:** Expresión ORM que genera un `EXISTS (SELECT 1 FROM ... WHERE ... = tabla_externa.id)` en SQL, resolviendo flags booleanos por fila en una sola consulta sin provocar problemas N+1.
- **Idempotencia (`seed_catalog`):** Propiedad de una operación que produce exactamente el mismo estado final sin importar cuántas veces se ejecute repetidamente (`get_or_create`).

---

## 8. Posibles preguntas del profesor

1. **¿Por qué se creó `FlexibleImageField` en lugar de usar directamente `serializers.ImageField`?**
   - *Respuesta modelo:* `serializers.ImageField` solo acepta archivos enviados como `multipart/form-data`. Sin embargo, clientes móviles como React Native / Expo frecuentemente envían imágenes capturadas en JSON codificadas en Base64 (como Data URI, string puro o diccionario `{base64, name}`). `FlexibleImageField` normaliza cualquiera de esos formatos a `ContentFile` antes de delegar la validación estándar a `ImageField`.

2. **¿Qué pasos realiza `optimize_image` y por qué ocurre en `models.py` dentro de `save()`?**
   - *Respuesta modelo:* Abre la imagen con Pillow, aplica `ImageOps.exif_transpose` para corregir la rotación de fotos móviles, normaliza el modo de color a RGB/RGBA, redimensiona manteniendo proporción dentro de `1080x1080` con `LANCZOS`, y guarda como `WEBP` al 75% de calidad. Al estar en `save()` de `Equipment` y `Exercise`, aplica uniformemente tanto si la imagen entra por la API REST como desde el Django Admin.

3. **¿Cómo evita el catálogo el problema de consultas N+1 al indicar si cada ejercicio o máquina es favorito del usuario?**
   - *Respuesta modelo:* En `get_queryset()` de `EquipmentViewSet` y `ExerciseViewSet`, cuando el usuario está autenticado, se anota el queryset con `is_favorite=Exists(UserFavorite*.objects.filter(user=user, ...=OuterRef('pk')))`. De este modo la base de datos resuelve el booleano en la misma consulta SQL principal en lugar de ejecutar una consulta por cada elemento serializado.

4. **¿Qué sucede si un ejercicio no tiene imagen propia al consultarlo en el listado?**
   - *Respuesta modelo:* La función auxiliar `_resolve_exercise_image_url(obj, request)` aplica una cascada de respaldo: primero usa `obj.image`; si no existe, toma la foto de su máquina asociada (`obj.equipment.image`); si tampoco existe, busca la miniatura de su primer registro multimedia (`obj.media.first().thumbnail`); y solo si todo falta devuelve `None`.

5. **¿Por qué `ExerciseViewSet.perform_destroy` borra `routine_placements` y `logged_workouts` explícitamente dentro de `transaction.atomic()`?**
   - *Respuesta modelo:* Porque las migraciones iniciales `0002_initial.py` de `routines` y `tracking` establecieron `on_delete=PROTECT` en las llaves foráneas hacia `Exercise`. Borrar ambos conjuntos relacionados explícitamente antes de eliminar el ejercicio evita un error `ProtectedError` o fallo de clave foránea en SQLite, y el bloque `transaction.atomic()` garantiza que si algún paso falla, no quede el ejercicio parcialmente desvinculado.

6. **¿Por qué `ExerciseViewSet.get_queryset()` finaliza con `.distinct()`?**
   - *Respuesta modelo:* Porque soporta búsquedas y filtros a través de la relación muchos-a-muchos `muscles` (`search_fields` incluye `muscles__name` y filtra por `?muscle=`). Al hacer `JOIN` en SQL, un ejercicio con múltiples músculos puede aparecer repetido en el conjunto resultado; `.distinct()` elimina esos duplicados antes de paginar.

---

## 9. Resumen para repasar

- El catálogo abarca **7 modelos** (`Equipment`, `MuscleGroup`, `Exercise`, `ExerciseMuscle`, `ExerciseMedia`, `UserFavoriteEquipment`, `UserFavoriteExercise`) gobernados por `IsAdminOrReadOnly` (lectura libre, escritura exclusiva de `is_staff=True`).
- Las imágenes aceptan multipart o **Base64** (`FlexibleImageField`), se validan a máximo **5 MB**, se optimizan a **WebP 1080x1080** con corrección **EXIF** y se limpian del disco en actualizaciones y borrados (`post_delete`).
- La bandera `is_favorite` se calcula en SQL con `Exists(OuterRef('pk'))` y se alterna mediante `POST .../favorite/` (`IsAuthenticated`).
- `ExerciseViewSet.perform_destroy` protege la integridad mediante `transaction.atomic()`, y `python manage.py seed_catalog` inicializa de forma idempotente 12 músculos, 6 máquinas y 3 ejercicios base.
