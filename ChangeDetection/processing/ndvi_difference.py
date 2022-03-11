import sys
import os
import argparse

import pandas as pd
import numpy as np
from pandas.tseries.offsets import DateOffset
from osgeo import gdal


""" Given a row in a DataFrame representing a granule, return the full filename
    of that granule in the s3 filesystem so GDAL can access it. """
def get_granule_filename(granule):
    return f"/vsis3/{granule['bucket']}/{granule['key']}"


""" Given two dates, a Pandas DataFrame, and an output name, generate a mosaic
    .tif file using granules between the two dates to fill in any gaps. """
def create_mosaic(date_latest, date_earliest, df, name):
    df = df[(df['date'] > date_earliest) & 
            (df['date'] <= date_latest)]
    granules = df.apply(get_granule_filename, axis=1).tolist()

    # build vrts
    vrt_filename = f"{name}.vrt"
    print(f"Building {vrt_filename}...")
    vrt = gdal.BuildVRT(vrt_filename, granules)

    # convert vrt to tif. this seems to be much faster than using a nested vrt for the difference calculation
    tif_filename = f"{name}.tif"
    print(f"Translating {vrt_filename} to {tif_filename}...")
    tif = gdal.Translate(tif_filename, vrt, format="GTiff")

    # flush cache
    vrt = tif = None

    os.remove(vrt_filename)
    return tif_filename


def main():
    parser = argparse.ArgumentParser(
        description="Perform NDVI differencing on L8 scenes between two dates.")
    
    parser.add_argument("start", type=str,
                        help="first date (format: yyyy-mm-dd)")
    parser.add_argument("end", type=str,
                        help="second date (format: yyyy-mm-dd, should be later than start)")
    parser.add_argument("-years", "--y", dest="years", type=int, default=0,
                        help="how many years to look back to fill in missing data")
    parser.add_argument("-months", "--m", dest="months", type=int, default=0,
                        help="how many months to look back to fill in missing data")
    parser.add_argument("-days", "--d", dest="days", type=int, default=0,
                        help="how many days to look back to fill in missing data")
    args = parser.parse_args()
    
    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end)
    delta = DateOffset(years=args.years, months=args.months, days=args.days)
    
    start_d = start - delta
    end_d = end - delta
    # avoid using redundant data
    if end_d <= start:
        end_d = start

    # TODO: verbosity
    print("Searching for granules...")
    # load database of granules
    # TODO: turn this into a proper database
    # using a csv file as a temp measure
    granules = pd.read_csv("l8-granules.csv")
    granules['date'] = pd.to_datetime(granules['date'])
    granules = granules.sort_values(by="date", ascending=False)
    
    start_tif = create_mosaic(start, start_d, granules, "start")
    end_tif = create_mosaic(end, end_d, granules, "end")

    # build a combined vrt with the start and end rasters. this will automatically handle differences in bounds
    print("Building combined VRT from TIF images...")
    combined_vrt = gdal.BuildVRT("combined.vrt", [start_tif, end_tif], separate=True)
    # flush cache
    combined_vrt = None

    # get difference between start & end
    print("Calculating difference raster...")
    combined = gdal.Open("combined.vrt")
    start_band = combined.GetRasterBand(1).ReadAsArray().astype(np.float32)
    end_band = combined.GetRasterBand(2).ReadAsArray().astype(np.float32)
    gt = combined.GetGeoTransform()
    proj = combined.GetProjection()
    xsize = combined.RasterXSize
    ysize = combined.RasterYSize

    diff = np.subtract(end_band, start_band)

    # save to raster
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    # TODO: change output name
    out_ds = driver.Create("diff.tif",
                           xsize = xsize,
                           ysize = ysize,
                           bands = 1,
                           eType = gdal.GDT_Float32)
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    outband = out_ds.GetRasterBand(1)
    outband.WriteArray(diff)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache

    # flush cashe
    combined = start_band = end_band = gt = proj = driver = out_ds = outband = xsize = ysize = None

    # remove unnecessary files
    # os.remove(start_tif)
    # os.remove(end_tif)
    os.remove("combined.vrt")
    print("Done.")


if __name__ == "__main__":
    main()
