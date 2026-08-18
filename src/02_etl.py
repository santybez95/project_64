import sys
import os
# Agrega la raíz del proyecto al Path de Python
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

sys.path.append(os.path.abspath(os.path.join(script_dir, "..")))

from resources.utils import read_csv_files_aws_s3, write_csv_file_aws_s3
from resources.config import (BUCKET_DB_AWS,
                    REGION_DB_AWS,
                    ACCESS_KEY_DB_AWS,
                    SECRET_ACCESS_KEY_DB_AWS)


def extraer():
    path_bronze = "bi-streaming/bronze/doctores_bronze.csv"
    df_bronce =  read_csv_files_aws_s3(path_bronze,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                                       separator=",",na_filter=False,dtype="object")
    return df_bronce



def transformar(df):
    df = df.loc[df["UpdateAt"].notna()]  
    return df

def exportar(df):
    path_silver = "bi-streaming/silver/doctores_silver.csv"
    write_csv_file_aws_s3(df,path_silver,BUCKET_DB_AWS,REGION_DB_AWS,ACCESS_KEY_DB_AWS,SECRET_ACCESS_KEY_DB_AWS,
                          separator=",")
    print(f"etl completada ok -> s3://{BUCKET_DB_AWS}/{path_silver}")


def main():
    df_extraer = extraer()
    df_trasformar = transformar(df_extraer)
    exportar(df_trasformar)

if __name__ == "__main__":
    main()
