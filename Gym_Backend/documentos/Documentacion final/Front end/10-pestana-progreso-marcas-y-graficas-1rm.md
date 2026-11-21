# 10. Pestaña Progreso, Marcas y Gráficas 1RM (Módulo `tracking/`)

---

## 1. Propósito

La pestaña **Progreso** (`activeTab === "tracking"`) y el módulo `tracking/` permiten al atleta registrar sus levantamientos reales durante una sesión activa, calcular y visualizar su **1RM estimado (Repetición Máxima)** mediante la fórmula de Brzycki en una gráfica vectorial SVG, consultar y editar su historial de marcas, y auditar el historial paginado de rutinas completadas (con métricas de tiempo, filtros por periodo/rutina, desglose serie por serie y eliminación segura).

---

## 2. Ubicación

Todas las rutas parten de `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

| Archivo en `src/components/dashboard/tracking/` | Rol |
| :--- | :--- |
| `MarcaFormCard.tsx` | Formulario de registro de levantamientos (Paso 1: Rutina, Paso 2: Ejercicio, Paso 3: Peso, Reps y RPE). |
| `RMTrackingChart.tsx` | Gráfica vectorial SVG interactiva de evolución del 1RM estimado con degradado, récord personal (`PR`) y porcentaje de mejora. |
| `MarcaHistoryList.tsx` | Contiene **dos** componentes exportados: `MarcaHistoryList` (historial de marcas de fuerza con editar/eliminar) y `RoutineSessionHistorySection` (historial completo y paginado de sesiones de entrenamiento). |
| `RoutineSessionHistorySection.tsx` | Archivo re-exportador de 4 líneas que expone `RoutineSessionHistorySection` y `RoutineSessionHistorySectionProps` desde `./MarcaHistoryList`. |
| `src/components/dashboard/MarcaFormCard.tsx` | **Shim heredado (1 línea):** `export * from "./tracking/MarcaFormCard";`. |
| `src/components/dashboard/RMTrackingChart.tsx` | **Shim heredado (1 línea):** `export * from "./tracking/RMTrackingChart";`. |
| `src/components/dashboard/MarcaHistoryList.tsx` | **Shim heredado (1 línea):** `export * from "./tracking/MarcaHistoryList";`. |

---

## 3. Cómo se conecta

```text
GymDashboard.tsx (activeTab === "tracking")
  │
  ├── ActiveSessionBar (siempre visible arriba en "tracking")
  │
  ├── ¿canRegisterMarca? (`activeSession !== null`)
  │     ├── false ──► Card de bloqueo con candado ("Inicia una sesión activa")
  │     └── true  ──► MarcaFormCard
  │                     └── onSave ──► `vm.handleSaveMarca()` ──► `api.saveMarca()`
  │                                     ├── actualiza `sessionMarcasCount` y `sessionLoggedExerciseIds`
  │                                     └── recarga `vm.loadProgressionHistory(exerciseId)`
  │
  ├── MarcaHistoryList
  │     ├── Selector de ejercicio de la rutina (`currentRoutineExercises`)
  │     └── Long-press / `⋮` ──► `vm.handleOpenMarcaOptions(item)`
  │                                 └──► `ItemActionSheet` ──► `EditMarcaForm` / `ConfirmDeleteModal`
  │
  └── RoutineSessionHistorySection
        ├── Carga paralela: `api.getCompletedSessionsPaginated` + `api.getRoutineSessionsSummary`
        ├── Tap en sesión ──► `api.getWorkoutSessionDetail(id)` ──► Modal detalle de sesión
        └── Papelera ──► `ConfirmDeleteModal (itemType="session")` ──► `api.deleteWorkoutSession(id)`
                                                                       └──► `onSessionDeleted()` (refresca asistencia semanal e historial)

Nota: `RMTrackingChart` está conectado en `MyRoutinesSubTab.tsx` (sub-pestaña "Mis Rutinas") compartiendo los mismos estados `trackingRoutineId`, `trackingExerciseId` y `marcaHistory` de `useGymDashboardData`.
```

---

## 4. Componentes, funciones y variables clave

### `MarcaFormCard.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `MarcaFormCardProps` | Interfaz | `colors`, `routines`, `trackingRoutineId`, `trackingExerciseId`, `currentRoutineExercises`, `onSelectRoutine`, `onSelectExercise`, `marcaWeight`, `marcaReps`, `marcaRpe`, `savingMarca`, `onSave`, `lastSavedSummary`. |
| Deduplicación de chips | Expresión `Map` | `Array.from(new Map(currentRoutineExercises.map((e) => [e.id, e])).values())` evita llaves duplicadas si una rutina repite un ejercicio. |

### `RMTrackingChart.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `chartSize` | Estado (`LayoutRectangle \| null`) | Dimensiones reales del lienzo medidas por `onLayout` para calcular coordenadas SVG responsivas. |
| `validHistory` | Filtrado | Descarta registros sin peso o repeticiones positivas (`weight > 0 && reps > 0`). |
| `rmList` | Mapeo Brzycki | Calcula `oneRm = reps > 0 && reps < 37 ? weight * (36 / (37 - reps)) : weight` redondeado a 1 decimal. |
| `bestRM`, `firstRM`, `lastRM`, `deltaPct` | Estadísticas | Máximo histórico (insignia `PR`), primer y último registro, y variación porcentual `((last - first) / first) * 100`. |
| `pointCoords`, `linePoints`, `areaPoints` | Coordenadas SVG | Puntos `(x, y)` normalizados entre `minVal` y `maxVal` con padding horizontal/vertical de `24px`. |

### `MarcaHistoryList` y `RoutineSessionHistorySection` (en `MarcaHistoryList.tsx`)

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `MarcaHistoryList` | Componente | Lista scrollable (`maxHeight: 225`) de marcas del ejercicio seleccionado con píldora `1RM`, fecha, RPE y menú contextual (`onMarcaOptionsPress`). |
| `viewMode` | Estado (`"sessions" \| "by_routine"`) | Alterna entre vista cronológica de sesiones y vista agrupada por rutina. |
| `periodFilter` | Estado (`"week" \| "month" \| "all"`) | Filtra por semana actual, mes actual o todo el historial mediante `getLocalPeriodBounds`. |
| `selectedRoutineId` | Estado (`string`) | `"all"` o el UUID de una rutina específica. |
| `summaryTotals` | Estado | Totales superiores: `total_sessions`, `total_duration_seconds`, `average_duration_seconds`. |
| `page`, `hasNextPage`, `totalCount`, `loadingMore` | Estados de paginación | Controlan el botón **"Cargar más"** (`handleLoadMore`). |
| `requestSeqRef` | `useRef(0)` | Contador incremental anti-*race condition* para descartar respuestas HTTP obsoletas cuando el usuario cambia filtros rápido. |
| `detailModalVisible`, `detailSession`, `detailLoading`, `hasDetailError` | Estados del modal de detalle | Controlan la ficha de ejercicios y series de una sesión pasada. |
| `sessionToDelete` | Estado (`{ id, title } \| null`) | Dispara `<ConfirmDeleteModal itemType="session" />`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### A. Bloqueo de registro hasta iniciar sesión activa (`GymDashboard.tsx`)

```tsx
const canRegisterMarca = Boolean(activeSession !== null);
// ...
{!canRegisterMarca ? (
  <View style={[localStyles.lockStateCard, ...]}>
    <View style={[localStyles.lockIconBadge, ...]}>
      <GymIcon name="lock" size={26} color={colors.primary} />
    </View>
    <Text style={[localStyles.lockTitle, { color: colors.text }]}>
      {t("tracking.lockTitle")}
    </Text>
    <Text style={[localStyles.lockMessage, { color: colors.textSecondary }]}>
      {t("tracking.lockMessage")}
    </Text>
  </View>
) : (
  <MarcaFormCard ... />
)}
```

- **Regla de negocio:** El usuario solo puede registrar levantamientos (`MarcaFormCard`) cuando existe una sesión en vivo (`activeSession !== null`). Si no la ha iniciado, ve la tarjeta con candado indicando que primero debe pulsar **Iniciar Rutina** en `ActiveSessionBar`. Sin embargo, la consulta histórica (`MarcaHistoryList` y `RoutineSessionHistorySection`) permanece siempre visible debajo.
- Al guardar con éxito (`ok === true`), `GymDashboard` incrementa `sessionMarcasCount` y agrega `savedExerciseId` a `sessionLoggedExerciseIds` para que `FinishSessionConfirmModal` sepa qué ejercicios ya fueron trabajados en la sesión actual.

### B. Fórmula de Brzycki y normalización vectorial SVG en `RMTrackingChart.tsx`

```tsx
const oneRm =
  reps > 0 && reps < 37 ? weight * (36 / (37 - reps)) : weight;
```

- **Protección matemática:** La fórmula clásica de Brzycki es $\text{1RM} = \text{peso} \times \frac{36}{37 - \text{reps}}$. Cuando $\text{reps} \ge 37$, el denominador se vuelve cero o negativo; el condicional `reps < 37` previene divisiones por cero o resultados negativos absurdos devolviendo `weight` directamente.

```tsx
pointCoords = rmList.map((item, index) => {
  const t = rmList.length === 1 ? 0.5 : index / (rmList.length - 1);
  const x = paddingHorizontal + t * usableWidth;
  const norm = (item.oneRm - minVal) / span;
  const y = paddingVertical + (1 - norm) * usableHeight;
  return { x, y, value: item.oneRm, dateLabel: item.dateLabel };
});
```

- **Proyección en pantalla:** `t` distribuye horizontalmente los puntos de izquierda a derecha (o los centra en `0.5` si solo hay un registro). Como en coordenadas SVG `y = 0` es el borde superior, se invierte con `(1 - norm)` para que el 1RM más alto quede arriba y el más bajo abajo. Si hay más de 1 punto, dibuja `<Polygon points={areaPoints} fill="url(#emeraldGrad)" />` (degradado vertical de opacidad `0.38` a `0.0`) y `<Polyline />`, además de `<SvgCircle>` y etiquetas `<Text>` flotantes encima de cada punto.

### C. Protección contra condiciones de carrera y filtros locales en `RoutineSessionHistorySection` (`MarcaHistoryList.tsx`)

```tsx
const getLocalPeriodBounds = (period: PeriodFilter) => {
  if (period === "all") return { desde: undefined, hasta: undefined };
  const now = new Date();
  if (period === "week") {
    const dayIdx = (now.getDay() + 6) % 7;
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayIdx, 0, 0, 0, 0);
    const sundayEnd = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6, 23, 59, 59, 999);
    return { desde: monday.toISOString(), hasta: sundayEnd.toISOString() };
  }
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999);
  return { desde: monthStart.toISOString(), hasta: monthEnd.toISOString() };
};
```

```tsx
const loadHistoryInitial = useCallback(async () => {
  const seq = ++requestSeqRef.current;
  setLoadingInitial(true);
  setHasLoadError(false);
  try {
    const [paginatedRes, routineSummaryRes] = await Promise.all([
      api.getCompletedSessionsPaginated({ page: 1, ...filterParams }),
      api.getRoutineSessionsSummary(filterParams),
    ]);
    if (seq !== requestSeqRef.current) return;
    // ...
```

- **¿Para qué sirve `requestSeqRef`?** Si el usuario cambia rápidamente de `"Semana"` a `"Mes"` y luego a `"Todo"`, tres peticiones HTTP compiten en red. Si la respuesta vieja llega al último, `seq !== requestSeqRef.current` la descarta limpiamente evitando que sobrescriba la vista actual.
- **Límites en zona horaria local:** `getLocalPeriodBounds` construye el inicio/fin de semana o mes en hora local del dispositivo y luego los serializa a ISO-8601 (`desde`, `hasta`), garantizando que una sesión nocturna no salte de día o mes por diferencia con UTC.

### D. Modal de detalle y borrado de sesión (`MarcaHistoryList.tsx`)

- `handleOpenSessionDetail(sessionItem)` abre inmediatamente el modal con los datos de cabecera ya conocidos y dispara `api.getWorkoutSessionDetail(sessionItem.id)`. Para cada ejercicio en `detailSession.exercises`:
  - Si `ex.unrecorded || ex.sets.length === 0`, muestra un banner informativo indicando `"Sin series registradas"` más la meta planeada (`ex.planned_sets` × `ex.planned_reps`).
  - Si tiene series, lista cada `s` con número de serie, `weight × reps`, `RPE` (si existe) y píldora `1RM`.
- **Eliminación:** El botón de papelera (tanto en la tarjeta de la lista con `e.stopPropagation()` como dentro del modal de detalle tras cerrarlo con `setTimeout(..., 180)`) llama `requestDeleteSession`, abre `ConfirmDeleteModal` (`itemType="session"`), y al confirmar ejecuta `api.deleteWorkoutSession(target.id)`, recarga el historial, invoca `onSessionDeleted()` (que recalcula asistencia semanal e historial 1RM) y emite un toast.

### E. Detalles técnicos relevantes detectados en `api.ts` y `MarcaHistoryList.tsx`

- **Nota sobre `api.saveMarca` (`src/services/api.ts` líneas 805-834):** Al guardar una marca desde `MarcaFormCard`, `api.saveMarca` invoca internamente `this.ensureSession()` (que busca en `/tracking/sessions/` una sesión con `!s.is_completed` o crea `"Entrenamiento Móvil"`), crea un registro en `/tracking/exercises/` con `order: 1` y luego crea la serie en `/tracking/sets/` con `set_number: 1`. Es un comportamiento acoplado a cómo el backend agrupa series dentro de la sesión activa.
- **Detalle visual menor:** En el filtro de rutinas de `RoutineSessionHistorySection` (línea 1014), muestra `{r.title}` sin respaldo `(r as any).name`, a diferencia de `MarcaFormCard` y `RMTrackingChart` que sí usan `r.title || (r as any).name || ...`.

---

## 6. Flujo paso a paso

1. **Bloqueo inicial:** Al entrar a **Progreso**, si `activeSession === null`, `ActiveSessionBar` muestra **"Iniciar Rutina"** y en lugar de `MarcaFormCard` se muestra el recuadro bloqueado con candado.
2. **Inicio y registro:** Al iniciar sesión en `ActiveSessionBar`, `canRegisterMarca` pasa a `true` y aparece `MarcaFormCard`. El usuario elige rutina → ejercicio → ingresa peso, repeticiones y RPE → pulsa **Guardar Marca**.
3. **Actualización en vivo:** `api.saveMarca` devuelve el `estimated_1rm`; se muestra el banner `lastSavedSummary`, un toast de éxito, se incrementa `sessionMarcasCount`, se añade el ejercicio a `sessionLoggedExerciseIds` y se recarga `marcaHistory`.
4. **Consulta y edición de marcas:** En `MarcaHistoryList`, el usuario puede cambiar de ejercicio con los chips horizontales, ver su lista de levantamientos con el 1RM calculado, y mantener presionado o tocar `⋮` para abrir `ItemActionSheet` → editar en `EditMarcaForm` (`PATCH /tracking/sets/{id}/`) o eliminar en `ConfirmDeleteModal` (`DELETE /tracking/sets/{id}/`).
5. **Auditoría de sesiones completadas:** En `RoutineSessionHistorySection`, alterna entre **"Sesiones"** y **"Por rutina"**, filtra por `Semana` / `Mes` / `Todo` o por rutina, carga páginas adicionales con **"Cargar más"**, abre el desglose serie por serie de cualquier sesión o la elimina de su historial.

---

## 7. Conceptos y términos técnicos

- **1RM estimado (Fórmula de Brzycki):** Ecuación biomecánica ($\text{peso} \times \frac{36}{37 - \text{reps}}$) que estima el peso máximo que una persona podría levantar una sola vez a partir de una serie submáxima.
- **RPE (*Rate of Perceived Exertion*):** Escala subjetiva del esfuerzo (habitualmente 1 al 10) que indica qué tan cerca del fallo muscular estuvo la serie.
- **Gráfica vectorial SVG (`react-native-svg`):** Gráfica dibujada con primitivos matemáticos (`Polygon`, `Polyline`, `Circle`, `LinearGradient`) que escala sin pixelarse a cualquier tamaño de pantalla.
- **Control de secuencia anti-*race condition* (`requestSeqRef`):** Patrón con contador incremental en `useRef` que asegura que únicamente la petición más reciente actualice el estado cuando múltiples filtros disparan llamadas asíncronas seguidas.
- **Paginación incremental deduplicada:** Técnica en `handleLoadMore` que combina resultados de `page + 1` filtrando por `Set` de IDs ya cargados para evitar tarjetas duplicadas si se agregaron o borraron sesiones entre páginas.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué `MarcaFormCard` está bloqueado hasta que el usuario inicia una sesión activa?**
   - *Respuesta modelo:* Para garantizar integridad en el seguimiento: cada marca de peso/repeticiones pertenece a una `WorkoutSession` real con hora de inicio y duración. Al exigir `activeSession !== null`, evitamos registros huérfanos y alimentamos correctamente tanto la asistencia semanal como la validación de ejercicios pendientes al finalizar la sesión.
2. **¿Cómo está construida la gráfica de evolución 1RM y por qué no usa una librería pesada de gráficas?**
   - *Respuesta modelo:* Se construyó directamente con `react-native-svg` (`Svg`, `Defs`, `LinearGradient`, `Polygon`, `Polyline` y `Circle`). Mide el ancho/alto disponible mediante el evento `onLayout` (`chartSize`), normaliza los valores entre el mínimo y el máximo de `rmList`, invierte el eje Y para que valores mayores queden arriba y proyecta tanto el área degradada como los nodos interactivos con su etiqueta en kilogramos. Esto evita dependencias externas pesadas e incompatibilidades entre Android, iOS y Web.
3. **¿Qué ocurre en la fórmula de Brzycki si alguien registra 37 o más repeticiones?**
   - *Respuesta modelo:* Tanto en `RMTrackingChart.tsx` como en `MarcaHistoryList.tsx` y `EditMarcaForm.tsx` existe la guarda `reps > 0 && reps < 37`. Si las repeticiones son 37 o más (donde `37 - reps` sería 0 o negativo), se omite la división y se toma directamente `weight` como 1RM estimado, evitando `Infinity` o valores negativos.
4. **¿Por qué `RMTrackingChart` aparece en `MyRoutinesSubTab` y no únicamente en la pestaña Progreso?**
   - *Respuesta modelo:* Para ofrecer contexto de fuerza justo antes de que el usuario elija qué rutina entrenar en **Mis Rutinas**, reutilizando exactamente los mismos estados (`trackingRoutineId`, `trackingExerciseId`, `marcaHistory`) administrados por `useGymDashboardData`.
5. **¿Cómo evita `RoutineSessionHistorySection` errores de desincronización si el usuario cambia rápido entre "Esta semana", "Este mes" y "Todas"?**
   - *Respuesta modelo:* Utiliza una referencia mutable `requestSeqRef`. Cada llamada a `loadHistoryInitial` incrementa el contador en `const seq = ++requestSeqRef.current`. Cuando `Promise.all` termina, verifica `if (seq !== requestSeqRef.current) return;`, descartando cualquier respuesta vieja que haya llegado después de una petición más nueva.
6. **¿Qué muestra el modal de detalle de una sesión completada si un ejercicio de la rutina no tuvo series registradas?**
   - *Respuesta modelo:* El backend devuelve `unrecorded: true` y el arreglo `sets` vacío junto con `planned_sets` y `planned_reps`. `RoutineSessionHistorySection` renderiza un banner informativo indicando `"Sin series registradas"` y mostrando entre paréntesis la meta que estaba planeada.
7. **¿Por qué se usa `setTimeout(..., 180)` al pasar del modal de detalle de sesión al modal de confirmación de borrado?**
   - *Respuesta modelo:* Para cerrar primero el `Modal` de detalle y dar 180 ms a la animación nativa de cierre (especialmente en iOS) antes de montar el `ConfirmDeleteModal`, evitando bloqueos de interfaz al abrir dos `Modal` nativos simultáneos.

---

## 9. Resumen para repasar

- **`canRegisterMarca`** bloquea `MarcaFormCard` hasta iniciar una sesión activa en `ActiveSessionBar` y alimenta el conteo de ejercicios registrados.
- **`RMTrackingChart`** calcula el 1RM con Brzycki (con guarda `< 37` reps) y renderiza área degradada, polilínea, nodos, récord personal (`PR`) y porcentaje de mejora en `react-native-svg`.
- **`MarcaHistoryList`** lista marcas con edición/eliminación vía `ItemActionSheet`, mientras **`RoutineSessionHistorySection`** ofrece resumen, vista por sesiones o por rutina, filtros de periodo en hora local, paginación, `requestSeqRef` anti-race-condition y modal de detalle/borrado de sesión.
