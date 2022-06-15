import os
import sys

from osgeo import gdal
import numpy as np
import boto3

# sys.path.insert(0, "../util/") # only needed if running locally
from processing_utils import mask_clouds_and_calc_ndvi
from arr_to_gtiff import arr_to_gtiff


def lambda_handler(event, context):
    prefix = event['Records'][0]['body']
    prefix = prefix.split('/', 1)
    bucket = prefix[0]
    key = prefix[1]
    
    # we can only write files to the tmp directory (max. 512 mb)
    os.chdir("/tmp")
    
    # vsis3 tells gdal that the file is in an s3 bucket
    result = calc_ndvi_and_mask_s2_clouds(f"/vsis3/{bucket}/{key}")
    print(f"Generated {result}")
    
    # upload generated file to s3
    dest_bucket = "processed-granules"
    # remove redundant folder name from uploaded file
    prefix = os.path.dirname(os.path.dirname(key))
    key = f"{prefix}/{result}"
    s3 = boto3.client('s3')
    s3.upload_file(result, dest_bucket, key)
    print(f"Uploaded {key} to {dest_bucket}")
    os.remove(result)
    
    
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
    cloud_mask_tif = gdal.Rasterize("mask.tif", cloud_mask_band_file, xRes=10, yRes=10, burnValues=1, 
                                    noData=np.nan, outputType=gdal.GDT_Byte, outputBounds=[x_min, y_min, x_max, y_max])
    if not cloud_mask_tif:
        cloud_mask = np.zeros_like(red)
    else:
        cloud_mask_tif = None
        cloud_mask_ds = gdal.Open("mask.tif")
        cloud_mask = cloud_mask_ds.GetRasterBand(1).ReadAsArray()

    ndvi_masked = mask_clouds_and_calc_ndvi(red, nir, cloud_mask)

    # remove temp cloud mask file to save space
    cloud_mask_ds = None
    try:
        os.remove("mask.tif")
    except FileNotFoundError:
        pass
    
    ndvi_masked_file = f"{os.path.basename(file)}_NDVI_MASKED.TIF"
    arr_to_gtiff(ndvi_masked, ndvi_masked_file, red_band_file)
    
    # free data so it saves to disk properly
    red_ds = nir_ds = cloud_mask_ds = out_ds = outband = driver = None
    
    return ndvi_masked_file