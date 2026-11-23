# 06 · Autenticación: Login, Registro y Componente Legado `UserProfileCard`

## 1. Propósito

Este documento explica el flujo de autenticación orientado al usuario en **Apex Gym Hub**: el componente **`LoginForm.tsx`** (pestañas intercambiables de *Iniciar Sesión* y *Registrarse*, validaciones locales en el cliente, limpieza reactiva de errores, integración con `AuthContext` e inicio de sesión automático tras crear cuenta de atleta básico) y la auditoría técnica de **`UserProfileCard.tsx`**, aclarando con evidencia del código fuente que se trata de **código legado / sin uso**, reemplazado actualmente por `ProfileSection.tsx`.

---

## 2. Ubicación

Archivos analizados bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\auth\LoginForm.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\auth\UserProfileCard.tsx`

Archivos directamente conectados consultados para verificación:
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\app\index.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\context\AuthContext.tsx`
- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\components\dashboard\profile\ProfileSection.tsx`

---

## 3. Cómo se conecta

```text
HomeScreen (src/app/index.tsx)
   │
   ├── user === null ──▶ <LoginForm />
   │                        │
   │                        ├── Pestaña "login"    ──▶ login(email.trim(), password)
   │                        │                             └──▶ AuthContext ──▶ api.login() ──▶ AsyncStorage
   │                        │
   │                        └── Pestaña "register" ──▶ register({ username, email, password, password_confirm })
   │                                                      └──▶ AuthContext ──▶ api.register()
   │                                                            └──▶ extractApiError() si falla
   │                                                            └──▶ Auto-login + AsyncStorage si tiene éxito
   │
   └── user !== null ──▶ <GymDashboard /> ──▶ Tab "profile" ──▶ <ProfileSection />
                                                                     (reemplazó a UserProfileCard.tsx)
```

---

## 4. Componentes, funciones y variables clave

### 4.1. `LoginForm.tsx`
- **Tipo local**: `AuthMode = "login" | "register"`.
- **Contextos consumidos**:
  - `useAuth()`: `login`, `register`, `error`, `isAuthenticating`, `clearError`.
  - `useAppTheme()`: `colors`, `resolvedMode`.
  - `useLanguage()`: `t`.
- **Estados locales**:
  - `mode`: `"login"` por defecto.
  - `username`, `email`, `password`, `confirmPassword`: valores controlados de los campos.
  - `localError`: mensaje de validación local previo a llamar al servidor.
- **Manejadores**:
  - `handleSwitchMode(nextMode)`: cambia entre login y registro limpiando errores previos.
  - `handleSubmit()`: ejecuta validaciones de cliente según `mode` y llama a `login()` o `register()`.
- **Variable derivada**: `displayError = localError || error` (prioriza errores locales inmediatos sobre el error de servidor en `AuthContext`).

### 4.2. `UserProfileCard.tsx` (Código legado)
- **Estado actual**: **No importado ni renderizado en ninguna pantalla activa.**
- **Dependencias que delatan su antigüedad**: `useColorScheme()` directo de `react-native`, objeto estático `Colors`, textos mezclados en inglés/español sin `i18n` y emojis en lugar de `GymIcon`.

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. Cambio de pestaña y limpieza de errores (`LoginForm.tsx`)

```tsx
  const handleSwitchMode = (nextMode: AuthMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setLocalError(null);
    clearError();
  };
```

- Al cambiar entre `"login"` (`t("auth.tabLogin")`) y `"register"` (`t("auth.tabRegister")`), limpia tanto `localError` como el `error` remoto almacenado en `AuthContext`, evitando que un mensaje de error de inicio de sesión siga visible en el formulario de registro (y viceversa).
- Además, cada `AppInput` ejecuta en su `onChangeText`:

```tsx
  onChangeText={(text) => {
    setEmail(text);
    if (localError) setLocalError(null);
    if (error) clearError();
  }}
```

  De modo que en cuanto el usuario empieza a corregir cualquier campo, el banner de error desaparece inmediatamente.

### 5.2. Validaciones locales en el cliente (`handleSubmit`)

#### Modo `"login"`:
```tsx
    if (mode === "login") {
      if (!email.trim()) {
        setLocalError(t("auth.emailRequired"));
        return;
      }

      if (!password) {
        setLocalError(t("auth.passwordRequired"));
        return;
      }

      await login(email.trim(), password);
      return;
    }
```

- Valida que el campo `email` (que también admite nombre de usuario, etiqueta `auth.emailOrUserLabel`) no esté vacío tras `.trim()` y que `password` haya sido ingresada.
- **Nota de implementación**: en modo `"login"` también mantiene `keyboardType="email-address"` en el `AppInput`, lo que facilita escribir `@` cuando se entra con correo, permitiendo igualmente ingresar usuario.

#### Modo `"register"`:
```tsx
    if (!username.trim()) {
      setLocalError(t("auth.usernameRequired"));
      return;
    }

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      setLocalError(t("auth.emailInvalid"));
      return;
    }

    if (password.length < 6) {
      setLocalError(t("auth.passwordTooShort"));
      return;
    }

    if (password !== confirmPassword) {
      setLocalError(t("auth.passwordsMismatch"));
      return;
    }

    await register({
      username: username.trim(),
      email: cleanEmail.toLowerCase(),
      password,
      password_confirm: confirmPassword,
    });
```

- Aplica 4 reglas de validación antes de consumir red:
  1. Nombre/usuario obligatorio (`username.trim()`).
  2. Formato de correo electrónico válido con la expresión regular `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`.
  3. Longitud mínima de contraseña de `6` caracteres (`password.length < 6`).
  4. Coincidencia exacta entre `password` y `confirmPassword`.
- Normaliza `email` a minúsculas (`cleanEmail.toLowerCase()`) y envía `password_confirm` tal como espera el serializador del endpoint `/auth/register/`.

### 5.3. Interfaz estable, banner de error y envío con teclado

```tsx
  return (
    <View
      collapsable={false}
      style={[
        styles.card,
        {
          backgroundColor: colors.backgroundElement,
          borderColor: colors.border,
          shadowOpacity: resolvedMode === "dark" ? 0.18 : 0.08,
        },
      ]}
    >
```

- Usa `collapsable={false}` en la tarjeta raíz para proteger el foco de los `AppInput` en móviles.
- Muestra el banner de error (`errorBanner`) cuando `displayError` (`localError || error`) tiene texto.
- Configura `onSubmitEditing={mode === "login" ? handleSubmit : undefined}` en el campo de contraseña y `onSubmitEditing={handleSubmit}` en el de confirmar contraseña, permitiendo enviar el formulario desde la tecla Enter/Ir del teclado.
- El botón `<AppButton>` enlaza `loading={isAuthenticating}`, mostrando un spinner e impidiendo doble envío mientras `login` o `register` están en curso.

### 5.4. Manejo de errores en servidor (`extractApiError`) y auto-inicio de sesión

En `src/context/AuthContext.tsx` (conectado directamente a `LoginForm`):

```tsx
      const response = await api.register({
        email: payload.email.trim().toLowerCase(),
        username: payload.username?.trim() || undefined,
        password: payload.password,
        password_confirm: payload.password_confirm,
      });

      const access = response.tokens?.access;
      const refresh = response.tokens?.refresh;
      if (!access || !refresh || !response.user) {
        throw new Error("Respuesta de registro incompleta.");
      }

      setToken(access);
      setUser(response.user);
      await storage.saveTokens(access, refresh);
      await storage.saveUser(response.user);
      return true;
    } catch (err) {
      setError(extractApiError(err, "No se pudo crear la cuenta"));
      return false;
    }
```

- **Auto-inicio de sesión como atleta básico**: cuando el backend crea la cuenta en `POST /auth/register/` (asignando rol estándar no-staff, `is_staff: false`), retorna inmediatamente `user` y `tokens: { access, refresh }`. `AuthContext.register` guarda ambos en `AsyncStorage` y actualiza `user` en estado, haciendo que `HomeScreen` reemplace automáticamente el `LoginForm` por `GymDashboard` sin requerir un segundo paso de login.
- **Extracción de errores (`extractApiError`)**: si el servidor devuelve HTTP 400 (por ejemplo, correo duplicado o contraseña débil según Django), `extractApiError` busca mensajes en orden de prioridad (`email`, `username`, `password`, `password_confirm`, `non_field_errors`, `detail`) o el primer campo disponible, y lo refleja en `error`, que `LoginForm` muestra en `errorBanner`. *(Nota: como detalle observado, `AuthContext.login` usa `err.message` directamente en vez de `extractApiError`).*

### 5.5. Auditoría de `UserProfileCard.tsx`: ¿código legado o utilizado?

```tsx
export const UserProfileCard: React.FC = () => {
  const scheme = useColorScheme();
  const colors = Colors[scheme === "dark" ? "dark" : "light"];
  const { user, logout } = useAuth();
  ...
          <Text style={[styles.greeting, { color: colors.textSecondary }]}>
            HELLO!
          </Text>
          ...
          <Text style={styles.badgeText}>
            {user.is_staff ? "🛡️ Administrador" : "👤 Atleta"}
          </Text>
          ...
          <Text style={[styles.detailValue, { color: colors.text }]}>
            {user.height ? `${user.height} cm` : "--"}
          </Text>
      ...
      <AppButton title="Exit" variant="outline" onPress={logout} ... />
```

**Veredicto técnico: `UserProfileCard.tsx` es código legado / muerto (no utilizado).**

Evidencia verificada en los archivos fuente del proyecto:
1. **No tiene consumidores activos**: ni `src/app/index.tsx` ni `src/components/dashboard/GymDashboard.tsx` ni `src/components/dashboard/profile/ProfileSection.tsx` importan `UserProfileCard`. La pantalla real de perfil en la pestaña `"profile"` es `ProfileSection.tsx`.
2. **Ignora `ThemeContext`**: utiliza `useColorScheme()` nativo y `Colors` estáticos en vez de `useAppTheme()`, además de colores fijos como `#0b0ead` y `#4b5563` en la insignia de rol.
3. **No usa el sistema `i18n` ni `GymIcon`**: mezcla textos literales sin traducir (`"HELLO!"`, `"Level"`, `"Peso"`, `"Estatura"`, `"Exit"`) y emojis (`"🛡️"`, `"👤"`) que fueron eliminados en el diseño actual de la app.
4. **Inconsistencia de unidades**: muestra la estatura con sufijo `cm`, mientras que el sistema actual (`ProfileSection.tsx` y `EditProfileForm`) normaliza y muestra la estatura en metros (`m`).

---

## 6. Flujo paso a paso (Registro e ingreso automático)

1. El usuario abre la app sin sesión; `HomeScreen` renderiza `<LoginForm />` con `mode === "login"`.
2. El usuario toca la pestaña **"Registrarse"** (`handleSwitchMode("register")`), lo que muestra los campos `username` y `confirmPassword` y limpia errores previos.
3. Ingresa nombre, correo, contraseña y confirmación, y presiona **"Crear Cuenta"** (`handleSubmit`).
4. `LoginForm` valida localmente: usuario no vacío, correo válido por regex, contraseña `>= 6` caracteres y contraseñas iguales. Si algo falla, muestra `localError` en el banner rojo sin gastar peticiones al servidor.
5. Al pasar las validaciones locales, llama a `register(...)` en `AuthContext`.
6. Si el backend responde `400`, `extractApiError` extrae el error específico del campo de DRF y `LoginForm` lo despliega en `errorBanner`.
7. Si el backend responde éxito con `{ user, tokens }`, `AuthContext` guarda `access`, `refresh` y `user` en `AsyncStorage` y actualiza `user` en memoria.
8. `HomeScreen` detecta `user !== null` y monta inmediatamente `<GymDashboard />` con perfil de atleta (`is_staff: false`).

---

## 7. Conceptos y términos técnicos

- **Validación del lado del cliente (Client-Side Validation)**: comprobaciones rápidas ejecutadas en la app antes de enviar datos por red, mejorando la respuesta visual y evitando peticiones innecesarias al servidor.
- **Expresión Regular (Regex)**: patrón de texto (`/^\S+@...$/`) utilizado para verificar de forma instantánea la estructura básica de un correo electrónico (`usuario@dominio.ext`).
- **Auto-login post-registro**: patrón UX donde la API de registro devuelve directamente los tokens JWT junto al usuario creado para evitar obligarlo a iniciar sesión manualmente tras registrarse.
- **Código legado / muerto (Dead Code)**: archivos o componentes que pertenecieron a una etapa temprana del desarrollo (`UserProfileCard.tsx` en los primeros prototipos de login) y quedaron en el repositorio tras ser sustituidos por versiones más completas (`ProfileSection.tsx`).

---

## 8. Posibles preguntas del profesor

1. **¿Qué validaciones realiza `LoginForm.tsx` en el cliente antes de hacer la petición HTTP?**
   - *Respuesta modelo:* En modo `"login"`, valida que el campo correo/usuario y la contraseña no estén vacíos. En modo `"register"`, verifica que el nombre/usuario no esté vacío, que el correo cumpla la expresión regular `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, que la contraseña tenga al menos 6 caracteres y que coincida exactamente con la confirmación.
2. **¿Cómo diferencia e integra `LoginForm` los errores locales de los errores devueltos por Django?**
   - *Respuesta modelo:* Combina ambos en `const displayError = localError || error`. Las validaciones rápidas rellenan `localError` localmente sin llamar a la API; si pasan y el servidor rechaza la petición, `AuthContext` guarda el mensaje en `error` (usando `extractApiError` en el registro). Además, tanto cambiar de pestaña como editar cualquier input limpia ambos errores.
3. **¿Por qué al registrarse una cuenta nueva el usuario entra directo al dashboard sin pasar de nuevo por el login?**
   - *Respuesta modelo:* Porque el endpoint `/auth/register/` devuelve `{ user, tokens: { access, refresh } }`, y el método `register` de `AuthContext` guarda ambos tokens y el usuario en `AsyncStorage` y actualiza el estado `user`. Al cambiar `user` de `null` a un objeto válido, `HomeScreen` renderiza automáticamente `<GymDashboard />`.
4. **¿Qué hace `extractApiError` en `AuthContext.tsx` y por qué es útil con Django REST Framework?**
   - *Respuesta modelo:* Django REST Framework devuelve errores de validación agrupados por campo en arreglos, por ejemplo `{ "email": ["Ya existe un usuario con este correo."] }`. `extractApiError` inspecciona `err.data` cuando es un `ApiError`, busca claves prioritarias (`email`, `username`, `password`, `password_confirm`, `non_field_errors`, `detail`) o el primer valor disponible, y devuelve un texto limpio para el banner de `LoginForm`.
5. **¿Se utiliza actualmente `UserProfileCard.tsx` en la aplicación? ¿Cómo se puede comprobar?**
   - *Respuesta modelo:* No, `UserProfileCard.tsx` es código legado que no se importa ni en `index.tsx`, ni en `GymDashboard.tsx`, ni en `ProfileSection.tsx`. Se confirma también porque todavía usa `useColorScheme` directo en vez de `ThemeContext`, textos sin `i18n` (`"HELLO!"`, `"Exit"`), emojis en vez de `GymIcon` y estatura en `cm` en lugar de metros.

---

## 9. Resumen para repasar

- **`LoginForm` unifica acceso y registro** en una tarjeta con pestañas, validaciones instantáneas por modo y envío directo desde el teclado (`onSubmitEditing`).
- **Limpieza reactiva de errores**: editar cualquier campo o alternar pestaña borra tanto `localError` como el `error` remoto de `AuthContext`.
- **Auto-login de atleta básico**: `register()` recibe `tokens` y `user` de `/auth/register/`, los persiste en `AsyncStorage` y desbloquea `<GymDashboard />` al instante.
- **`UserProfileCard.tsx` es código legado sin uso**, reemplazado por la arquitectura moderna de `ProfileSection.tsx` (conectada a `ThemeContext`, `LanguageContext` y `GymIcon`).
