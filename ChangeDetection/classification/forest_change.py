import os
import sys
import argparse

from osgeo import gdal
import numpy as np
import pandas as pd

sys.path.insert(0, "../util/")
from arr_to_gtiff import arr_to_gtiff


def get_granule_filename(granule):
    return f"/vsis3/{granule['bucket']}/{granule['key']}"


n_obs = 5


def main():
    parser = argparse.ArgumentParser(
        description="Calculate probability of forest loss for a certain date.")

    parser.add_argument("date", type=str,
                        help="date of most recent observation (format: yyyy-mm-dd)")
    parser.add_argument("csv", type=str,
                        help="name of csv file containing granules")
    args = parser.parse_args()
    
    date = pd.to_datetime(args.date)
    print("Searching for granules...")
    # load database of granules
    granules = pd.read_csv(args.csv)
    granules['date'] = pd.to_datetime(granules['date'])
    granules = granules.sort_values(by="date", ascending=False)

    # 4 most recent observations
    observations = granules[granules['date'] <= date].iloc[0:n_obs].apply(get_granule_filename, axis=1).tolist()
    base = "/vsis3/processed-granules/tree_cover/77/1191/tree_cover_2020_projected.tif" # matt hansen base tree map for 2020
    observations.append(base)

    # build a combined vrt with the observations. this will automatically handle differences in bounds
    print("Building combined VRT from TIF images...")
    combined_file = "combined.vrt"
    combined_vrt = gdal.BuildVRT(combined_file, observations, separate=True)
    # flush cache
    combined_vrt = None
    
    print("Detecting forest change...")
    combined = gdal.Open(combined_file)
    # use earliest observation as basemap
    # TODO: create better basemap
    base = combined.GetRasterBand(n_obs + 1).ReadAsArray()
    # base = combined.GetRasterBand(1).ReadAsArray()
    sum = None
    for i in range(1, n_obs + 1):
    # for i in range(2, n_obs + 2):
        band = combined.GetRasterBand(i).ReadAsArray()
        diff = np.where(np.logical_and(band == 0, base == 1), 1, 0)
        if sum is None:
            sum = diff
        else:
            sum = np.add(sum, diff)

    # save results to geotiff
    loss_file = f"loss_s1_{args.date}.tif"
    shape = base.shape
    arr_to_gtiff(sum, loss_file, combined_file, dtype=gdal.GDT_Int16, xsize=shape[1], ysize=shape[0])
    
    # flush cashe
    combined = start_band = end_band = None

    # remove unnecessary files
    os.remove(combined_file)
    print("Done.")


if __name__ == "__main__":
    main()