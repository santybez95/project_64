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
    path_silver = "bi-streaming/silver/doctores_silver.csv"
    df_silver =  read_csv_files_aws_s3(path_silver,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                                       separator=",",na_filter=False,dtype="object")
    return df_silver



def exportar(df):
    path_gold = "bi-streaming/gold/doctores_gold.csv"
    write_csv_file_aws_s3(df,path_gold,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                          separator=",")
    print(f"load completada ok -> s3://{BUCKET_DB_AWS}/{path_gold}")

def main():
    df_gold = extraer()
    exportar(df_gold)

if __name__ == "__main__":  
    main()
