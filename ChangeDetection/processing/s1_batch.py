from pathlib import Path
import os

from osgeo import gdal
import numpy as np
import rasterio
import cv2 as cv
import boto3
from scipy.ndimage import generic_filter


s3 = boto3.client('s3')


# Enhanced Lee Filter for speckle reduction
def enhanced_lee(img, win_size=5, num_looks=1, nodata=None):
    src_dtype = img.dtype
    img = img.astype(np.float64)

    # Get image mask (0: nodata; 1: data)
    mask = np.ones(img.shape)
    mask[img == nodata] = 0
    mask[np.isnan(img)] = 0     # in case there are pixels of NaNs

    # Change nodata pixels to 0 so they don't contribute to the sums
    img[mask == 0] = 0

    # Kernel size
    ksize = (win_size, win_size)

    # Window sum of image values
    img_sum = cv.boxFilter(img, -1, ksize,
                           normalize=False, borderType=cv.BORDER_ISOLATED)
    # Window sum of image values squared
    img2_sum = cv.boxFilter(img**2, -1, ksize,
                            normalize=False, borderType=cv.BORDER_ISOLATED)
    # Pixel number within window
    pix_num = cv.boxFilter(mask, -1, ksize,
                           normalize=False, borderType=cv.BORDER_ISOLATED)

    # There might be a loss of accuracy as how boxFilter handles floating point
    # number subtractions/additions, causing a window of all zeros to have
    # non-zero sum, hence correction here using np.isclose.
    img_sum[np.isclose(img_sum, 0)] = 0
    img2_sum[np.isclose(img2_sum, 0)] = 0

    # Get image mean and std within window
    img_mean = np.full(img.shape, np.nan, dtype=np.float64)     # E[X]
    img2_mean = np.full(img.shape, np.nan, dtype=np.float64)    # E[X^2]
    img_mean2 = np.full(img.shape, np.nan, dtype=np.float64)    # (E[X])^2
    img_std = np.full(img.shape, 0, dtype=np.float64)           # sqrt(E[X^2] - (E[X])^2)

    idx = np.where(pix_num != 0)                # Avoid division by zero
    img_mean[idx] = img_sum[idx]/pix_num[idx]
    img2_mean[idx] = img2_sum[idx]/pix_num[idx]
    img_mean2 = img_mean**2

    idx = np.where(~np.isclose(img2_mean, img_mean2))           # E[X^2] and (E[X])^2 are close
    img_std[idx] = np.sqrt(img2_mean[idx] - img_mean2[idx])

    # Get weighting function
    k = 1
    cu = 0.523/np.sqrt(num_looks)
    cmax = np.sqrt(1 + 2/num_looks)
    ci = img_std / img_mean         # it's fine that img_mean could be zero here
    w_t = np.zeros(img.shape)
    w_t[ci <= cu] = 1
    idx = np.where((cu < ci) & (ci < cmax))
    w_t[idx] = np.exp((-k * (ci[idx] - cu)) / (cmax - ci[idx]))

    # Apply weighting function
    img_filtered = (img_mean * w_t) + (img * (1 - w_t))

    # Assign nodata value
    img_filtered[pix_num == 0] = nodata

    return img_filtered.astype(src_dtype)


# Filter VV/VH bands using Enhanced Lee Filter
def filter_elee(file, bands, lee_win_size=5, lee_num_looks=3):
    filtered = []
    # Process backscatter (VV/VH)
    for pq in bands:
        print(f"Processing {pq} for {file}...")
        # Read in DN
        basename = os.path.splitext(os.path.basename(file))[0]
        dn_raster = f"{file}/{basename}/{basename}_{pq}.tif"
        with rasterio.open(dn_raster) as dset:
            dn = dset.read(1).astype(np.float64)
            mask = dset.read_masks(1)
            dn[mask == 0] = np.nan
            profile = dset.profile

        # Convert DN to gamma0
        g0 = dn**2 * 100

        # Filter gamma0 using enhanced Lee filter
        g0_filtered = enhanced_lee(g0, lee_win_size, lee_num_looks, nodata=np.nan)

        # Write to GeoTIFF
        profile.update(driver='GTiff', dtype=np.float32, nodata=np.nan)
        g0_filtered_tif = Path(f'{basename}_{pq}_FILTERED.tif')
        with rasterio.open(g0_filtered_tif, 'w', **profile) as dset:
            dset.write(g0_filtered.astype(np.float32), 1)

        filtered.append(str(g0_filtered_tif))
    
    return filtered


# Filter INC_MAP by calculating standard deviation of neighborhood of pixels
def filter_std(file, bands, window_size=5):
    filtered = []

    for pq in bands:
        print(f"Processing {pq} for {file}...")
        # Read in DN
        basename = os.path.splitext(os.path.basename(file))[0]
        dn_raster = f"{file}/{basename}/{basename}_{pq}.tif"
        with rasterio.open(dn_raster) as dset:
            dn = dset.read(1).astype(np.float64)
            mask = dset.read_masks(1)
            dn[mask == 0] = np.nan
            profile = dset.profile

        dn_filtered = generic_filter(dn, np.std, window_size, mode='nearest')

        # Write to GeoTIFF
        profile.update(driver='GTiff', dtype=np.float32, nodata=np.nan)
        dn_filtered_tif = Path(f'{basename}_{pq}_FILTERED.tif')
        with rasterio.open(dn_filtered_tif, 'w', **profile) as dset:
            dset.write(dn_filtered.astype(np.float32), 1)

        filtered.append(str(dn_filtered_tif))
    return filtered


def process(zipfile):
    basename = os.path.splitext(os.path.basename(zipfile))[0]
    dirname = os.path.dirname(zipfile)
    print(f"Processing {basename}...")

    # enhanced lee filter
    bands = ['VV', 'VH']
    processed = filter_elee(f"/vsizip/vsis3/{zipfile}", bands)

    # skip INC band for now
    # bands = ['INC']
    # processed.append(filter_std(f"/vsizip/vsis3/{zipfile}", ['inc_map']))

    # upload to s3
    dst_bucket = "processed-granules"
    
    for file, postfix in zip(processed, bands):
        bucket, prefix = dirname.split('/', 1)
        key = f"{prefix}/{basename}/{basename}_{postfix}_FILTERED.tif"
        s3.upload_file(file, dst_bucket, key)
        print(f"Uploaded {key} to {dst_bucket}")
        os.remove(file)


def main():
    src_bucket = "raw-granules"
    # avoid re-processing existing tifs for now
    existing = s3.list_objects(Bucket='processed-granules', Prefix='s1')['Contents']
    existing = set([os.path.dirname(file['Key']) for file in existing])
    for file in s3.list_objects(Bucket=src_bucket, Prefix="s1")['Contents']:
        file = file['Key']
        if file[:-4] not in existing:
            filepath = src_bucket + '/' + file
            process(filepath)
    print("Done.")
            

if __name__ == '__main__':
    main()