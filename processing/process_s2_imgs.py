import urllib.parse
import os

from osgeo import gdal
import numpy as np
import boto3

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
    prefix = os.path.dirname(key)
    key = f"{prefix}/{result}"
    s3 = boto3.client('s3')
    s3.upload_file(result, dest_bucket, key)
    print(f"Uploaded {key} to {dest_bucket}")
    os.remove(result)
    
    
""" Given a Landsat 8 scene, caclulate NDVI, mask clouds, and upload the result in dest_bucket. """
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
    cloud_mask_tif = None
    cloud_mask_ds = gdal.Open("mask.tif")
    cloud_mask = cloud_mask_ds.GetRasterBand(1).ReadAsArray()
    
    # calculate NDVI
    # TODO: this throws a warning, but the actual file looks fine. I'm guessing
    # it has to do with the fact that the tifs are rotated--maybe numpy is padding
    # them with zeroes to compensate, which causes some calculations to be 0/0.
    ndvi = np.divide(np.subtract(nir, red), np.add(nir, red))
    ndvi = np.where(ndvi == np.inf, np.nan, ndvi)
    
    # mask out clouds, and delete temporary cloud mask raster after to save space
    ndvi_masked = np.where(cloud_mask, np.nan, ndvi)
    cloud_mask_ds = cloud_mask = None
    os.remove("mask.tif")
    
    # get gt, projection, and size from red band
    gt = red_ds.GetGeoTransform()
    proj = red_ds.GetProjection()
    xsize = red_ds.RasterXSize
    ysize = red_ds.RasterYSize
    
    ndvi_masked_file = f"{os.path.basename(file)}_NDVI_MASKED.TIF"
    
    # write mask to new file
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    out_ds = driver.Create(ndvi_masked_file,
                          xsize = xsize,
                          ysize = ysize,
                          bands = 1,
                          eType = gdal.GDT_Float32)
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    outband = out_ds.GetRasterBand(1)
    outband.WriteArray(ndvi_masked)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache
    
    # free data so it saves to disk properly
    red_ds = nir_ds = cloud_mask_ds = out_ds = outband = driver = None
    
    return ndvi_masked_file


def main():
    file = "/vsis3/raw-granules/sentinel-2/18/N/WM/2020/04/03/S2B_OPER_MSI_L2A_TL_MTI__20200403T211516_A016067_T18NWM_N02.14"
    calc_ndvi_and_mask_s2_clouds(file)

if __name__ == "__main__":
    main()