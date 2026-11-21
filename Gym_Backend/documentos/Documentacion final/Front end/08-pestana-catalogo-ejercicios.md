# 08. Pestaña Catálogo de Ejercicios (`CatalogSection`, `AddExerciseModal`, `ExerciseDetailModal` y `muscleValidation.ts`)

---

## 1. Propósito

La pestaña **Catálogo** (`activeTab === "catalog"`) centraliza la biblioteca de ejercicios del gimnasio **Apex Gym Hub** junto con su lógica de clasificación anatómica y consulta técnica:

1. **Exploración y filtrado (`CatalogSection`):** permite a cualquier usuario buscar ejercicios por nombre, máquina o músculo principal, filtrarlos por grupo muscular (Pecho, Espalda, Pierna, Hombro, Brazo, Core) o favoritos, y abrir la ficha técnica completa.
2. **Heurística anatómica (`muscleValidation.ts`):** determina de forma tolerante si un ejercicio pertenece a un enfoque muscular determinado, combinando relaciones estructuradas de base de datos con palabras clave por si faltan metadatos.
3. **Ficha técnica multimedia (`ExerciseDetailModal`):** presenta la imagen del ejercicio (o heredada de su máquina), acceso a video demostrativo externo (`Linking.openURL`), máquina requerida con guía de ajuste, músculos primarios/secundarios e instrucciones paso a paso.
4. **Administración (`AddExerciseModal`):** habilita únicamente para cuentas con rol `isStaff` la creación de nuevos ejercicios vinculados a un `MuscleGroup` y un `Equipment` opcional, además de edición/borrado mediante long-press o menú `⋮`.

---

## 2. Ubicación

Todas las rutas parten de `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

| Archivo | Rol |
| :--- | :--- |
| `src/components/dashboard/catalog/CatalogSection.tsx` | Vista principal de la pestaña Catálogo: buscador, chips musculares, favoritos y tarjetas de ejercicio. |
| `src/components/dashboard/catalog/AddExerciseModal.tsx` | Modal inferior para que el staff registre un nuevo ejercicio en el catálogo. |
| `src/components/dashboard/catalog/ExerciseDetailModal.tsx` | Ficha técnica detallada de un ejercicio con video externo, máquina requerida, anatomía y pasos. |
| `src/components/dashboard/muscleValidation.ts` | Utilidad pura de validación y etiquetado anatómico (`isExerciseCompatibleWithFocus`, `getExerciseMuscleLabel`). |
| `src/components/dashboard/CatalogSection.tsx` | **Shim heredado (1 línea):** `export * from "./catalog/CatalogSection";`. |
| `src/components/dashboard/AddExerciseModal.tsx` | **Shim heredado (1 línea):** `export * from "./catalog/AddExerciseModal";`. |
| `src/components/dashboard/ExerciseDetailModal.tsx` | **Shim heredado (1 línea):** `export * from "./catalog/ExerciseDetailModal";`. |

> **Nota sobre archivos legacy:** Igual que en Máquinas, los tres archivos en la raíz `src/components/dashboard/` son *barrel re-exports* de una sola línea; la lógica real vive únicamente en `src/components/dashboard/catalog/` y `src/components/dashboard/muscleValidation.ts`.

---

## 3. Cómo se conecta

```text
GymDashboard.tsx (activeTab === "catalog")
  │
  ├──► CatalogSection (./catalog/CatalogSection.tsx)
  │       ├── Usa `isExerciseCompatibleWithFocus` de `../muscleValidation`
  │       ├── Resuelve imagen propia o heredada con `resolveExerciseImageUrl(ex, equipmentList)`
  │       ├── Tap en tarjeta ──► `vm.openExerciseDetail(ex.id)` ──► `GET /catalog/exercises/{id}/`
  │       │                                                            └──► abre `ExerciseDetailModal`
  │       ├── Corazón ❤️ ──► `vm.handleToggleExerciseFavorite(ex.id)` ──► `POST /catalog/exercises/{id}/favorite/`
  │       ├── Botón "+ Nuevo" (solo `isStaff`) ──► `vm.loadCatalogExtras()` + `vm.setShowAddExerciseModal(true)`
  │       └── Long-press / `⋮` (solo `isStaff`) ──► `vm.handleOpenExerciseOptions(ex)` ──► `ItemActionSheet`
  │
  ├──► ExerciseDetailModal (./catalog/ExerciseDetailModal.tsx)
  │       └── Botón "Ver Video" / "Abrir Video Externo" ──► `Linking.openURL(videoUrl)`
  │
  └──► AddExerciseModal (./catalog/AddExerciseModal.tsx) [solo montado si `isAdmin === true`]
          └── `onSubmit` ──► `vm.handleCreateExercise()` ──► `POST /catalog/exercises/`
```

- **Consumo compartido de `muscleValidation.ts`:** Además de `CatalogSection.tsx`, las funciones de `muscleValidation.ts` son reutilizadas por `RoutinesSection.tsx`, `RoutineCard.tsx`, `SelectExerciseModal.tsx`, `EditRoutineForm.tsx` y `useGymDashboardData.ts` para validar compatibilidad de ejercicios con el enfoque de cada rutina.
- **Carga bajo demanda de catálogos auxiliares:** Al presionar "+ Nuevo" en Catálogo, `GymDashboard` llama a `vm.loadCatalogExtras()`, que descarga `api.getEquipment()` y `api.getMuscles()` si aún no estaban cargados, asegurando que los selectores de `AddExerciseModal` tengan opciones disponibles.

---

## 4. Componentes, funciones y variables clave

### En `CatalogSection.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `CatalogSectionProps` | Interfaz | `colors`, `exercises`, `equipmentList`, `isStaff`, `onOpenAddExercise`, `onOpenExerciseDetail`, `onExerciseOptionsPress`, `onToggleFavorite`. |
| `MUSCLE_FILTER_OPTIONS` | Constante | 6 grupos: `pecho`, `espalda`, `pierna`, `hombro`, `brazo`, `core`. |
| `searchQuery` | Estado local (`string`) | Texto de búsqueda. |
| `selectedMuscleFilter` | Estado local (`string`) | `"all"`, `"favorites"` o un grupo muscular de `MUSCLE_FILTER_OPTIONS`. |
| `favoritesCount` | `useMemo` | Total de ejercicios con `is_favorite === true`. |
| `filteredExercises` | `useMemo` | Lista filtrada por `searchQuery` (en `name`, `equipment_name`, `primary_muscle`) y `selectedMuscleFilter`. |
| `handleLongPress(ex)` | Handler | Protegido por `if (!isStaff || !onExerciseOptionsPress) return;`, vibra 45 ms y abre opciones de edición/borrado. |

### En `AddExerciseModal.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `AddExerciseModalProps` | Interfaz | Props controladas desde `useGymDashboardData` (`newExName`, `newExVideo`, `newExInstructions`, `selectedEquipment`, `selectedMuscle`, `newExImage`, más sus setters y `onSubmit`/`onClose`). |
| `dropdownOpen`, `muscleDropdownOpen` | Estados locales (`boolean`) | Controlan el despliegue de los dos selectores personalizados (máquina y grupo muscular). |
| `selectedEquipObj`, `selectedMuscleObj` | Derivados | Buscan los objetos seleccionados en `equipmentList` y `muscleList` para mostrar sus etiquetas. |
| `previewUri` | Derivado | `newExImage?.uri \|\| resolveMediaUrl(selectedEquipObj?.image)`: si el usuario no sube foto propia, previsualiza automáticamente la foto de la máquina vinculada. |

### En `ExerciseDetailModal.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `imgError` | Estado local (`boolean`) | Si falla la carga de `heroImage`, activa el *fallback* al bloque `placeholderHero` con botón de video en línea. |
| `matchedEquipment` | `useMemo` | Resuelve la máquina requerida desde `exercise.equipment` (si es objeto), o buscando por `equipment_id` / ID numérico / `equipment_name` en `equipmentList`. |
| `videoMedia`, `videoUrl` | Derivados | Localiza en `exercise.media` el elemento con `media_type === "video"` o `external_url` y extrae `external_url \|\| file`. |
| `primaryMuscles`, `secondaryMuscles` | Derivados | Filtran `exercise.muscles` según `m.role === "primary"` o `"secondary"`. |
| `instructionsList` | Derivado (`string[]`) | Normaliza `exercise.instructions` sea arreglo o texto plano en un listado iterable. |

### En `muscleValidation.ts`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `isExerciseCompatibleWithFocus(exerciseOrName, focus?, primaryMuscleOverride?)` | Función pura exportada | Evalúa compatibilidad anatómica mediante una cascada heurística de 3 niveles. |
| `getExerciseMuscleLabel(exerciseOrName, primaryMuscleOverride?)` | Función pura exportada | Devuelve la etiqueta muscular visible priorizando `primary_muscle`, luego `muscles[0]` y por último `"General"`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### A. Cascada heurística anatómica de 3 niveles en `muscleValidation.ts`

```ts
export function isExerciseCompatibleWithFocus(
  exerciseOrName: Exercise | string,
  focus?: string,
  primaryMuscleOverride?: string,
): boolean {
  if (!focus || focus.toLowerCase() === "fullbody") {
    return true;
  }

  const f = focus.toLowerCase().trim();
  const exercise: Partial<Exercise> =
    typeof exerciseOrName === "string"
      ? { name: exerciseOrName, primary_muscle: primaryMuscleOverride }
      : exerciseOrName;
```

La función opera en **tres niveles de prioridad descendente**:

1. **Nivel 1 — Relación estructurada `exercise.muscles` (líneas 22-82):** si recibe un objeto `Exercise` con su arreglo `muscles` (proveniente de la tabla intermedia en Django), revisa si `m.body_part` coincide exactamente con el enfoque (`bp === f`) o si `m.muscle_name` contiene términos anatómicos asociados (por ejemplo, para `"pierna"` acepta `cuádriceps`, `femoral`, `glúteo`, `isquiotibial`, `pantorrilla`, `gemelo`; para `"brazo"` acepta `bíceps`, `tríceps`, `antebrazo`).
2. **Nivel 2 — Campo plano `primary_muscle` (líneas 84-125):** si no hubo coincidencia en el arreglo `muscles`, inspecciona `primaryMuscleOverride || exercise.primary_muscle` con las mismas familias anatómicas.
3. **Nivel 3 — Heurística léxica sobre el nombre del ejercicio (líneas 127-196):** como respaldo cuando el ejercicio no tiene músculo asignado o solo se pasa su nombre, detecta palabras clave biomecánicas en español e inglés (`"press banca"`, `"bench"`, `"aperturas"` → pecho; `"jalón"`, `"remo"`, `"dominada"`, `"pulldown"` → espalda; `"sentadilla"`, `"squat"`, `"prensa"`, `"peso muerto"` → pierna; `"curl"`, `"copa"`, `"fondos"` → brazo; `"militar"`, `"elevaciones"`, `"arnold"` → hombro; `"crunch"`, `"plancha"` → core). Si ningún nivel coincide, retorna `false`.

> **Detalle técnico importante detectado en la revisión:** En `CatalogSection.tsx` (líneas 89-93), `SelectExerciseModal.tsx` (líneas 140-144) y `EditRoutineForm.tsx` (líneas 247-251) se invoca `isExerciseCompatibleWithFocus(ex.name, ..., ex.primary_muscle)` pasando `ex.name` (string) en lugar del objeto `ex` completo. Eso hace que en esos puntos **se omita el Nivel 1 (`ex.muscles`)** y la validación dependa únicamente de `primary_muscle` y del nombre; en cambio `RoutinesSection.tsx` y `useGymDashboardData.ts` sí pasan el objeto `ex` completo.

### B. Toggle de chip muscular y permisos de solo lectura vs `isStaff` en `CatalogSection.tsx`

```tsx
{isStaff && onOpenAddExercise && (
  <Pressable onPress={onOpenAddExercise} style={[styles.addBtn, ...]}>
    <GymIcon name="plus" size={16} color={colors.onPrimary} />
    <Text style={[styles.addBtnText, { color: colors.onPrimary }]}>
      {t("catalog.newBtn")}
    </Text>
  </Pressable>
)}
```

```tsx
onPress={() =>
  setSelectedMuscleFilter(isSelected ? "all" : opt.value)
}
```

- **Permisos granulares:** Un atleta estándar (`isStaff = false`) nunca ve el botón "+ Nuevo" ni el botón `⋮`, ni puede disparar `onLongPress`. Solo puede consultar el detalle (`onOpenExerciseDetail`), buscar, filtrar y guardar favoritos personales (`onToggleFavorite`). Además, en `GymDashboard.tsx`, `canManageItem` (`isAdmin || (type !== "exercise" && type !== "equipment")`) y `requireAdmin()` en `useGymDashboardData.ts` refuerzan este bloqueo.
- **Comportamiento de chips:** Al tocar un grupo muscular ya activo (`isSelected === true`), vuelve automáticamente a `"all"`, facilitando alternar filtros con un solo toque.

### C. Resolución de video externo y fallback de imagen en `ExerciseDetailModal.tsx`

```tsx
const imageUri = !imgError
  ? resolveExerciseImageUrl(exercise, equipmentList)
  : null;

const videoMedia = exercise.media?.find(
  (m) => m.media_type === "video" || Boolean(m.external_url),
);
const videoUrl = videoMedia?.external_url || videoMedia?.file;
```

- **Imagen heredada:** `resolveExerciseImageUrl` intenta usar primero la imagen propia del ejercicio (`exercise.image`, `image_url`, `thumbnail` o `media` de tipo `"image"`) y, si no tiene ninguna, busca la foto de la máquina vinculada dentro de `equipmentList`.
- **Apertura de video externo:** Si existe `videoUrl` y hay `imageUri`, superpone una píldora flotante (`videoOverlayBtn`) en la esquina inferior derecha de la foto que ejecuta `Linking.openURL(videoUrl)`. Si no hay imagen (o falló su descarga), muestra el recuadro `placeholderHero` con un botón central `"Abrir Video Externo"`.

### D. Notas de revisión técnica (código muerto menor)

- En `CatalogSection.tsx`, línea 16 importa `useAuth` sin utilizarlo (el rol llega por la prop `isStaff`), y en línea 642 existe un estilo `favoriteBtn` duplicado de `favBtn` que no se referencia.
- En `ExerciseDetailModal.tsx`, los estilos `infoValue` e `infoSub` (líneas 668-675) tampoco se usan tras rediseñar la tarjeta de máquina requerida.

---

## 6. Flujo paso a paso

### Flujo 1: Consultar la ficha técnica de un ejercicio
1. El usuario abre la pestaña **Catálogo** y opcionalmente escribe en la barra de búsqueda o selecciona un chip muscular (validado con `isExerciseCompatibleWithFocus`) o **Favoritos**.
2. Toca la tarjeta del ejercicio deseado (`onPress={() => onOpenExerciseDetail(ex.id)}`).
3. `useGymDashboardData.openExerciseDetail` activa el indicador de carga, solicita `GET /catalog/exercises/{id}/` (`api.getExerciseDetail`) para traer todos los detalles (`muscles`, `media`, `instructions`, `description`), guarda el resultado en `selectedExercise` y pone `modalExerciseVisible = true`.
4. `ExerciseDetailModal` resuelve la máquina requerida (`matchedEquipment`), separa músculos primarios y secundarios, lista las instrucciones enumeradas y, si existe `videoUrl`, abre el enlace en el navegador/app de YouTube mediante `Linking.openURL`.

### Flujo 2: Crear un nuevo ejercicio (Solo Staff)
1. El administrador pulsa **"+ Nuevo"**; se cargan máquinas y músculos si estaban vacíos (`loadCatalogExtras`) y se abre `AddExerciseModal`.
2. Ingresa nombre, selecciona grupo muscular (`selectedMuscle`), máquina opcional (`selectedEquipment`), URL de video, instrucciones y opcionalmente captura/elige una foto (`pickAndCompressImage`).
3. Al guardar (`handleCreateExercise`), `useGymDashboardData` valida `requireAdmin()`, nombre no vacío y músculo obligatorio (`!newExMuscle`), envía `POST /catalog/exercises/`, limpia los estados, recarga la lista con `api.getExercises()` y muestra un toast de confirmación.

---

## 7. Conceptos y términos técnicos

- **Heurística anatómica en cascada:** Algoritmo de clasificación con varios niveles de respaldo: primero confía en los datos relacionales exactos de la base de datos (`muscles`), luego en campos de texto resumidos (`primary_muscle`) y finalmente en coincidencia de palabras clave en el nombre.
- **Deep linking saliente (`Linking.openURL`):** API nativa de React Native que delega la apertura de una URL externa (por ejemplo, YouTube) al navegador o aplicación nativa correspondiente del dispositivo.
- **Herencia visual de recursos (`resolveExerciseImageUrl`):** Estrategia para evitar tarjetas vacías mostrando la foto de la máquina asociada cuando el ejercicio aún no tiene imagen propia cargada.
- **Modo solo lectura vs Privilegios de Staff:** Patrón de autorización en UI donde el mismo componente sirve para consulta general y para administración condicional mediante la bandera `isStaff`.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué `muscleValidation.ts` tiene tres niveles de verificación en lugar de depender solo del campo `primary_muscle`?**
   - *Respuesta modelo:* Porque los datos de catálogo pueden llegar con distintos grados de detalle según el endpoint (listado resumido vs detalle completo) o con ejercicios creados sin etiqueta explícita. La cascada primero revisa el arreglo relacional `muscles` (`body_part` y `muscle_name`), luego `primary_muscle`, y como último recurso analiza palabras clave anatómicas en el nombre del ejercicio.
2. **¿Cómo sabe `ExerciseDetailModal` qué máquina mostrar si el ejercicio no trae el objeto `equipment` embebido?**
   - *Respuesta modelo:* A través del `useMemo` `matchedEquipment`. Primero revisa si `exercise.equipment` ya es un objeto completo; si solo trae un ID (`equipment_id` o `equipment` numérico) o un nombre (`equipment_name`), busca la máquina correspondiente dentro de `equipmentList` que ya está cargado en memoria.
3. **¿Cómo reproduce los videos demostrativos `ExerciseDetailModal` y qué pasa si el ejercicio no tiene imagen?**
   - *Respuesta modelo:* No incrusta un reproductor pesado sino que detecta el recurso de video en `exercise.media` (`media_type === "video"` o `external_url`) y lo abre externamente mediante `Linking.openURL(videoUrl)`. Si el ejercicio tiene imagen, el botón aparece superpuesto sobre la foto; si no tiene imagen (o falla su carga y se activa `imgError`), muestra una cabecera alternativa con el botón en línea o un aviso de que no hay video adjunto.
4. **¿Qué validaciones mínimas exige el frontend antes de crear un ejercicio en `AddExerciseModal`?**
   - *Respuesta modelo:* En `handleCreateExercise` (`useGymDashboardData.ts`) primero verifica que el usuario sea administrador (`requireAdmin()`), luego exige que el nombre no esté vacío (`!newExName.trim()`) y que se haya seleccionado un grupo muscular (`!newExMuscle`). La máquina, el video, las instrucciones (que toman un texto por defecto si están vacías) y la foto son opcionales.
5. **¿Qué diferencia hay entre lo que puede hacer un atleta normal y un administrador (`isStaff`) dentro del Catálogo?**
   - *Respuesta modelo:* Un atleta normal tiene acceso de solo lectura sobre el catálogo (buscar, filtrar por músculo o favoritos, marcar/desmarcar sus propios favoritos y abrir la ficha técnica con video e instrucciones). El administrador además ve el botón "+ Nuevo", puede mantener presionada una tarjeta o tocar el menú `⋮` para editar o eliminar el ejercicio.
6. **¿Detectaste algún punto de mejora en la llamada a `isExerciseCompatibleWithFocus` desde `CatalogSection.tsx`?**
   - *Respuesta modelo:* Sí: `CatalogSection.tsx` pasa `(ex.name, selectedMuscleFilter, ex.primary_muscle)` en lugar del objeto `ex` completo, por lo que omite revisar `ex.muscles` (el primer nivel de la heurística) aunque en el catálogo por defecto el filtro funciona gracias a `primary_muscle` y al nombre. Pasar `ex` directamente aprovecharía los tres niveles por completo.

---

## 9. Resumen para repasar

- **`CatalogSection`** ofrece búsqueda en tiempo real, chips de 6 grupos musculares + favoritos, fotos heredadas de máquina (`resolveExerciseImageUrl`) y controles CRUD exclusivos para `isStaff`.
- **`muscleValidation.ts`** implementa una heurística de 3 niveles (`muscles` → `primary_muscle` → palabras clave en `name`) usada en Catálogo y en Rutinas.
- **`ExerciseDetailModal`** consulta el detalle completo del ejercicio (`GET /catalog/exercises/{id}/`), resuelve la máquina requerida con su `setup_guide` y abre videos externos con `Linking.openURL`.
- **`AddExerciseModal`** permite al staff registrar ejercicios vinculando grupo muscular obligatorio, máquina opcional y fotografía comprimida.
