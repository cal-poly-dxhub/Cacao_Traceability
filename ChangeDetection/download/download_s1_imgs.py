import argparse
import re
import os
from datetime import datetime, timezone

import asf_search as asf
import geopandas as gpd
import pandas as pd
from hyp3_sdk import HyP3
import boto3

from download_utils import get_credentials, confirm


# ------------------------------------------------------------------------  #
# Code adapted from routines in VegMapper repo
# Originally written by Richard Chen, Lemar Popal, Harmeen Singh, Remy Wolf
# https://github.com/NaiaraSPinto/VegMapper
# ------------------------------------------------------------------------- #


def search_granules(aoi_boundary, start, end, processing_level=asf.PRODUCT_TYPE.GRD_HD, 
                    beam_mode=asf.BEAMMODE.IW, polarization=asf.POLARIZATION.VV_VH, flight_direction=None):

    # Get WKT of AOI boundary
    gdf_boundary = gpd.read_file(aoi_boundary).dissolve()
    aoi_wkt = gdf_boundary.simplify(0.1).geometry[0].wkt

    search_opts = {
        'start': start,
        'end': end,
        'platform': asf.PLATFORM.SENTINEL1,
        'processingLevel': processing_level,
        'beamMode': beam_mode,
        'polarization': polarization,
    }

    # Search granules
    if flight_direction is None:
        search_opts['flightDirection'] = asf.FLIGHT_DIRECTION.ASCENDING
        search_results_a = asf.geo_search(intersectsWith=aoi_wkt, **search_opts)
        print(f'{len(search_results_a)} granules found for ASCENDING orbits.')

        search_opts['flightDirection'] = asf.FLIGHT_DIRECTION.DESCENDING
        search_results_d = asf.geo_search(intersectsWith=aoi_wkt, **search_opts)
        print(f'{len(search_results_d)} granules found for DESCENDING orbits.')

        if len(search_results_a) >= len(search_results_d):
            search_results = search_results_a
            print('\nThe granules of ASCENDING orbits will be used.')
        else:
            search_results = search_results_d
            print('\nThe granules of DESCENDING orbits will be used.')
    elif flight_direction.lower() in ['a', 'ascending']:
        search_opts['flightDirection'] = asf.FLIGHT_DIRECTION.ASCENDING
        search_results = asf.geo_search(intersectsWith=aoi_wkt, **search_opts)
        print(f'{len(search_results)} granules found for ASCENDING orbits.')
    elif flight_direction.lower() in ['d', 'descending']:
        search_opts['flightDirection'] = asf.FLIGHT_DIRECTION.DESCENDING
        search_results = asf.geo_search(intersectsWith=aoi_wkt, **search_opts)
        print(f'{len(search_results)} granules found for DESCENDING orbits.')
    else:
        raise Exception(f'{flight_direction} is not a valid flight_direction')

    granules = [granule['properties'] for granule in search_results.geojson()['features']]
    return granules


def submit_jobs(hyp3, granules):
    for granule in granules:
        print(f"Submitting granule {granule}...")

        hyp3.submit_rtc_job(granule, granule, resolution=30.0, radiometry='gamma0',
                            scale='power', speckle_filter=False, dem_matching=True,
                            include_dem=False, include_inc_map=True, include_scattering_area=False)


def copy_granules(s3, hyp3, granules, dst_bucket):
    for granule in granules:
        job_name = granule['sceneName']
        batch = hyp3.find_jobs(name=job_name)
        if len(batch) == 0:
            print(f'\nJobs for {job_name} have not been submitted for RTC processing yet.')
        else:
            if not batch.complete():
                print(f"\nThe jobs for {job_name} are not complete yet. You can see the progress below (Ctrl+C if you don't want to wait).")
                batch = hyp3.watch(batch)

            # List of tuples:
            # item 1: dictionary with Bucket and Key
            # item 2: datetime of expiration time
            # item 3: URL of processed granule
            job =  [({'Bucket': job.files[0]['s3']['bucket'], 'Key': job.files[0]['s3']['key']}, job.expiration_time, job.files[0]['url'])
                    for job in batch.jobs]

            print(f'\nYour processed granule(s) for {job_name} are available here:')
            for copy_source, expiration_time, _ in job:
                print(f"\n{copy_source['Bucket']}/{copy_source['Key']}")
                print(f'Expiration Time: {expiration_time}')
                basename = os.path.basename(copy_source['Key'])
                print(f"Copying {basename} to {dst_bucket}...")

                year = granule['processingDate'][0:4]
                month = granule['processingDate'][5:7]
                path = granule['pathNumber']
                frame = granule['frameNumber']
                dst_key = f"s1/{path}/{frame}/{year}/{month}/{basename}"
                s3.meta.client.copy(copy_source, dst_bucket, dst_key, ExtraArgs={'RequestPayer': 'requester'})


def main():
    parser = argparse.ArgumentParser(
        description='Search Sentinel-1 granules for an area of interest (AOI)'
    )
    parser.add_argument('boundary', type=str,
                        help='boundary of AOI (shp/geojson)')
    parser.add_argument('start', type=str,
                        help='start date (YYYY-MM-DD)')
    parser.add_argument('end', type=str,
                        help='end date (YYYY-MM-DD)')
    args = parser.parse_args()

    # Obtain NASA Earthdata credentials here:
    # https://www.earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/earthdata-login
    username, password = get_credentials("Earthdata username: ")
    hyp3 = HyP3(username=username, password=password)
    s3 = boto3.resource('s3')

    print("Searching for granules...")
    granules = search_granules(args.boundary, args.start, args.end, flight_direction="ASCENDING")

    quota = hyp3.check_quota()
    print(f'\nYour remaining quota for HyP3 jobs: {quota} granules.')
    if confirm("Submit HyP3 jobs? (Y/N): "):
        submit_jobs(hyp3, granules)
        print("Jobs successfully submitted.")

    dst_bucket = "raw-granules"
    if confirm(f"Copy granules to {dst_bucket}? (Y/N): "):
        copy_granules(s3, hyp3, granules, dst_bucket)

    print("Done.")


if __name__ == "__main__":
    main()
