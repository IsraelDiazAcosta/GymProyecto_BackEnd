# 09. Pestaña Rutinas y Sesión Activa (Módulo `routines/`)

---

## 1. Propósito

La pestaña **Rutinas** (`activeTab === "routines"`) y los componentes de **Sesión Activa** permiten al atleta planificar sus entrenamientos, validar la coherencia muscular de sus planes, ajustar series y repeticiones, ejecutar sesiones cronometradas en vivo y llevar control de su asistencia semanal. Este módulo abarca **11 archivos** dentro de `src/components/dashboard/routines/` y constituye el núcleo operativo diario del usuario dentro de **Apex Gym Hub**.

---

## 2. Ubicación

Todas las rutas parten de `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

| Archivo en `src/components/dashboard/routines/` | Rol |
| :--- | :--- |
| `RoutinesSection.tsx` | Contenedor de la pestaña Rutinas; alterna sub-pestañas (`Mis Rutinas` / `Crear`) y vista de detalle. |
| `MyRoutinesSubTab.tsx` | Sub-pestaña **Mis Rutinas**: muestra la gráfica de evolución `RMTrackingChart` y la lista compacta de rutinas (o estado vacío). |
| `CreateRoutineCard.tsx` | Sub-pestaña **Crear**: tarjeta para definir enfoque muscular, nombre de rutina y selección múltiple de ejercicios. |
| `RoutineCard.tsx` | Tarjeta de rutina (modo compacto o expandido); incluye alerta de compatibilidad muscular, edición inline de series/reps y botón de eliminar. |
| `RoutineDetailView.tsx` | Vista de detalle al seleccionar una rutina: botón volver, `RoutineCard` expandida y bloque de las últimas sesiones completadas de esa rutina. |
| `RoutineAddExerciseForm.tsx` | Subformulario embebido dentro de `RoutineCard` para anexar uno o varios ejercicios con series, mín. y máx. repeticiones. |
| `SelectExerciseModal.tsx` | Modal de selección simple o múltiple de ejercicios del catálogo, con buscador y filtro toggle por enfoque muscular. |
| `SelectRoutineToStartModal.tsx` | Modal que se abre al pulsar iniciar entrenamiento para elegir qué rutina se va a ejecutar en vivo. |
| `ActiveSessionBar.tsx` | Barra adhesiva (*sticky*) en la parte superior de la pestaña **Progreso** con cronómetro en vivo `HH:MM:SS`, botones Cancelar/Finalizar y banner resumen al terminar. |
| `FinishSessionConfirmModal.tsx` | Modal de confirmación para cerrar una sesión activa; incluye la **alerta amarilla de ejercicios sin marcas** (`missingExercises`). |
| `WeeklyAttendanceCard.tsx` | Tarjeta de asistencia semanal Lun–Dom (`0`/`1` por día) con indicador de día actual (`HOY`) y contador `X/7`. |

> **Nota sobre duplicidad legacy:** En la raíz `src/components/dashboard/` únicamente permanecen 3 *barrel re-exports* de una sola línea (`CreateRoutineCard.tsx`, `RoutineCard.tsx`, `SelectExerciseModal.tsx`). Los otros 8 archivos fueron creados directamente dentro de `routines/`.

---

## 3. Cómo se conecta

```text
GymDashboard.tsx
  ├── Tab "routines" ──► RoutinesSection
  │       ├── subTab === "crear" ──► CreateRoutineCard
  │       │                             └──► SelectExerciseModal (desde GymDashboard: vm.showNewRoutineModal)
  │       ├── subTab === "mis_rutinas" (sin selectedRoutineId) ──► MyRoutinesSubTab
  │       │                                                          ├── RMTrackingChart (de ../tracking/)
  │       │                                                          └── RoutineCard (compact={true})
  │       └── subTab === "mis_rutinas" (con selectedRoutineId) ──► RoutineDetailView
  │                                                                   ├── RoutineCard (compact={false})
  │                                                                   │     ├── RoutineAddExerciseForm
  │                                                                   │     └── SelectExerciseModal (local)
  │                                                                   └── Historial corto de la rutina
  │
  ├── Tab "tracking" (cabecera fija) ──► ActiveSessionBar
  │       ├── Idle ("Iniciar Rutina") ──► SelectRoutineToStartModal ──► POST /tracking/sessions/start/
  │       ├── En vivo (cronómetro 1s) ──► Cancelar ──► POST /tracking/sessions/cancel/
  │       └── Finalizar ──► GET /tracking/sessions/{id}/ ──► FinishSessionConfirmModal ──► POST /tracking/sessions/finish/
  │
  └── Tab "profile" ──► ProfileSection ──► WeeklyAttendanceCard (usa trainedDayFlags de GymDashboard)
```

- **Nota importante de ubicación en pantalla:**
  - `ActiveSessionBar` **no** se renderiza dentro de la pestaña `routines`, sino fija en la parte superior de la pestaña `tracking` (**Progreso**), donde el usuario registra sus series mientras corre el reloj.
  - `WeeklyAttendanceCard` vive en la carpeta `routines/`, pero actualmente se renderiza dentro de `ProfileSection` (pestaña **Perfil**), además de reflejar `trainedCount/7` en `DashboardHeader`. De hecho, `RoutinesSectionProps` aún declara `trainedDayFlags`, `todayWeekIndex` y `trainedCount` y `GymDashboard` se los pasa, pero `RoutinesSection` ya no los desestructura ni dibuja (props heredadas sin uso).

---

## 4. Componentes, funciones y variables clave

### Navegación, creación y detalle de rutinas

| Archivo / Símbolo | Rol y variables clave |
| :--- | :--- |
| `RoutinesSection` | Recibe `routinesSubTab` (`"mis_rutinas" \| "crear"`), `selectedRoutineId`, y pasa a `CreateRoutineCard` solo los `selectedExercises` compatibles con `newRoutineFocus`. |
| `MyRoutinesSubTab` | Muestra estado vacío con botón a `"crear"`, o bien `<RMTrackingChart />` seguido de `<RoutineCard compact={true} />` por cada rutina. |
| `CreateRoutineCard` | `FOCUS_OPTIONS` (`pecho`, `espalda`, `pierna`, `hombro`, `brazo`, `core`, `fullbody`), chips horizontales, `TextInput` para título, chips removibles de ejercicios seleccionados y botón `onCreate`. |
| `RoutineCard` | Estados locales: `selectModalVisible`, `editingRoutineExId`, `editSets`, `editMinReps`, `editMaxReps`, `savingInline`. Calcula `incompatibleExercises` con `isExerciseCompatibleWithFocus`. |
| `RoutineDetailView` | Recibe `routine`, `routineExercises`, `routineSessions` (máximo 5 últimas de esa rutina calculadas en `GymDashboard`) y define `formatDurationHMS`. |
| `RoutineAddExerciseForm` | Recibe `effectiveSelectedIds`, `selectedExercisesDetails`, `setsCount`, `minReps`, `maxReps`, `onOpenModal`, `onRemoveSelectedId`, `onConfirmAdd`, `onCancel`. |
| `SelectExerciseModal` | `isMulti`, `filterByFocus` (inicia en `Boolean(routineFocus)`), `searchQuery`, `tempSelectedIds`, `ExerciseThumbnail` con manejo de `hasError`. |

### Sesión activa, finalización y asistencia semanal

| Archivo / Símbolo | Rol y variables clave |
| :--- | :--- |
| `SelectRoutineToStartModal` | Lista rutinas con su enfoque y cantidad de ejercicios (`getCount`), o muestra botón `onGoToCreate` si no hay rutinas. |
| `ActiveSessionBar` | Props: `activeSession`, `elapsedSeconds`, `sessionActionLoading`, `finishedSummaryDuration`, `onStartPress`, `onCancelSession`, `onFinishPress`, `onDismissFinishedSummary`. |
| `FinishSessionConfirmModal` | Props: `activeSession`, `elapsedSeconds`, `sessionActionLoading`, `missingExercises = []`, `onCancel`, `onConfirm`. Variable clave `hasMissing = missingExercises.length > 0`. |
| `WeeklyAttendanceCard` | Props: `trainedDayFlags` (arreglo de 7 ceros/unos), `todayWeekIndex` (`0` = Lunes … `6` = Domingo), `trainedCount`. Usa `WEEK_DAYS_BY_LANG[language]`. |
| En `GymDashboard.tsx` | `computeElapsedSeconds`, `restoreActiveSession`, `timerRef` (`setInterval` cada 1000 ms respetando `AppState`), `hasRecordedMarcaInSession`, `computeMissingExercisesForSession`, `handleAttemptFinishSession`, `handleConfirmFinishSession`, `loadWeeklyAndHistory`. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### A. Filtro automático de ejercicios al cambiar el enfoque muscular (`RoutinesSection.tsx`)

```tsx
selectedExercises={exercises.filter(
  (ex) =>
    newRoutineExerciseIds.includes(ex.id) &&
    isExerciseCompatibleWithFocus(ex, newRoutineFocus),
)}
```

- **Coherencia en vivo:** Si el usuario seleccionó "Press Banca" con enfoque `fullbody` y luego cambia el chip a `pierna`, `CreateRoutineCard` deja de mostrar "Press Banca" inmediatamente, y `useGymDashboardData.handleCreateRoutine` aplica el mismo filtro antes de enviar `validExerciseIds` a `api.createRoutine`.

### B. Edición inline de series y repeticiones en `RoutineCard.tsx`

```tsx
const startInlineEdit = (ex: RoutineExerciseItem) => {
  if (!ex.routineExerciseId) return;
  setEditingRoutineExId(ex.routineExerciseId);
  setEditSets(String(ex.setsCount ?? 4));
  setEditMinReps(String(ex.minReps ?? 8));
  setEditMaxReps(String(ex.maxReps ?? 12));
};

const handleSaveInlineEdit = async () => {
  if (!editingRoutineExId || !onUpdateRoutineExercise) return;
  const sc = parseInt(editSets, 10);
  const minR = parseInt(editMinReps, 10);
  const maxR = parseInt(editMaxReps, 10);
  if (!sc || sc < 1 || !minR || minR < 1 || !maxR || maxR < 1) return;
  setSavingInline(true);
  try {
    await onUpdateRoutineExercise(
      editingRoutineExId,
      sc,
      minR,
      Math.max(minR, maxR),
    );
    setEditingRoutineExId(null);
  } finally {
    setSavingInline(false);
  }
};
```

- **Validación automática de rango:** Antes de invocar `PATCH /routines/exercises/{id}/`, verifica que todos los valores sean enteros positivos (`>= 1`) y garantiza con `Math.max(minR, maxR)` que las repeticiones máximas nunca sean menores que las mínimas.

### C. Cronómetro sincronizado con el servidor y `AppState` (`GymDashboard.tsx` y `ActiveSessionBar.tsx`)

```tsx
const computeElapsedSeconds = (session: WorkoutSessionItem | null) => {
  if (!session) return 0;
  const raw = session.started_at || session.start_time;
  const startMs = new Date(raw).getTime();
  if (isNaN(startMs)) return 0;
  return Math.max(0, Math.floor((Date.now() - startMs) / 1000));
};
```

- **¿Por qué no sumar `+1` en un contador local?** Porque si el teléfono se bloquea o el sistema pausa JavaScript en segundo plano, un contador `+1` se atrasaría. Al calcular siempre `(Date.now() - startMs) / 1000` a partir de `started_at` del servidor, el cronómetro muestra el tiempo real exacto incluso al restaurar la app (`api.getActiveRoutineSession()`) o volver de segundo plano (`AppState.addEventListener("change", ...)`).
- En `ActiveSessionBar.tsx`, `timerText` aplica `fontVariant: ["tabular-nums"]` para que los dígitos tengan ancho fijo y el reloj no vibre visualmente cada segundo.

### D. Detección de ejercicios sin marcas y alerta amarilla (`GymDashboard.tsx` + `FinishSessionConfirmModal.tsx`)

En `GymDashboard.tsx`:

```tsx
const detail = await api.getWorkoutSessionDetail(activeSession.id);
const detailLoggedIds = extractLoggedExerciseIds(detail);
setSessionLoggedExerciseIds(detailLoggedIds);

const hasAnySet = Boolean(
  detail.has_logged_sets || detailLoggedIds.length > 0,
);
if (!hasAnySet) {
  vm.showToast(
    "warning",
    t("toasts.marcaRequiredTitle"),
    t("toasts.marcaRequiredMsg"),
  );
  return;
}

const missing = computeMissingExercisesForSession(
  new Set(detailLoggedIds),
  detail || activeSession,
  detail.exercises,
);
setMissingFinishExercises(missing);
setShowFinishConfirm(true);
```

En `FinishSessionConfirmModal.tsx`:

```tsx
const hasMissing = missingExercises.length > 0;
// ...
<View style={[styles.confirmIconHalo, {
  backgroundColor: hasMissing ? colors.warningGlow : colors.primaryGlow,
  borderColor: hasMissing ? colors.warning : colors.border,
}]}>
  <GymIcon
    name={hasMissing ? "alert-triangle" : "check-circle"}
    size={28}
    color={hasMissing ? colors.warning : colors.primary}
  />
</View>
```

- **Dos reglas de negocio claras:**
  1. **Bloqueo total si no hay ninguna marca:** si `hasAnySet` es falso, ni siquiera se abre el modal de finalizar; se muestra un toast de advertencia exigiendo registrar al menos una marca.
  2. **Alerta amarilla parcial (`missingExercises`):** si ya se registró al menos una serie pero quedaron otros ejercicios de la rutina sin marcas, el halo del modal cambia a amarillo (`colors.warning` / `colors.warningGlow`), muestra el icono `alert-triangle` y despliega un `ScrollView` (`maxHeight: 120`) con la lista de los ejercicios faltantes (`missingExercises.map(...)`), dando la opción al usuario de pulsar **"Seguir"** (`onCancel`) o confirmar **"Finalizar"** de todas formas (`onConfirm`).

### E. Cálculo de asistencia semanal Lun–Dom (`GymDashboard.tsx` + `WeeklyAttendanceCard.tsx`)

En `GymDashboard.tsx`, `loadWeeklyAndHistory` calcula el lunes `00:00:00` y domingo `23:59:59.999` de la semana local actual usando `(now.getDay() + 6) % 7` (porque en JavaScript `getDay()` devuelve `0` para domingo, y con `+ 6 % 7` el lunes pasa a ser índice `0`). Luego consulta `api.getRoutineSessionHistory({ desde, hasta })`, arma un `Set` de fechas `YYYY-MM-DD` locales y genera `trainedDayFlags` de longitud 7 con `1` o `0`. `WeeklyAttendanceCard` pinta 7 barras verticales (altura `"100%"` si `val === 1`, `"0%"` si es `0`), resalta con borde primario y píldora `"HOY"` la columna de `todayWeekIndex`, y muestra la insignia `{trainedCount}/7`.

### F. Notas de revisión técnica (código muerto / riesgos detectados)

- En `RoutinesSection.tsx` (líneas 36-38) se declaran `trainedDayFlags`, `todayWeekIndex` y `trainedCount` en `RoutinesSectionProps`, pero el componente no los usa (la tarjeta semanal se renderiza en `ProfileSection`).
- En `SelectExerciseModal.tsx` (líneas 40 y 106) existe la prop `allRoutines?: any[]` sin uso en el cuerpo del componente.
- En `GymDashboard.tsx` (línea 133) el estado `lastFinishedRoutineId` se declara pero `setLastFinishedRoutineId` nunca se invoca.
- **Riesgo de flujo en long-press de `RoutineCard`:** `RoutineCard` pasa `onLongPress` hacia `vm.handleOpenRoutineOptions`, que abre `ItemActionSheet` con `itemType="routine"`. Como se detalla en el documento 11, `ItemActionSheet.tsx` oculta las opciones de editar y eliminar cuando `itemType === "routine"`.

---

## 6. Flujo paso a paso

1. **Crear rutina:** El usuario va a la sub-pestaña **Crear** (`CreateRoutineCard`), elige enfoque muscular (ej. `pecho`), escribe título, abre `SelectExerciseModal`, selecciona múltiples ejercicios compatibles y pulsa crear (`POST /routines/routines/`). Al recibir toast con `code: "routine_created"`, `GymDashboard` limpia el formulario y regresa automáticamente a `mis_rutinas`.
2. **Editar rutina y añadir ejercicios:** En `MyRoutinesSubTab` toca una `RoutineCard` compacta → entra a `RoutineDetailView`. Puede editar series/reps inline (`PATCH /routines/exercises/{id}/`), tocar `"Agregar ejercicio"` (`RoutineAddExerciseForm` + `SelectExerciseModal` → `POST /routines/routines/{id}/add-exercise/`) o borrar la rutina con la papelera (`ConfirmDeleteModal`).
3. **Iniciar sesión en vivo:** En la pestaña **Progreso**, toca **Iniciar Rutina** en `ActiveSessionBar` → se abre `SelectRoutineToStartModal` → elige una rutina → `POST /tracking/sessions/start/` devuelve `activeSession` con `started_at`, arranca `timerRef` cada segundo y cambia `trackingRoutineId` automáticamente a esa rutina.
4. **Finalizar sesión:** El usuario pulsa **Finalizar** en `ActiveSessionBar` → `GymDashboard` consulta `GET /tracking/sessions/{id}/` → si tiene 0 marcas, bloquea con toast; si tiene ≥ 1 marca, calcula `missingExercises` y abre `FinishSessionConfirmModal` → al confirmar (`POST /tracking/sessions/finish/`), detiene el timer, muestra `finishedSummaryDuration` en el banner de `ActiveSessionBar` y actualiza `trainedDayFlags`.

---

## 7. Conceptos y términos técnicos

- **Sub-pestaña controlada (*Controlled Sub-tab*):** Navegación interna (`"mis_rutinas" | "crear"`) cuyo estado vive en el componente padre (`GymDashboard`) para poder redirigir automáticamente desde otros modales (ej. tras crear una rutina o desde `SelectRoutineToStartModal` cuando no hay rutinas).
- **Edición inline (*Inline Editing*):** Patrón UX donde los controles de edición (inputs numéricos de series y repeticiones) aparecen dentro de la misma fila del listado sin abrir un modal adicional.
- **Cálculo de tiempo por diferencia de timestamp (`Date.now() - startMs`):** Técnica robusta para cronómetros que evita desfasajes cuando la app pasa a segundo plano o se recarga la pantalla.
- **`fontVariant: ["tabular-nums"]`:** Propiedad tipográfica que obliga a que todos los dígitos tengan el mismo ancho horizontal para evitar saltos en contadores que cambian cada segundo.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué el cronómetro de `ActiveSessionBar` no pierde la cuenta si el usuario cierra la app o la manda a segundo plano?**
   - *Respuesta modelo:* Porque el inicio real (`started_at`) está persistido en el backend. Al abrir el dashboard se ejecuta `restoreActiveSession()` (`GET /tracking/sessions/active/`), y el `setInterval` de 1 segundo no incrementa un contador local sino que recalcula `Math.floor((Date.now() - startMs) / 1000)` respecto a `started_at`. Además, un listener de `AppState` detiene el intervalo en segundo plano y lo recalcula al volver a `"active"`.
2. **¿Cómo funciona la validación al intentar finalizar una sesión activa?**
   - *Respuesta modelo:* `handleAttemptFinishSession` consulta `GET /tracking/sessions/{id}/`. Si no hay ninguna serie registrada (`!detail.has_logged_sets && detailLoggedIds.length === 0`), impide finalizar y muestra un toast de advertencia. Si hay al menos una serie pero faltan otros ejercicios de la rutina, `computeMissingExercisesForSession` genera el arreglo `missingExercises` y `FinishSessionConfirmModal` muestra la alerta amarilla listando los ejercicios sin marcas antes de confirmar.
3. **¿Cómo evita la aplicación que un usuario agregue un ejercicio de pierna a una rutina con enfoque de pecho?**
   - *Respuesta modelo:* En tres puntos: `SelectExerciseModal` activa por defecto el chip `"Solo <ENFOQUE>"` usando `isExerciseCompatibleWithFocus`; en `CreateRoutineCard` se filtran automáticamente los ejercicios seleccionados cuando cambia `newRoutineFocus`; y en `useGymDashboardData.handleAddExerciseToRoutine` se vuelve a validar antes de llamar a la API, mostrando un toast de error si hay incompatibilidad (excepto si el enfoque es `fullbody`).
4. **¿Cómo transforma la app el índice de día de JavaScript para mostrar la semana de Lunes a Domingo en `WeeklyAttendanceCard`?**
   - *Respuesta modelo:* En JavaScript `Date.getDay()` devuelve `0` para Domingo y `1..6` para Lunes..Sábado. En `GymDashboard` se aplica la fórmula `(now.getDay() + 6) % 7`, que convierte Lunes en `0`, Martes en `1`, ..., y Domingo en `6`, alineándose exactamente con `WEEK_DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]`.
5. **¿Qué diferencia hay entre `RoutineCard` en `MyRoutinesSubTab` y en `RoutineDetailView`?**
   - *Respuesta modelo:* En `MyRoutinesSubTab`, `RoutineCard` recibe `compact={true}`, por lo que muestra únicamente la cabecera (título, enfoque, cantidad de ejercicios y papelera) y al tocarla navega al detalle. En `RoutineDetailView`, `compact` toma el valor por defecto `false`, desplegando la lista de ejercicios, edición inline de series/reps, banner de compatibilidad y formulario para agregar más ejercicios.
6. **¿Por qué `SelectExerciseModal` utiliza `FlatList` en lugar de un `ScrollView` con `.map()`?**
   - *Respuesta modelo:* Porque el catálogo de ejercicios puede crecer mucho; `FlatList` virtualiza las filas y solo renderiza las visibles en pantalla, optimizando memoria y fluidez al buscar y seleccionar múltiples ejercicios.

---

## 9. Resumen para repasar

- **`RoutinesSection`** gestiona dos sub-pestañas (`crear` y `mis_rutinas`) más la vista profunda `RoutineDetailView` con historial corto de sesiones.
- **`SelectExerciseModal`** y **`CreateRoutineCard`** se apoyan en `muscleValidation.ts` para filtrar ejercicios por enfoque muscular y permitir selección múltiple.
- **`ActiveSessionBar`** (en la pestaña Progreso) y **`FinishSessionConfirmModal`** implementan un cronómetro basado en timestamp del servidor, bloqueo si hay 0 marcas y alerta amarilla cuando faltan ejercicios por registrar (`missingExercises`).
- **`WeeklyAttendanceCard`** grafica con barras binarias (`0`/`1`) los días entrenados de lunes a domingo de la semana local actual.
