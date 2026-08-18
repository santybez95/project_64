import io
from io import BytesIO, StringIO
import boto3
import pandas as pd


#Funciones S3
def read_csv_files_aws_s3(prefix, bucket_name, region_name, aws_access_key_id, aws_secret_access_key, separator, na_filter= None, dtype=None):
    if na_filter is None:
        na_filter = True
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        #aws_session_token=temp,
        region_name=region_name)
    s3 = session.resource("s3")
    bucket = s3.Bucket(bucket_name)
    prefix_objs = bucket.objects.filter(Prefix=prefix)
    prefix_df = []
    for obj in prefix_objs:
        key = obj.key
        body = obj.get()["Body"].read()
        df = pd.read_csv(io.BytesIO(body), encoding="utf8", sep=separator, na_filter=na_filter, dtype=dtype) 
        prefix_df.append(df)
    return pd.concat(prefix_df)


def write_csv_file_aws_s3(data_frame, path_aws_s3, bucket_name, region_name, aws_access_key_id, aws_secret_access_key, separator):
    df = data_frame
    path = path_aws_s3
    s3 = boto3.client("s3",
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    #aws_session_token=temp, 
                    region_name=region_name)
    
    csv_buf = StringIO()
    df.to_csv(csv_buf, sep=separator, header=True, index=False)
    csv_buf.seek(0)
    s3.put_object(Bucket=bucket_name, Body=csv_buf.getvalue(), Key=path)