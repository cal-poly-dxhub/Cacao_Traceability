import argparse
import json
import re
import os
from pathlib import Path
from sys import path_importer_cache

import boto3
from sentinelhub import SHConfig, WebFeatureService, DataCollection, Geometry, AwsTileRequest, AwsTile


DATA_COLLECTION = DataCollection.SENTINEL2_L2A


""" Authenticate the user based on the credentials in their config.json file.
    See https://sentinelhub-py.readthedocs.io/en/latest/configure.html to configure,
    or https://www.sentinel-hub.com/ to register an account. """
def authenticate():
    config = SHConfig()

    if config.sh_client_id == '' or config.sh_client_secret == '':
        print("To use Sentinel Hub Catalog API, please provide the credentials (client ID and client secret).")
        return None
    
    return config


""" Search for images matching a certain criteria, and return a list of products that can
    be downloaded. date_range should be a tuple, cloud_max should be an int, and boundary
    should oint to a GeoJSON file. Reserving **kwargs to be used in the future if needed. """
def search(config, dataset=None,  date_range=None, cloud_max=1, boundary=None, **kwargs):
    print("Fetching scenes...")

    # convert geojson to BBox object
    if boundary:
        with open(boundary) as file:
            geojson = json.load(file)
            geojson = geojson['features'][0]['geometry'] # assume not multipolygon
            bbox = Geometry.from_geojson(geojson).bbox
    else:
        bbox = None

    wfs_iterator = WebFeatureService(
        bbox,
        date_range,
        data_collection=DATA_COLLECTION,
        maxcc=cloud_max,
        config=config
    )
    
    # return get_tiles() if using local download
    # return wfs_iterator.get_tiles()
    # return tuple with id and path to tile in SentinelHub S3 bucket
    return [(tile['properties']['id'], tile['properties']['path']) for tile in list(wfs_iterator)]


""" Given a list of tiles in the Sentinelhub S2 bucket and a list of files to copy for
    each tile, copy those files into dst_bucket. """
def copy_to_s3(tile_list, dst_bucket, files):
    if len(tile_list) == 0:
        print("No tiles matching the criteria were found.")
        return None

    download = input(f"Copy {len(tile_list)} scene(s) to s3://{dst_bucket}? (Y/N) ")
    if download.lower() not in {'y', 'yes'}:
        return None

    s3 = boto3.resource('s3')

    # a full breakdown of the naming convention can be found here:
    # https://roda.sentinel-hub.com/sentinel-s2-l2a/readme.html
    s2_name_pattern = re.compile(r"""
        (?:s3://)
        (?P<bucket>sentinel-s2-\w{3})   # match the bucket name (ex. sentinel-s2-l2a)
        (?:/tiles/)
        (?P<utm>\d{1,2})                # match the utm zone
        (?:/)
        (?P<lat>\w{1})                  # match the latitute band
        (?:/)
        (?P<square>\w{2})               # match the square within the utm zone/lat band
        (?:/)
        (?P<year>\d{4})                 # match the year
        (?:/)
        (?P<month>\d{1,2})              # match the month
        (?:/)
        (?P<day>\d{1,2})                # match the day
        (?:/\d+)
        """, re.VERBOSE)
    
    for tile in tile_list:
        id = tile[0] # use tile id when naming output files
        path = tile[1]
        m = s2_name_pattern.match(path)
        # pad month and day with a zero if necessary
        month = pad_zeroes(m.group('month'))
        day = pad_zeroes(m.group('day'))
        for file in files:
            # split bucket name from key
            copy_key = f"{path[21:]}/{file}"
            copy_source = {
                'Bucket': m.group('bucket'),
                'Key': copy_key
            }
            # construct the appropriate key, removing the /tiles/ prefix and stripping any folders from the
            # individual files (ex. R10m/B04.jp2 -> B04.jp2)
            dst_key = (f"sentinel-2/{m.group('utm')}/{m.group('lat')}/{m.group('square')}/"
                        f"{m.group('year')}/{month}/{day}/{id}_{os.path.basename(file)}")
            print(f"Copying to s3://{dst_bucket}/{dst_key}...")
            s3.meta.client.copy(copy_source, dst_bucket, dst_key, ExtraArgs={'RequestPayer': 'requester'})


""" Given a string, return that string padded with zeroes, if necessary.
    Useful for ensuring months/days all have the same length (3 -> 03). """
def pad_zeroes(string):
    if len(string) < 2:
        string = f"0{string}"
    return string


# download tiles locally
def download(downloads, bands=['R10m/B04', 'R10m/B08'], metafiles=['tileInfo', 'qi/MSK_CLOUDS_B00'], data_folder="."):
    # by default, select R/NIR bands, tile info metadata file, and cloud mask

    download = input(f"Download {len(downloads)} scene(s)? (Y/N) ")
    if download.lower() not in {'y', 'yes'}:
        return None

    downloaded = []
    for tile in downloads:
        print(f"Downloading {tile}...")
        request = AwsTileRequest(
            tile = tile[0],
            time = tile[1],
            aws_index = tile[2],
            bands = bands,
            metafiles = metafiles,
            data_folder = data_folder,
            data_collection = DATA_COLLECTION
        )

        # trigger download
        downloaded.append(request.save_data())
        # downloaded.append(request.get_data(save_data=True))
    
    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Search for and download L8 scenes that match criteria.")
    
    parser.add_argument("-date-range", "--dr", metavar=("start", "end"), 
                        dest="date_range", nargs=2, type=str,
                        help="filter scenes by acquisition date (format: yyyy-mm-dd yyyy-mm-dd)")
    parser.add_argument("-cloud-max", "--cm", dest="cloud_max", type=int,
                        help="filter scenes by cloud cover")
    parser.add_argument("-boundary", "--b", metavar="path/to/geojson",
                        dest="boundary", type=Path,
                        help="path to geojson file with boundary of search")
    parser.add_argument("-dst", metavar="bucket", type=str,
                        help="s3 bucket to store downloaded scenes in")
    parser.add_argument("-quiet", "--q", dest="verbose", action="store_false",
                        help="suppress printing to the console")
    args = parser.parse_args()


    # credentials are needed to use SentinelHub API for search functionality.
    # if we can perform searching ourselves, credentials would not be necessary
    config = authenticate()

    tile_list = search(config, date_range=args.date_range, boundary=args.boundary)
    # grab only desired files: R band, NIR band, metadata file, and cloud mask
    files = ['R10m/B04.jp2', 'R10m/B08.jp2', 'tileInfo.json', 'qi/MSK_CLOUDS_B00.gml']
    copy_to_s3(tile_list, args.dst, files)

    print("Done.")

    # downloaded = download(downloads)
    # print(downloaded)

if __name__ == "__main__":
    main()