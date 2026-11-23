# 07. Pestaña Máquinas y Equipos (`EquipmentSection` y `AddEquipmentModal`)

---

## 1. Propósito

La pestaña **Máquinas y Equipos** (`activeTab === "equipment"`) administra y muestra el inventario físico de máquinas, bancos, poleas y pesos libres disponibles en el gimnasio **Apex Gym Hub**. Su objetivo es doble:

1. **Para todos los usuarios (Atletas y Staff):** permitir consultar qué máquinas existen en el gimnasio, buscarlas por nombre/marca/descripción, filtrarlas por categoría biomecánica o por favoritos personales (`is_favorite`), y leer su guía rápida de ajuste (`setup_guide`) antes de entrenar.
2. **Exclusivo para administradores (`isStaff === true`):** habilitar el registro de nuevas máquinas con fotografía comprimida (`AddEquipmentModal`), así como editar o eliminar máquinas existentes mediante la hoja de acciones (`ItemActionSheet` → `EditItemModal` / `ConfirmDeleteModal`).

---

## 2. Ubicación

Todas las rutas parten de la raíz del repositorio Front End (`c:\Users\idiaz\Music\Proyecto Final\GymProyecto_FrontEnd\`):

| Archivo | Rol |
| :--- | :--- |
| `src/components/dashboard/equipment/EquipmentSection.tsx` | Componente principal de la pestaña: cabecera, buscador, chips de filtro, lista de tarjetas, favoritos y disparador de opciones CRUD. |
| `src/components/dashboard/equipment/AddEquipmentModal.tsx` | Modal inferior (*bottom sheet*) de administración para crear una máquina nueva y exportar el catálogo `EQUIPMENT_TYPES`. |
| `src/components/dashboard/EquipmentSection.tsx` | **Archivo shim heredado (legacy):** contiene únicamente `export * from "./equipment/EquipmentSection";`. |
| `src/components/dashboard/AddEquipmentModal.tsx` | **Archivo shim heredado (legacy):** contiene únicamente `export * from "./equipment/AddEquipmentModal";`. |

> **Nota sobre duplicidad heredada:** Los archivos en la raíz `src/components/dashboard/EquipmentSection.tsx` y `src/components/dashboard/AddEquipmentModal.tsx` **no contienen código duplicado antiguo**; fueron convertidos en *barrel re-exports* de una sola línea para mantener compatibilidad con importaciones previas durante la refactorización hacia subcarpetas por dominio (`equipment/`, `catalog/`, `routines/`, `tracking/`, `profile/`, `modals/`). Sin embargo, `GymDashboard.tsx` ya importa directamente desde `./equipment/EquipmentSection` y `./equipment/AddEquipmentModal`.

---

## 3. Cómo se conecta

```text
GymDashboard.tsx (activeTab === "equipment")
  │
  ├──► EquipmentSection (./equipment/EquipmentSection.tsx)
  │       ├── Lee colores del tema (`DashboardColors`), idioma (`useLanguage`) y catálogo `vm.equipmentList`
  │       ├── Resuelve imágenes con `resolveMediaUrl(item.image)` de `@/services/api`
  │       ├── Importa `EQUIPMENT_TYPES` desde `./AddEquipmentModal`
  │       ├── Favorito ❤️ ──► `vm.handleToggleEquipmentFavorite(id)` ──► `POST /catalog/equipment/{id}/favorite/`
  │       ├── Botón "+ Nuevo" (solo `isStaff`) ──► `vm.setShowAddEquipmentModal(true)`
  │       └── Long-press / botón `⋮` (solo `isStaff`) ──► `vm.handleOpenEquipmentOptions(item)`
  │                                                          └──► `ItemActionSheet` ──► `EditEquipmentForm` / `ConfirmDeleteModal`
  │
  └──► AddEquipmentModal (./equipment/AddEquipmentModal.tsx) [montado solo si `isAdmin === true`]
          ├── `pickAndCompressImage("camera" | "gallery")` de `@/services/api`
          └── `onSubmit` ──► `vm.handleCreateEquipment(data)` ──► `POST /catalog/equipment/` (JSON con base64 o multipart FormData)
```

- **Orquestador:** `GymDashboard.tsx` conecta `EquipmentSection` y `AddEquipmentModal` con el estado centralizado de `useGymDashboardData` (`src/hooks/useGymDashboardData.ts`).
- **Control de acceso (`isAdmin`):** En `GymDashboard.tsx`, `isAdmin = Boolean(user?.is_staff)` se pasa como `isStaff={isAdmin}`. Si el usuario no es staff, `onOpenAddEquipment` y `onEquipmentOptionsPress` se envían como `undefined` y `AddEquipmentModal` ni siquiera se monta en el árbol de React.
- **Sincronización automática:** Cada vez que el usuario cambia a `vm.activeTab === "equipment"` o la app vuelve a primer plano, `GymDashboard.tsx` ejecuta `silentSyncRef.current()`, refrescando `equipmentList` silenciosamente.

---

## 4. Componentes, funciones y variables clave

### En `EquipmentSection.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `EquipmentSectionProps` | Interfaz | `colors`, `equipmentList`, `isStaff = false`, `onOpenAddEquipment`, `onEquipmentOptionsPress`, `onToggleFavorite`. |
| `getEquipmentIconName(type?)` | Helper exportado | Mapea el `equipment_type` a un `IconName` vectorial (`plate_loaded` → `"cog"`, `pin_selected` → `"sliders"`, `cable` → `"activity"`, `smith` → `"layers"`, `free_weight` → `"dumbbell"`, `bodyweight` → `"user"`, `cardio` → `"flame"`, por defecto → `"target"`). |
| `searchQuery` | Estado local (`string`) | Texto del buscador en tiempo real. |
| `selectedTypeFilter` | Estado local (`string`) | Filtro activo: `"all"`, `"favorites"` o un `value` de `EQUIPMENT_TYPES`. |
| `favoritesCount` | Variable derivada | Cantidad de máquinas donde `Boolean(item.is_favorite)` es verdadero. |
| `filteredEquipment` | Variable derivada | Subconjunto de `equipmentList` que cumple simultáneamente con la búsqueda textual y el filtro de tipo/favoritos. |
| `handleTriggerOptions(item)` | Handler | Verifica `isStaff && onEquipmentOptionsPress`, emite vibración háptica (`Vibration.vibrate(45)`) y abre el menú contextual. |

### En `AddEquipmentModal.tsx`

| Elemento | Tipo | Descripción |
| :--- | :--- | :--- |
| `EQUIPMENT_TYPES` | Constante exportada | Arreglo de 8 categorías biomecánicas (`plate_loaded`, `pin_selected`, `cable`, `smith`, `free_weight`, `bodyweight`, `cardio`, `accessory`) con su `label` e `icon`. |
| `AddEquipmentModalProps` | Interfaz | `visible`, `colors`, `onSubmit(payload) => Promise<void>`, `onClose`. |
| `name`, `equipmentType`, `brand`, `description`, `setupGuide` | Estados locales (`string`) | Campos del formulario controlado. `equipmentType` inicia en `"plate_loaded"`. |
| `pickedImage` | Estado local (`PickedImageAsset \| null`) | Foto seleccionada y comprimida lista para enviarse al backend. |
| `submitting` | Estado local (`boolean`) | Bloquea/muestra *spinner* en el botón de guardado mientras dura la petición HTTP. |
| `handlePickImage(source)` | Función async | Llama a `pickAndCompressImage("camera" \| "gallery")` para pedir permisos, recortar y comprimir la foto (máx. 1080px, calidad `0.7`). |
| `handleSave()` | Función async | Valida `!name.trim()`, llama a `onSubmit`, limpia todos los estados del formulario y cierra el modal solo si la creación tuvo éxito. |

---

## 5. Explicación del código línea por línea o bloque por bloque

### A. Filtrado combinado (búsqueda + categoría + favoritos) en `EquipmentSection.tsx`

```tsx
const filteredEquipment = equipmentList.filter((item) => {
  const matchesSearch =
    !searchQuery.trim() ||
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.brand?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.description?.toLowerCase().includes(searchQuery.toLowerCase());

  const matchesType =
    selectedTypeFilter === "all"
      ? true
      : selectedTypeFilter === "favorites"
        ? Boolean(item.is_favorite)
        : item.equipment_type === selectedTypeFilter;
  return matchesSearch && matchesType;
});
```

- **¿Qué hace?** Evalúa cada máquina contra dos condiciones independientes que deben cumplirse al mismo tiempo (`matchesSearch && matchesType`).
- **Búsqueda tolerante:** Si `searchQuery` está vacío o tiene solo espacios, devuelve `true`. De lo contrario, busca coincidencias sin distinguir mayúsculas/minúsculas en `name`, `brand` y `description` usando encadenamiento opcional (`?.`) para evitar errores si una máquina no tiene marca o descripción registrada.
- **Filtro triple:** Si el chip seleccionado es `"all"`, pasan todas; si es `"favorites"`, solo las marcadas por el usuario; en cualquier otro caso, compara `item.equipment_type` con la clave biomecánica seleccionada.

### B. Tarjeta de máquina, miniatura de imagen, favorito y acciones de administrador (`EquipmentSection.tsx`)

```tsx
const imgUrl = resolveMediaUrl(item.image);
const isFav = Boolean(item.is_favorite);
return (
  <Pressable
    key={`${item.id}-${idx}`}
    onLongPress={
      isStaff && onEquipmentOptionsPress
        ? () => handleTriggerOptions(item)
        : undefined
    }
    delayLongPress={380}
    style={[styles.equipCard, { backgroundColor: colors.backgroundElevated, borderColor: colors.borderSubtle }]}
  >
```

- **`resolveMediaUrl(item.image)`:** Convierte rutas relativas entregadas por Django (ej. `/media/equipment/prensa.jpg`) en URLs absolutas usando la IP/host configurada en `API_BASE_URL`, o devuelve la URL tal cual si ya empieza por `http`.
- **Fallback visual:** Dentro de `iconCircle`, si `imgUrl` existe se renderiza `<Image>` de `expo-image` con `cachePolicy="memory-disk"`; si no tiene foto, se dibuja el icono vectorial correspondiente con `getEquipmentIconName(item.equipment_type)`.
- **Seguridad en UI:** El `onLongPress` (tras 380 ms) y el botón de tres puntos (`more-vertical`) únicamente se asignan/renderizan cuando `isStaff` es verdadero. En contraste, el botón de corazón (`onToggleFavorite`) está disponible para cualquier usuario autenticado y en `useGymDashboardData.ts` aplica **actualización optimista** (cambia el corazón al instante en pantalla y revierte si la API falla).

### C. Manejo de errores y preservación del formulario en `AddEquipmentModal.tsx`

```tsx
const handleSave = async () => {
  if (!name.trim()) return;
  setSubmitting(true);
  try {
    await onSubmit({
      name: name.trim(),
      equipment_type: equipmentType,
      brand: brand.trim(),
      description: description.trim(),
      setup_guide: setupGuide.trim(),
      image: pickedImage,
    });
    setName("");
    setEquipmentType("plate_loaded");
    setBrand("");
    setDescription("");
    setSetupGuide("");
    setPickedImage(null);
    onClose();
  } catch {
    // El toast de error ya se muestra en useGymDashboardData
  } finally {
    setSubmitting(false);
  }
};
```

- **¿Por qué hay un `catch` vacío con comentario?** En `useGymDashboardData.ts`, la función `handleCreateEquipment` captura cualquier `ApiError`, muestra un *toast* de error en pantalla y **relanza el error (`throw e`)**. Gracias a ese `throw e`, cuando la petición falla, la ejecución dentro de `handleSave` salta directamente al bloque `catch`, **evitando** limpiar los campos y **evitando** llamar a `onClose()`. Así el administrador no pierde lo que escribió si hubo un fallo de red o validación, y `finally` garantiza que `submitting` regrese a `false`.

### D. Nota de revisión técnica (código heredado / detalles menores)

- En `EquipmentSection.tsx` (líneas 623-636) quedaron definidos en `StyleSheet.create` tres estilos sin uso (`countBadge`, `countNumber`, `countLabel`), vestigio de cuando la tarjeta mostraba un contador numérico de unidades por máquina.
- El tipo `"accessory"` existe en `EQUIPMENT_TYPES` (`icon: "target"`), pero en `getEquipmentIconName` no tiene un `case "accessory":` explícito; aun así, cae en el `default:` que también retorna `"target"`, por lo que visualmente coincide.

---

## 6. Flujo paso a paso

### Flujo 1: Consultar y filtrar máquinas (Atleta / Admin)
1. El usuario toca la pestaña **Equipos** en `DashboardTabBar`, cambiando `vm.activeTab` a `"equipment"`.
2. `GymDashboard` dispara una sincronización silenciosa (`silentSyncRef`) y renderiza `EquipmentSection` con `vm.equipmentList`.
3. Si el usuario escribe en el buscador o toca un chip (por ejemplo, *Polea / Cable* o *Favoritos*), los estados `searchQuery` y `selectedTypeFilter` recalculan `filteredEquipment` en el cliente sin nuevas peticiones de red.
4. Si toca el corazón de una máquina, `handleToggleEquipmentFavorite` actualiza la UI de forma optimista y envía `POST /catalog/equipment/{id}/favorite/`.

### Flujo 2: Registrar una nueva máquina (Solo Staff / Admin)
1. El administrador presiona el botón **"+ Nuevo"** (`onOpenAddEquipment`), lo que pone `showAddEquipmentModal = true`.
2. Completa nombre, selecciona uno de los 8 chips de `EQUIPMENT_TYPES`, añade marca, descripción, guía de ajuste y opcionalmente toma/elige una foto (`pickAndCompressImage` la redimensiona a máximo 1080px y comprime a calidad `0.7`).
3. Presiona guardar: `AddEquipmentModal` llama `onSubmit` → `vm.handleCreateEquipment`.
4. `handleCreateEquipment` verifica `requireAdmin()`, llama a `api.createEquipment(data)` (serializando con base64 en JSON o `FormData`), recarga `api.getEquipment()`, muestra el toast de éxito y `AddEquipmentModal` limpia sus campos y se cierra.

---

## 7. Conceptos y términos técnicos

- **Barrel re-export (Archivo puente):** Archivo en una ruta antigua cuyo único contenido es `export * from "./subcarpeta/Archivo"` para no romper importaciones existentes tras reorganizar carpetas.
- **Actualización optimista (*Optimistic UI*):** Técnica en la que la interfaz refleja inmediatamente la acción del usuario (como encender el corazón de favorito) antes de esperar la respuesta del servidor, revirtiendo el cambio solo si la API devuelve error.
- **Compresión en cliente (`expo-image-manipulator`):** Reducción de resolución (máx. 1080px por lado) y peso (calidad 0.7, WebP en web / JPEG en móvil) en el dispositivo antes de subir la imagen al backend, ahorrando ancho de banda y almacenamiento.
- **Control de acceso basado en rol (`isStaff` / `is_staff`):** Bandera booleana del perfil de usuario proveniente de Django (`User.is_staff`) que oculta botones administrativos en la UI y además se valida en `requireAdmin()` y en los permisos del backend.
- **`cachePolicy="memory-disk"` (`expo-image`):** Política de caché que guarda miniaturas tanto en RAM como en almacenamiento local para evitar re-descargar fotos al desplazarse por la lista.

---

## 8. Posibles preguntas del profesor

1. **¿Por qué existen archivos `EquipmentSection.tsx` y `AddEquipmentModal.tsx` tanto en `src/components/dashboard/` como dentro de `src/components/dashboard/equipment/`? ¿No hay código duplicado?**
   - *Respuesta modelo:* No están duplicados. Los archivos en `src/components/dashboard/` son *barrel re-exports* de una sola línea (`export * from "./equipment/..."`) dejados por compatibilidad tras refactorizar el dashboard en subcarpetas por dominio. La implementación real vive exclusivamente dentro de `equipment/`.
2. **¿Cómo protege la pestaña de Máquinas las operaciones de creación, edición y borrado para que un atleta normal no pueda modificar el inventario?**
   - *Respuesta modelo:* En tres capas: primero en la interfaz (`EquipmentSection` oculta el botón "+ Nuevo", desactiva `onLongPress` y oculta el botón `⋮` cuando `isStaff` es falso, y `GymDashboard` ni siquiera monta `AddEquipmentModal` ni abre `ItemActionSheet`/`EditItemModal` gracias a `canManageItem`); segundo en el hook (`requireAdmin()` bloquea `handleCreateEquipment`, `handleSaveEquipmentEdit` y `handleConfirmDelete`); y tercero en los permisos del backend Django.
3. **¿Cómo funciona la subida de imágenes en `AddEquipmentModal` para web y móvil?**
   - *Respuesta modelo:* `pickAndCompressImage` solicita permisos de cámara o galería, habilita recorte, redimensiona a máximo 1080px y comprime a calidad `0.7` (WebP en web, JPEG en iOS/Android) generando tanto `uri` como `base64`. Luego `serializePayloadWithImage` en `api.ts` lo envía como cadena `data:<mime>;base64,...` dentro del JSON (o como `FormData` multipart si no hubiera `base64`).
4. **¿Qué ocurre si falla la petición al guardar una nueva máquina en `AddEquipmentModal`?**
   - *Respuesta modelo:* `handleCreateEquipment` muestra el toast de error y relanza la excepción (`throw e`). En `AddEquipmentModal`, el `catch` captura esa excepción y evita ejecutar el reseteo de estados y el `onClose()`, de modo que el administrador conserva los datos capturados y puede corregir y reintentar.
5. **¿Cómo maneja la app las rutas de imágenes que vienen del backend?**
   - *Respuesta modelo:* Usa el helper `resolveMediaUrl(item.image)`. Si la ruta ya es absoluta (`http://` o `https://`), la deja intacta; si es relativa (como `/media/...`), le antepone el host derivado de `API_BASE_URL` quitando `/api/v1`. Si no hay imagen, muestra un icono vectorial acorde a `equipment_type` mediante `getEquipmentIconName`.
6. **¿Los filtros de búsqueda y categorías consultan al servidor cada vez que el usuario teclea?**
   - *Respuesta modelo:* No. El filtrado (`filteredEquipment`) es 100 % reactivo en memoria del cliente sobre `equipmentList`, combinando coincidencia parcial en `name`, `brand` y `description` con el chip de categoría biomecánica o favoritos. Esto brinda respuesta instantánea sin saturar la API.

---

## 9. Resumen para repasar

- **`EquipmentSection`** muestra el inventario con búsqueda instantánea en cliente, chips de favoritos y 8 tipos biomecánicos (`EQUIPMENT_TYPES`), y restringe edición/creación a `isStaff`.
- **`AddEquipmentModal`** gestiona el alta de máquinas por administradores con compresión de imagen (`pickAndCompressImage`) y mantiene abierto el formulario con sus datos si el backend devuelve error (`throw e`).
- **Archivos raíz legacy:** `dashboard/EquipmentSection.tsx` y `dashboard/AddEquipmentModal.tsx` son solo re-exportaciones de 1 línea hacia `./equipment/...`, no código duplicado.
- **Favoritos optimistas:** `onToggleFavorite` actualiza el corazón al instante y sincroniza con `POST /catalog/equipment/{id}/favorite/`.
