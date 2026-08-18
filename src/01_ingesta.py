import sys
import os
# Agrega la raíz del proyecto al Path de Python
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

sys.path.append(os.path.abspath(os.path.join(script_dir, "..")))

# Permite importar utils/ cuando este archivo corre como task aislado en Databricks
from resources.utils import read_csv_files_aws_s3, write_csv_file_aws_s3
from resources.config import (BUCKET_DB_AWS,
                    REGION_DB_AWS,
                    ACCESS_KEY_DB_AWS,
                    SECRET_ACCESS_KEY_DB_AWS)

def extraer():
    path_raw = "bi-streaming/raw/Doctores.csv"
    productos =  read_csv_files_aws_s3(path_raw,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                                       separator=";",na_filter=False,dtype="object")
    return productos



def exportar(df):
    path_bronze = "bi-streaming/bronze/doctores_bronze.csv"
    write_csv_file_aws_s3(df,path_bronze,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                          separator=",")
    print(f"Ingesta completada ok -> s3://{BUCKET_DB_AWS}/{path_bronze}")

def main():
    df_extraer = extraer()
    exportar(df_extraer)

if __name__ == "__main__":  
    main()
