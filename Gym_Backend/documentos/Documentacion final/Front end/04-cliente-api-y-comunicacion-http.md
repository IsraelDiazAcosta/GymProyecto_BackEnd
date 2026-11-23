# 04 · Cliente API y Comunicación HTTP (`api.ts`)

## 1. Propósito

Este documento analiza el módulo central de comunicación HTTP del cliente: **`src/services/api.ts`**. Explica cómo se resuelve dinámicamente la IP LAN del servidor backend Django en desarrollo (`resolveDevHostIp` y `extractLanIp`), cómo opera el cliente genérico `request<T>` con la clase `ApiError`, cómo se capturan, comprimen y serializan imágenes en Web y móvil (`pickAndCompressImage`, `buildMultipartBody`, `serializePayloadWithImage`), cómo se resuelven URLs absolutas de archivos multimedia (`resolveMediaUrl`, `resolveExerciseImageUrl`), y el catálogo completo de métodos `api.*` para autenticación, catálogo, rutinas, marcas de fuerza y sesiones de entrenamiento.

> **Nota de auditoría del código real:** En esta versión de `src/services/api.ts` la resolución de host se llama `resolveDevHostIp` (no `resolveApiUrl`), las imágenes se procesan con `pickAndCompressImage` / `buildMultipartBody` / `serializePayloadWithImage` (no `prepareImageBase64` / `appendImageToFormData`), el desempaquetado de listas paginadas se hace en línea en cada método (`res.results || res` en lugar de un helper `unwrapList`), y `request<T>` actualmente **no incluye** `AbortController` con timeout de 12 s ni renovación automática de token (`tryRefreshToken`) ante HTTP `401`. Todos estos detalles reales y hallazgos técnicos se documentan con exactitud más adelante.

---

## 2. Ubicación

Archivo analizado bajo `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`:

- `c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\src\services\api.ts` (970 líneas)

---

## 3. Cómo se conecta

```text
.env (EXPO_PUBLIC_DEV_PC_IP) / Constants.expoConfig.hostUri
   │
   ▼
resolveDevHostIp() + Platform.select() ──▶ API_BASE_URL (http://<host>:8000/api/v1)
   │
   ▼
storage.getAccessToken() ──▶ request<T>(endpoint, options) ──▶ fetch(url, headers)
                                                                     │
   ┌─────────────────────────────────────────────────────────────────┴───────────────────────────┐
   ▼                                                                                             ▼
Éxito (response.ok)                                                                  Error (!response.ok o red)
   └──▶ JSON parseado tipado como T                                                      └──▶ throw ApiError(status, msg, data)

Consumidores principales de `api.*` y helpers:
├── AuthContext.tsx           (login, register, getProfile, updateProfile)
├── useGymDashboardData.ts    (catálogo, máquinas, músculos, rutinas, marcas, favoritos, usuarios admin)
├── GymDashboard.tsx          (sesiones activas, historial semanal, detalle de sesión)
├── ProfileSection.tsx        (weight-logs, getWeight1RMProgress, resolveMediaUrl)
├── RoutineSessionHistory...  (getCompletedSessionsPaginated, getRoutineSessionsSummary, deleteWorkoutSession)
└── Modales de imagen/detalle (pickAndCompressImage, resolveExerciseImageUrl)
```

---

## 4. Componentes, funciones y variables clave

### 4.1. Configuración de red y URLs
- **`extractLanIp(raw)`**: limpia protocolo/puerto y valida formato IPv4 excluyendo `localhost` y `127.0.0.1`.
- **`resolveDevHostIp()`**: resuelve la IP de desarrollo en orden de prioridad (`EXPO_PUBLIC_DEV_PC_IP` -> `Constants.expoConfig` / `manifest2` / `manifest` -> `"192.168.100.8"`).
- **`DEV_PC_IP`** y **`API_BASE_URL`**: constantes exportadas con la URL base del API (`/api/v1`).

### 4.2. Clases y helpers internos de transporte
- **`ApiError`**: subclase de `Error` que agrega `status: number` y `data: any`.
- **`buildMultipartBody(payload)`**: construye un `FormData` adaptado a Web (`File`) y Nativo (`{ uri, name, type }`).
- **`serializePayloadWithImage(payload)`**: decide entre enviar JSON con imagen Base64 (`data:<mime>;base64,...`) o delegar a `buildMultipartBody`.
- **`request<T>(endpoint, options)`**: wrapper único sobre `fetch` que inyecta cabeceras, token Bearer y normaliza errores HTTP/red.

### 4.3. Helpers multimedia exportados
- **`resolveMediaUrl(path)`**: convierte rutas relativas (`/media/...`) en URLs absolutas contra el host del backend.
- **`resolveExerciseImageUrl(exercise, equipmentList)`**: obtiene la imagen propia del ejercicio o la hereda de su máquina asignada.
- **`pickAndCompressImage(source)`**: pide permisos, abre cámara o galería, redimensiona a máximo `1080px`, comprime al `70%` y genera `uri`, `base64` y `file` (en Web).

### 4.4. Constantes e interfaces de dominio
- **`EXPERIENCE_LEVELS`**, **`TRAINING_GOALS`** y tipos `User`, `ProfileUpdatePayload`, `RegisterPayload`, `RegisterResponse`, `AuthResponse`, `Equipment`, `MuscleGroup`, `Exercise`, `ExerciseMedia`, `Routine`, `RoutineDay`, `RoutineExercise`, `RoutineSet`, `ProgressionItem`, `WorkoutSessionItem`, `WorkoutSessionDetail`, `RoutineSessionSummaryItem`, `PaginatedSessionsResponse`, `BodyWeightLogItem`, `Weight1RMProgressResponse`, `PickedImageAsset`.

### 4.5. Objeto exportado `api`
Agrupa **33 métodos** divididos en Autenticación (7), Catálogo (13), Rutinas y Progreso 1RM (8 en sección rutinas) y Tracking / Sesiones con Timer (14). *(Total: 42 métodos contando todas las subsecciones).*

---

## 5. Explicación del código línea por línea o bloque por bloque

### 5.1. Resolución automática de IP LAN y `API_BASE_URL`

```ts
function extractLanIp(raw?: string | null): string | null {
  if (!raw || typeof raw !== "string") return null;
  const cleaned = raw.replace(/^[a-z]+:\/\//i, "").split("/")[0];
  const host = cleaned.split(":")[0]?.trim();
  if (!host || host === "localhost" || host === "127.0.0.1") {
    return null;
  }
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(host) ? host : null;
}

function resolveDevHostIp(): string {
  const envIp = process.env.EXPO_PUBLIC_DEV_PC_IP?.trim();
  if (envIp) return envIp;

  const expoHostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoClient?.hostUri ||
    (Constants as any).manifest?.debuggerHost ||
    (Constants as any).manifest?.hostUri;

  return extractLanIp(expoHostUri) || "192.168.100.8";
}

export const DEV_PC_IP = resolveDevHostIp();
export const API_BASE_URL = Platform.select({
  web: "http://127.0.0.1:8000/api/v1",
  android: `http://${DEV_PC_IP}:8000/api/v1`,
  ios: `http://${DEV_PC_IP}:8000/api/v1`,
  default: `http://${DEV_PC_IP}:8000/api/v1`,
});
```

- **¿Por qué es necesario esto?** En un celular físico corriendo Expo Go, `127.0.0.1` apunta al propio teléfono y no a la computadora donde corre Django.
- **Orden de resolución**:
  1. Primero revisa si existe `process.env.EXPO_PUBLIC_DEV_PC_IP` (definido en `.env`).
  2. Si no existe, inspecciona el manifiesto de Expo (`Constants.expoConfig?.hostUri`, y variantes heredadas `manifest2` / `manifest`) que contiene la dirección IP:puerto de Metro Bundler (por ejemplo `"192.168.1.45:8081"`).
  3. `extractLanIp` quita protocolos y puerto, descarta `localhost`/`127.0.0.1` y valida mediante expresión regular que sea una IPv4 válida.
  4. Si nada funciona, cae al valor de respaldo `"192.168.100.8"`.
- **En Web**: `Platform.select` fuerza `"http://127.0.0.1:8000/api/v1"` porque el navegador corre en la misma máquina que el servidor local.

### 5.2. `ApiError` y núcleo `request<T>`

```ts
export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await storage.getAccessToken();
  const isMultipart =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isMultipart ? {} : { "Content-Type": "application/json" }),
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg =
        data.detail || data.non_field_errors?.[0] || "Error en la petición";
      throw new ApiError(response.status, errorMsg, data);
    }

    return data as T;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      0,
      `No se pudo conectar a ${url}. Asegúrate de correr Django con: python manage.py runserver 0.0.0.0:8000 y que tu celular esté en el mismo WiFi.`,
    );
  }
}
```

- **Manejo de `Content-Type` con `FormData`**: si `options.body instanceof FormData`, **omite** `"Content-Type": "application/json"` intencionalmente para que `fetch` genere automáticamente el encabezado `multipart/form-data; boundary=...` con el delimitador correcto.
- **Inyección automática de JWT**: lee el token de acceso desde `storage.getAccessToken()` y lo envía en `Authorization: Bearer <token>`.
- **Parseo seguro**: `await response.json().catch(() => ({}))` evita que respuestas sin cuerpo (como `204 No Content` en peticiones `DELETE`) o páginas de error HTML provoquen un fallo de sintaxis JSON no controlado.
- **Diferenciación de errores**:
  - Error HTTP del backend (`!response.ok`): extrae `data.detail` o `data.non_field_errors?.[0]` y conserva tanto `status` (`400`, `401`, `403`, `404`, `500`) como el objeto `data` completo dentro de `ApiError` (usado luego por `AuthContext.extractApiError`).
  - Error de red / servidor caído: atrapado en el `catch`, lanza `ApiError` con `status = 0` y un mensaje guía recordando levantar Django en `0.0.0.0:8000`.
- **Anomalías / mejoras pendientes detectadas en `request<T>`**:
  1. **Sin timeout (`AbortController`)**: actualmente `fetch` espera indefinidamente si la red se queda colgada; no hay límite de 12 s ni `AbortController`.
  2. **Sin auto-refresh de token ante `401`**: aunque `storage.ts` guarda `refreshToken`, `request<T>` no intercepta respuestas HTTP `401` para intentar renovarlo antes de lanzar `ApiError`.

### 5.3. Captura, compresión y serialización de imágenes (Web vs Nativo)

```ts
  const result = await pickerFn({
    mediaTypes: ["images"],
    allowsEditing: true,
    quality: 0.9,
  });
  if (result.canceled || !result.assets?.[0]) return null;

  const asset = result.assets[0];
  const w = asset.width || 0;
  const h = asset.height || 0;
  const actions: ImageManipulator.Action[] = [];

  if (w > 1080 || h > 1080) {
    if (w >= h) {
      actions.push({ resize: { width: 1080 } });
    } else {
      actions.push({ resize: { height: 1080 } });
    }
  }

  const format =
    Platform.OS === "web"
      ? ImageManipulator.SaveFormat.WEBP
      : ImageManipulator.SaveFormat.JPEG;
  ...
  const manipulated = await ImageManipulator.manipulateAsync(
    asset.uri,
    actions,
    { compress: 0.7, format, base64: true },
  );

  let webFile: File | undefined;
  if (Platform.OS === "web" && manipulated.uri) {
    try {
      const resp = await fetch(manipulated.uri);
      const blob = await resp.blob();
      webFile = new File([blob], `upload_${Date.now()}.${ext}`, { type: mime });
    } catch {}
  }
```

- **`pickAndCompressImage(source)`**:
  1. Solicita permisos nativos de cámara (`requestCameraPermissionsAsync`) o galería (`requestMediaLibraryPermissionsAsync`), lanzando un mensaje claro si son denegados.
  2. Redimensiona proporcionalmente solo si alguno de los lados supera `1080 px` (ajustando el lado mayor a `1080`).
  3. Elige formato **`WEBP`** en Web y **`JPEG`** en Android/iOS, comprimiendo a calidad `0.7` y solicitando `base64: true`.
  4. En Web, además convierte la `uri` resultante en un objeto estándar `File` del navegador (`fetch` -> `blob` -> `new File`).

```ts
function buildMultipartBody(payload: Record<string, any>): FormData {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, val]) => {
    if (val === undefined || val === null) return;
    if (key === "image" && typeof val === "object" && "uri" in val) {
      if (Platform.OS === "web" && val.file) {
        formData.append("image", val.file, val.name || "upload.jpg");
      } else {
        formData.append("image", {
          uri: val.uri,
          name: val.name || "upload.jpg",
          type: val.type || "image/jpeg",
        } as any);
      }
    } else {
      formData.append(key, String(val));
    }
  });
  return formData;
}

function serializePayloadWithImage(
  payload: Record<string, any>,
): string | FormData {
  const img = payload?.image as PickedImageAsset | null | undefined;
  if (img && typeof img === "object") {
    if (img.base64) {
      const cleanPayload: Record<string, any> = {};
      Object.entries(payload).forEach(([key, val]) => {
        if (key === "image" || val === undefined) return;
        cleanPayload[key] = val;
      });
      const mime = img.type || "image/jpeg";
      const cleanBase64 = img.base64.includes(";base64,")
        ? img.base64.split(";base64,")[1]
        : img.base64;
      cleanPayload.image = `data:${mime};base64,${cleanBase64}`;
      return JSON.stringify(cleanPayload);
    }
    if ("uri" in img || "file" in img) {
      return buildMultipartBody(payload);
    }
  }
  ...
  return JSON.stringify(cleanPayload);
}
```

- **Estrategia híbrida Base64 vs Multipart (`FormData`)**:
  - Cuando la imagen ya trae `img.base64` (caso normal de `pickAndCompressImage`), `serializePayloadWithImage` la empaqueta como cadena Data URI (`data:image/jpeg;base64,...` o `webp`) dentro de un JSON limpio, evitando problemas con límites o cabeceras multipart entre Expo Web y React Native.
  - Si llegara un `PickedImageAsset` sin `base64` (solo con `uri` o `file`), cae a `buildMultipartBody`, que adjunta `val.file` en Web o el descriptor `{ uri, name, type }` nativo de React Native en `FormData`.
  - Si `image` es `null` o `undefined`, la omite del JSON para no sobrescribir una imagen existente durante peticiones `PATCH`.

### 5.4. Resolución de URLs multimedia (`resolveMediaUrl` y `resolveExerciseImageUrl`)

```ts
export function resolveMediaUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  const host = (API_BASE_URL ?? "").replace(/\/api\/v1\/?$/, "");
  return `${host}${path.startsWith("/") ? "" : "/"}${path}`;
}
```

- Si `path` ya es una URL completa (`http://` o `https://`), la devuelve intacta.
- Si es una ruta relativa de Django (por ejemplo `"/media/equipment/prensa.jpg"`), elimina el sufijo `"/api/v1"` de `API_BASE_URL` y concatena el host raíz (`http://192.168.x.x:8000/media/...`).

```ts
export function resolveExerciseImageUrl(
  exercise?: Exercise | null,
  equipmentList?: Equipment[],
): string | null {
  if (!exercise) return null;
  const direct =
    exercise.image ||
    exercise.image_url ||
    exercise.thumbnail ||
    exercise.media?.find(
      (m) => m.media_type === "image" || Boolean(m.thumbnail),
    )?.thumbnail ||
    exercise.media?.find((m) => m.media_type === "image")?.file ||
    (typeof exercise.equipment === "object" && exercise.equipment
      ? exercise.equipment.image
      : null);
  if (direct) return resolveMediaUrl(direct);
  if (equipmentList && equipmentList.length > 0) {
    const eqId =
      typeof exercise.equipment === "object" && exercise.equipment
        ? exercise.equipment.id
        : (exercise as any).equipment_id;
    const eqMatch = equipmentList.find(
      (eq) =>
        (eqId && eq.id === eqId) ||
        (exercise.equipment_name &&
          eq.name.toLowerCase() === exercise.equipment_name.toLowerCase()),
    );
    if (eqMatch?.image) return resolveMediaUrl(eqMatch.image);
  }
  return null;
}
```

- Aplica una **cascada de resolución** para que un ejercicio siempre muestre foto si su máquina tiene una:
  1. Campos directos en el ejercicio (`image`, `image_url`, `thumbnail`).
  2. Galería `media[]` del ejercicio (`thumbnail` o `file` donde `media_type === "image"`).
  3. Objeto `exercise.equipment.image` si viene anidado.
  4. Búsqueda de respaldo en `equipmentList` por `equipment_id` o coincidencia de `equipment_name` (sin distinguir mayúsculas).

### 5.5. Catálogo completo de métodos `api.*` y desempaquetado de listas

En lugar de una función separada `unwrapList`, los métodos de listado manejan la paginación DRF (`{ count, next, previous, results }`) o arreglos directos usando `res.results || res` o `Array.isArray(res) ? res : res?.results || []`.

| Dominio | Método `api.*` | Verbo y Endpoint | Notas clave |
| :--- | :--- | :--- | :--- |
| **Auth** | `login(email, password)` | `POST /auth/login/` | Devuelve `{ access, refresh, user }`. |
| **Auth** | `register(payload)` | `POST /auth/register/` | Devuelve `{ user, tokens: { access, refresh } }`. |
| **Auth** | `getProfile()` / `updateProfile(payload)` | `GET` / `PATCH /auth/profile/` | Lee y actualiza perfil biométrico/preferencias. |
| **Auth** | `getWeightLogs()` / `createWeightLog(w, date?)` | `GET` / `POST /auth/weight-logs/` | Historial de peso corporal. |
| **Auth** | `getAdminUsers()` | `GET /auth/users/` | Directorio de usuarios para staff. |
| **Catálogo** | `getExercises()` / `getExerciseDetail(id)` | `GET /catalog/exercises/` & `/{id}/` | Listado (`res.results \|\| res`) y detalle completo. |
| **Catálogo** | `createExercise` / `updateExercise` / `deleteExercise` | `POST` / `PATCH` / `DELETE /catalog/exercises/` | Usa `serializePayloadWithImage`. |
| **Catálogo** | `getEquipment()` / `getFavoriteEquipment()` | `GET /catalog/equipment/` & `/favorites/` | Inventario de máquinas. |
| **Catálogo** | `createEquipment` / `updateEquipment` / `deleteEquipment` | `POST` / `PATCH` / `DELETE /catalog/equipment/` | Usa `serializePayloadWithImage`. |
| **Catálogo** | `toggleEquipmentFavorite(id)` / `toggleExerciseFavorite(id)` | `POST .../favorite/` | Alterna favorito en BD. |
| **Catálogo** | `getMuscles()` | `GET /catalog/muscles/` | Catálogo de grupos musculares. |
| **Rutinas** | `getRoutines()` / `createRoutine(...)` | `GET` / `POST /routines/routines/` | Soporta `exercise_ids`, `sets_count`, `min_reps`, `max_reps`. |
| **Rutinas** | `updateRoutine(id, payload)` / `deleteRoutine(id)` | `PATCH` / `DELETE /routines/routines/{id}/` | Edición y borrado de rutina. |
| **Rutinas** | `addExerciseToRoutine(routineId, payload)` | `POST /routines/routines/{id}/add-exercise/` | Asegura `exercise_id` tomando el primero de `exercise_ids` si falta. |
| **Rutinas** | `updateRoutineExercise` / `removeExerciseFromRoutine` | `PATCH` / `DELETE /routines/exercises/{id}/` | Edita series/reps o quita ejercicio de una rutina. |
| **Tracking** | `getWeight1RMProgress(exerciseId?)` | `GET /tracking/progress/weight-1rm/` | Cruce de peso corporal vs curva 1RM (opcional `?exercise_id=`). |
| **Tracking** | `ensureSession()` | `GET` / `POST /tracking/sessions/` | Busca sesión con `!s.is_completed` o crea `"Entrenamiento Móvil"`. *(Detalle técnico: usa `is_completed`, esquema legado frente a `status === "active"` de sesiones con timer).* |
| **Tracking** | `saveMarca(exerciseId, weight, reps, rpe?)` | `ensureSession` -> `POST /tracking/exercises/` -> `POST /tracking/sets/` | Flujo en 3 pasos: asegura sesión, vincula ejercicio y guarda la serie. |
| **Tracking** | `getProgression(exerciseId)` | `GET /tracking/progression/{id}/` | Historial de levantamientos por ejercicio. |
| **Tracking** | `updateMarca(setId, payload)` / `deleteMarca(setId)` | `PATCH` / `DELETE /tracking/sets/{id}/` | Edición/borrado de marcas. |
| **Sesiones** | `startRoutineSession(routineId)` | `POST /tracking/sessions/start/` | Inicia sesión ligada a una rutina con cronómetro. |
| **Sesiones** | `finishRoutineSession()` / `cancelRoutineSession()` | `POST /tracking/sessions/finish/` & `/cancel/` | Finaliza o cancela la sesión activa. |
| **Sesiones** | `getActiveRoutineSession()` | `GET /tracking/sessions/active/` | Retorna la sesión si trae `id`, o `null`. |
| **Sesiones** | `getRoutineSessionHistory(params?)` | `GET /tracking/sessions/history/` | Filtra con `URLSearchParams` (`desde`, `hasta`, `routine_id`). |
| **Sesiones** | `getCompletedSessionsPaginated(params?)` | `GET /tracking/sessions/history/` | Normaliza respuesta paginada `{ count, next, previous, summary, results }`. |
| **Sesiones** | `getWorkoutSessionDetail(id)` / `deleteWorkoutSession(id)` | `GET` / `DELETE /tracking/sessions/{id}/` | Detalle con series por ejercicio o eliminación de sesión. |
| **Sesiones** | `getRoutineSessionsSummary(params?)` | `GET /tracking/sessions/routine-summary/` | Métricas agregadas (conteo, promedio y duración total por rutina). |

---

## 6. Flujo paso a paso (Ejemplo: Subir imagen al crear un ejercicio)

1. El administrador pulsa cámara o galería en el modal; se invoca `pickAndCompressImage("gallery")`.
2. Se verifica el permiso del sistema operativo; si se concede, `ImagePicker` abre el selector con recorte habilitado.
3. Si la imagen supera `1080 px`, se calcula la acción de redimensión manteniendo la relación de aspecto y `ImageManipulator` genera la imagen comprimida (`0.7`) en `WEBP` (web) o `JPEG` (móvil) junto con su cadena `base64`.
4. Al enviar el formulario, `api.createExercise(payload)` llama a `serializePayloadWithImage(payload)`, que empaqueta el campo `image` como `data:image/...;base64,...` dentro de un JSON (o `FormData` vía `buildMultipartBody` si no hubiera `base64`).
5. `request<Exercise>("/catalog/exercises/", { method: "POST", body })` lee el JWT de `storage`, configura `Accept` y `Content-Type` según corresponda, ejecuta `fetch` contra `API_BASE_URL` y retorna el nuevo `Exercise` o lanza `ApiError` si hubo validación fallida o pérdida de red.

---

## 7. Conceptos y términos técnicos

- **Cliente HTTP (`fetch`)**: API estándar de JavaScript usada en React Native y navegadores para enviar peticiones HTTP/HTTPS asíncronas al backend REST.
- **Bearer Token (JWT)**: credencial enviada en la cabecera `Authorization: Bearer <token>` para autenticar cada petición privada ante Django REST Framework.
- **Multipart `FormData` vs Data URI Base64**: dos formas de enviar archivos binarios por HTTP. `FormData` envía el archivo en partes binarias sin encabezado manual `Content-Type: application/json`, mientras que Base64 codifica la imagen como texto dentro del JSON.
- **Paginación DRF (`results`)**: formato estándar de Django REST Framework que envuelve listados dentro de `{ count, next, previous, results: [...] }` cuando hay paginación activa, o devuelve un arreglo plano si está desactivada.
- **URLSearchParams**: utilidad estándar que construye y escapa parámetros de consulta (`?desde=...&routine_id=...`) evitando errores con caracteres especiales.

---

## 8. Posibles preguntas del profesor

1. **¿Cómo logra la app móvil conectarse a Django en desarrollo sin editar el código cada vez que cambia la IP del Wi-Fi?**
   - *Respuesta modelo:* Mediante `resolveDevHostIp()` en `src/services/api.ts`. Primero busca `EXPO_PUBLIC_DEV_PC_IP` en las variables de entorno (`.env`); si no está definida, lee el `hostUri` del servidor Metro desde `expo-constants` (`Constants.expoConfig?.hostUri`) y extrae la IPv4 con `extractLanIp()`, descartando `localhost`/`127.0.0.1` y dejando `"192.168.100.8"` solo como último respaldo.
2. **¿Por qué `request<T>` omite el header `"Content-Type": "application/json"` cuando `options.body instanceof FormData`?**
   - *Respuesta modelo:* Porque una petición `multipart/form-data` necesita incluir un `boundary` único generado automáticamente por el motor de red (`fetch`) para separar los campos y los bytes de la imagen. Si fijáramos `Content-Type: application/json` o `multipart/form-data` sin boundary manualmente, el servidor no podría parsear los archivos.
3. **¿Cómo optimiza el frontend el peso de las fotografías antes de mandarlas al servidor?**
   - *Respuesta modelo:* Con `pickAndCompressImage()` usando `expo-image-manipulator`. Antes de subir nada, calcula si el ancho o alto supera `1080 px`, redimensiona proporcionalmente el lado mayor a `1080 px` y aplica compresión `0.7` (en formato `WEBP` en web y `JPEG` en móviles).
4. **¿Qué pasa en el frontend cuando un ejercicio no tiene fotografía propia?**
   - *Respuesta modelo:* La función `resolveExerciseImageUrl(exercise, equipmentList)` implementa una cascada de herencia: primero busca `image`, `image_url`, `thumbnail` o `media` del propio ejercicio; si no existen, toma la imagen de `exercise.equipment` o busca la máquina correspondiente dentro de `equipmentList` (por ID o por nombre) y convierte la ruta relativa con `resolveMediaUrl`.
5. **¿Qué mejoras o brechas técnicas identificaste al auditar `src/services/api.ts`?**
   - *Respuesta modelo:* Tres puntos concretos: (1) aunque `storage.ts` persiste el `refreshToken`, `request<T>` todavía no implementa un flujo automático de renovación ante HTTP `401`; (2) `fetch` no usa actualmente un `AbortController` para cortar peticiones colgadas por timeout; y (3) el helper legado `ensureSession()` aún busca `!s.is_completed`, a diferencia de las sesiones modernas con cronómetro que usan `status: "active"` mediante `/tracking/sessions/active/`.
6. **¿Cómo se registra una marca desde el cliente hacia el backend en `api.saveMarca()`?**
   - *Respuesta modelo:* Ejecuta tres pasos encadenados: primero llama a `this.ensureSession()` para obtener o crear una sesión activa; segundo hace `POST /tracking/exercises/` para asociar el `exerciseId` a esa sesión y obtener `logEx.id`; y tercero hace `POST /tracking/sets/` con `log_exercise`, `set_number: 1`, `weight`, `reps` y `rpe`.

---

## 9. Resumen para repasar

- **`resolveDevHostIp` + `Platform.select`** generan `API_BASE_URL` automáticamente (`127.0.0.1` en Web, IP LAN desde `.env` o `Constants.expoConfig` en móvil).
- **`request<T>` y `ApiError`** centralizan la inyección del token Bearer, la detección de `FormData` y el manejo uniforme de errores HTTP (`status`, `data`) y de red (`status = 0`).
- **Imágenes optimizadas**: `pickAndCompressImage` limita a `1080 px` y calidad `0.7` (`WEBP`/`JPEG`), y `serializePayloadWithImage` envía Base64 en JSON o `FormData` vía `buildMultipartBody`.
- **`resolveExerciseImageUrl`** hereda la foto de la máquina cuando el ejercicio no tiene imagen propia.
- **Hallazgo clave para defensa**: en la versión actual de `api.ts` no existe `AbortController` de timeout ni auto-refresh de JWT en 401 pese a existir `getRefreshToken()` en `storage.ts`.
