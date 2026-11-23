# 02 · Navegación y Orquestador del Dashboard (`GymDashboard`)

## 1. Propósito

Este documento detalla la arquitectura de la vista principal tras iniciar sesión: **el orquestador `GymDashboard`**, su barra de cabecera (`DashboardHeader`), su barra de navegación inferior (`DashboardTabBar`), la hoja de estilos compartidos (`dashboardStyles.ts`) y los tipos base del dashboard (`types.ts`). Se explican las 5 pestañas principales, el control de acceso basado en roles (`isAdmin` / `canManageItem`), el ciclo completo de una sesión de entrenamiento con cronómetro ligado a `AppState`, las estrategias de actualización manual y silenciosa, y la verificación de marcas registradas antes de finalizar una rutina.

---

## 2. Ubicación

Archivos analizados bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\GymDashboard.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\DashboardHeader.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\DashboardTabBar.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\dashboardStyles.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\types.ts`

---

## 3. Cómo se conecta

```text
HomeScreen (user !== null)
   │
   ▼
GymDashboard.tsx  ◀──► useGymDashboardData() (vm: estado global del dashboard y CRUD API)
   │
   ├── DashboardHeader          (saludo, conteos rápidos, rol Admin/Atleta, botón refresh)
   ├── ActiveSessionBar         (solo visible cuando vm.activeTab === "tracking")
   ├── ScrollView + RefreshControl
   │     ├── activeTab === "equipment" ──▶ EquipmentSection
   │     ├── activeTab === "catalog"   ──▶ CatalogSection
   │     ├── activeTab === "routines"  ──▶ RoutinesSection
   │     ├── activeTab === "tracking"  ──▶ MarcaFormCard (bloqueado si !activeSession)
   │     │                               + MarcaHistoryList + RoutineSessionHistorySection
   │     └── activeTab === "profile"   ──▶ ProfileSection
   ├── DashboardTabBar          (barra inferior fija: equipment | catalog | routines | tracking | profile)
   ├── 9 Modales de operación   (Detalle, Selección, Crear Ejercicio/Equipo, ActionSheet,
   │                             EditItem, ConfirmDelete, SelectRoutineToStart, FinishSessionConfirm)
   └── AnimatedToast            (notificaciones flotantes)
```

---

## 4. Componentes, funciones y variables clave

### 4.1. Tipos base (`types.ts`)
- **`TabType`**: unión literal `"routines" | "tracking" | "catalog" | "equipment" | "profile"`.
- **`DashboardColors`**: alias de `ThemeColors` para pasar colores tipados a cada subsección.
- **`RoutineExerciseItem`**: estructura normalizada para mostrar ejercicios dentro de una rutina (`id`, `name`, `routineExerciseId`, `equipmentName`, `setsCount`, `minReps`, `maxReps`).

### 4.2. Cabecera (`DashboardHeader.tsx`)
- **Props**: `username`, `isAdmin`, `routinesCount`, `exercisesCount`, `colors`, `trainedCount` (default `0`), `onRefresh`, `refreshing` (default `false`).
- Muestra 3 píldoras numéricas (rutinas, ejercicios y `trainedCount/7`), insignia de rol (`shield` + Admin o `user` + Atleta) y botón de actualización rápida (`refresh-cw` o `ActivityIndicator` si `refreshing` es `true`).

### 4.3. Barra de pestañas (`DashboardTabBar.tsx`)
- **Constante `TABS`**: define el orden visual de izquierda a derecha:
  1. `equipment` (`"tabs.equipment"`, icono `"cog"`)
  2. `catalog` (`"tabs.catalog"`, icono `"book-open"`)
  3. `routines` (`"tabs.routines"`, icono `"layers"`) — *pestaña inicial por defecto en `useGymDashboardData`*
  4. `tracking` (`"tabs.tracking"`, icono `"trending-up"`)
  5. `profile` (`"tabs.profile"`, icono `"user"`)
- Usa `useSafeAreaInsets()` para calcular `paddingBottom: Math.max(insets.bottom, 8)` en una barra con `position: "absolute", bottom: 0`.

### 4.4. Orquestador (`GymDashboard.tsx`)
- **Hooks consumidos**: `useAppTheme()`, `useLanguage()`, `useAuth()`, `useGymDashboardData()` (`vm`).
- **Estados locales principales**:
  - `routinesSubTab`: `"crear" | "mis_rutinas"` (inicia en `"mis_rutinas"`).
  - `selectedRoutineId`: ID de la rutina abierta en detalle.
  - `trainedDayFlags`: arreglo de 7 números (`[0..1]`, lunes a domingo) para asistencia semanal.
  - `activeSession`: `WorkoutSessionItem | null` de la sesión de entrenamiento activa.
  - `elapsedSeconds`: segundos transcurridos del cronómetro.
  - `showSelectRoutineToStart`, `showFinishConfirm`: visibilidad de modales de sesión.
  - `finishedSummaryDuration`: duración total (en segundos) para mostrar el banner de sesión completada.
  - `routineHistoryList`: sesiones completadas recibidas del backend.
  - `sessionActionLoading`: bloqueo durante llamadas de inicio/cierre/cancelación de sesión.
  - `sessionMarcasCount`, `sessionLoggedExerciseIds`, `missingFinishExercises`: control de marcas registradas en la sesión actual y ejercicios pendientes al finalizar.
  - `historyRefreshKey`: contador incremental para forzar recarga de `RoutineSessionHistorySection`.
- **Refs**:
  - `timerRef`: referencia al `setInterval` de 1 segundo del cronómetro.
  - `didMountTabRef`: evita disparar sincronización silenciosa duplicada en el primer montaje.
  - `silentSyncRef`: referencia mutable actualizada en cada render para evitar re-suscribir listeners de `AppState` / `window`.
- **Helpers puros y de control**:
  - `computeElapsedSeconds(session)`
  - `getSessionRoutineId(session)`
  - `extractLoggedExerciseIds(session)`
  - `computeMissingExercisesForSession(loggedIds, sessionRef, detailExercises)`
  - `isAdmin = Boolean(user?.is_staff)`
  - `canManageItem = (type?: string) => isAdmin || (type !== "exercise" && type !== "equipment")`
  - `canRegisterMarca = Boolean(activeSession !== null)`

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. Control de roles y acceso a acciones (`GymDashboard.tsx`)

```tsx
  const isAdmin = Boolean(user?.is_staff);
  const canManageItem = (type?: string) =>
    isAdmin || (type !== "exercise" && type !== "equipment");
  const canRegisterMarca = Boolean(activeSession !== null);
```

- **`isAdmin`**: deriva directamente de `user?.is_staff` proveniente del backend Django.
- **`canManageItem`**: función guardiana usada en `ItemActionSheet`, `EditItemModal` y `ConfirmDeleteModal`. Un atleta regular puede editar o borrar sus propias `"routine"` o `"marca"`, pero solo un administrador (`isAdmin === true`) puede gestionar `"exercise"` o `"equipment"`.
- Adicionalmente, a las secciones `<CatalogSection>` y `<EquipmentSection>` solo se les pasan las props `onOpenAddExercise`, `onExerciseOptionsPress`, `onOpenAddEquipment` y `onEquipmentOptionsPress` si `isAdmin` es verdadero; de lo contrario reciben `undefined`, ocultando los botones de administración en la UI.
- **`canRegisterMarca`**: en la pestaña `"tracking"`, si no hay `activeSession`, el formulario `<MarcaFormCard />` no se muestra; en su lugar se renderiza la tarjeta de bloqueo (`lockStateCard`) con el icono `"lock"` pidiendo iniciar una rutina primero.

### 5.2. Asistencia semanal y cálculo de fechas locales

```tsx
  const nowLocal = new Date();
  const todayWeekIndex = (nowLocal.getDay() + 6) % 7;
  const trainedCount = trainedDayFlags.reduce((acc, val) => acc + val, 0);

  const loadWeeklyAndHistory = useCallback(async () => {
    try {
      const now = new Date();
      const currentDayIdx = (now.getDay() + 6) % 7;
      const monday = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() - currentDayIdx,
        0, 0, 0, 0,
      );
      const sundayEnd = new Date(
        monday.getFullYear(),
        monday.getMonth(),
        monday.getDate() + 6,
        23, 59, 59, 999,
      );
      const toLocalKey = (d: Date) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

      const [weekSessions, allHistory] = await Promise.all([
        api.getRoutineSessionHistory({
          desde: monday.toISOString(),
          hasta: sundayEnd.toISOString(),
        }),
        api.getRoutineSessionHistory(),
      ]);
```

- **`(getDay() + 6) % 7`**: JavaScript devuelve `0` para domingo y `1` para lunes. Esta fórmula convierte el índice a lunes = `0`, martes = `1`, ..., domingo = `6`.
- **`Promise.all`**: consulta en paralelo las sesiones de la semana actual (filtradas entre lunes `00:00:00` y domingo `23:59:59.999` en hora local convertida a ISO UTC) y el historial completo de sesiones.
- Luego marca un `1` o `0` en `trainedDayFlags` para cada día de la semana usando `toLocalKey(dt)` para evitar desfases de zona horaria.

### 5.3. Ciclo de sesión activa y cronómetro resiliente con `AppState`

```tsx
const computeElapsedSeconds = (session: WorkoutSessionItem | null) => {
  if (!session) return 0;
  const raw = session.started_at || session.start_time;
  const startMs = new Date(raw).getTime();
  if (isNaN(startMs)) return 0;
  return Math.max(0, Math.floor((Date.now() - startMs) / 1000));
};
```

- **Por qué no usar un simple `prev + 1`**: si la app pasa a segundo plano o se suspende la pantalla, un contador `prev + 1` se retrasaría. Al calcular `(Date.now() - startMs) / 1000` en cada tick usando la marca de tiempo real de inicio enviada por el backend (`started_at || start_time`), el cronómetro **siempre muestra el tiempo exacto** al volver a la app.

```tsx
  useEffect(() => {
    let cancelled = false;
    const restoreActiveSession = async () => {
      try {
        const active = await api.getActiveRoutineSession();
        if (!cancelled && active && active.status === "active") {
          setActiveSession(active);
          setElapsedSeconds(computeElapsedSeconds(active));
          setSessionLoggedExerciseIds(extractLoggedExerciseIds(active));
        }
      } catch {}
    };
    restoreActiveSession();
    return () => { cancelled = true; };
  }, []);
```

- Al montar `GymDashboard`, consulta `GET /tracking/sessions/active/`. Si el usuario cerró la app con una sesión en curso, la restaura automáticamente con su tiempo transcurrido y sus ejercicios ya registrados.

```tsx
  useEffect(() => {
    const stopTimer = () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
    const startTimer = () => {
      stopTimer();
      if (!activeSession) return;
      setElapsedSeconds(computeElapsedSeconds(activeSession));
      timerRef.current = setInterval(() => {
        setElapsedSeconds(computeElapsedSeconds(activeSession));
      }, 1000);
    };

    if (!activeSession) {
      stopTimer();
      setElapsedSeconds(0);
      return;
    }

    if (AppState.currentState === "active") {
      startTimer();
    }

    const sub = AppState.addEventListener("change", (nextState) => {
      if (nextState === "active") {
        startTimer();
      } else {
        stopTimer();
      }
    });

    return () => {
      stopTimer();
      sub.remove();
    };
  }, [activeSession]);
```

- Cuando `AppState` cambia a `"background"` o `"inactive"`, `stopTimer()` detiene el intervalo para ahorrar batería y evitar trabajo innecesario. Al regresar a `"active"`, `startTimer()` recalcula inmediatamente los segundos transcurridos y reanuda el intervalo cada `1000 ms`.

### 5.4. Actualización manual, pull-to-refresh y sincronización silenciosa

```tsx
  const handleManualRefresh = async () => {
    await Promise.all([
      vm.refreshAllData({ silent: false, force: true }),
      loadWeeklyAndHistory(),
    ]);
    setHistoryRefreshKey((prev) => prev + 1);
  };

  silentSyncRef.current = () => {
    vm.refreshAllData({ silent: true });
    loadWeeklyAndHistory();
    setHistoryRefreshKey((prev) => prev + 1);
  };
```

- **Botón rápido en `DashboardHeader` y `RefreshControl` en `ScrollView`**: ambos invocan `handleManualRefresh`, pasando `{ silent: false, force: true }` (muestra spinner de refresco, ignora el *cooldown* de 4 s y muestra un *toast* de confirmación).
- **Sincronización silenciosa al cambiar de pestaña**:

```tsx
  useEffect(() => {
    if (!didMountTabRef.current) {
      didMountTabRef.current = true;
      return;
    }
    if (
      vm.activeTab === "catalog" ||
      vm.activeTab === "equipment" ||
      vm.activeTab === "routines" ||
      vm.activeTab === "tracking"
    ) {
      silentSyncRef.current();
    }
  }, [vm.activeTab]);
```

  `didMountTabRef` evita recargar innecesariamente justo al abrir la app (cuando `loadInitialData()` ya se está ejecutando). Al cambiar entre las pestañas operativas (`catalog`, `equipment`, `routines`, `tracking`), llama a `silentSyncRef.current()`, que refresca sin mostrar toast ni spinner intrusivo (sujeto al filtro de 4 segundos en `useGymDashboardData`).

- **Sincronización al enfocar app o ventana web**:

```tsx
  useEffect(() => {
    const appStateSub = AppState.addEventListener("change", (nextState) => {
      if (nextState === "active") {
        silentSyncRef.current();
      }
    });

    if (Platform.OS === "web" && typeof window !== "undefined") {
      const handleFocus = () => silentSyncRef.current();
      const handleVisibility = () => {
        if (
          typeof document !== "undefined" &&
          document.visibilityState === "visible"
        ) {
          silentSyncRef.current();
        }
      };
      window.addEventListener("focus", handleFocus);
      if (typeof document !== "undefined") {
        document.addEventListener("visibilitychange", handleVisibility);
      }
      ...
```

  En móviles reacciona a `AppState === "active"`; en navegador web escucha además `window.focus` y `document.visibilitychange` (`visible`), de modo que si el usuario o un administrador editó algo en otra pestaña o en Django Admin, la app se sincroniza sola al volver.

### 5.5. Verificación previa a finalizar sesión (`handleAttemptFinishSession`)

```tsx
  const handleAttemptFinishSession = async () => {
    if (!activeSession?.id) {
      if (!hasRecordedMarcaInSession) {
        vm.showToast(
          "warning",
          t("toasts.marcaRequiredTitle"),
          t("toasts.marcaRequiredMsg"),
        );
        return;
      }
      setMissingFinishExercises([]);
      setShowFinishConfirm(true);
      return;
    }

    try {
      setSessionActionLoading(true);
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

      if (detail.has_logged_sets) {
        setSessionMarcasCount((prev) => Math.max(prev, 1));
      }

      const missing = computeMissingExercisesForSession(
        new Set(detailLoggedIds),
        detail || activeSession,
        detail.exercises,
      );
      setMissingFinishExercises(missing);
      setShowFinishConfirm(true);
    } catch {
      if (!hasRecordedMarcaInSession) {
        vm.showToast(
          "warning",
          t("toasts.marcaRequiredTitle"),
          t("toasts.marcaRequiredMsg"),
        );
        return;
      }
      const missing = computeMissingExercisesForSession(
        new Set(sessionLoggedExerciseIds),
        activeSession,
      );
      setMissingFinishExercises(missing);
      setShowFinishConfirm(true);
    } finally {
      setSessionActionLoading(false);
    }
  };
```

- **Regla de negocio**: no se permite finalizar una sesión vacía sin marcas (series registradas).
- **Consulta autoritativa**: consulta `api.getWorkoutSessionDetail(activeSession.id)` en el servidor y extrae los ejercicios con series mediante `extractLoggedExerciseIds(detail)`.
- **Detección de ejercicios faltantes (`computeMissingExercisesForSession`)**:
  1. Obtiene el `routineId` mediante `getSessionRoutineId(sessionRef)` y busca la rutina planificada en `vm.routines` para comparar cada ejercicio planificado contra `loggedIds`.
  2. Si la rutina no tiene ejercicios locales o no se encuentra en `vm.routines`, usa el arreglo `detail.exercises` devuelto por el backend verificando `sets.length > 0` o `unrecorded === false`.
  3. Los nombres de los ejercicios sin marcas se guardan en `missingFinishExercises` para mostrarlos como advertencia dentro de `<FinishSessionConfirmModal />`.
- **Resiliencia ante error de red (`catch`)**: si falla `getWorkoutSessionDetail`, recurre al estado local `hasRecordedMarcaInSession` (que incluso revisa `vm.marcaHistory` con un margen de tolerancia de 60 segundos `sessionStart - 60000`) y `sessionLoggedExerciseIds`.

### 5.6. Navegación automática tras crear rutina (`useEffect` sobre `vm.toast`)

```tsx
  useEffect(() => {
    if (
      vm.toast.visible &&
      vm.toast.type === "success" &&
      vm.toast.code === "routine_created"
    ) {
      vm.setNewRoutineTitle("");
      vm.setNewRoutineExerciseIds([]);
      vm.setNewRoutineFocus("fullbody");
      setSelectedRoutineId(null);
      setRoutinesSubTab("mis_rutinas");
    }
  }, [vm.toast]);
```

- Escucha el código `"routine_created"` emitido por `useGymDashboardData.handleCreateRoutine()` para limpiar el formulario de creación y devolver al usuario automáticamente a la sub-pestaña `"mis_rutinas"`.

### 5.7. Barra de navegación (`DashboardTabBar.tsx`) y estilos (`dashboardStyles.ts`)

- `DashboardTabBar` utiliza `position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 50`. Por ello, `dashboardStyles.scrollContent` aplica `paddingBottom: 110` para que el último elemento de cualquier lista pueda desplazarse por encima de la barra inferior sin quedar tapado.
- `dashboardStyles.mainWrapper` fija `maxWidth: 760` y `alignSelf: "center"`, logrando que en pantallas anchas (tablets o navegadores web de escritorio) el dashboard se mantenga centrado y proporcionado.
- **Detalle técnico detectado**: `dashboardStyles.ts` define estilos heredados de una versión previa (`topTabBar`, `profileHero`, `avatarCircle` con color fijo `#10B981`) y exporta un alias `export const styles = dashboardStyles;` que ya no utiliza el nuevo `DashboardTabBar` flotante ni `ProfileSection`. Además, en `GymDashboard.tsx`, las funciones `handleStartRoutineSession`, `handleConfirmFinishSession` y `handleCancelRoutineSession` tienen bloques `catch` que silencian errores puntuales sin notificar con toast.

---

## 6. Flujo paso a paso (Ciclo de una sesión de entrenamiento)

1. El usuario abre la pestaña **Progreso (`tracking`)**. Como `activeSession` es `null`, `ActiveSessionBar` muestra el botón **"Iniciar rutina"** y `MarcaFormCard` permanece bloqueado (`lockStateCard`).
2. Al pulsar **"Iniciar rutina"**, se abre `SelectRoutineToStartModal`. Si el usuario no tiene rutinas, puede pulsar el botón para saltar directamente a `routines` en la sub-pestaña `"crear"`.
3. Al elegir una rutina, `handleStartRoutineSession(routineId)` llama a `api.startRoutineSession(routineId)`, guarda `activeSession`, inicia el contador en `0`, cierra el modal y preselecciona esa rutina en el formulario de marcas (`vm.handleRoutineChangeInTracking(routineId)`).
4. El `useEffect` de cronómetro arranca el `setInterval` de 1 segundo calculando la diferencia contra `started_at`. Si el usuario minimiza la app, el `AppState` pausa el intervalo y lo reanuda con el tiempo exacto al regresar.
5. `canRegisterMarca` pasa a `true`, desbloqueando `MarcaFormCard`. Cada vez que guarda una marca (`onSave`), si `vm.handleSaveMarca()` retorna `true`, incrementa `sessionMarcasCount` y añade `savedExerciseId` a `sessionLoggedExerciseIds`.
6. Cuando el usuario pulsa **"Finalizar"**, `handleAttemptFinishSession()` consulta `api.getWorkoutSessionDetail(activeSession.id)`.
   - Si no hay ninguna serie registrada, muestra un toast de advertencia (`toasts.marcaRequiredTitle`) y detiene el cierre.
   - Si hay al menos una serie, calcula `missingFinishExercises` y abre `FinishSessionConfirmModal`.
7. Si el usuario confirma en el modal, `handleConfirmFinishSession()` llama a `api.finishRoutineSession()`, limpia el estado de sesión activa, muestra el banner con `finishedSummaryDuration` y actualiza el historial y la asistencia semanal (`loadWeeklyAndHistory()`).

---

## 7. Conceptos y términos técnicos

- **Orquestador (Container Component)**: componente de alto nivel (`GymDashboard`) que no dibuja todo el HTML/JSX de detalle por sí mismo, sino que coordina estado, modales, barra superior, pestañas y subcomponentes de dominio.
- **Control de acceso por rol (RBAC básico en UI)**: verificación de permisos (`user?.is_staff` / `canManageItem`) para mostrar u ocultar acciones administrativas y bloquear modales de edición/eliminación sobre recursos protegidos.
- **AppState (React Native)**: API que informa si la aplicación está en primer plano (`"active"`), segundo plano (`"background"`) o en transición (`"inactive"`), usada para pausar el cronómetro y disparar resincronizaciones.
- **Pull-to-Refresh (`RefreshControl`)**: gesto estándar móvil de arrastrar la lista (`ScrollView`) hacia abajo para forzar la recarga de datos desde la API.
- **Ref mutable (`useRef`) para callbacks (`silentSyncRef`)**: patrón de React para guardar siempre la versión más reciente de una función y llamarla desde listeners montados una sola vez (`useEffect(..., [])`), evitando *stale closures* (datos obsoletos en memoria).
- **Safe Area Insets**: medidas exactas (en píxeles) de las áreas ocupadas por barras del sistema, gestos de navegación o muescas de pantalla, devueltas por `useSafeAreaInsets()`.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo evita `GymDashboard` que el cronómetro de entrenamiento se atrase si el usuario cambia a WhatsApp o bloquea la pantalla del celular?**
   - *Respuesta modelo:* El cronómetro no incrementa un contador local (`+1` cada segundo), sino que calcula en cada intervalo la diferencia real entre `Date.now()` y la marca temporal `started_at || start_time` devuelta por el backend (`computeElapsedSeconds`). Además, un listener de `AppState` detiene el `setInterval` al salir de primer plano y lo reanuda recalculando el tiempo exacto al volver a `"active"`.
2. **¿Por qué existe tanto un botón de actualización en `DashboardHeader`, un `RefreshControl` en el `ScrollView` y además sincronización silenciosa?**
   - *Respuesta modelo:* Cubren tres necesidades distintas: el botón en `DashboardHeader` sirve especialmente para Web y escritorio (donde no hay gesto táctil de arrastrar hacia abajo) y ofrece recarga rápida; `RefreshControl` ofrece la experiencia nativa móvil pull-to-refresh (ambos usan `force: true` y muestran confirmación); y la sincronización silenciosa (`silent: true`) mantiene actualizados los datos sin molestar al usuario al cambiar de pestaña o recuperar el foco de la ventana.
3. **¿Cómo garantiza el frontend que un atleta normal no pueda editar o borrar máquinas o ejercicios del catálogo?**
   - *Respuesta modelo:* En dos capas en `GymDashboard`: primero, solo pasa los callbacks de creación/edición (`onOpenAddExercise`, `onExerciseOptionsPress`, `onOpenAddEquipment`, `onEquipmentOptionsPress`) cuando `isAdmin` (`Boolean(user?.is_staff)`) es verdadero; segundo, los modales `ItemActionSheet`, `EditItemModal` y `ConfirmDeleteModal` filtran su propiedad `visible` mediante `canManageItem(type)`, que impide gestionar `"exercise"` o `"equipment"` si no es administrador (como respaldo al permiso del servidor).
4. **¿Qué hace exactamente `handleAttemptFinishSession()` antes de permitir terminar un entrenamiento?**
   - *Respuesta modelo:* Si existe `activeSession.id`, llama a `api.getWorkoutSessionDetail(activeSession.id)` para verificar en el servidor si hay al menos una serie registrada (`has_logged_sets` o ejercicios con series). Si no hay ninguna, bloquea la acción con un toast de advertencia (`marcaRequiredTitle`). Si sí hay, llama a `computeMissingExercisesForSession` para detectar qué ejercicios planificados en la rutina faltan por registrar y los pasa a `FinishSessionConfirmModal` para que el usuario decida si continuar o finalizar así.
5. **¿Para qué sirve `silentSyncRef` en `GymDashboard.tsx`?**
   - *Respuesta modelo:* El `useEffect` que registra los listeners de `AppState` y eventos web (`focus`, `visibilitychange`) tiene arreglo de dependencias vacío `[]` para suscribirse una sola vez. Si llamara directamente a una función definida en el render, quedaría atrapada con un estado viejo (*stale closure*). Actualizar `silentSyncRef.current` en cada render garantiza que el listener siempre ejecute la función con el estado actualizado sin tener que destruir y recrear los eventos.
6. **¿Qué ocurre si el usuario intenta registrar una marca en la pestaña "Progreso" sin haber iniciado una sesión?**
   - *Respuesta modelo:* `canRegisterMarca` evalúa `Boolean(activeSession !== null)`. Mientras sea `false`, en lugar de renderizar `<MarcaFormCard />`, se muestra una tarjeta de bloqueo (`lockStateCard`) indicando que primero debe pulsar "Iniciar rutina" en la `ActiveSessionBar`.

---

## 9. Resumen para repasar

- **`GymDashboard` orquesta 5 pestañas**: `equipment`, `catalog`, `routines` (inicial), `tracking` y `profile`, conectadas mediante `useGymDashboardData()` (`vm`).
- **Seguridad por rol (`isAdmin`)**: `user?.is_staff` controla la visibilidad de acciones administrativas y `canManageItem` protege `exercise` y `equipment`.
- **Cronómetro exacto con `AppState`**: calcula el tiempo desde `started_at` contra `Date.now()`, pausando el intervalo en segundo plano y restaurando sesiones activas al abrir la app.
- **Triple sincronización**: manual con `DashboardHeader` / `RefreshControl` (`force: true`) y automática silenciosa al cambiar de pestaña o recuperar foco (`AppState` / web `focus` & `visibilitychange`).
- **Cierre inteligente de sesión**: `handleAttemptFinishSession` consulta `getWorkoutSessionDetail`, exige mínimo una marca y avisa en el modal qué ejercicios de la rutina quedaron sin marcas.
