from osgeo import gdal
import numpy as np


""" Given a numpy array and an output name, save the array as a geotiff using
    base_tif to set the geotransform and projection of the new geotiff. """
def arr_to_gtiff(arr, out_name, base_tif, dtype=gdal.GDT_Float32, xsize=None, ysize=None):
    base_ds = gdal.Open(base_tif)

    # get geotransform, projection, and size from the base geotiff
    gt = base_ds.GetGeoTransform()
    proj = base_ds.GetProjection()
    if not xsize:
        xsize = base_ds.RasterXSize
        ysize = base_ds.RasterYSize

    # write the array to a new file
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    out_ds = driver.Create(out_name,
                          xsize = xsize,
                          ysize = ysize,
                          bands = 1,
                          eType = dtype)
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    outband = out_ds.GetRasterBand(1)
    outband.WriteArray(arr)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache
    
    # free data so it saves to disk properly
    base_ds = out_ds = outband = driver = None
