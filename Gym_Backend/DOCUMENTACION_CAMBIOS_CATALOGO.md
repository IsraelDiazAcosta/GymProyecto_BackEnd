# Bitácora Técnica de Cambios: Catálogo, Favoritos y Tarjeta de Máquinas

**Fecha:** 15 de Noviembre de 2026  
**Proyecto:** Gym Proyecto (Fullstack: Django REST Framework + React Native / Expo)  
**Audiencia:** Equipo de Desarrollo Frontend & Backend  

---

## 1. Resumen Ejecutivo de Cambios

Durante esta sesión de trabajo se completaron 4 objetivos clave:

1. **Persistencia de Ejercicios Favoritos en Backend y Frontend:**
   - Creación del modelo relacional `UserFavoriteExercise` y migración en base de datos.
   - Endpoint REST `@action(methods=["post"], detail=True)` para toggling (`/favorite/`).
   - Integración en el hook `useGymDashboardData` con sincronización de estado optimista y actualización de chips/contadores globales.

2. **Resolución de Bugs Críticos:**
   - **404 Not Found al marcar favorito en ejercicio:** La acción `toggle_favorite` estaba vinculada erróneamente en el ViewSet de Equipamiento en lugar del ViewSet de Ejercicios.
   - **Warning de React (`Each child in a list should have a unique "key" prop`):** `ExerciseMuscleSerializer` no serializaba `id` explícito, retornando `undefined` al iterar músculos primarios/secundarios en `ExerciseDetailModal`.

3. **Chip de Días Asistidos Semanales en la Card Global de Usuario:**
   - Se expuso la asistencia semanal (`weekly_attended_days / 7`) desde el hook del dashboard.
   - Se agregó el chip interactivo en la cabecera/perfil estático (`DashboardHeader` / `UserProfileCard`) junto a los chips de rutinas y ejercicios.

4. **Diseño y Desacoplamiento Visual de Máquinas vs. Ejercicios:**
   - Enriquecimiento de la sección `EQUIPO / MÁQUINA REQUERIDA` dentro de `ExerciseDetailModal`.
   - Búsqueda reactiva de la máquina física (`matchedEquipment`), resolución de URL de imagen (`resolveMediaUrl`), badges de tipo, marca y guía de ajuste (`setup_guide`).
   - Fallback limpio y semántico para ejercicios de peso libre y calistenia.

---

## 2. Cambios en Backend (Django REST Framework)

### 2.1 Modelo `UserFavoriteExercise`
**Archivo modificado:** `apps/catalog/models.py`

Se diseñó la tabla intermedia que asocia usuarios con ejercicios marcados como favoritos, garantizando unicidad y cascada limpia al borrar usuarios o ejercicios:

```python
class UserFavoriteExercise(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_exercises"
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="favorited_by_users"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ejercicio Favorito de Usuario"
        verbose_name_plural = "Ejercicios Favoritos de Usuarios"
        unique_together = ("user", "exercise")
        ordering = ["-created_at"]
```

> **Migración aplicada:** `apps/catalog/migrations/0003_userfavoriteexercise.py`.

---

### 2.2 Serializadores: Anotación y Flag `is_favorite`
**Archivo modificado:** `apps/catalog/serializers.py`

En `ExerciseListSerializer` y `ExerciseDetailSerializer` se incorporó el campo booleano `is_favorite`:

```python
class ExerciseListSerializer(serializers.ModelSerializer):
    is_favorite = serializers.BooleanField(read_only=True, default=False)
    # ... demás campos
```

En `ExerciseMuscleSerializer`, se aseguró la exposición del identificador para evitar keys huérfanas en el cliente:
```python
class ExerciseMuscleSerializer(serializers.ModelSerializer):
    muscle_name = serializers.CharField(source="muscle.name", read_only=True)
    class Meta:
        model = ExerciseMuscle
        fields = ["id", "muscle", "muscle_name", "role", "order"]
```

---

### 2.3 ViewSet y Endpoint de Favorito
**Archivo modificado:** `apps/catalog/views.py`

Se optimizó el `get_queryset()` de `ExerciseViewSet` con `Exists` subquery para anotar `is_favorite` en un solo query SQL sin queries N+1:

```python
class ExerciseViewSet(viewsets.ModelViewSet):
    # ...
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            favorite_subquery = UserFavoriteExercise.objects.filter(
                user=user,
                exercise=OuterRef("pk")
            )
            qs = qs.annotate(is_favorite=Exists(favorite_subquery))
        else:
            qs = qs.annotate(is_favorite=Value(False, output_field=BooleanField()))
        return qs

    @action(detail=True, methods=["post"], url_path="favorite")
    def toggle_favorite(self, request, pk=None):
        exercise = self.get_object()
        fav, created = UserFavoriteExercise.objects.get_or_create(
            user=request.user,
            exercise=exercise
        )
        if not created:
            fav.delete()
            return Response({"status": "removed", "is_favorite": False})
        return Response({"status": "added", "is_favorite": True})
```

---

## 3. Cambios en Frontend (React Native & TypeScript)

### 3.1 Integración en la Capa API
**Archivo modificado:** `src/services/api.ts`

Se añadió el método tipado para alternar favoritos:
```typescript
async toggleExerciseFavorite(id: string | number): Promise<{ status: string; is_favorite: boolean }> {
  return this.post(`/catalog/exercises/${id}/favorite/`, {});
}
```

---

### 3.2 Lógica de Negocio y Estado en Hook
**Archivo modificado:** `src/hooks/useGymDashboardData.ts`

- Implementación de `handleToggleExerciseFavorite` con actualización inmediata en el listado de ejercicios (`exerciseList`).
- Cálculo reactivo de `favoriteExercisesCount` para alimentar chips y contadores en tiempo real.
- Exposición de la asistencia semanal acumulada (`weeklyAttendedDays`).

---

### 3.3 Corrección de Keys en Renderizado de Listas
**Archivo modificado:** `src/components/dashboard/catalog/ExerciseDetailModal.tsx`

**Causa del error previo:** React arrojaba `Each child in a list should have a unique "key" prop` porque el objeto serializado `m` no garantizaba un `id` único consistente en tiempo de ejecución.

**Solución aplicada:**
```tsx
{primaryMuscles.map((m, idx) => (
  <View
    key={m.id ?? m.muscle ?? `${m.muscle_name}-${idx}`}
    style={[styles.primaryMuscleBadge, ...]}
  >
    <Text style={[styles.primaryMuscleText, ...]}>
      {m.muscle_name || m.muscle}
    </Text>
  </View>
))}
```

---

### 3.4 Rediseño de la Tarjeta de Máquina Requerida en `ExerciseDetailModal`
**Archivo modificado:** `src/components/dashboard/catalog/ExerciseDetailModal.tsx`

#### A. Resolución de Máquina y Multimedia
Para desacoplar la imagen del ejercicio de la máquina y permitir la coexistencia de ambas:
```tsx
const matchedEquipment = useMemo(() => {
  if (!exercise) return null;
  if (typeof exercise.equipment === "object" && exercise.equipment !== null) {
    return exercise.equipment;
  }
  const targetId = exercise.equipment_id ?? (typeof exercise.equipment === "number" ? exercise.equipment : null);
  if (targetId && equipmentList?.length) {
    const found = equipmentList.find((eq) => eq.id === targetId);
    if (found) return found;
  }
  if (exercise.equipment_name && equipmentList?.length) {
    const foundByName = equipmentList.find(
      (eq) => eq.name.trim().toLowerCase() === exercise.equipment_name?.trim().toLowerCase()
    );
    if (foundByName) return foundByName;
  }
  return null;
}, [exercise, equipmentList]);

const equipmentImageUrl = useMemo(() => {
  if (!matchedEquipment?.image) return null;
  return resolveMediaUrl(matchedEquipment.image);
}, [matchedEquipment]);
```

#### B. Componente Visual
La tarjeta ahora cuenta con:
1. **Thumbnail de Máquina (48x48):** Imagen con `cachePolicy="memory-disk"` y `contentFit="cover"`, o fallback a icono SVG `cog`.
2. **Nombre e Información:** Nombre del equipo, chip con el tipo (`PALANCA`, `POLEA`, `CARDIO`, etc.) y texto de la marca (`• Matrix`, `• Hammer Strength`).
3. **Caja de Ajuste (`setup_guide`):** Instrucciones de graduación (asientos, pines, respaldos) acompañada del icono `sliders`.
4. **Fallback Semántico:** Si el ejercicio es de peso libre o corporal, muestra el icono `dumbbell` e informa claramente que no requiere maquinaria fija.

---

## 4. Estado de Verificación y Compilación

| Prueba | Entorno | Resultado |
| :--- | :--- | :--- |
| `python manage.py check` | Backend (Django) | **System check identified no issues (0 silenced).** |
| `python manage.py showmigrations catalog` | Backend (PostgreSQL/SQLite) | **[X] 0003_userfavoriteexercise aplicado.** |
| `npx tsc --noEmit` | Frontend (TypeScript) | **0 errores de compilación.** |
| Endpoint `/api/v1/catalog/exercises/<id>/favorite/` | API REST | **200 OK con respuesta toggleada.** |

---

## 5. Recomendaciones para el Equipo

1. **Subida de Medios en Admin / Dashboard:**
   - Las imágenes de **Máquinas** deben mostrar la máquina física en el gimnasio y su modelo.
   - Las imágenes/GIFs de **Ejercicios** deben ilustrar la postura y ejecución anatómica.
2. **Uso de IDs:** Recordar que los ejercicios utilizan identificadores UUID (`string`) por portabilidad y unicidad global en el catálogo, mientras que las máquinas utilizan `integer autoincrement` (`number`). Los hooks y helpers ya contemplan ambos tipos.
