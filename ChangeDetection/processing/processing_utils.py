from osgeo import gdal
import numpy as np


""" Given a numpy array and an output name, save the array as a geotiff using
    base_tif to set the geotransform and projection of the new geotiff. """
def arr_to_gtiff(arr, out_name, base_tif, dtype=gdal.GDT_Float32):
    base_ds = gdal.Open(base_tif)

    # get geotransform, projection, and size from the base geotiff
    gt = base_ds.GetGeoTransform()
    proj = base_ds.GetProjection()
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


""" Calculate NDVI and mask clouds given numpy arrays representing the 
    red band, NIR band, and cloud mask band of a given image. Returns
    the result as a numpy array. """
def mask_clouds_and_calc_ndvi(red, nir, mask):
    # calculate NDVI
    # TODO: this throws a warning, but the actual file looks fine. I'm guessing
    # it has to do with the fact that the tifs are rotated--maybe numpy is padding
    # them with zeroes to compensate, which causes some calculations to be 0/0.
    ndvi = np.divide(np.subtract(nir, red), np.add(nir, red))
    ndvi = np.where(ndvi == np.inf, np.nan, ndvi)

    # mask clouds
    ndvi_masked = np.where(mask, np.nan, ndvi)
    return ndvi_masked