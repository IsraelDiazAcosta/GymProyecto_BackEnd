# 05 · Sistema de Estilos, Temas, Componentes UI e Internacionalización (i18n)

## 1. Propósito

Este documento describe la capa visual, de componentes reutilizables y de traducción de **Apex Gym Hub**: cómo `theme.ts` y `global.css` construyen dinámicamente la paleta de colores para modo claro/oscuro y 5 colores de acento (`buildThemeColors`), cómo funcionan los 5 componentes base de UI (`GymIcon`, `AppButton`, `AppInput`, `AnimatedCard`, `AnimatedToast`), y cómo opera el sistema tipado de internacionalización (`src/i18n/*`) con detección automática de idioma del dispositivo e interpolación de parámetros `{{...}}`.

---

## 2. Ubicación

Archivos analizados bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\constants\theme.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\global.css`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\ui\GymIcon.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\ui\AppButton.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\ui\AppInput.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\ui\AnimatedCard.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\ui\AnimatedToast.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\i18n\index.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\i18n\types.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\i18n\es.ts`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\i18n\en.ts`

---

## 3. Cómo se conecta

```text
src/global.css (variables CSS web)
   │
   ▼
src/constants/theme.ts (ACCENT_PALETTES, DARK_BASE, LIGHT_BASE, buildThemeColors, Spacing, Radius)
   │
   ├──▶ ThemeContext.tsx ──▶ useAppTheme().colors
   │                            ├── AppButton, AppInput, AnimatedToast
   │                            └── Todas las pantallas y modales del Dashboard
   └──▶ preferences.ts (valida AccentId contra ACCENT_PALETTES)

src/i18n/types.ts + es.ts + en.ts
   │
   ▼
src/i18n/index.ts (DICTIONARIES, detectSystemLanguage, translate, mappers de dominio)
   │
   ├──▶ LanguageContext.tsx ──▶ useLanguage().t(key, params)
   └──▶ Helpers directos (getExperienceLevelLabel, getMuscleFocusLabel, etc.)
```

---

## 4. Componentes, funciones y variables clave

### 4.1. Sistema de diseño (`theme.ts` y `global.css`)
- **Tipos**: `ThemeMode` (`"dark" | "light" | "system"`), `ResolvedThemeMode` (`"dark" | "light"`), `AccentId` (`"emerald" | "ocean" | "amber" | "violet" | "crimson"`), `ThemeColors`, `AccentPaletteConfig`, `AccentPaletteVariant`.
- **Constantes**: `Palette`, `ACCENT_PALETTES`, `ACCENT_LIST`, `DARK_BASE`, `LIGHT_BASE`, `Colors`, `Fonts`, `Spacing`, `Radius`, `BottomTabInset`, `MaxContentWidth` (`800`).
- **Función clave**: `buildThemeColors(mode, accent)`.

### 4.2. Componentes UI (`src/components/ui/*`)
- **`GymIcon`**: Props `name: IconName` (50 iconos disponibles), `size = 20`, `color = "#10B981"`, `strokeWidth = 2`, `fill?`.
- **`AppButton`**: Props `title`, `onPress`, `variant` (`"primary" | "secondary" | "outline" | "danger"`), `loading`, `disabled`, `style`, `icon`.
- **`AppInput`**: Extiende `TextInputProps`; añade `label`, `error`, `leftIcon`.
- **`AnimatedCard`**: Props `children`, `style`, `delay?` *(declarada en la interfaz pero sin uso interno)*, `onPress?`, `disabled`.
- **`AnimatedToast`**: Props `toast: ToastConfig` (`visible`, `type`, `title`, `message`, `code?`) y `onHide`.

### 4.3. Internacionalización (`src/i18n/*`)
- **`types.ts`**: `LanguageMode` (`"es" | "en" | "system"`), `ResolvedLanguage` (`"es" | "en"`), `TranslationParams`.
- **`es.ts`**: diccionario maestro en español (`598` líneas); exporta `TranslationKey = keyof typeof es` y `TranslationDictionary`.
- **`en.ts`**: diccionario en inglés (`585` líneas) tipado como `TranslationDictionary`.
- **`index.ts`**: `DICTIONARIES`, `LOCALE_MAP`, `WEEK_DAYS_BY_LANG`, `MONTHS_SHORT_BY_LANG`, `detectSystemLanguage()`, `translate(lang, key, params?)`, y 5 mappers de dominio (`getExperienceLevelLabel`, `getTrainingGoalLabel`, `getEquipmentTypeLabel`, `getMuscleFocusLabel`, `getAccentMeta`).

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. `theme.ts` y `global.css`: `buildThemeColors` y tokens

```ts
export function buildThemeColors(
  mode: ResolvedThemeMode,
  accent: AccentId = "emerald",
): ThemeColors {
  const base = mode === "dark" ? DARK_BASE : LIGHT_BASE;
  const accentVariant = (ACCENT_PALETTES[accent] ?? ACCENT_PALETTES.emerald)[
    mode
  ];
  return {
    ...base,
    ...accentVariant,
  };
}
```

- **Separación Base vs Acento**:
  - `DARK_BASE` usa superficies carbón neutras (`#0A0A0A`, `#141414`, `#1F1F1F`) y texto blanco `#FFFFFF`, mientras que `LIGHT_BASE` usa fondos claros (`#F4F6F8`, `#FFFFFF`, `#EEF1F5`) y texto oscuro `#0F172A`.
  - Cada una de las 5 paletas de `ACCENT_PALETTES` (`emerald`, `ocean`, `amber`, `violet`, `crimson`) define tonos calibrados por separado para `dark` y `light` (por ejemplo, en `emerald`: `#10B981` en oscuro vs `#047857` en claro para preservar contraste WCAG sobre fondos blancos).
  - `buildThemeColors` combina ambos objetos mediante *spread*, produciendo un objeto `ThemeColors` completo y consistente sin importar qué combinación elija el usuario.
- **`global.css` y `Fonts`**: `theme.ts` importa `@/global.css`, que define en `:root` las variables CSS `--font-display`, `--font-mono`, `--font-rounded` y `--font-serif` utilizadas en `Platform.select({ web: ... })`.
- **`Spacing` y `Radius`**: escala consistente de espaciados (`half: 2`, `one: 4`, `two: 8`, `three: 16`, `four: 24`, `five: 32`, `six: 64`) y radios (`sm: 8`, `md: 12`, `lg: 16`, `xl: 22`, `pill: 999`).

### 5.2. `GymIcon.tsx`: galería de 50 iconos SVG

```tsx
export function GymIcon({
  name,
  size = 20,
  color = "#10B981",
  strokeWidth = 2,
  fill,
}: GymIconProps) {
  const commonProps = {
    stroke: color,
    strokeWidth,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none" as const,
  };
  ...
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {renderPaths()}
    </Svg>
  );
}
```

- Reemplaza el uso de emojis por **50 iconos vectoriales nítidos** sobre `react-native-svg` (`Svg`, `Path`, `Circle`, `Rect`, `Line`, `Polyline`) en un lienzo estándar `viewBox="0 0 24 24"`, garantizando idéntica apariencia en iOS, Android y Web.
- Permite relleno dinámico en casos específicos: `"heart"` usa `fill={fill ?? "none"}` para mostrarse vacío o relleno al marcar favoritos; `"play"` usa `fill={color} fillOpacity={0.18}`; `"more-vertical"` y los puntos de `"palette"` usan `fill={color}`.
- Si recibiera un nombre desconocido en tiempo de ejecución, el `default:` renderiza un círculo neutro seguro.

### 5.3. `AppButton.tsx`: botón con variantes y rebote elástico

```tsx
  const handlePressIn = () => {
    if (isDisabled) return;
    Animated.spring(scaleAnim, {
      toValue: 0.97,
      damping: 15,
      stiffness: 300,
      useNativeDriver: true,
    }).start();
  };
```

- Soporta 4 variantes visuales (`primary`, `secondary`, `outline`, `danger`), sombra dinámica ajustada según `resolvedMode`, indicador de carga (`ActivityIndicator`) que reemplaza al contenido mientras bloquea pulsaciones (`isDisabled = disabled || loading`), e icono opcional vía `GymIcon`.
- La micro-animación al tocar comprime suavemente la escala a `0.97` con `useNativeDriver: true` y regresa a `1` en `onPressOut`.

### 5.4. `AppInput.tsx`: estabilidad de foco de teclado

```tsx
export function AppInput({
  label,
  error,
  style,
  leftIcon,
  secureTextEntry,
  ...rest
}: AppInputProps) {
  const { colors } = useAppTheme();
  const [hidePassword, setHidePassword] = useState(Boolean(secureTextEntry));

  return (
    <View style={styles.container} collapsable={false}>
      <Text style={[styles.label, { color: colors.textSecondary }]}>
        {label}
      </Text>
      <View
        collapsable={false}
        style={[
          styles.inputWrapper,
          {
            backgroundColor: colors.backgroundElevated,
            borderColor: error ? colors.danger : colors.border,
          },
        ]}
      >
        ...
        <TextInput ... />
        {secureTextEntry && (
          <Pressable onPress={() => setHidePassword((prev) => !prev)} ...>
            <GymIcon name={hidePassword ? "eye" : "eye-off"} ... />
          </Pressable>
        )}
      </View>
```

- **Decisión técnica clave contra bugs de teclado en Android/iOS**: usa `collapsable={false}` en ambos contenedores `View` y **evita cambiar estado en `onFocus`/`onBlur`** (como resaltar el borde vía `useState`). En React Native sobre Android, reestructurar la jerarquía nativa durante `onFocus` puede provocar que el `TextInput` pierda el foco y cierre el teclado inmediatamente.
- Cuando se pasa `secureTextEntry`, renderiza automáticamente un botón ocular (`"eye"` / `"eye-off"`) para alternar visibilidad de la contraseña.

### 5.5. `AnimatedCard.tsx`: tarjeta híbrida interactiva o de formulario

```tsx
  if (onPress) {
    return (
      <Animated.View style={{ transform: [{ scale }] }}>
        <Pressable
          onPress={onPress}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          disabled={disabled}
          style={style}
        >
          {children}
        </Pressable>
      </Animated.View>
    );
  }

  return (
    <View collapsable={false} style={style}>
      {children}
    </View>
  );
```

- Si recibe `onPress`, envuelve el contenido en `Animated.View` + `Pressable` con efecto de presión (`0.985`).
- Si se usa como tarjeta contenedora de formularios (sin `onPress`), devuelve un `View` estable con `collapsable={false}` por la misma razón que `AppInput`: proteger el foco del teclado en los campos internos.
- **Detalle menor**: la prop opcional `delay?: number` está declarada en `AnimatedCardProps`, pero no se utiliza en la implementación actual.

### 5.6. `AnimatedToast.tsx`: notificaciones animadas con barra de progreso

```tsx
  useEffect(() => {
    if (toast.visible) {
      progress.setValue(1);

      Animated.parallel([
        Animated.spring(translateY, { toValue: 0, friction: 7, tension: 75, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 220, useNativeDriver: true }),
        Animated.spring(scale, { toValue: 1, friction: 6, tension: 85, useNativeDriver: true }),
      ]).start();

      Animated.timing(progress, {
        toValue: 0,
        duration: 3800,
        useNativeDriver: false,
      }).start();

      const timer = setTimeout(() => {
        dismissToast();
      }, 3800);

      return () => clearTimeout(timer);
    }
  }, [toast.visible, toast.title, toast.message]);
```

- Se renderiza en la parte superior (`top: 52`, `zIndex: 9999`) con 4 temas según `toast.type` (`success`, `error`, `warning`, `info`) mapeados en `getToastTheme`.
- Combina entrada paralela en hilo nativo (`translateY`, `opacity`, `scale` con `useNativeDriver: true`) y una barra de progreso descendente de `3800 ms` (`width` interpolado de `"0%"` a `"100%"`, que requiere `useNativeDriver: false` porque las propiedades de layout como `width` no corren en el driver nativo).
- Permite cierre manual al pulsar cualquier parte de la tarjeta (`dismissToast()`), ejecutando la animación de salida antes de llamar a `onHide()`.

### 5.7. Sistema i18n (`types.ts`, `es.ts`, `en.ts`, `index.ts`)

En `es.ts`:
```ts
export const es = {
  ...
  "header.greeting": "Hola, {{username}}",
  ...
} as const;

export type TranslationKey = keyof typeof es;
export type TranslationDictionary = Record<TranslationKey, string>;
```

En `en.ts`:
```ts
import type { TranslationDictionary } from "./es";

export const en: TranslationDictionary = {
  ...
};
```

- **Seguridad en tiempo de compilación**: como `en` debe cumplir `TranslationDictionary` (derivado de `keyof typeof es`), TypeScript detecta inmediatamente si falta o sobra alguna clave de traducción en inglés.

En `src/i18n/index.ts`:
```ts
export function detectSystemLanguage(): ResolvedLanguage {
  try {
    const resolvedLocale = Intl.DateTimeFormat().resolvedOptions().locale;
    if (
      typeof resolvedLocale === "string" &&
      resolvedLocale.toLowerCase().startsWith("en")
    ) {
      return "en";
    }
  } catch {
    // Fallback seguro a español si Intl no está disponible
  }
  return "es";
}

export function translate(
  lang: ResolvedLanguage,
  key: TranslationKey,
  params?: TranslationParams,
): string {
  const dict = DICTIONARIES[lang] ?? DICTIONARIES.es;
  let template = dict[key] ?? DICTIONARIES.es[key] ?? String(key);
  if (params) {
    for (const [paramKey, paramValue] of Object.entries(params)) {
      template = template.replace(
        new RegExp(`\\{\\{${paramKey}\\}\\}`, "g"),
        String(paramValue),
      );
    }
  }
  return template;
}
```

- **`translate()`**: busca la clave en el diccionario activo, cae al español como respaldo si no existiera, o a la propia clave como último recurso; después reemplaza todas las ocurrencias de `{{paramKey}}` usando una expresión regular global.
- **Mappers de dominio**: funciones como `getExperienceLevelLabel`, `getTrainingGoalLabel`, `getEquipmentTypeLabel`, `getMuscleFocusLabel` y `getAccentMeta` traducen valores técnicos internos de la base de datos (por ejemplo `"plate_loaded"`, `"hypertrophy"`, `"pecho"`) a etiquetas legibles en español o inglés sin modificar los valores técnicos enviados al backend.

---

## 6. Flujo paso a paso (Cómo un cambio de tema o idioma actualiza toda la UI)

1. El usuario elige en Ajustes el modo `"light"`, acento `"ocean"` e idioma `"en"`.
2. `ThemeContext.setMode("light")` y `setAccent("ocean")` guardan en `@apex_gym_preferences` (`preferencesStorage`) y ejecutan `buildThemeColors("light", "ocean")`.
3. `LanguageContext.setLanguageMode("en")` actualiza `language` a `"en"` y regenera la función `t` memorizada.
4. Todos los componentes conectados (`AppButton`, `AppInput`, `AnimatedToast`, `GymIcon`, `GymDashboard`) se re-renderizan automáticamente leyendo `colors` y llamando a `t(key, params)` con interpolación dinámica.

---

## 7. Conceptos y términos técnicos

- **Design Tokens**: conjunto centralizado de valores visuales reutilizables (`Spacing`, `Radius`, `Colors`, `Fonts`) que evitan "números mágicos" o colores repetidos en cada pantalla.
- **WCAG / Contraste adaptativo**: práctica de ajustar los tonos de color (`swatchDark` vs `swatchLight`) para que texto e iconos sigan siendo legibles tanto sobre fondo negro (`#0A0A0A`) como blanco (`#FFFFFF`).
- **`useNativeDriver`**: opción de React Native `Animated` que serializa la animación para ejecutarla en el hilo nativo (propiedades `transform`, `opacity`), siendo obligatoria en `false` cuando se animan propiedades de diseño como `width`.
- **View Flattening (`collapsable={false}`)**: optimización de Android donde React Native elimina vistas `View` vacías del árbol nativo; desactivarla con `collapsable={false}` estabiliza los `TextInput` para evitar pérdida de foco del teclado.
- **Interpolación i18n (`{{variable}}`)**: sustitución dinámica de marcadores dentro de cadenas traducidas para respetar el orden gramatical de cada idioma.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo está diseñado `theme.ts` para soportar 5 colores de acento en modo claro y oscuro sin duplicar paletas enteras?**
   - *Respuesta modelo:* Separa las superficies neutras (`DARK_BASE` y `LIGHT_BASE`) de las variantes de acento (`ACCENT_PALETTES[accent][mode]`). La función `buildThemeColors(resolvedMode, accent)` fusiona ambos objetos dinámicamente, asegurando contraste adecuado en cada combinación.
2. **¿Por qué `GymIcon.tsx` dibuja los iconos con `react-native-svg` en vez de usar emojis o archivos PNG?**
   - *Respuesta modelo:* Los emojis se renderizan distinto según la versión de Android, iOS o Windows, y los PNG pierden nitidez al escalar. Usar trazos SVG vectoriales sobre `viewBox="0 0 24 24"` permite cambiar `size`, `color`, `strokeWidth` y `fill` dinámicamente con nitidez perfecta en todas las plataformas.
3. **¿Por qué `AppInput` y `AnimatedCard` utilizan `collapsable={false}` y evitan `onFocus` con estado en `AppInput`?**
   - *Respuesta modelo:* Para prevenir un fallo conocido en Android/iOS donde re-renderizar o colapsar vistas padre al enfocar un `TextInput` provoca que el teclado virtual se cierre solo inmediatamente después de abrirse.
4. **¿Por qué en `AnimatedToast.tsx` las animaciones de entrada usan `useNativeDriver: true` pero la barra de progreso usa `useNativeDriver: false`?**
   - *Respuesta modelo:* El driver nativo solo soporta transformaciones (`translateY`, `scale`) y `opacity`. Como la barra de progreso anima la propiedad de layout `width` interpolada de `"0%"` a `"100%"`, React Native exige `useNativeDriver: false` para esa animación en particular.
5. **¿Cómo garantiza el proyecto en TypeScript que no falte ninguna traducción al agregar texto en español?**
   - *Respuesta modelo:* `src/i18n/es.ts` exporta `TranslationKey = keyof typeof es` y `TranslationDictionary = Record<TranslationKey, string>`. El archivo `en.ts` está tipado explícitamente como `: TranslationDictionary`, de modo que si se agrega una clave en `es.ts` y se olvida en `en.ts`, TypeScript marca error de compilación.
6. **¿Cómo funciona `translate()` cuando recibe parámetros dinámicos y qué pasa si falta una traducción?**
   - *Respuesta modelo:* Busca la clave en `DICTIONARIES[lang]`; si no existe, hace fallback a `DICTIONARIES.es[key]` y finalmente a `String(key)`. Luego recorre `params` y reemplaza cada marcador `{{paramKey}}` mediante una expresión regular global.

---

## 9. Resumen para repasar

- **`buildThemeColors(mode, accent)`** combina superficies neutras (`DARK_BASE` / `LIGHT_BASE`) con una de las 5 paletas (`emerald`, `ocean`, `amber`, `violet`, `crimson`).
- **`GymIcon`** provee 50 iconos SVG consistentes sin depender de emojis del sistema operativo.
- **`AppButton`, `AppInput`, `AnimatedCard` y `AnimatedToast`** encapsulan micro-animaciones, variantes del tema y estabilidad de teclado (`collapsable={false}`).
- **i18n con tipado estricto**: `es.ts` define el contrato `TranslationDictionary` que `en.ts` debe satisfacer, con `detectSystemLanguage()` e interpolación `{{...}}`.
