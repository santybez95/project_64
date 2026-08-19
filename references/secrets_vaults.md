# Gestión de credenciales con Azure Key Vault para proyectos Fabric

Guía de referencia: desde crear el Key Vault hasta consumir los secretos en un notebook de Fabric.

---

## 1. Crear el Key Vault

1. En [portal.azure.com](https://portal.azure.com), busca **"Almacenes de claves"** (no "HSM administrado" ni las opciones de Marketplace).
2. **"+ Crear"** y completa los datos básicos (suscripción, grupo de recursos, nombre único, región).
3. En la pestaña **"Configuración de acceso"**:
   - Modelo de permisos: **"Control de acceso basado en rol de Azure (RBAC)"** — es el recomendado, no el modelo de "Directiva de acceso" (legacy).
   - **"Acceso a los recursos"**: deja las 3 casillas **sin marcar** (VMs, Resource Manager, Disk Encryption) — son para integraciones que no aplican a este caso de uso.
4. En **"Redes"**: elige **"Todas las redes"** (acceso público). No hace falta una red privada (VNet/Private Endpoint) para este caso; el vault sigue protegido por autenticación de Entra ID + RBAC.
5. **"Etiquetas"**: opcional, se puede dejar vacío.
6. **"Revisar y crear"** → **"Crear"**. Tarda 1-2 minutos.

---

## 2. Los dos tipos de permisos (RBAC)

El acceso a Key Vault tiene dos planos separados:

- **Plano de control**: administrar el recurso en sí (configurar, borrar, cambiar redes). Lo da el rol **"Propietario"** heredado de la suscripción — pero **no incluye acceso a los datos**.
- **Plano de datos**: leer/escribir el contenido real de los secretos. Requiere un rol explícito, sin importar si ya eres Propietario.

| Rol | Para quién | Qué permite |
|---|---|---|
| **Agente de secretos de Key Vault** (*Key Vault Secrets Officer*) | Tu cuenta administradora — la que crea/edita/borra secretos manualmente | Crear, editar, eliminar y leer secretos |
| **Usuario de secretos de Key Vault** (*Key Vault Secrets User*) | La cuenta que solo consume secretos desde código (ej. tu usuario de Fabric) | Solo leer el contenido de los secretos |

**Regla simple**: quien *administra* el vault necesita **Officer**; quien solo *ejecuta notebooks y consume* credenciales necesita únicamente **User**. Nunca le des Officer a una cuenta que solo debería consumir.

### Cómo asignar un rol

1. En el Key Vault → **"Access control (IAM)"** → **"+ Agregar"** → **"Agregar asignación de roles"**.
2. Busca y selecciona el rol correspondiente (tabla de arriba).
3. En **"Seleccionar miembros"**, busca la cuenta:
   - Si es una cuenta normal del tenant, buscar por nombre o correo suele funcionar.
   - Si es una cuenta **invitada externa** (`#EXT#`, típico de cuentas personales tipo Hotmail/Gmail agregadas a un tenant), el buscador por nombre puede fallar — usa el **Object ID** de la cuenta (lo ves en "Usuarios" de Microsoft Entra ID) para encontrarla sin ambigüedad.
4. **"Revisar y asignar"**.
5. Si da un error tipo *"RBAC no permite la operación"* justo después de asignar el rol, espera unos minutos — es demora normal de propagación.

---

## 3. Crear los secretos

1. En el Key Vault → **"Objects"** → **"Secrets"** → **"+ Generate/Import"**.
2. **Upload options**: Manual.
3. **Name**: nombre en **kebab-case** (minúsculas, guiones medios) — es una restricción técnica de Azure, no acepta guion bajo.
4. **Value**: el valor real de la credencial.
5. **Create**. Repite uno por cada credencial.

### Convención de nombres (el mismo nombre lógico, 3 formatos distintos)

| Sistema | Formato | Ejemplo |
|---|---|---|
| **Key Vault** | kebab-case | `aws-access-key` |
| **.env local** | SCREAMING_SNAKE_CASE (regla POSIX) | `AWS_ACCESS_KEY` |
| **Código Python** | UPPER_SNAKE_CASE (PEP8) | `AWS_ACCESS_KEY` |

Agrupa por sistema de origen con el mismo orden de palabras: `aws-access-key`, `aws-secret-key`, `sftp-username`, `sftp-password`, `sharepoint-client-id`, `sharepoint-client-secret`, etc.

**Recomendación**: un Key Vault por ambiente (`vault-dev`, `vault-prod`), no mezclar dev/test/prod con prefijos dentro del mismo vault.

---

## 4. Verificar que un secret quedó bien

Como Fabric **redacta automáticamente** cualquier valor obtenido con `getSecret()` (muestra `[REDACTED]` si lo intentas imprimir — es una protección intencional, no un error), hay tres formas válidas de verificar sin exponer el valor:

1. **En el Portal de Azure**: abre el secret → su versión actual → botón/ícono de ojo **"Show Secret Value"**. Sirve para confirmar que no hubo un typo al crearlo.
2. **Prueba funcional (la forma profesional recomendada)**: usa la credencial en una llamada real y confirma si autentica bien:
   ```python
   import boto3
   from botocore.exceptions import ClientError

   try:
       s3 = boto3.client(
           "s3",
           aws_access_key_id=AWS_ACCESS_KEY,
           aws_secret_access_key=AWS_SECRET_KEY,
           region_name=REGION_DB_AWS
       )
       s3.list_buckets()
       print("✅ Credenciales de AWS correctas")
   except ClientError as e:
       print(f"❌ Error de autenticación: {e.response['Error']['Code']}")
   ```
3. **Chequeo rápido de longitud** (no expone el valor, solo su tamaño):
   ```python
   print(f"Longitud: {len(AWS_ACCESS_KEY)}")
   ```

---

## 5. Consumir los secretos desde un notebook de Fabric

```python
# URL de tu Key Vault (Overview del recurso en Azure Portal)
vault_url = "https://tu-vault.vault.azure.net/"

# Cada llamada trae un secreto puntual, usando el nombre en kebab-case
AWS_ACCESS_KEY = notebookutils.credentials.getSecret(vault_url, "aws-access-key")
AWS_SECRET_KEY = notebookutils.credentials.getSecret(vault_url, "aws-secret-key")
REGION_DB_AWS = notebookutils.credentials.getSecret(vault_url, "region-db-aws")

SHAREPOINT_CLIENT_ID = notebookutils.credentials.getSecret(vault_url, "sharepoint-client-id")
SHAREPOINT_CLIENT_SECRET = notebookutils.credentials.getSecret(vault_url, "sharepoint-client-secret")

# Uso normal, como cualquier variable — Fabric protege el valor en la salida automáticamente
import boto3

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_DB_AWS
)
```

**Requisito**: la cuenta que ejecuta el notebook debe tener el rol **"Usuario de secretos de Key Vault"** (o superior) asignado en el Key Vault — sin eso, `getSecret()` falla aunque el código esté perfecto.

---

## Resumen del flujo completo

```
Crear Key Vault (RBAC, sin acceso a recursos, red pública)
        │
        ▼
Asignar roles: Officer (admin) / User (consumidor, ej. Fabric)
        │
        ▼
Crear secrets (kebab-case, agrupados por sistema de origen)
        │
        ▼
Verificar (Portal / prueba funcional / longitud)
        │
        ▼
Consumir desde notebook con notebookutils.credentials.getSecret()
```