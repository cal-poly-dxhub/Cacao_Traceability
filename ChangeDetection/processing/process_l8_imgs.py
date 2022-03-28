import urllib.parse
import os

from osgeo import gdal
import numpy as np
import boto3

from processing_utils import mask_clouds_and_calc_ndvi, arr_to_gtiff


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # we can only write files to the tmp directory (max. 512 mb)
    os.chdir("/tmp")
    
    # vsitar tells gdal that the file is a tarfile
    # vsis3 tells gdal that the file is in an s3 bucket
    result = calc_ndvi_and_mask_l8_clouds(f"/vsitar/vsis3/{bucket}/{key}")
    print(f"Generated {result}")
    
    # upload generated file to s3
    dest_bucket = "processed-granules"
    prefix = os.path.dirname(key)
    key = f"{prefix}/{result}"
    s3 = boto3.client('s3')
    s3.upload_file(result, dest_bucket, key)
    print(f"Uploaded {key} to {dest_bucket}")
    os.remove(result)
    
    
""" Given a the base name of a Landsat 8 scene, caclulate NDVI, mask clouds, and save the result as a geotiff. """
def calc_ndvi_and_mask_l8_clouds(file):
    red_band = "SR_B4"
    nir_band = "SR_B5"
    qa_band = "QA_PIXEL"
    
    base_name = os.path.splitext(os.path.basename(file))[0]
    red_band_file = f"{file}/{base_name}_{red_band}.TIF"
    nir_band_file = f"{file}/{base_name}_{nir_band}.TIF"
    qa_band_file = f"{file}/{base_name}_{qa_band}.TIF"
    
    # open red, nir, and qa tif files
    red_ds = gdal.Open(red_band_file)
    red = red_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nir_ds = gdal.Open(nir_band_file)
    nir = nir_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    qa_ds = gdal.Open(qa_band_file)
    qa = qa_ds.GetRasterBand(1).ReadAsArray()
    
    # calculate cloud mask
    # bits 3 and 4 are cloud and cloud shadow, respectively
    cloud_bit = 1 << 3
    cloud_shadow_bit = 1 << 4
    bit_mask = cloud_bit | cloud_shadow_bit
    cloud_mask = ((np.bitwise_and(qa, bit_mask) != 0) * 1).astype(np.int16)
    
    ndvi_masked = mask_clouds_and_calc_ndvi(red, nir, cloud_mask)
    ndvi_masked_file = f"{base_name}_NDVI_MASKED.TIF"
    arr_to_gtiff(ndvi_masked, ndvi_masked_file, red_band_file)
    
    # free data so it saves to disk properly
    red_ds = nir_ds = qa_ds = out_ds = outband = driver = None
    
    return ndvi_masked_file