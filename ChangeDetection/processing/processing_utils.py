import numpy as np


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