import os
import sys

import boto3
import botocore

# allow imports from sibling directories
sys.path.insert(0, "../util/")
from s2_lambda import calc_ndvi_and_mask_s2_clouds


def main():
    src_bucket = "raw-granules"
    dest_bucket = "processed-granules"
    s3 = boto3.client('s3')

    response = s3.list_objects(Bucket=src_bucket, Prefix="s2-l1c")
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
        result = calc_ndvi_and_mask_s2_clouds(f"/vsis3/{bucket}/{key}")
        if result:
            print(f"Generated {result}")
        
            # remove redundant folder name from uploaded file
            prefix = os.path.dirname(os.path.dirname(key))
            key = f"{prefix}/{result}"
            s3.upload_file(result, dest_bucket, key)
            print(f"Uploaded {key} to {dest_bucket}")
            os.remove(result)
    
    print(f"Processed {len(granules)} granules.")


if __name__ == "__main__":
    main()
