import urllib.parse
import os

from osgeo import gdal
import numpy as np
import boto3
import botocore

from processing_utils import mask_clouds_and_calc_ndvi, arr_to_gtiff
from process_l8_imgs import calc_ndvi_and_mask_l8_clouds


def main():
    src_bucket = "raw-granules"
    dest_bucket = "processed-granules"
    s3 = boto3.client('s3')

    response = s3.list_objects(Bucket=src_bucket, Prefix="landsat")
    granules = []
    for key in response['Contents']:
            path = os.path.dirname(key['Key'])
            granule = f"{src_bucket}/{path}/{os.path.basename(path)}"
            try:
                # check if file already exists
                s3.head_object(Bucket=dest_bucket, Key=f"{path}_NDVI_MASKED.TIF")
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    granules.append(granule)
                else:
                    raise e

    granules = set(granules)
    for granule in granules:
        prefix = granule.split('/', 1)
        bucket = prefix[0]
        key = prefix[1]
        # vsis3 tells gdal that the file is in an s3 bucket
        result = calc_ndvi_and_mask_l8_clouds(f"/vsitar/vsis3/{bucket}/{key}")
        if result:
            print(f"Generated {result}")
            prefix = os.path.dirname(key)
            key = f"{prefix}/{result}"
            s3.upload_file(result, dest_bucket, key)
            print(f"Uploaded {key} to {dest_bucket}")
            os.remove(result)
    
    print(f"Processed {len(granules)} granules.")


if __name__ == "__main__":
    main()
