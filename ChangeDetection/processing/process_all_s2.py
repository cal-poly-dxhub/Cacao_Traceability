import urllib.parse
import os

from osgeo import gdal
import numpy as np
import boto3
import botocore

from processing_utils import mask_clouds_and_calc_ndvi, arr_to_gtiff


""" Given a the base name of a Sentinel-2 scene, caclulate NDVI, mask clouds, and save the results as a geotiff. """
def calc_ndvi_and_mask_s2_clouds(file):
    red_band = "B04.jp2"
    nir_band = "B08.jp2"
    cloud_mask_band = "MSK_CLOUDS_B00.gml"
    
    red_band_file = f"{file}_{red_band}"
    nir_band_file = f"{file}_{nir_band}"
    cloud_mask_band_file = f"{file}_{cloud_mask_band}"
    
    # open red and nir jp2 files
    red_ds = gdal.Open(red_band_file)
    red = red_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nir_ds = gdal.Open(nir_band_file)
    nir = nir_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    
    # get extent of red band to ensure cloud_mask and ndvi will have the same extent
    x_min, xres, xskew, y_max, yskew, yres  = red_ds.GetGeoTransform()
    x_max = x_min + (red_ds.RasterXSize * xres)
    y_min = y_max + (red_ds.RasterYSize * yres)

    # rasterize the cloud_mask file first
    # in theory we should be able to use the vector file to mask out clouds, but
    # in practice gdal had complaints about the gml files. will reinvestigate this
    # at a later date
    try:
        cloud_mask_tif = gdal.Rasterize("mask.tif", cloud_mask_band_file, xRes=10, yRes=10, burnValues=1, 
                                    noData=np.nan, outputType=gdal.GDT_Byte, outputBounds=[x_min, y_min, x_max, y_max])
        cloud_mask_tif = None
        cloud_mask_ds = gdal.Open("mask.tif")
        cloud_mask = cloud_mask_ds.GetRasterBand(1).ReadAsArray()
    except AttributeError as e:
        print(f"Could not read cloud mask file {cloud_mask_band_file}")
        return None

    ndvi_masked = mask_clouds_and_calc_ndvi(red, nir, cloud_mask)

    # remove temp cloud mask file to save space
    cloud_mask_ds = None
    os.remove("mask.tif")
    
    ndvi_masked_file = f"{os.path.basename(file)}_NDVI_MASKED.TIF"
    arr_to_gtiff(ndvi_masked, ndvi_masked_file, red_band_file)
    
    # free data so it saves to disk properly
    red_ds = nir_ds = cloud_mask_ds = out_ds = outband = driver = None
    
    return ndvi_masked_file


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
