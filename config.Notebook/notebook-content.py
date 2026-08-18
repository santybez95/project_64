# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "e3e7e512-8475-42eb-8add-0f928d29e9dd",
# META       "default_lakehouse_name": "repositorio_64",
# META       "default_lakehouse_workspace_id": "ee2262fa-7ef7-4f52-be10-539a4bb78f01",
# META       "known_lakehouses": [
# META         {
# META           "id": "e3e7e512-8475-42eb-8add-0f928d29e9dd"
# META         }
# META       ]
# META     },
# META     "environment": {
# META       "environmentId": "37844d50-ad7e-9fe6-41aa-50e90c67d522",
# META       "workspaceId": "00000000-0000-0000-0000-000000000000"
# META     }
# META   }
# META }

# MARKDOWN ********************

# ### Librerias

# CELL ********************

import os
import io
import base64
import boto3
import requests
import openpyxl
import pandas as pd
import numpy as np
from io import BytesIO
from io import StringIO
from dotenv import find_dotenv, load_dotenv

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ### funciones

# CELL ********************

def tabla():
    x = 2+2
    return x

x =  tabla()
# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
