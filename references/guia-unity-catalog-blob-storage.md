# Guía completa: conectar Azure Blob Storage (ADLS Gen2) a Databricks con Unity Catalog

Esta guía documenta, de punta a punta, cómo dejar un Data Lake en Azure Blob Storage conectado a Databricks a través de Unity Catalog: desde la cuenta de almacenamiento hasta tener un catálogo con datos reales dentro.

---

## 0. Conceptos previos (glosario rápido)

Antes de tocar nada, conviene tener claro qué es cada pieza y cómo se relacionan:

| Concepto | Qué es |
|---|---|
| **Storage Account (ADLS Gen2)** | La cuenta de Azure donde físicamente viven tus archivos. Debe tener el **namespace jerárquico** activado para que Unity Catalog la pueda usar. |
| **Access Connector for Azure Databricks** | Un recurso de Azure con identidad administrada. Es el "puente": Databricks lo usa para autenticarse contra tu storage sin manejar claves ni contraseñas. |
| **Storage Credential** (en Databricks) | El objeto dentro de Unity Catalog que referencia al Access Connector. Es la "llave" que Databricks usa internamente. |
| **External Location** | Le dice a Databricks *qué ruta exacta* de tu storage puede usar y *con qué credencial*. Es el objeto que realmente valida la conexión. |
| **Catálogo (Catalog)** | El contenedor lógico de más alto nivel dentro de Unity Catalog (equivalente a una "base de datos" a gran escala). Se apoya en una External Location para saber dónde guardar sus datos físicamente. |
| **Schema / Tabla** | Divisiones normales dentro de un catálogo, igual que en SQL tradicional. |
| **SQL Warehouse (Almacén SQL)** | El cómputo (motor) que ejecuta tus consultas SQL. Sin uno activo/en ejecución, no puedes correr ningún comando SQL. |

**Orden de dependencias** (de abajo hacia arriba):

```
Storage Account (ADLS Gen2)
   └── Access Connector for Azure Databricks (+ roles IAM)
         └── Storage Credential (en Databricks)
               └── External Location (apunta a una ruta abfss://)
                     └── Catálogo (usa esa External Location como almacenamiento)
                           └── Schema → Tabla
```

No puedes saltarte pasos: cada nivel necesita que el anterior ya exista y esté bien configurado.

---

## 1. Prerrequisito: la cuenta de Storage debe ser ADLS Gen2 (Hierarchical Namespace activado)

Unity Catalog **no soporta Blob Storage plano** — necesita que la cuenta tenga el **espacio de nombres jerárquico** habilitado (eso es, técnicamente, lo que convierte una cuenta de Blob Storage en "ADLS Gen2").

- Esta opción **solo se define al crear la cuenta** — normalmente no se puede activar después en una cuenta ya existente (aparece deshabilitada/gris en el portal).
- Si ya tienes una cuenta sin esto activado, la vía más simple y segura es **crear una cuenta nueva** con la opción activada desde el inicio, y migrar los datos con AzCopy si ya tenías algo ahí. (Existe una vía de "actualización in-place" oficial de Microsoft, pero es irreversible y deja la cuenta offline durante el proceso — solo recomendable si ya tienes mucha data y no puedes crear cuenta nueva).

**Cómo crear la cuenta correctamente:**

1. Azure Portal → Crear un recurso → **Storage account**.
2. Completa Suscripción, Resource Group, Nombre y Región como siempre.
3. Ve a la pestaña **Avanzado**.
4. En la sección de Data Lake Storage Gen2, activa **"Habilitar espacio de nombres jerárquico"** (Enable hierarchical namespace).
5. Crea la cuenta normalmente.
6. Dentro de la cuenta, crea al menos un **contenedor** (ej. `santy-cont`) — es donde vivirán tus archivos/carpetas.

---

## 2. Crear el Access Connector for Azure Databricks

Este es un recurso de Azure independiente, distinto al storage account. Es la identidad que usará Databricks para autenticarse.

1. Azure Portal → Crear un recurso → busca **"Access Connector for Azure Databricks"**.
2. Elige el mismo Resource Group y región que tu storage account (no es obligatorio que coincidan, pero simplifica la administración).
3. Ponle un nombre descriptivo (ej. `ac-databricks-analitica`).
4. Tipo de identidad: **system-assigned** es suficiente para la mayoría de los casos.
5. Crea el recurso.
6. Una vez creado, entra a su página de **"Información general"** y copia el **Resource ID** (o ábrelo en formato JSON y copia el campo `id`). Se ve así:
   ```
   /subscriptions/<sub-id>/resourceGroups/<resource-group>/providers/Microsoft.Databricks/accessConnectors/<nombre>
   ```
   **Guarda este valor** — lo vas a necesitar más adelante en Databricks, al crear el Storage Credential.

---

## 3. Configurar los permisos IAM (roles)

Aquí es donde le das permiso al Access Connector para que pueda leer/escribir datos y (opcionalmente) gestionar eventos de archivo. Son **4 roles en total**, repartidos en **2 lugares distintos**: el storage account y el resource group.

### 3.1 En el Storage Account (o en el contenedor específico)

Ve a tu storage account → **Control de acceso (IAM)** → **+ Agregar** → **Agregar asignación de roles**, y repite el proceso para cada uno de estos roles:

| Rol | Para qué sirve | Dónde buscarlo |
|---|---|---|
| **Storage Blob Data Owner** (o `Contributor`, según cuánto acceso quieras) | Leer y escribir los blobs/archivos | Pestaña "Roles de función de trabajo" |
| **Storage Account Contributor** | Necesario si quieres que Databricks configure automáticamente la infraestructura de eventos de archivo | Pestaña **"Roles de administrador con privilegios"** (no aparece en la de función de trabajo, porque da acceso a claves de cuenta) |
| **Storage Queue Data Contributor** | Necesario para las colas que usan los eventos de archivo | Pestaña "Roles de función de trabajo" |

**Truco importante:** el buscador de roles del portal a veces no encuentra el rol exacto por nombre (búsqueda difusa). Si te pasa, busca por el **ID del rol** directamente en el mismo cuadro de búsqueda (el placeholder dice "Buscar por nombre de rol, descripción o id"):

- `Storage Account Contributor` → ID: `17d1049b-9a84-46fb-8f53-869881c3d3ab`
- `Storage Queue Data Contributor` → ID: `974c5e8b-45b9-4653-ba55-5f855dd0fb88`

**Pasos exactos para cada asignación:**
1. Selecciona el rol → Siguiente.
2. En "Miembros" → "Asignar acceso a": elige **Identidad administrada**.
3. **+ Seleccionar miembros** → busca tu Access Connector (ej. `ac-databricks-analitica`) → selecciónalo.
4. **Revisar y asignar**.

Puedes asignar `Storage Blob Data Owner` a nivel de todo el storage account, o solo a nivel del contenedor específico (clic en el contenedor → Control de acceso (IAM) → mismos pasos) si quieres limitar el acceso a esa carpeta únicamente. Los otros dos roles (`Storage Account Contributor` y `Storage Queue Data Contributor`) **deben ir a nivel de la cuenta completa**, no del contenedor, porque gestionan configuración de cuenta y colas que no existen a nivel de un contenedor individual.

### 3.2 En el Resource Group que contiene el storage account

1. Azure Portal → Grupos de recursos → entra al resource group de tu storage account.
2. Control de acceso (IAM) → + Agregar → Agregar asignación de roles.
3. Busca **`EventGrid EventSubscription Contributor`**.
4. Miembros → Identidad administrada → busca tu Access Connector → selecciónalo.
5. Revisar y asignar.

**¿Por qué en el resource group y no en el storage account?** Porque los eventos de archivo crean una suscripción de Event Grid, que es un tipo de recurso que se gestiona a nivel de resource group, no dentro del storage account mismo.

### 3.3 Resumen de los 4 roles

| # | Rol | Ámbito | Pestaña de búsqueda |
|---|---|---|---|
| 1 | Storage Blob Data Owner/Contributor | Storage account o contenedor | Función de trabajo |
| 2 | Storage Account Contributor | Storage account (cuenta completa) | Administrador con privilegios |
| 3 | Storage Queue Data Contributor | Storage account (cuenta completa) | Función de trabajo |
| 4 | EventGrid EventSubscription Contributor | Resource Group | Función de trabajo |

La propagación de estos permisos en Azure normalmente tarda 1-2 minutos, en casos raros hasta 8 minutos.

---

## 4. Registrar el proveedor de recursos Microsoft.EventGrid

Este paso es independiente de los permisos IAM — es un requisito a nivel de **suscripción** de Azure. Si tu suscripción nunca ha usado Event Grid antes, este proveedor aparece "No registrado", y sin registrarlo, la creación automática de eventos de archivo fallará aunque los roles IAM estén perfectos.

1. Azure Portal → busca **"Suscripciones"** → entra a tu suscripción.
2. Menú lateral → **"Proveedores de recursos"** (Resource providers).
3. Busca `Microsoft.EventGrid`.
4. Si el estado dice **"No registrado"**, selecciónalo → clic en **"Registrar"**.
5. Espera 1-3 minutos hasta que cambie a **"Registrado"**.

(Necesitas rol de Contributor u Owner sobre la suscripción para hacer esto.)

---

## 5. Del lado de Databricks: por qué empezar desde los Almacenes SQL (SQL Warehouses)

Para poder ejecutar cualquier comando SQL en Databricks (crear catálogos, credenciales por código, consultar tablas, etc.) necesitas **cómputo activo** que procese esas consultas — ese cómputo es el **Almacén SQL (SQL Warehouse)**. Sin uno corriendo, el Editor de SQL no tiene dónde ejecutar nada.

**Por qué se recomienda empezar por ahí:**
- Es el cómputo más simple y rápido de levantar (a diferencia de un cluster completo), pensado justo para tareas de SQL/administración como esta.
- Muchos de los pasos siguientes (verificar credenciales con `SHOW STORAGE CREDENTIALS`, crear el catálogo por SQL, cargar datos de prueba) requieren tenerlo activo.
- Si usas la interfaz gráfica de Catalog Explorer para crear catálogos/credenciales/external locations, **no siempre necesitas un warehouse** — esas acciones de creación son administrativas y corren en el backend de Unity Catalog. Pero en el momento en que quieras **consultar datos** (`SELECT * FROM ...`) o correr comandos `SHOW`/`DESCRIBE`, sí lo vas a necesitar.

**Cómo iniciarlo:**
1. Sidebar → **Almacenes de SQL** (SQL Warehouses).
2. Si ya existe uno (Databricks suele crear uno "Serverless Starter Warehouse" por defecto), solo dale **Start** si está detenido.
3. Si no existe, **Crear almacén SQL** → tamaño pequeño (2X-Small) es suficiente para tareas administrativas → Crear.
4. Una vez en estado "Running" (verde), ya puedes usar el Editor de SQL con normalidad.

---

## 6. Crear el Storage Credential en Databricks

Este objeto conecta Unity Catalog con tu Access Connector de Azure.

**Vía interfaz gráfica:**
1. Sidebar → **Catálogo**.
2. Botón **"External data"** (o el ícono de conexión) → pestaña **Credentials** → **Create credential**.
3. Tipo: **Azure Managed Identity**.
4. Nombre para la credencial (ej. `analitica_credential`).
5. **Access Connector ID**: pega aquí el Resource ID que copiaste en el paso 2 (`/subscriptions/.../accessConnectors/ac-databricks-analitica`).
6. Guardar.

**Ver credenciales existentes (para no duplicar):**
```sql
SHOW STORAGE CREDENTIALS;
DESCRIBE STORAGE CREDENTIAL <nombre_credencial>;
```

---

## 7. Crear la External Location

Aquí se valida realmente la conexión — es donde Databricks intenta leer/escribir/listar sobre tu contenedor usando la credencial del paso anterior.

### 7.1 Armar la URL en formato `abfss://`

El portal de Azure solo te muestra la URL en formato `blob://`, tienes que convertirla tú mismo:

```
https://<cuenta>.blob.core.windows.net/<contenedor>
```
se convierte en:
```
abfss://<contenedor>@<cuenta>.dfs.core.windows.net/
```

Ejemplo: si tu cuenta es `analica` y tu contenedor `santy-cont`:
```
abfss://santy-cont@analica.dfs.core.windows.net/
```

Cambios clave: el endpoint pasa de `blob` a `dfs` (el que habilita las capacidades jerárquicas), y el contenedor se mueve al frente, antes del `@`.

Si quieres apuntar a una subcarpeta específica (por ejemplo, reservada para tu catálogo), agrégala al final:
```
abfss://santy-cont@analica.dfs.core.windows.net/analitica_dl
```

**De dónde sacar la URL base:** Azure Portal → tu storage account → "Información general" (o "Puntos de conexión") → copia el nombre exacto de la cuenta que aparece ahí, y el nombre del contenedor desde Explorador de almacenamiento → Contenedores. Con esos dos datos armas la URL abfss manualmente con el patrón de arriba.

### 7.2 Crear la External Location

1. Catálogo → External data → pestaña **External Locations** → **Create location**.
2. Nombre (ej. `analitica_dl_location`).
3. **URL**: pega la URL abfss que armaste en el paso 7.1.
4. **Credencial de almacenamiento**: selecciona la que creaste en el paso 6.
5. Databricks prueba la conexión automáticamente y te muestra un checklist:
   - ✅ Leer / Lista / Escribir / Eliminar / La ruta existe / Espacio de nombres jerárquico activado → esto confirma que la URL y la credencial están bien.
   - Los eventos de archivo (Aprovisionamiento/Desmontaje de recursos) son una optimización **opcional** — solo necesaria si más adelante usas Auto Loader/streaming. Si fallan, puedes darle **"Forzar la creación de la ubicación"** y seguir sin problema; la ingesta usará enumeración de directorios (más lenta a gran escala, pero funcional).

### 7.3 Si quieres que los eventos de archivo también queden en verde

Al crear/editar la ubicación, entra a **Opciones avanzadas** y llena:
- **Grupo de recursos**: el resource group que contiene tu storage account (ej. `st-practicas`).
- **ID de suscripción**: el de tu suscripción de Azure.
- **Tipo de evento de archivo**: déjalo en **Automático** (Databricks crea la cola y suscripción por ti, usando los roles IAM que ya diste en el paso 3).

No uses el enlace "Rellenar automáticamente desde el ID del conector de acceso" — puede traer valores que no coinciden exactamente con el resource group real de tu storage account; mejor escribe estos dos valores a mano.

Esto solo funciona si ya completaste correctamente los pasos 3 (los 4 roles IAM) y 4 (registro de Microsoft.EventGrid).

---

## 8. Crear el Catálogo

Con la External Location lista, ya puedes crear el catálogo apoyado en ella.

**Vía interfaz gráfica:**
1. Catálogo → botón **Crear** → tipo **Standard catalog**.
2. Nombre del catálogo (ej. `analitica_dl`).
3. En **Storage location**, navega/selecciona tu External Location (o pega la URL abfss, incluso con un subpath propio para este catálogo).
4. Crear.

**Vía SQL:**
```sql
CREATE CATALOG analitica_dl
MANAGED LOCATION 'abfss://santy-cont@analica.dfs.core.windows.net/analitica_dl';
```

Esto crea automáticamente dos schemas dentro: `default` e `information_schema` (metadata autogenerada, estándar en todo catálogo de Unity Catalog).

---

## 9. Crear un schema y una tabla de prueba (verificar que todo funciona)

```sql
CREATE SCHEMA analitica_dl.bronze;

CREATE TABLE analitica_dl.bronze.base_dv AS
SELECT * FROM read_files(
  'abfss://santy-cont@analica.dfs.core.windows.net/diners-report/bronze/base_dv_bronze.csv',
  format => 'csv',
  header => true,
  sep => ','
);

SELECT * FROM analitica_dl.bronze.base_dv LIMIT 10;
```

Si ves los datos, todo el flujo (Storage Account → Access Connector → roles IAM → Storage Credential → External Location → Catálogo) quedó correctamente conectado de punta a punta.

---

## 10. Checklist resumen del orden completo

- [ ] 1. Storage Account creado con **Hierarchical Namespace activado** (ADLS Gen2).
- [ ] 2. Contenedor creado dentro de esa cuenta.
- [ ] 3. Access Connector for Azure Databricks creado, Resource ID copiado.
- [ ] 4. Rol Storage Blob Data Owner/Contributor asignado (cuenta o contenedor).
- [ ] 5. Rol Storage Account Contributor asignado (cuenta completa, pestaña "administrador con privilegios").
- [ ] 6. Rol Storage Queue Data Contributor asignado (cuenta completa).
- [ ] 7. Rol EventGrid EventSubscription Contributor asignado (resource group).
- [ ] 8. Proveedor Microsoft.EventGrid registrado en la suscripción.
- [ ] 9. Almacén SQL activo en Databricks.
- [ ] 10. Storage Credential creado en Databricks (Azure Managed Identity + Access Connector ID).
- [ ] 11. External Location creada (URL abfss:// + credencial), validada en verde.
- [ ] 12. Catálogo creado, apuntando a esa External Location.
- [ ] 13. Schema y tabla de prueba creados y consultados con éxito.

---

## 11. Problemas comunes durante esta configuración (y su solución)

| Error / síntoma | Causa | Solución |
|---|---|---|
| No se puede activar "namespace jerárquico" en una cuenta existente | Es una opción que solo se define al crear la cuenta | Crear cuenta nueva con la opción activada, o usar la actualización in-place oficial (irreversible) |
| No encuentras "Storage Account Contributor" al buscar por nombre | Es un rol privilegiado, vive en otra pestaña, o el buscador es difuso | Pestaña "Roles de administrador con privilegios", o busca por su ID exacto |
| Error `AuthorizationFailure` al provisionar eventos de archivo | Falta alguno de los 4 roles IAM, especialmente el de EventGrid en el resource group | Revisar el mensaje de error — indica el scope exacto donde falta el permiso |
| Error `Microsoft.EventGrid is not registered in Azure Subscription` | El proveedor de recursos EventGrid nunca se registró en tu suscripción | Suscripciones → Proveedores de recursos → registrar Microsoft.EventGrid |
| Todo lo demás en verde, pero eventos de archivo en rojo | Es una optimización opcional, no bloqueante | "Forzar la creación de la ubicación" y continuar; revisar más adelante si usas Auto Loader |

---

*Guía elaborada a partir de la configuración real del proyecto `analitica` — cuenta `analica`, contenedor `santy-cont`, Access Connector `ac-databricks-analitica`, resource group `st-practicas`.*
