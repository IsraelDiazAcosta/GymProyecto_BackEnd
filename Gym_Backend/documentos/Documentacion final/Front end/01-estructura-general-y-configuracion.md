# 01 · Estructura General, Configuración y Flujo de Arranque

## 1. Propósito

Este documento explica cómo está estructurado, configurado y arrancado el proyecto Front End de **Apex Gym Hub** (`Gym_FrontEnd`). Cubre desde las dependencias y scripts en `package.json`, la configuración multiplataforma de Expo (`app.json`), la resolución estricta de TypeScript y alias de rutas (`tsconfig.json`), las variables de entorno de desarrollo (`.env.example` y `.env`), hasta el árbol raíz de navegación, la jerarquía de *Context Providers*, la pantalla de entrada (`index.tsx`) y la transición desde la pantalla *splash* nativa hacia la interfaz animada (`animated-icon.tsx` / `animated-icon.web.tsx`).

---

## 2. Ubicación

Todos los archivos analizados pertenecen al proyecto ubicado en `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\package.json`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\app.json`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\tsconfig.json`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\.env.example`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\.env`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\app\_layout.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\app\index.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\app\explore.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\animated-icon.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\animated-icon.web.tsx`

---

## 3. Cómo se conecta

```text
package.json ("main": "expo-router/entry")
   │
   ▼
app.json (scheme: "gymfrontend", plugins: expo-router & expo-splash-screen)
   │
   ▼
src/app/_layout.tsx  ──(detiene ocultamiento automático con SplashScreen.preventAutoHideAsync)
   ├── AppThemeProvider        (tema oscuro/claro/sistema + paleta de acento)
   │     └── LanguageProvider  (idioma es/en/sistema + función t())
   │           └── RootLayoutContent
   │                 └── ThemeProvider (expo-router) + StatusBar
   │                       └── AuthProvider (sesión JWT y usuario en AsyncStorage)
   │                             ├── AnimatedSplashOverlay (.tsx en móvil / .web.tsx -> null en web)
   │                             └── HomeScreen (src/app/index.tsx)
   │                                   ├── isLoading === true  ──▶ Pantalla de carga sincronizando
   │                                   ├── user !== null       ──▶ GymDashboard (5 pestañas)
   │                                   └── user === null       ──▶ LoginForm (Iniciar Sesión / Registrarse)
```

> **Observación arquitectónica importante:** Aunque `package.json` usa `expo-router/entry` y `app.json` declara el plugin `expo-router`, el archivo `src/app/_layout.tsx` **no renderiza `<Slot />`, `<Stack />` ni `<Tabs />`**. En su lugar, importa y renderiza directamente `<HomeScreen />` (`src/app/index.tsx`). Como consecuencia, toda la navegación interna ocurre mediante el estado `activeTab` dentro de `GymDashboard`, dejando a `src/app/explore.tsx` (proveniente de la plantilla inicial de Expo) como una ruta **inalcanzable / código heredado sin uso**.

---

## 4. Componentes, funciones y variables clave

| Archivo | Elemento | Tipo / Rol | Descripción |
| :--- | :--- | :--- | :--- |
| `package.json` | `"main"` | Punto de entrada | Apunta a `"expo-router/entry"`, que inicia Expo Router buscando `src/app/_layout.tsx`. |
| `app.json` | `expo.plugins` | Plugins Expo | Registra `expo-router` y `expo-splash-screen` (fondo `#208AEF`, imagen `splash-icon.png`, ancho `76`). |
| `app.json` | `expo.experiments` | Flags experimentales | Activa `typedRoutes: true` y `reactCompiler: true`. |
| `tsconfig.json` | `compilerOptions.paths` | Alias de importación | Mapea `@/*` a `./src/*` y `@/assets/*` a `./assets/*` con modo `strict: true`. |
| `.env` / `.env.example` | `EXPO_PUBLIC_DEV_PC_IP` | Variable pública | Define la IP LAN de la PC donde corre Django para pruebas desde dispositivos físicos en la misma red Wi-Fi. |
| `src/app/_layout.tsx` | `RootLayout` | Componente raíz | Anida `AppThemeProvider` y `LanguageProvider` alrededor de `RootLayoutContent`. |
| `src/app/_layout.tsx` | `RootLayoutContent` | Subcomponente | Construye `navigationTheme` con `useMemo`, monta `ThemeProvider`, `StatusBar`, `AuthProvider`, `AnimatedSplashOverlay` y `HomeScreen`. |
| `src/app/index.tsx` | `HomeScreen` | Pantalla principal | Decide entre vista de carga (`isLoading`), `GymDashboard` (`user` autenticado) o `LoginForm` (visitante). |
| `src/app/explore.tsx` | `TabTwoScreen` | Pantalla plantilla | Pantalla de ejemplo del template inicial de Expo; no se navega hacia ella desde `_layout.tsx`. |
| `src/components/animated-icon.tsx` | `AnimatedSplashOverlay` | Overlay nativo | Oculta el splash nativo en `onLayout`, ejecuta `splashKeyframe` (600 ms) y se desmonta usando `scheduleOnRN`. |
| `src/components/animated-icon.web.tsx` | `AnimatedSplashOverlay` | Stub web | Retorna `null` para evitar overlay bloqueante en navegador web. |
| `src/components/animated-icon*.tsx` | `AnimatedIcon` | Componente plantilla | Logo animado con brillo giratorio (`glowKeyframe`); heredado del template y actualmente no renderizado en la app. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. `package.json`: dependencias principales y scripts

```json
{
  "name": "gym_frontend",
  "version": "1.0.0",
  "main": "expo-router/entry",
  "dependencies": {
    "@react-native-async-storage/async-storage": "2.2.0",
    "expo": "~58.0.17",
    "expo-constants": "~58.0.13",
    "expo-image": "~58.0.16",
    "expo-image-manipulator": "^58.0.16",
    "expo-image-picker": "^58.0.10",
    "expo-router": "~58.0.25",
    "expo-splash-screen": "~58.0.11",
    "expo-status-bar": "~58.0.4",
    "expo-system-ui": "~58.0.6",
    "react": "19.3.0",
    "react-native": "0.88.0",
    "react-native-reanimated": "4.7.1",
    "react-native-safe-area-context": "~5.10.1",
    "react-native-svg": "15.16.0",
    "react-native-worklets": "0.13.0"
  }
}
```

- **`"main": "expo-router/entry"`**: indica a Metro Bundler que el punto de arranque no es un `App.tsx` clásico, sino el enrutador de Expo Router que lee la carpeta `src/app/`.
- **Ecosistema Expo SDK 58 + React 19.3 + RN 0.88**: integra librerías nativas clave para el proyecto:
  - `@react-native-async-storage/async-storage`: persistencia local de sesión JWT y preferencias.
  - `expo-image-picker` y `expo-image-manipulator`: captura/selección y compresión de fotografías de equipos y ejercicios.
  - `expo-constants`: lectura de `hostUri` en tiempo de desarrollo para detectar la IP LAN del servidor.
  - `react-native-svg`: renderizado de iconos vectoriales (`GymIcon`) y gráficas biométricas/1RM.
  - `react-native-reanimated` y `react-native-worklets`: animaciones en hilo nativo (UI thread), utilizadas en la transición de splash.
- **Detalle técnico detectado**: aparece `"exp": "^57.2.1"` en `dependencies`, un paquete residual que no es requerido por el código fuente del proyecto.
- **Scripts disponibles**: `start` (`expo start`), `android`, `ios`, `web` (`expo start --web`), `lint` (`expo lint`) y `reset-project`.

### 5.2. `app.json`: identidad, plataforma y splash nativo

```json
{
  "expo": {
    "name": "Gym_FrontEnd",
    "slug": "Gym_FrontEnd",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/images/icon.png",
    "scheme": "gymfrontend",
    "userInterfaceStyle": "automatic",
    "android": {
      "package": "com.tacoguapodiaz.Gym_FrontEnd",
      "predictiveBackGestureEnabled": false
    },
    "web": {
      "output": "static",
      "favicon": "./assets/images/favicon.png"
    },
    "plugins": [
      "expo-router",
      [
        "expo-splash-screen",
        {
          "backgroundColor": "#208AEF",
          "image": "./assets/images/splash-icon.png",
          "imageWidth": 76
        }
      ]
    ],
    "experiments": {
      "typedRoutes": true,
      "reactCompiler": true
    }
  }
}
```

- **`orientation: "portrait"`**: bloquea la orientación vertical en móviles para mantener la legibilidad de tablas de series, formularios y tarjetas.
- **`scheme: "gymfrontend"`**: esquema de *deep linking* exigido por Expo Router.
- **`userInterfaceStyle: "automatic"`**: permite que la app reciba el tema del sistema operativo (necesario para que el modo `"system"` en `ThemeContext` funcione correctamente en iOS y Android).
- **`web.output: "static"`**: configura exportación estática para despliegues web.
- **`expo-splash-screen`**: define el color `#208AEF` e imagen de ancho `76`, valores idénticos al `AnimatedSplashOverlay` en `animated-icon.tsx` (`#208AEF` y `width: 76`) para que el paso del splash nativo al componente React sea imperceptible.
- **`experiments.reactCompiler: true`**: habilita el compilador de React 19 para optimización automática de renderizados.

### 5.3. `tsconfig.json`: tipado estricto y alias `@/*`

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": [
        "./src/*"
      ],
      "@/assets/*": [
        "./assets/*"
      ]
    }
  },
  "include": [
    "**/*.ts",
    "**/*.tsx",
    ".expo/types/**/*.ts",
    "expo-env.d.ts"
  ]
}
```

- **`"strict": true`**: obliga a validar nulos (`null`/`undefined`), tipos implícitos y firmas de funciones en todo el proyecto.
- **`paths`**: evita rutas relativas frágiles tipo `../../../services/api`. Cualquier módulo puede importarse limpiamente como `@/services/api`, `@/context/AuthContext` o `@/assets/images/expo-logo.png`.
- **`include`**: incluye `.expo/types/**/*.ts` y `expo-env.d.ts` para soporte de rutas tipadas y variables `EXPO_PUBLIC_*`.

### 5.4. `.env.example` y `.env`: configuración de red local

En `.env.example`:

```env
EXPO_PUBLIC_DEV_PC_IP=192.168.100.7
```

- El proyecto sigue la convención de Expo de exponer al bundle cliente únicamente variables prefijadas con **`EXPO_PUBLIC_`**.
- Tanto `.env.example` (plantilla versionable de referencia) como `.env` (archivo local activo) contienen únicamente la variable `EXPO_PUBLIC_DEV_PC_IP` con una IP privada de red local (LAN) para conectar dispositivos Android/iOS reales con el backend Django durante desarrollo. **No existen contraseñas, llaves secretas ni credenciales sensibles en `.env`.**

### 5.5. `src/app/_layout.tsx`: SplashScreen, Providers y RootLayout

```tsx
SplashScreen.preventAutoHideAsync();

function RootLayoutContent() {
  const { resolvedMode, colors } = useAppTheme();

  const navigationTheme = useMemo(() => {
    const base = resolvedMode === "dark" ? DarkTheme : DefaultTheme;
    return {
      ...base,
      colors: {
        ...base.colors,
        background: colors.background,
        card: colors.backgroundElement,
        text: colors.text,
        border: colors.borderSubtle,
        primary: colors.primary,
      },
    };
  }, [resolvedMode, colors]);

  return (
    <ThemeProvider value={navigationTheme}>
      <StatusBar style={resolvedMode === "dark" ? "light" : "dark"} animated />
      <AuthProvider>
        <AnimatedSplashOverlay />
        <HomeScreen />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default function RootLayout() {
  return (
    <AppThemeProvider>
      <LanguageProvider>
        <RootLayoutContent />
      </LanguageProvider>
    </AppThemeProvider>
  );
}
```

- **Línea 12 (`SplashScreen.preventAutoHideAsync()`)**: se ejecuta fuera de los componentes (al cargar el módulo) para impedir que el sistema operativo oculte la pantalla de arranque antes de que `AppThemeProvider`, `LanguageProvider` y el árbol inicial estén montados.
- **Jerarquía de Providers**:
  1. `AppThemeProvider` (nivel más externo): carga de `AsyncStorage` el modo de pantalla y paleta de acento.
  2. `LanguageProvider`: carga el idioma elegido (`es`, `en` o `system`) para que toda la UI, incluyendo la pantalla de carga de autenticación, ya disponga de `t()`.
  3. `RootLayoutContent`: ya puede consumir `useAppTheme()` porque está dentro de `AppThemeProvider`. Construye `navigationTheme` memorizado con `useMemo` adaptando `DarkTheme`/`DefaultTheme` de `expo-router` a los colores activos de la app.
  4. `ThemeProvider` y `StatusBar`: sincronizan los colores base de navegación y el color de los iconos de la barra de estado del teléfono (`"light"` sobre fondo oscuro, `"dark"` sobre fondo claro).
  5. `AuthProvider`: restaura la sesión JWT almacenada e inyecta `user`, `login`, `register` y `logout`.
  6. `AnimatedSplashOverlay` + `HomeScreen`: la capa animada se superpone al `HomeScreen` mientras oculta el splash nativo y luego se desvanece.

### 5.6. `src/app/index.tsx`: `HomeScreen` y bifurcación por estado de sesión

```tsx
export default function HomeScreen() {
  const { user, isLoading } = useAuth();
  const { colors } = useAppTheme();
  const { t } = useLanguage();

  if (isLoading) {
    return (
      <SafeAreaView
        style={[styles.safeArea, { backgroundColor: colors.background }]}
      >
        <View style={styles.centerContainer}>
          <View
            style={[
              styles.loaderBadge,
              {
                backgroundColor: colors.primaryGlow,
                borderColor: colors.border,
              },
            ]}
          >
            <GymIcon name="dumbbell" size={32} color={colors.primary} />
          </View>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            {t("auth.syncingPlatform")}
          </Text>
        </View>
      </SafeAreaView>
    );
  }
```

- **Estado 1 (`isLoading === true`)**: mientras `AuthProvider` consulta `AsyncStorage` y valida el perfil contra `/auth/profile/`, muestra un emblema con icono vectorial `dumbbell`, un `ActivityIndicator` y el texto traducido `auth.syncingPlatform`.

```tsx
  if (user) {
    return (
      <SafeAreaView
        edges={["top", "left", "right"]}
        style={[styles.safeArea, { backgroundColor: colors.background }]}
      >
        <GymDashboard />
      </SafeAreaView>
    );
  }
```

- **Estado 2 (`user` presente)**: monta `GymDashboard` dentro de `SafeAreaView` protegiendo únicamente los bordes `["top", "left", "right"]`. El borde inferior (`bottom`) se excluye intencionalmente porque `DashboardTabBar` gestiona su propio `useSafeAreaInsets().bottom` al estar fijado en la parte inferior.

```tsx
  return (
    <SafeAreaView
      style={[styles.safeArea, { backgroundColor: colors.background }]}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        enabled={Platform.OS === "ios"}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="always"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.headerBlock}>
            <Text style={[styles.kicker, { color: colors.primary }]}>
              {t("auth.systemKicker")}
            </Text>
            <Text style={[styles.brandTitle, { color: colors.text }]}>
              {t("auth.brandTitle")}
            </Text>
          </View>

          <LoginForm />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
```

- **Estado 3 (sin usuario)**: renderiza el encabezado de marca y `<LoginForm />`.
  - `KeyboardAvoidingView` se habilita solo en iOS (`enabled={Platform.OS === "ios"}`), evitando conflictos con el ajuste nativo de teclado en Android (`adjustResize`).
  - `keyboardShouldPersistTaps="always"` garantiza que tocar botones o cambiar de campo dentro del `ScrollView` no requiera dos toques cuando el teclado está abierto.

### 5.7. `src/app/explore.tsx`: archivo plantilla no utilizado

```tsx
export default function TabTwoScreen() {
  const safeAreaInsets = useSafeAreaInsets();
  ...
  const theme = useTheme();
```

- Es la segunda pantalla de ejemplo incluida cuando se crea un proyecto Expo con `tabs` (`"This starter app includes example code to help you get started"`).
- Importa `@/hooks/use-theme`, `@/components/themed-text`, `@/components/themed-view`, `@/components/ui/collapsible` y `@/components/web-badge`.
- Dado que `src/app/_layout.tsx` no declara un navegador de archivos (`<Tabs>` o `<Stack>`), esta pantalla **nunca se muestra al usuario final** en la aplicación actual.

### 5.8. `src/components/animated-icon.tsx` vs `src/components/animated-icon.web.tsx`

En **nativo** (`animated-icon.tsx`):

```tsx
export function AnimatedSplashOverlay() {
  const [animate, setAnimate] = useState(false);
  const [visible, setVisible] = useState(true);

  if (!visible) return null;
  ...
  return animate ? (
    <Animated.View
      entering={splashKeyframe.duration(DURATION).withCallback((finished) => {
        'worklet';
        if (finished) {
          scheduleOnRN(setVisible, false);
        }
      })}
      style={styles.splashOverlay}>
      {image}
    </Animated.View>
  ) : (
    <View
      onLayout={() => {
        SplashScreen.hideAsync().finally(() => {
          setAnimate(true);
        });
      }}
      style={styles.splashOverlay}>
      {image}
    </View>
  );
}
```

- **Resolución específica por plataforma**: Metro/Expo selecciona automáticamente `animated-icon.web.tsx` al compilar para Web y `animated-icon.tsx` para Android/iOS.
- **Mecánica en móvil**:
  1. Primero renderiza un `View` idéntico al splash nativo (`backgroundColor: '#208AEF'`, `...StyleSheet.absoluteFill`, `zIndex: 1000`).
  2. Cuando el `View` termina de medirse en pantalla (`onLayout`), llama a `SplashScreen.hideAsync()` para retirar el splash del sistema operativo y cambia `animate` a `true`.
  3. Al cambiar a `animate === true`, se monta `<Animated.View entering={splashKeyframe.duration(600)...}>`, que mantiene opacidad `1` hasta el `20%` y desvanece a `0` al `70%`.
  4. Al concluir el *worklet* en el hilo de UI, invoca `scheduleOnRN(setVisible, false)` (de `react-native-worklets`) para desmontar definitivamente el overlay en el hilo JS.
- **En Web (`animated-icon.web.tsx`)**:

```tsx
export function AnimatedSplashOverlay() {
  return null;
}
```

  No existe splash nativo del sistema operativo que ocultar en navegador, por lo que `AnimatedSplashOverlay` retorna `null` inmediatamente. Además, su versión de `AnimatedIcon` usa `<div className={classes.expoLogoBackground} />` con CSS modules (`animated-icon.module.css`), ya que `experimental_backgroundImage` de `StyleSheet` es específico de la contraparte nativa/Reanimated.

---

## 6. Flujo paso a paso (Arranque completo de la aplicación)

1. **Inicio del runtime**: Expo carga `expo-router/entry` (`package.json`), lee `app.json` y muestra el splash nativo azul (`#208AEF`) con `splash-icon.png`.
2. **Carga del módulo raíz (`_layout.tsx`)**: se invoca `SplashScreen.preventAutoHideAsync()` para mantener congelado el splash nativo mientras se inicializa React.
3. **Montaje de contextos globales**: `RootLayout` monta `AppThemeProvider` (tema y acento) y `LanguageProvider` (idioma), que comienzan a leer `@apex_gym_preferences` desde `AsyncStorage`.
4. **Montaje de contenido y sesión**: `RootLayoutContent` construye el tema de navegación y monta `AuthProvider`, `AnimatedSplashOverlay` y `HomeScreen`.
5. **Liberación del splash nativo**:
   - En iOS/Android, cuando el `View` de `AnimatedSplashOverlay` dispara `onLayout`, ejecuta `SplashScreen.hideAsync()`, activa la animación de desvanecimiento de `600 ms` y luego retorna `null`.
   - En Web, `AnimatedSplashOverlay` retorna `null` desde el inicio.
6. **Validación de sesión**: en paralelo, `AuthProvider` lee el token y usuario guardados en `AsyncStorage` y valida la sesión con `api.getProfile()`.
7. **Renderizado de destino en `HomeScreen`**:
   - Mientras verifica la sesión (`isLoading`), muestra el indicador de carga.
   - Si el token es válido y existe `user`, muestra `<GymDashboard />`.
   - Si no hay sesión válida, muestra `<LoginForm />`.

---

## 7. Conceptos y términos técnicos

- **Expo Router**: librería de enrutamiento para Expo basada en archivos dentro de `src/app/` (en este proyecto configurada como punto de entrada, aunque `_layout.tsx` delega la navegación interna a `GymDashboard`).
- **Context Provider**: componente de React (`AppThemeProvider`, `LanguageProvider`, `AuthProvider`) que almacena estado compartido y lo distribuye a cualquier componente hijo sin tener que pasar *props* manualmente nivel por nivel.
- **Alias de TypeScript (`@/*`)**: atajo configurado en `tsconfig.json` para escribir rutas absolutas respecto a `src/` (por ejemplo, `@/services/api`) en lugar de rutas relativas largas.
- **Resolución de archivos por plataforma (`.web.tsx`)**: convención del empaquetador Metro mediante la cual `import { ... } from "@/components/animated-icon"` carga `animated-icon.web.tsx` en compilaciones web y `animated-icon.tsx` en Android/iOS.
- **Splash Screen**: pantalla inicial de marca que se muestra mientras el entorno nativo y JavaScript terminan de cargar.
- **Worklet (`'worklet'`)**: función pequeña compilada por `react-native-reanimated` y `react-native-worklets` para ejecutarse directamente en el hilo de interfaz nativa (UI thread) a 60/120 FPS sin bloquear el hilo de JavaScript; cuando necesita actualizar estado de React usa `scheduleOnRN`.
- **SafeAreaView**: contenedor de `react-native-safe-area-context` que añade relleno automático para evitar que la UI quede tapada por el *notch*, isla dinámica o barras del sistema.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué en `_layout.tsx` se llama a `SplashScreen.preventAutoHideAsync()` fuera del componente `RootLayout`?**
   - *Respuesta modelo:* Porque debe ejecutarse en cuanto se importa el módulo raíz, antes del primer renderizado de React. Si se colocara dentro de un `useEffect`, el sistema operativo ya habría ocultado el splash nativo antes de hidratar el tema o verificar si hay sesión, produciendo un parpadeo visual.
2. **¿En qué orden están anidados los *Providers* en `_layout.tsx` y por qué importa ese orden?**
   - *Respuesta modelo:* De afuera hacia adentro están `AppThemeProvider`, `LanguageProvider`, `ThemeProvider` (de `expo-router`) y `AuthProvider`. `AppThemeProvider` y `LanguageProvider` van por fuera porque `RootLayoutContent` necesita consumir `useAppTheme()` para armar `navigationTheme` y `StatusBar`, y `HomeScreen` (que renderiza el loader de `AuthProvider`) necesita `colors` y `t()` desde el primer instante.
3. **¿Cómo sabe `HomeScreen` (`src/app/index.tsx`) si mostrar el login o el dashboard?**
   - *Respuesta modelo:* Consume `const { user, isLoading } = useAuth()`. Primero, si `isLoading` es `true`, muestra la pantalla de sincronización; una vez terminada la comprobación, si `user` existe renderiza `<GymDashboard />`, y si `user` es `null` renderiza `<LoginForm />`.
4. **Si el proyecto usa `expo-router/entry`, ¿cómo funciona realmente la navegación entre pantallas como Catálogo, Rutinas y Perfil?**
   - *Respuesta modelo:* `_layout.tsx` renderiza directamente `<HomeScreen />` en lugar de usar `<Stack />` o `<Tabs />` de Expo Router. Por eso, las 5 pestañas del usuario no son archivos de ruta en `src/app/`, sino vistas condicionales controladas por el estado `activeTab` dentro de `GymDashboard` y `DashboardTabBar`. Como detalle técnico, `src/app/explore.tsx` quedó como residuo de la plantilla inicial de Expo.
5. **¿Para qué sirve tener tanto `animated-icon.tsx` como `animated-icon.web.tsx`?**
   - *Respuesta modelo:* Para aprovechar la resolución por plataforma de Metro/Expo. En móviles (`animated-icon.tsx`), `AnimatedSplashOverlay` oculta el splash nativo en `onLayout` y reproduce un fade-out de 600 ms usando Reanimated y `scheduleOnRN`. En navegadores (`animated-icon.web.tsx`), como no hay splash screen nativo que ocultar, retorna `null` para no bloquear la carga web.
6. **¿Qué ventaja tiene configurar `paths: { "@/*": ["./src/*"] }` en `tsconfig.json` y por qué `strict: true` es importante?**
   - *Respuesta modelo:* Los alias `@/*` hacen las importaciones legibles e independientes de la profundidad de carpetas al mover archivos. `strict: true` obliga a manejar explícitamente valores `null` o `undefined` (por ejemplo `user: User | null` o respuestas opcionales de la API), evitando errores en tiempo de ejecución.
7. **¿Por qué `HomeScreen` pasa `edges={["top", "left", "right"]}` al `SafeAreaView` cuando muestra `GymDashboard`?**
   - *Respuesta modelo:* Porque la barra inferior de pestañas (`DashboardTabBar`) está posicionada de forma absoluta abajo (`bottom: 0`) y ya calcula su propio margen seguro inferior usando `useSafeAreaInsets().bottom`. Si el `SafeAreaView` también aplicara margen inferior, quedaría un espacio vacío doble debajo de la barra de navegación.

---

## 9. Resumen para repasar

- **`_layout.tsx` es la raíz de la app**: retiene el splash nativo, monta `AppThemeProvider` → `LanguageProvider` → `ThemeProvider` → `AuthProvider` y renderiza `AnimatedSplashOverlay` + `HomeScreen`.
- **`index.tsx` es el guardia de autenticación**: muestra carga (`isLoading`), `<GymDashboard />` (`user` activo) o `<LoginForm />` (sin sesión).
- **Expo Router actúa como lanzador, no como navegador de pestañas**: las 5 secciones viven dentro de `GymDashboard`, por lo que `src/app/explore.tsx` es código plantilla sin uso.
- **`.web.tsx` adapta el arranque a navegador**: desactiva `AnimatedSplashOverlay` en web mientras móvil ejecuta `SplashScreen.hideAsync()` + animación Reanimated.
- **`.env` y `tsconfig.json` facilitan el desarrollo**: `EXPO_PUBLIC_DEV_PC_IP` permite apuntar a la IP LAN de Django sin credenciales sensibles, y `@/*` estandariza los imports en modo estricto.
