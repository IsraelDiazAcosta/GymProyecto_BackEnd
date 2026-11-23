# 11. Pestaña Perfil, IMC, Ajustes y Modales CRUD Reutilizables

---

## 1. Propósito

Este bloque documenta los dos pilares finales de interacción del Front End de **Apex Gym Hub**:

1. **Pestaña Perfil (`profile/`):** presenta la identidad del atleta o administrador, sus métricas biométricas (peso, estatura normalizada en metros e **IMC**), edición de perfil (`EditProfileForm`), auditoría del directorio de usuarios para staff, asistencia semanal (`WeeklyAttendanceCard`), gráfica dual SVG **Peso Corporal vs Curva 1RM**, panel de **Ajustes** de apariencia/idioma en vivo (`SettingsModal`) y botón compacto de cierre de sesión.
2. **Sistema modular de Modales CRUD (`modals/` y `modals/edit-forms/`):** provee una arquitectura desacoplada para inspeccionar acciones (`ItemActionSheet`), confirmar eliminaciones destructivas (`ConfirmDeleteModal`) y editar cualquiera de las entidades del sistema (`EditItemModal` coordinando 4 formularios especializados).

---

## 2. Ubicación

Todas las rutas parten de `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

| Archivo | Rol |
| :--- | :--- |
| `src/components/dashboard/profile/ProfileSection.tsx` | Pantalla principal de Perfil: cabecera con botones espejo, métricas, IMC, directorio admin, gráfica dual Peso vs 1RM y Log Out. |
| `src/components/dashboard/profile/EditProfileForm.tsx` | Formulario inline para editar username, nivel, objetivo, peso, estatura (normalizada a metros) y biografía. |
| `src/components/dashboard/profile/SettingsModal.tsx` | Modal inferior de Ajustes: vista previa en vivo, modo de pantalla (`dark`/`light`/`system`), 5 acentos e idioma (`es`/`en`/`system`). |
| `src/components/dashboard/modals/ConfirmDeleteModal.tsx` | Modal de confirmación de borrado reutilizable para 5 tipos de entidad (`routine`, `exercise`, `marca`, `equipment`, `session`). |
| `src/components/dashboard/modals/ItemActionSheet.tsx` | Hoja de acciones animada (*Bottom Sheet*) para elegir Editar o Eliminar tras un *long-press* o clic en `⋮`. |
| `src/components/dashboard/modals/EditItemModal.tsx` | Coordinador modal modular de edición (sustituyó un archivo monolítico de +1,370 líneas). |
| `src/components/dashboard/modals/edit-forms/EditEquipmentForm.tsx` | Subformulario de edición de máquinas/equipos. |
| `src/components/dashboard/modals/edit-forms/EditExerciseForm.tsx` | Subformulario de edición de ejercicios del catálogo. |
| `src/components/dashboard/modals/edit-forms/EditRoutineForm.tsx` | Subformulario de edición de rutinas y gestor interno de sus ejercicios y series/reps. |
| `src/components/dashboard/modals/edit-forms/EditMarcaForm.tsx` | Subformulario de edición de marcas de levantamiento con previsualización en vivo del 1RM. |
| `src/components/dashboard/ProfileSection.tsx`, `ConfirmDeleteModal.tsx`, `ItemActionSheet.tsx`, `EditItemModal.tsx` | **Shims heredados (1 línea):** únicamente re-exportan desde `./profile/...` y `./modals/...`. |

---

## 3. Cómo se conecta

```text
GymDashboard.tsx
  ├── Tab "profile" ──► ProfileSection
  │       ├── AuthContext (`useAuth`): `user`, `logout()`, `updateProfile()`
  │       ├── API directa: `api.getWeightLogs()`, `api.getWeight1RMProgress(exId)`, `api.createWeightLog()`
  │       ├── Botón lápiz (arriba izq.) ──► `isEditing = true` ──► EditProfileForm ──► `PATCH /auth/profile/`
  │       ├── Botón engrane (arriba der.) ──► `settingsVisible = true` ──► SettingsModal
  │       │                                                                  ├── `useAppTheme()` ──► AsyncStorage (`@apex_gym_preferences`)
  │       │                                                                  └── `useLanguage()` ──► AsyncStorage (`@apex_gym_preferences`)
  │       ├── Botón "Auditar Directorio de Usuarios (API)" (solo `user?.is_staff`) ──► `vm.loadAdminUsers()` ──► `GET /auth/users/`
  │       ├── WeeklyAttendanceCard (desde `../routines/WeeklyAttendanceCard`)
  │       └── Botón compacto Log Out (abajo centrado) ──► `logout()`
  │
  └── Modales globales en GymDashboard (protegidos por `canManageItem`)
          ├── ItemActionSheet ──► `onEdit` ──► EditItemModal ──► EditRoutineForm / EditExerciseForm / EditEquipmentForm / EditMarcaForm
          │                   └── `onDelete` ──► ConfirmDeleteModal ──► `vm.handleConfirmDelete()`
          └── RoutineSessionHistorySection también reutiliza `ConfirmDeleteModal` (`itemType="session"`).
```

---

## 4. Componentes, funciones y variables clave

### En `ProfileSection.tsx` y `EditProfileForm.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `normalizeHeightToMeters(v)` | Helper | Convierte estatura a metros; si `n > 3` (cm heredados, ej. `175`), divide entre `100` (`1.75`). |
| `parseHeightMeters(raw, label, lang)` | Helper en `EditProfileForm` | Si el usuario escribe entre `50` y `280` (cm), divide entre `100`; valida rango `[0.50, 2.80]` m y formatea a 2 decimales. |
| `parseDecimal(raw, label, lang)` | Helper en `EditProfileForm` | Reemplaza coma por punto y valida valores positivos `< 1000` compatibles con `DecimalField(max_digits=5, decimal_places=2)` de Django. |
| `bmi` | Variable derivada | `(weight / (heightMeters * heightMeters)).toFixed(1)` usando `latestLogWeight ?? user?.current_weight`. |
| `weightLogs`, `rmProgress`, `selectedExId`, `newWeightInput`, `chartSize` | Estados en `ProfileSection` | Alimentan el registro rápido de peso corporal y la gráfica SVG dual. |
| `sortedLogs`, `rmSeries`, `bwPointsStr`, `rmPointsStr` | Series SVG | Coordenadas independientes para peso corporal (línea discontinua) y curva 1RM (línea sólida). |
| `isEditing`, `settingsVisible` | Estados UI | Alternan el formulario inline y el modal de Ajustes. |

### En `SettingsModal.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `MODE_OPTIONS` | Constante | `dark` (luna), `light` (sol), `system` (smartphone). |
| `LANGUAGE_OPTIONS` | Constante | `es`, `en`, `system`. |
| `useAppTheme()` | Hook de `ThemeContext` | Provee `mode`, `resolvedMode`, `systemScheme`, `accent` (`"emerald" \| "ocean" \| "amber" \| "violet" \| "crimson"`), `colors`, `setMode`, `setAccent`, `resetAppearance`. |
| `useLanguage()` | Hook de `LanguageContext` | Provee `languageMode`, `language`, `systemLanguage`, `t`, `setLanguageMode`. |

### En `modals/` y `modals/edit-forms/`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `ItemActionSheet` | Bottom Sheet animado | Usa `Animated.spring` sobre `translateY` (`300 → 0`), `Vibration.vibrate(45)` y `setTimeout(..., 180)` antes de abrir `EditItemModal` o `ConfirmDeleteModal`. |
| `ConfirmDeleteModal` | Modal de confirmación | Acepta `itemType`: `"routine" \| "exercise" \| "marca" \| "equipment" \| "session"`; bloquea botones con `deleting` durante la promesa `onConfirm()`. |
| `EditItemModal` | Coordinador modal | Hidrata estados de los 4 formularios mediante `useEffect` al cambiar `visible`/`itemType`/datos y delega el guardado a `onSaveRoutine`, `onSaveExercise`, `onSaveMarca`, `onSaveEquipment`. |
| `EditEquipmentForm` | Formulario | Edita nombre, tipo (`EQUIPMENT_TYPES`), marca, descripción, guía de ajuste e imagen. |
| `EditExerciseForm` | Formulario | Edita nombre, músculo (`muscleList`), máquina (`equipmentList`), video, instrucciones e imagen (con preview heredado). |
| `EditRoutineForm` | Formulario | Edita título, enfoque muscular (`FOCUS_OPTIONS`), muestra borde amarillo en ejercicios incompatibles, permite editar series/reps inline, quitar ejercicios y añadir nuevos. |
| `EditMarcaForm` | Formulario | Muestra tarjeta con previsualización Brzycki en vivo (`preview1RM`) y edita peso, reps y RPE. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### A. Disposición espejo en cabecera y botón compacto Log Out (`ProfileSection.tsx`)

```tsx
editBtnTop: {
  position: "absolute",
  top: 14,
  left: 14,
  width: 40,
  height: 40,
  borderRadius: 12,
  ...
},
settingsBtn: {
  position: "absolute",
  top: 14,
  right: 14,
  width: 40,
  height: 40,
  borderRadius: 12,
  ...
},
logoutCompactBtn: {
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "center",
  alignSelf: "center",
  gap: 6,
  height: 40,
  paddingHorizontal: 22,
  borderRadius: Radius.md,
  ...
}
```

- **Simetría visual:** Dentro de `heroCard` (`position: "relative"`), el botón de editar perfil se ubica en la esquina superior izquierda (`top: 14, left: 14`) y desaparece cuando `isEditing` está activo; en la esquina opuesta (`top: 14, right: 14`) se sitúa en posición espejo el engrane de **Ajustes** (`SettingsModal`).
- **Cierre de sesión no intrusivo:** Al final de toda la columna (`sectionColumn`) se coloca `logoutCompactBtn` centrado (`alignSelf: "center"`), con altura compacta de `40px` y color de peligro (`colors.danger`), evitando que el usuario pulse "Cerrar Sesión" accidentalmente mientras navega por sus métricas.

### B. Normalización de estatura en metros y cálculo de IMC (`ProfileSection.tsx` y `EditProfileForm.tsx`)

```tsx
const normalizeHeightToMeters = (
  v?: number | string | null,
): number | null => {
  const n = formatDecimal(v);
  if (n === null || n <= 0) return null;
  return n > 3 ? n / 100 : n;
};
// ...
const latestLogWeight =
  weightLogs.length > 0 ? formatDecimal(weightLogs[0].weight) : null;
const weight = latestLogWeight ?? formatDecimal(user?.current_weight);
const heightMeters = normalizeHeightToMeters(user?.height);
const bmi =
  weight && heightMeters
    ? (weight / (heightMeters * heightMeters)).toFixed(1)
    : null;
```

- **Compatibilidad retroactiva:** Si la base de datos o el usuario ingresó estatura en centímetros (`175`), `n > 3` (en lectura) o `num >= 50 && num <= 280` (en `parseHeightMeters` al editar) la divide automáticamente entre `100` para trabajar siempre en metros (`1.75 m`) y calcular correctamente $\text{IMC} = \frac{\text{peso (kg)}}{\text{estatura (m)}^2}$.
- Además, en `EditProfileForm.handleSave`, si el peso guardado cambió respecto a `user.current_weight`, también llama automáticamente a `api.createWeightLog(...)` para que el historial de peso corporal quede sincronizado con la edición del perfil.

### C. Gráfica dual SVG Peso Corporal vs Curva 1RM (`ProfileSection.tsx`)

```tsx
<Svg width={chartSize.width} height={chartSize.height}>
  {bwDots.length > 1 && (
    <Polyline
      points={bwPointsStr}
      fill="none"
      stroke={colors.textSecondary}
      strokeWidth={2.5}
      strokeDasharray="5,4"
      ...
    />
  )}
  {rmDots.length > 1 && (
    <Polyline
      points={rmPointsStr}
      fill="none"
      stroke={colors.primary}
      strokeWidth={3}
      ...
    />
  )}
```

- **Dos escalas independientes superpuestas:** `bwDots` (peso corporal en línea punteada `strokeDasharray="5,4"`) y `rmDots` (fuerza 1RM en línea sólida del color de acento) se normalizan cada una entre su propio `minV` y `maxV`. Esto permite comparar visualmente si la fuerza sube mientras el peso corporal baja o se mantiene, sin que una serie aplaste a la otra por tener magnitudes distintas (ej. 70 kg vs 150 kg).

### D. Panel de Auditoría Admin y Ajustes en vivo (`ProfileSection.tsx` y `SettingsModal.tsx`)

- **Auditar Directorio de Usuarios (API):** Solo visible si `user?.is_staff && !isEditing`. Al pulsar el botón, `useGymDashboardData.loadAdminUsers` verifica `requireAdmin()`, si ya estaba abierto lo colapsa (`setShowAdminUsers(false)`), y si estaba cerrado consulta `GET /auth/users/` y renderiza cada usuario con su icono de rol (`shield` vs `user`), correo/username y estado.
- **SettingsModal:** Permite cambiar en vivo el modo de pantalla (`dark`, `light`, `system`), 5 paletas de acento (`emerald`, `ocean`, `amber`, `violet`, `crimson` definidas en `ACCENT_PALETTES` de `src/constants/theme.ts`) y el idioma (`es`, `en`, `system`). Tanto `ThemeContext` como `LanguageContext` persisten los cambios automáticamente en `AsyncStorage` bajo `@apex_gym_preferences` y muestran una tarjeta de vista previa en tiempo real arriba del modal.

### E. Arquitectura de Modales CRUD y hallazgos importantes en código

1. **`EditItemModal` + `edit-forms/`:** Aplica el principio de responsabilidad única: `EditItemModal` gestiona la ventana modal, la barra superior localizada y la carga/guardado de estado, mientras delega el contenido visual a `EditEquipmentForm`, `EditExerciseForm`, `EditRoutineForm` o `EditMarcaForm` según `itemType`.
2. **Hallazgo crítico en `ItemActionSheet.tsx` (líneas 173 y 216):**
   ```tsx
   {itemType !== "routine" && ( /* Botón Editar */ )}
   {itemType !== "routine" && ( /* Botón Eliminar */ )}
   ```
   Aunque `GymDashboard` aún pasa `onOpenRoutineOptions={vm.handleOpenRoutineOptions}` a `RoutinesSection` (que se dispara al hacer *long-press* en `RoutineCard`) y aunque `EditItemModal` + `EditRoutineForm` + `ConfirmDeleteModal` tienen soporte completo para `itemType === "routine"`, `ItemActionSheet` oculta **ambos botones** cuando `itemType === "routine"`. En consecuencia, un *long-press* sobre una rutina abre un *bottom sheet* donde solo aparece el botón **"Cancelar"**. (El borrado de rutinas sigue funcionando por el botón directo de papelera en `RoutineCard`).
3. **Hallazgo de manejo de errores en `EditItemModal.tsx`:** En `handleSave`, `EditItemModal` siempre ejecuta `onClose()` al terminar `await onSave...(...)`. Sin embargo, en `useGymDashboardData.ts`, `handleSaveRoutineEdit`, `handleSaveExerciseEdit`, `handleSaveEquipmentEdit` y `handleSaveMarcaEdit` capturan los errores y muestran toast sin relanzarlos (`throw`), por lo que el modal de edición se cierra aunque el `PATCH` falle (a diferencia de `handleCreateEquipment` en `AddEquipmentModal`, que sí relanza el error).
4. **Limpieza menor:** En `SettingsModal.tsx` (líneas 762-797) hay estilos sin uso (`languageCard`, `comingSoonPill`, etc.) de una versión anterior donde el selector de idioma estaba marcado como "próximamente", y en `EditEquipmentForm`/`EditExerciseForm` falta el botón de papelera para limpiar la foto recién seleccionada que sí tienen `AddEquipmentModal` y `AddExerciseModal`.

---

## 6. Flujo paso a paso

1. **Consultar Perfil y Biometría:** Al abrir la pestaña **Perfil**, `ProfileSection` ejecuta `loadWeightAnd1RM`, trayendo `GET /auth/weight-logs/` y `GET /tracking/progress/weight-1rm/`, normaliza la estatura en metros, calcula el IMC y renderiza la tarjeta superior, `WeeklyAttendanceCard` y la gráfica dual SVG.
2. **Editar Perfil o Registrar Peso:**
   - Si toca el lápiz superior izquierdo, se abre `EditProfileForm` inline; al guardar envía `PATCH /auth/profile/` (y si cambió el peso, crea un `weight-log`), refresca el perfil en `AuthContext` y recarga la gráfica.
   - Si registra un peso rápido en la tarjeta inferior, llama `POST /auth/weight-logs/` y sincroniza `current_weight` en el perfil.
3. **Personalizar Apariencia e Idioma:** Al tocar el engrane superior derecho, se abre `SettingsModal`. Cada toque en modo, color de acento o idioma actualiza `ThemeContext`/`LanguageContext` al instante y persiste en `@apex_gym_preferences`.
4. **Flujo CRUD reutilizable (Ejercicios, Máquinas, Marcas):** Al hacer *long-press* o tocar `⋮`, `GymDashboard` carga `actionSheetItem` y abre `ItemActionSheet`. Si el usuario elige **Editar**, cierra la hoja y tras 180 ms abre `EditItemModal` con el subformulario correspondiente; si elige **Eliminar**, tras 180 ms abre `ConfirmDeleteModal`, el cual muestra un spinner mientras `handleConfirmDelete` envía el `DELETE` a la API.

---

## 7. Conceptos y términos técnicos

- **Normalización de unidades:** Conversión defensiva de entradas heterogéneas (centímetros heredados vs metros) a una unidad canónica única (`m`) antes de persistir y calcular fórmulas clínicas como el IMC.
- **Patrón Coordinador / Estrategia por tipo (`EditItemModal`):** Componente contenedor que comparte marco, ciclo de vida y botones de guardado, delegando el renderizado específico a subformularios especializados según `itemType`.
- **Encadenamiento seguro de modales (`setTimeout(..., 180)`):** Pausa breve entre el cierre de un `Modal` y la apertura del siguiente para prevenir condiciones de carrera visuales y bloqueos táctiles en iOS/Android.
- **Persistencia local reactiva (`Context` + `AsyncStorage`):** Combinación de React Context para re-renderizar toda la app al instante y `AsyncStorage` para recordar tema, acento e idioma tras reiniciar la aplicación.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo maneja el sistema si un usuario antiguo tenía guardada su estatura en centímetros (por ejemplo `175`) y ahora el sistema calcula el IMC en metros?**
   - *Respuesta modelo:* Tanto `normalizeHeightToMeters` en `ProfileSection` como `toHeightMetersInput` y `parseHeightMeters` en `EditProfileForm` detectan automáticamente si el valor viene en centímetros (`> 3` al leer, o entre `50` y `280` al editar) y lo dividen entre `100` para convertirlo a `1.75 m` antes de mostrarlo o calcular el IMC ($\text{peso} / \text{estatura}^2$).
2. **¿Por qué en la gráfica dual de `ProfileSection` la curva de Peso Corporal y la de 1RM se ven bien proporcionadas aunque una ronde los 70 kg y la otra los 160 kg?**
   - *Respuesta modelo:* Porque cada serie (`bwDots` y `rmDots`) calcula su propio rango `minV..maxV` y se normaliza de forma independiente dentro de la altura útil del lienzo SVG. Así el atleta compara la tendencia relativa de ambas curvas en paralelo sin que una quede aplastada abajo.
3. **¿Cómo logra `SettingsModal` cambiar el color de acento, el modo claro/oscuro y el idioma de toda la aplicación sin recargar la pantalla?**
   - *Respuesta modelo:* `SettingsModal` invoca `setMode`, `setAccent` (de `ThemeContext`) y `setLanguageMode` (de `LanguageContext`). Estos contextos actualizan su estado React —propagando inmediatamente los nuevos `colors` calculados por `buildThemeColors` y la función `t` a todos los componentes suscritos— y en paralelo guardan la preferencia en `AsyncStorage` bajo `@apex_gym_preferences`.
4. **¿Qué ventaja arquitectónica aporta haber dividido `EditItemModal` en `modals/edit-forms/`?**
   - *Respuesta modelo:* Evita un archivo monolítico de más de 1,370 líneas difícil de mantener. `EditItemModal` centraliza únicamente la cabecera, visibilidad, estado de guardado y botones Confirmar/Cancelar, mientras cada formulario (`EditEquipmentForm`, `EditExerciseForm`, `EditRoutineForm`, `EditMarcaForm`) encapsula su propia interfaz y validaciones particulares.
5. **¿Para qué sirve `ItemActionSheet` y qué particularidad tiene al transicionar hacia `EditItemModal` o `ConfirmDeleteModal`?**
   - *Respuesta modelo:* Es una hoja inferior animada con `Animated.spring` y respuesta háptica (`Vibration.vibrate(45)`) que unifica las opciones Editar y Eliminar para distintas entidades. Al pulsar una opción, primero llama a `onClose()` y espera `180 ms` con `setTimeout` antes de invocar `onEdit` u `onDelete`, evitando que dos `<Modal>` nativos se superpongan durante la animación de salida.
6. **¿Qué bug o detalle técnico detectaste en la integración entre `RoutineCard`, `ItemActionSheet` y `EditRoutineForm`?**
   - *Respuesta modelo:* En `ItemActionSheet.tsx` (líneas 173 y 216), tanto el botón de Editar como el de Eliminar tienen la condición `{itemType !== "routine" && ...}`. Como resultado, aunque `GymDashboard` abre `ItemActionSheet` al hacer *long-press* en una `RoutineCard` y existe `EditRoutineForm` completamente implementado dentro de `EditItemModal`, al usuario solo se le muestra el botón "Cancelar" en la hoja de acciones de rutinas.
7. **¿Cómo protege `ProfileSection` el botón "Auditar Directorio de Usuarios (API)"?**
   - *Respuesta modelo:* En la UI solo lo renderiza cuando `user?.is_staff && !isEditing`, y en `useGymDashboardData.ts` la función `loadAdminUsers` vuelve a verificar `requireAdmin()` antes de llamar a `api.getAdminUsers()` (`GET /auth/users/`).

---

## 9. Resumen para repasar

- **`ProfileSection`** ubica editar perfil arriba a la izquierda, ajustes arriba a la derecha, Log Out compacto abajo, normaliza estaturas cm→m para el IMC, audita usuarios si `is_staff` y dibuja la gráfica dual SVG Peso vs 1RM.
- **`EditProfileForm`** valida decimales compatibles con Django (`< 1000`), convierte cm→m (`50..280`) y sincroniza el registro de peso corporal al guardar.
- **`SettingsModal`** controla modo (`dark`/`light`/`system`), 5 acentos e idioma (`es`/`en`/`system`) persistidos en `AsyncStorage`.
- **`ItemActionSheet`**, **`EditItemModal`** (+ 4 formularios en `edit-forms/`) y **`ConfirmDeleteModal`** conforman una arquitectura CRUD reutilizable (con el detalle pendiente de habilitar `itemType === "routine"` en `ItemActionSheet`).
