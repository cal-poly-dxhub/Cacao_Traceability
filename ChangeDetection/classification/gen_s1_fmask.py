import os
import sys

from osgeo import gdal
import numpy as np
import boto3

sys.path.insert(0, "../util/")
from arr_to_gtiff import arr_to_gtiff


s3 = boto3.client('s3')


def gen_fmask(file):
    basename = os.path.basename(file)
    print(f"Generating forest mask for {file}...")

    # TODO: fine tune these
    vv_threshold = 1.7
    vh_threshold = 0.15

    # open datasets
    vv_tif = f"/vsis3/{file}/{basename}_VV_FILTERED.tif"
    vh_tif = f"/vsis3/{file}/{basename}_VH_FILTERED.tif"
    vv_ds = gdal.Open(vv_tif)
    vh_ds = gdal.Open(vh_tif)
    vv = vv_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    vh = vh_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)

    # generate fmasks
    mask = np.logical_and(vv > vv_threshold, vh > vh_threshold).astype(np.int16)
    mask = np.where(mask, mask, np.nan)
    
    # write to file
    outname = f"{basename}_FMASK.tif"
    arr_to_gtiff(mask, outname, vv_tif, dtype=gdal.GDT_Int16)

    # flush cache so gdal writes properly
    vv_ds = vh_ds = None

    # upload to s3
    bucket = "classified-granules"
    _, key = file.split('/', 1)
    key = f"{key}_FMASK.tif"
    s3.upload_file(outname, bucket, key)
    print(f"Uploaded {key} to {bucket}.")
    os.remove(outname)
    

def main():
    bucket = "processed-granules"
    while True: # temp while we wait for granule processing to finish
        files = []
        for file in s3.list_objects(Bucket=bucket, Prefix='s1')['Contents']:
            # we have vv and vh both stored in a single folder. we want to process them at the same time
            # this will get us the directory that contains them
            file = os.path.dirname(f"{bucket}/{file['Key']}")
            if file not in files:
                files.append(file)

        for file in files:
            gen_fmask(file)
        


if __name__ == "__main__":
    main()