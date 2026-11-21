# 03 · Estado Global, Contextos, Almacenamiento y `useGymDashboardData`

## 1. Propósito

Este documento explica cómo **Apex Gym Hub** gestiona su estado global y persistente en el cliente: la persistencia local con `AsyncStorage` (`storage.ts` y `preferences.ts`), los tres Contextos de React (`AuthContext`, `ThemeContext`, `LanguageContext`), y el *Custom Hook* central **`useGymDashboardData`**, encargado de mantener sincronizados catálogos, máquinas, rutinas, marcas de fuerza, favoritos optimistas, validaciones y formularios del dashboard.

---

## 2. Ubicación

Archivos analizados bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\context\AuthContext.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\context\ThemeContext.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\context\LanguageContext.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\services\storage.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\services\preferences.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\hooks\useGymDashboardData.ts`

---

## 3. Cómo se conecta

```text
AsyncStorage (persistencia local en dispositivo / navegador)
   ├── @gym_access_token, @gym_refresh_token, @gym_user_data  ◀── storage.ts ◀── AuthContext & api.ts
   └── @apex_gym_preferences                                   ◀── preferences.ts ◀── ThemeContext & LanguageContext

Árbol de React:
AppThemeProvider (ThemeContext)
   └── LanguageProvider (LanguageContext)
         └── AuthProvider (AuthContext)
               └── HomeScreen ──▶ GymDashboard
                                     └── useGymDashboardData()
                                           ├── Consume useAuth()     (user, refreshProfile)
                                           ├── Consume useLanguage() (language, locale, t)
                                           └── Invoca api.* + muscleValidation.ts
```

---

## 4. Componentes, funciones y variables clave

### 4.1. `storage.ts`
- **Claves en `AsyncStorage`**: `TOKEN_KEY` (`"@gym_access_token"`), `REFRESH_KEY` (`"@gym_refresh_token"`), `USER_KEY` (`"@gym_user_data"`).
- **Métodos de `storage`**: `saveTokens`, `getAccessToken`, `getRefreshToken`, `saveUser`, `getUser`, `clearAuth` (`multiRemove`).

### 4.2. `preferences.ts`
- **Clave**: `PREFERENCES_KEY` (`"@apex_gym_preferences"`).
- **Constante `DEFAULT_PREFERENCES`**: `{ version: 1, themeMode: "dark", accentId: "emerald", language: "es" }`.
- **Validadores y sanitización**: `isValidThemeMode`, `isValidAccentId`, `isValidLanguageMode`, `sanitizePreferences`.
- **API `preferencesStorage`**: `load()`, `save(partial)`, `resetAppearance()`.

### 4.3. `AuthContext.tsx`
- **Provider y hook**: `AuthProvider`, `useAuth()`.
- **Estados**: `user`, `token`, `isLoading`, `isAuthenticating`, `error`.
- **Propiedades derivadas**: `isInitializing: isLoading`, `isAuthenticated: Boolean(user || token)`.
- **Métodos**: `loadSavedSession`, `login`, `register`, `logout`, `updateProfile`, `refreshProfile`, `clearError`, y el helper privado `extractApiError`.

### 4.4. `ThemeContext.tsx`
- **Provider y hook**: `AppThemeProvider`, `useAppTheme()`.
- **Estados y ref**: `mode`, `accent`, `nativeSystemScheme`, `isHydrated`, `modeRef`.
- **Valores calculados**: `systemScheme`, `resolvedMode`, `colors` (`buildThemeColors(resolvedMode, accent)`).
- **Métodos**: `setMode`, `setAccent`, `resetAppearance`, más helpers `normalizeScheme` y `applyNativeColorScheme`.

### 4.5. `LanguageContext.tsx`
- **Provider y hook**: `LanguageProvider`, `useLanguage()`.
- **Estados y ref**: `languageMode`, `systemLanguage`, `isHydrated`, `modeRef`.
- **Valores calculados**: `language` (`ResolvedLanguage`), `locale` (`LOCALE_MAP[language]`), `t(key, params)`.
- **Métodos**: `setLanguageMode`, `resetLanguage`.

### 4.6. `useGymDashboardData.ts`
- **Refs de control de red**: `refreshInFlightRef` (candado de concurrencia), `lastSyncRef` (marca temporal para *throttle* de 4000 ms).
- **Estados globales de datos**: `exercises`, `routines`, `equipmentList`, `muscleList`, `marcaHistory`, `adminUsers`.
- **Estados de UI y formularios**: `activeTab`, `loading`, `refreshing`, `toast`, formularios de ejercicio (`newEx*`), rutina (`newRoutine*`, `setsCount`, `minReps`, `maxReps`), marcas (`trackingRoutineId`, `trackingExerciseId`, `marcaWeight`, `marcaReps`, `marcaRpe`, `savingMarca`, `lastSavedSummary`) y modales (`actionSheetItem`, `editModalItem`, `deleteConfirmItem`, etc.).
- **Acciones principales**: `loadInitialData`, `refreshAllData`, `loadCatalogExtras`, `openExerciseDetail`, `handleCreateExercise`, `handleCreateRoutine`, `handleAddExerciseToRoutine`, `handleRoutineChangeInTracking`, `loadProgressionHistory`, `handleSaveMarca`, `loadAdminUsers`, `handleOpen*Options`, `handleSave*Edit`, `handleRemoveExerciseFromRoutine`, `handleAddExerciseToRoutineInEdit`, `handleUpdateRoutineExercise`, `handleCreateEquipment`, `handleToggleEquipmentFavorite`, `handleToggleExerciseFavorite`, `handleConfirmDelete`.

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. `storage.ts`: persistencia de sesión JWT

```ts
const TOKEN_KEY = '@gym_access_token';
const REFRESH_KEY = '@gym_refresh_token';
const USER_KEY = '@gym_user_data';

export const storage = {
  async saveTokens(accessToken: string, refreshToken?: string): Promise<void> {
    try {
      await AsyncStorage.setItem(TOKEN_KEY, accessToken);
      if (refreshToken) {
        await AsyncStorage.setItem(REFRESH_KEY, refreshToken);
      }
    } catch (e) {
      console.error('Error saving tokens in storage', e);
    }
  },
  ...
  async clearAuth(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_KEY, USER_KEY]);
    } catch (e) {
      console.error('Error clearing auth storage', e);
    }
  },
};
```

- Encapsula las llamadas asíncronas de `AsyncStorage` con manejo de errores `try/catch` para evitar caídas si el almacenamiento falla.
- `saveUser` y `getUser` serializan/deserializan el objeto `User` en JSON.
- `clearAuth` borra las tres claves atómicamente con `AsyncStorage.multiRemove`.
- **Observación técnica**: `saveTokens` y `getRefreshToken` almacenan y exponen el *refresh token* (`@gym_refresh_token`), pero actualmente `api.ts` aún no consume `getRefreshToken()` para renovar tokens expirados automáticamente.

### 5.2. `preferences.ts`: sanitización segura de tema, acento e idioma

```ts
function sanitizePreferences(raw: unknown): AppPreferences {
  if (!raw || typeof raw !== "object") {
    return { ...DEFAULT_PREFERENCES };
  }
  const obj = raw as Record<string, unknown>;
  return {
    version: 1,
    themeMode: isValidThemeMode(obj.themeMode)
      ? obj.themeMode
      : DEFAULT_PREFERENCES.themeMode,
    accentId: isValidAccentId(obj.accentId)
      ? obj.accentId
      : DEFAULT_PREFERENCES.accentId,
    language: isValidLanguageMode(obj.language)
      ? obj.language
      : DEFAULT_PREFERENCES.language,
  };
}
```

- **Por qué sanitizar**: si en una actualización futura cambia el nombre de una paleta o el JSON en `AsyncStorage` queda corrupto/incompleto, `sanitizePreferences` valida propiedad por propiedad mediante *Type Guards* (`isValidThemeMode`, `isValidAccentId`, `isValidLanguageMode`) y recupera los valores por defecto sin perder los campos válidos.
- **`save(partial)`**: primero carga las preferencias actuales (`preferencesStorage.load()`), mezcla solo los campos válidos del `partial` recibido y persiste el nuevo JSON.
- **`resetAppearance()`**: restablece `themeMode` (`"dark"`) y `accentId` (`"emerald"`), manteniendo intacto el `language` elegido por el usuario.

### 5.3. `AuthContext.tsx`: ciclo de sesión persistente y error handling

```tsx
  const loadSavedSession = async () => {
    try {
      const savedToken = await storage.getAccessToken();
      const savedUser = await storage.getUser();

      if (savedToken) {
        setToken(savedToken);
        if (savedUser) {
          setUser(savedUser);
        }
        try {
          const freshUser = await api.getProfile();
          setUser(freshUser);
          await storage.saveUser(freshUser);
        } catch {
          await logout();
        }
      }
    } catch (e) {
      console.error("Error restoring session", e);
    } finally {
      setIsLoading(false);
    }
  };
```

- Si existe un token guardado, carga primero `savedUser` (hidratación optimista) y luego llama a `api.getProfile()` para confirmar contra el servidor que el token sigue vigente y traer datos actualizados (peso, favoritos, `is_staff`).
- **Detalle técnico importante**: si `api.getProfile()` lanza cualquier error (tanto un 401 por token vencido como un fallo temporal de conexión con el servidor), el bloque `catch` ejecuta `await logout()`, limpiando la sesión local.

```tsx
function extractApiError(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.data && typeof err.data === "object") {
    const data = err.data as Record<string, unknown>;
    const priorityKeys = [
      "email", "username", "password", "password_confirm",
      "non_field_errors", "detail",
    ];
    for (const key of priorityKeys) {
      const val = data[key];
      if (Array.isArray(val) && val.length > 0) return String(val[0]);
      if (typeof val === "string" && val.trim()) return val;
    }
    for (const val of Object.values(data)) { ... }
  }
  return (err as any)?.message || fallback;
}
```

- **`extractApiError`**: adapta los errores estructurados de Django REST Framework (donde los errores de validación llegan como `{ email: ["Este correo ya existe."] }`) a un mensaje legible.
- **Asimetría detectada**: `register()` utiliza `extractApiError(...)` para mostrar errores específicos de campo, mientras que `login()` asigna directamente `err.message || "Error al iniciar sesión"`.
- **Auto-login tras registro**: `register` envía `POST /auth/register/`, verifica `response.tokens?.access`, `response.tokens?.refresh` y `response.user`, actualiza `token` y `user` en estado y guarda ambos en `storage`, autenticando al usuario inmediatamente.

### 5.4. `ThemeContext.tsx`: tema dinámico y sincronización nativa

```tsx
  const systemScheme: ResolvedThemeMode =
    Platform.OS === "web" ? normalizeScheme(webScheme) : nativeSystemScheme;

  const resolvedMode: ResolvedThemeMode =
    mode === "system" ? systemScheme : mode;

  const colors = useMemo(
    () => buildThemeColors(resolvedMode, accent),
    [resolvedMode, accent],
  );

  useEffect(() => {
    if (Platform.OS === "web") return;
    SystemUI.setBackgroundColorAsync(colors.background).catch(() => undefined);
  }, [colors.background]);
```

- En Web utiliza `useColorScheme()` (`useRNColorScheme`) de React Native; en nativo mantiene `nativeSystemScheme` actualizado mediante `Appearance.addChangeListener` y `AppState` (`"active"`).
- **`applyNativeColorScheme(mode)`**: llama a `Appearance.setColorScheme(mode === "system" ? "auto" : mode)` en Android/iOS para que elementos nativos del sistema (teclado, diálogos) concuerden con la preferencia elegida en la app.
- **`SystemUI.setBackgroundColorAsync(colors.background)`**: pinta el fondo raíz de la ventana nativa para evitar destellos blancos/negros durante transiciones.

### 5.5. `LanguageContext.tsx`: internacionalización reactiva

```tsx
  const language: ResolvedLanguage =
    languageMode === "system" ? systemLanguage : languageMode;

  const locale = LOCALE_MAP[language];

  const t = useCallback(
    (key: TranslationKey, params?: TranslationParams) =>
      translate(language, key, params),
    [language],
  );
```

- Al iniciar, llama a `detectSystemLanguage()` y lee la preferencia persistida.
- Si `languageMode === "system"`, vuelve a ejecutar `detectSystemLanguage()` cada vez que `AppState` vuelve a `"active"`, permitiendo que si el usuario cambia el idioma del teléfono en Ajustes del sistema, la app se actualice al volver.
- Expone `locale` (`"es-ES"` o `"en-US"`) para formatear fechas con `toLocaleDateString(locale)` y la función `t` memorizada.

### 5.6. `useGymDashboardData.ts`: el motor del dashboard

#### A) Control de refresco, concurrencia y coherencia de tracking

```ts
  const refreshAllData = async (options?: {
    silent?: boolean;
    force?: boolean;
  }) => {
    if (refreshInFlightRef.current) return;
    if (
      options?.silent &&
      !options?.force &&
      Date.now() - lastSyncRef.current < 4000
    ) {
      return;
    }
```

- **`refreshInFlightRef`**: impide que dos recargas paralelas se pisen entre sí si el usuario cambia rápido de pestaña o presiona el botón de refresco varias veces.
- **Throttle de 4 segundos**: en sincronizaciones silenciosas no forzadas (`silent: true`), omite llamadas repetidas si pasaron menos de `4000 ms` desde `lastSyncRef.current`.
- En `refreshAllData`, recarga en paralelo `exercises`, `routines`, `equipmentList`, `muscleList` y `refreshProfile()`, cierra `ExerciseDetailModal` si el ejercicio abierto fue borrado en el servidor, y reajusta `trackingRoutineId` y `trackingExerciseId` si la rutina o ejercicio seleccionado ya no existe.

#### B) Transformación de estructura de rutina (`getExercisesOfRoutine`)

```ts
  const getExercisesOfRoutine = (routine?: Routine): RoutineExerciseItem[] => {
    if (!routine || !routine.days) return [];
    const list: RoutineExerciseItem[] = [];
    routine.days.forEach((d) => {
      d.exercises?.forEach((e) => {
        const sc = e.target_sets?.length || 4;
        const firstSet = e.target_sets?.[0];
        list.push({
          id: e.exercise,
          name: e.exercise_detail?.name || t("common.exerciseFallback"),
          routineExerciseId: e.id,
          equipmentName: e.exercise_detail?.equipment_name,
          setsCount: sc,
          minReps: firstSet?.min_reps || 8,
          maxReps: firstSet?.max_reps || 12,
        });
      });
    });
    return list;
  };
```

- Aplana la jerarquía `Routine -> days[] -> exercises[] -> target_sets[]` que devuelve Django en un arreglo plano fácil de iterar en listas, selectores de tracking y modales.

#### C) Validaciones de negocio al crear y editar

- **`handleCreateExercise`**: exige `requireAdmin()`, nombre no vacío (`newExName.trim()`) y grupo muscular (`newExMuscle`). Si faltan instrucciones, usa el texto traducido por defecto `t("toasts.defaultInstructions")`.
- **`handleCreateRoutine`**: valida título no vacío, filtra `newRoutineExerciseIds` con `isExerciseCompatibleWithFocus(ex, newRoutineFocus)` y lee `setsCount`, `minReps`, `maxReps`. Incluye un respaldo: si el endpoint de creación devolvió la rutina sin ejercicios (`getExercisesOfRoutine(created).length === 0`) pese a haber enviado `validExerciseIds`, invoca inmediatamente `api.addExerciseToRoutine(...)`.
- **`handleAddExerciseToRoutine`**:
  1. Soporta selección múltiple (`selectedExsToAdd`) o individual (`selectedExToAdd`).
  2. Si la rutina no es `"fullbody"`, valida cada ejercicio con `isExerciseCompatibleWithFocus`. Si alguno es incompatible, detiene la operación con un toast de error explicando el músculo del ejercicio vs el enfoque de la rutina.
  3. Filtra ejercicios duplicados que ya estén en la rutina.
- **`handleUpdateRoutineExercise`**: valida con `Number.isInteger(...) && >= 1` y asegura `max_reps: Math.max(minR, maxR)`.
- **Observación detectada**: `handleAddExerciseToRoutineInEdit` (usado desde `EditItemModal`) agrega ejercicios directamente sin ejecutar la validación `isExerciseCompatibleWithFocus` que sí aplica `handleAddExerciseToRoutine`.

#### D) Registro de marcas y directorio Admin

- **`handleSaveMarca`**: valida que exista `trackingExerciseId` y que `parseFloat(marcaWeight)` y `parseInt(marcaReps, 10)` no sean `NaN`. Llama a `api.saveMarca(...)`, actualiza `lastSavedSummary` con el `estimated_1rm` calculado por el backend, muestra toast de éxito, recarga el historial con `loadProgressionHistory` y retorna `boolean` (`true`/`false`) para que `GymDashboard` sepa si incrementar `sessionMarcasCount`.
- **`loadAdminUsers`**: exige `requireAdmin()`. Funciona como interruptor (*toggle*): si `showAdminUsers` ya es `true`, oculta el listado sin volver a llamar a la API; si es `false`, consulta `api.getAdminUsers()`.

#### E) Favoritos optimistas con reversión ante fallos

```ts
  const handleToggleExerciseFavorite = async (exerciseId: string) => {
    try {
      Vibration.vibrate(15);
    } catch {}
    setExercises((prev) =>
      prev.map((ex) =>
        ex.id === exerciseId ? { ...ex, is_favorite: !ex.is_favorite } : ex,
      ),
    );
    try {
      const res = await api.toggleExerciseFavorite(exerciseId);
      setExercises((prev) =>
        prev.map((ex) =>
          ex.id === exerciseId ? { ...ex, is_favorite: res.is_favorite } : ex,
        ),
      );
    } catch (e: any) {
      setExercises((prev) =>
        prev.map((ex) =>
          ex.id === exerciseId ? { ...ex, is_favorite: !ex.is_favorite } : ex,
        ),
      );
      showToast("error", t("toasts.favoritesError"), e.message);
    }
  };
```

- Tanto `handleToggleEquipmentFavorite` como `handleToggleExerciseFavorite` invierten inmediatamente `is_favorite` en memoria (acompañado de una vibración corta de `15 ms`) para respuesta instantánea al tacto. Luego confirman el valor definitivo del servidor (`res.is_favorite`), o revierten el cambio y muestran error si falla la red.

#### F) Eliminación unificada (`handleConfirmDelete`)

- Centraliza el borrado de los 4 tipos (`"routine"`, `"marca"`, `"equipment"`, `"exercise"`):
  - Al borrar una `"routine"`, si era la rutina activa en Tracking (`trackingRoutineId`), selecciona automáticamente la primera rutina restante (o limpia los estados si no quedan rutinas).
  - Al borrar `"equipment"` o `"exercise"`, exige `requireAdmin()`; en el caso de `"exercise"`, recarga tanto ejercicios como rutinas para mantener las rutinas limpias de ejercicios eliminados.

---

## 6. Flujo paso a paso (Hidratación y sincronización inicial)

1. `preferencesStorage.load()` lee `@apex_gym_preferences` y aplica `sanitizePreferences` para entregar tema, acento e idioma válidos a `AppThemeProvider` y `LanguageProvider`.
2. `AuthProvider` ejecuta `loadSavedSession()`, lee `storage.getAccessToken()` y `storage.getUser()`, y valida contra `api.getProfile()`.
3. Una vez autenticado, se monta `GymDashboard` y se ejecuta `useGymDashboardData()`.
4. El `useEffect(..., [])` de `useGymDashboardData` lanza `loadInitialData()`, cargando en paralelo ejercicios, rutinas, equipos y músculos, y seleccionando automáticamente la primera rutina y su primer ejercicio para graficar su historial 1RM (`loadProgressionHistory`).
5. Durante el uso, las acciones CRUD actualizan el estado tras confirmar con el servidor (excepto los favoritos, que usan actualización optimista), mientras `refreshAllData` coordina recargas concurrentes con mutex y *throttle*.

---

## 7. Conceptos y términos técnicos

- **AsyncStorage**: sistema de almacenamiento clave-valor asíncrono y persistente en React Native (equivalente a `localStorage` en web, y respaldado por `localStorage` cuando corre en Expo Web).
- **Hydration (Hidratación de estado)**: proceso mediante el cual una aplicación recién abierta lee datos guardados en disco (`AsyncStorage`) y los carga en la memoria de React (`useState`).
- **Actualización optimista (Optimistic UI)**: técnica donde la interfaz cambia visualmente de inmediato al pulsar un botón (como el corazón de favorito) asumiendo que la API responderá bien, revirtiendo el cambio solo si la petición falla.
- **Mutex / Lock con `useRef` (`refreshInFlightRef`)**: bandera booleana en referencia que evita lanzar múltiples peticiones idénticas mientras una sigue en curso, sin provocar re-renderizados adicionales.
- **Throttle (Limitación de frecuencia)**: restricción temporal (`< 4000 ms`) que evita saturar el backend cuando el usuario cambia rápidamente entre pestañas.
- **Type Guard**: función de TypeScript con firma `value is Tipo` (como `isValidThemeMode`) que valida datos desconocidos en tiempo de ejecución y ayuda al compilador a estrechar el tipo.

---

## 8. Posibles preguntas del profesor

1. **¿Qué diferencia hay entre `storage.ts` y `preferences.ts`? ¿Por qué no guardar todo en un solo archivo?**
   - *Respuesta modelo:* `storage.ts` gestiona credenciales y datos de sesión (`@gym_access_token`, `@gym_refresh_token`, `@gym_user_data`) que deben borrarse por completo al cerrar sesión (`clearAuth`). En cambio, `preferences.ts` guarda la configuración visual y de idioma del dispositivo (`@apex_gym_preferences`), la cual debe sobrevivir aunque el usuario cierre sesión o cambie de cuenta.
2. **¿Cómo protege `preferences.ts` a la aplicación si alguien corrompe el JSON guardado en `AsyncStorage`?**
   - *Respuesta modelo:* A través de `sanitizePreferences()` y los type guards `isValidThemeMode`, `isValidAccentId` e `isValidLanguageMode`. Si un campo tiene un valor inválido o falta, solo ese campo cae al valor por defecto de `DEFAULT_PREFERENCES`, y si `JSON.parse` falla, el `catch` devuelve una copia completa de los valores por defecto.
3. **¿Cómo funciona la actualización optimista de favoritos en `useGymDashboardData.ts`?**
   - *Respuesta modelo:* Al tocar el icono de favorito, inmediatamente se vibra `15 ms` y se invierte `is_favorite` en el arreglo local (`exercises` o `equipmentList`) antes de recibir respuesta del servidor. Luego se espera a `api.toggleExerciseFavorite` o `api.toggleEquipmentFavorite` para sincronizar el valor exacto retornado; si la petición lanza excepción, el `catch` vuelve a invertir el booleano para revertir la UI y muestra un toast de error.
4. **¿Qué sucede en `AuthContext` cuando un usuario se registra desde la app?**
   - *Respuesta modelo:* `AuthContext.register()` envía los datos normalizados (`email` en minúsculas) a `api.register()`, recibe `{ user, tokens: { access, refresh } }`, guarda los tokens y el usuario en `AsyncStorage` y actualiza los estados `token` y `user`. Al existir `user`, `HomeScreen` cambia de inmediato al `GymDashboard` sin pedir que vuelva a escribir su contraseña para iniciar sesión.
5. **¿Qué riesgo o detalle técnico tiene `loadSavedSession` en `AuthContext.tsx` respecto a errores de red?**
   - *Respuesta modelo:* Cuando encuentra un token guardado, ejecuta `await api.getProfile()` dentro de un `try/catch` y, ante cualquier error en ese `catch`, llama a `await logout()`. Eso garantiza que un token expirado o revocado cierre la sesión automáticamente, pero como efecto secundario también cerraría la sesión local si el servidor estuviera temporalmente inaccesible al abrir la app.
6. **¿Cómo evita `useGymDashboardData` peticiones duplicadas al cambiar rápido entre pestañas?**
   - *Respuesta modelo:* Usa dos `useRef`: `refreshInFlightRef` actúa como cerrojo para ignorar llamadas a `refreshAllData` mientras ya haya una en vuelo, y `lastSyncRef` bloquea sincronizaciones silenciosas (`silent: true`, sin `force`) si han pasado menos de 4000 ms desde la última sincronización exitosa.
7. **¿Por qué `ThemeContext` usa un `modeRef` además del estado `mode`?**
   - *Respuesta modelo:* Porque los listeners nativos (`Appearance.addChangeListener` y `AppState.addEventListener`) se registran una sola vez al montar el provider (`useEffect(..., [])`). Leer `modeRef.current` dentro del callback permite saber en tiempo real si el modo actual es `"system"` sin necesidad de volver a registrar los listeners cada vez que cambia el tema.

---

## 9. Resumen para repasar

- **Dos capas de almacenamiento en `AsyncStorage`**: `storage.ts` para autenticación (se limpia en `logout`) y `preferences.ts` para apariencia/idioma con sanitización segura y versión de esquema (`version: 1`).
- **Tres contextos globales**: `ThemeContext` (modo + 5 acentos + `SystemUI`), `LanguageContext` (detección automática y `t()`), y `AuthContext` (hidratación, auto-login en registro y `extractApiError`).
- **`useGymDashboardData` es el ViewModel del dashboard**: concentra todos los estados, validaciones de foco muscular (`isExerciseCompatibleWithFocus`), operaciones CRUD, favoritos optimistas y control de refrescos con candado de concurrencia y *throttle* de 4 segundos.
- **Resiliencia en UI**: el cambio de favorito responde al instante y revierte si falla la API, mientras que el borrado de rutinas o ejercicios reajusta automáticamente el estado de tracking y listas relacionadas.
