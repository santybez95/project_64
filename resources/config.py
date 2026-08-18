import os
SECRET_SCOPE = "analitica-scope"

try:
    # Disponible únicamente dentro de un cluster/job de Databricks
    from pyspark.dbutils import DBUtils
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)
    IS_DATABRICKS = True
except ImportError:
    IS_DATABRICKS = False
    from dotenv import load_dotenv


def get_config(key: str, scope: str = SECRET_SCOPE):
    """Obtiene una variable de configuración/credencial.

    - En Databricks: desde el Secret Scope.
    - En local: desde variables de entorno (.env), como ya lo tenías.
    """
    if IS_DATABRICKS:
        return dbutils.secrets.get(scope=scope, key=key)
    return os.getenv(key)


# --- Credenciales / variables AWS ---
if not IS_DATABRICKS:
    load_dotenv()
REGION_DB_AWS = get_config("REGION_DB_AWS")
ACCESS_KEY_DB_AWS = get_config("ACCESS_KEY_DB_AWS")
SECRET_ACCESS_KEY_DB_AWS = get_config("SECRET_ACCESS_KEY_DB_AWS")
BUCKET_DB_AWS = get_config("BUCKET_DB_AWS")
#TEMP_SESSION_TOKEN_AWS_ID = get_config("TEMP_SESSION_TOKEN_AWS_ID")



