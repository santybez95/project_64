# Setup Databricks CLI + Secret Scope (Azure Databricks)

## 1. Instalar Databricks CLI (versión nueva/unificada)

En PowerShell:
```powershell
winget install Databricks.DatabricksCLI
```
Si pregunta por los términos del `msstore`, aceptar con `Y`.

**Cerrar y volver a abrir la terminal** después de instalar (el PATH no se actualiza hasta reiniciar la ventana).

Verificar instalación:
```powershell
databricks -v
```

## 2. Autenticarse contra el workspace de Azure Databricks

Si ya estas logeado ingresa:
databricks auth login --profile adb-7405617245013665

Si no estas logeado sigue los siguientes pasos
Obtener la URL del workspace desde el navegador (barra de direcciones al entrar a Databricks), **sin** los parámetros después del dominio (sin `/?o=...`):

```
https://adb-7405617245013665.5.azuredatabricks.net
```
Correr login:
```powershell
databricks auth login --host https://adb-7405617245013665.5.azuredatabricks.net
```

- Cuando pregunte `Databricks profile name [...]:` → presionar **Enter** para aceptar el default.
- Se abre el navegador → iniciar sesión con la cuenta de Azure AD → autorizar acceso.
- Confirmación en terminal: `Profile ... was successfully saved`.

(Perfil guardado en este caso: `adb-7405617245013665`)

## 3. (Opcional) Fijar el perfil por defecto en la sesión de terminal

Para no tener que escribir `--profile adb-7405617245013665` en cada comando:
```powershell
$env:DATABRICKS_CONFIG_PROFILE="adb-7405617245013665"
```
(Solo dura mientras esa ventana de PowerShell esté abierta.)

## 4. Verificar que la conexión funciona

```powershell
databricks clusters list
```
Si responde sin error de autenticación/permisos, la conexión quedó OK.

## 5. Crear el Secret Scope

```powershell
databricks secrets create-scope analitica-scope
```

## 6. Cargar los secrets dentro del scope

```powershell
databricks secrets put-secret analitica-scope REGION_DB_AWS
databricks secrets put-secret analitica-scope BUCKET_DB_AWS
databricks secrets put-secret analitica-scope ACCESS_KEY_DB_AWS
databricks secrets put-secret analitica-scope SECRET_ACCESS_KEY_DB_AWS
```

Cada comando abre un editor de texto para pegar el valor (sin comillas, sin `NOMBRE=`), guardar y cerrar.

Alternativa directa en línea (queda en el historial de la terminal, usar solo si no importa):
```powershell
databricks secrets put-secret analitica-scope REGION_AN_AWS --string-value "valor-aqui"
```

## 7. Verificar que los secrets quedaron creados

```powershell
databricks secrets list-secrets analitica-scope
```
Muestra los nombres de los secrets (nunca los valores — no se pueden volver a leer en texto plano una vez guardados).

---

## 8. Eliminar secretos
```powershell
databricks secrets delete-secret <SCOPE> <KEY>
```
ejemplo:
```powershell
databricks secrets delete-secret mi-scope aws_secret_key
```


