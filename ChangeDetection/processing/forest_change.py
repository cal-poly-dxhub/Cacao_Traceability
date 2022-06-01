import os

from osgeo import gdal
import numpy as np

from processing_utils import arr_to_gtiff


def main():
    start = "/vsis3/processed-granules/s1/150/1194/2020/01/S1B_IW_20200111T231315_DVP_RTC30_G_gpunem_C6FE/S1B_IW_20200111T231315_DVP_RTC30_G_gpunem_C6FE_FMASK.tif"
    end = "/vsis3/processed-granules/s1/150/1194/2020/12/S1B_IW_20201212T231322_DVP_RTC30_G_gpunem_C9F2/S1B_IW_20201212T231322_DVP_RTC30_G_gpunem_C9F2_FMASK.tif"

    # build a combined vrt with the start and end rasters. this will automatically handle differences in bounds
    print("Building combined VRT from TIF images...")
    combined_file = "combined.vrt"
    combined_vrt = gdal.BuildVRT(combined_file, [start, end], separate=True)
    # flush cache
    combined_vrt = None
    
    print("Calculating difference raster...")
    combined = gdal.Open(combined_file)
    start_band = combined.GetRasterBand(1).ReadAsArray().astype(np.float32)
    end_band = combined.GetRasterBand(2).ReadAsArray().astype(np.float32)
    diff = np.subtract(end_band, start_band)

    # save results to geotiff
    diff_file = f"diff_s1.tif"
    arr_to_gtiff(diff, diff_file, combined_file)
    
    # flush cashe
    combined = start_band = end_band = None

    # remove unnecessary files
    os.remove(combined_file)
    print("Done.")


if __name__ == "__main__":
    main()