import argparse
import json
import re
import os
from pathlib import Path
from sys import path_importer_cache

import boto3
from sentinelhub import SHConfig, WebFeatureService, DataCollection, Geometry, AwsTileRequest, AwsTile


QUEUE = "S2ImgsToBeProcessed" # name of sqs queue to send messages to for processing
REGION = "us-west-2" # aws region of queue


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
    be downloaded. date_range should be a tuple, cloud_max should be an int, boundary
    should point to a GeoJSON file, and collection should be either 'L2A' or 'L1C'. """
def search(config, dataset=None,  date_range=None, cloud_max=1, boundary=None, collection="L2A"):
    # convert geojson to BBox object
    if boundary:
        with open(boundary) as file:
            geojson = json.load(file)
            geojson = geojson['features'][0]['geometry'] # assume not multipolygon
            bbox = Geometry.from_geojson(geojson).bbox
    else:
        bbox = None

    if collection == "L2A":
        data_collection = DataCollection.SENTINEL2_L2A
    elif collection == "L1C":
        data_collection = DataCollection.SENTINEL2_L1C
    else:
        raise ValueError(f"unsupported collection: {collection}")

    wfs_iterator = WebFeatureService(
        bbox,
        date_range,
        data_collection=data_collection,
        maxcc=cloud_max,
        config=config
    )
    
    # return get_tiles() if using local download
    # return wfs_iterator.get_tiles()
    # return tuple with id and path to tile in SentinelHub S3 bucket
    return [(tile['properties']['id'], tile['properties']['path']) for tile in list(wfs_iterator)]


""" Given a list of tiles in the Sentinelhub S2 bucket and a list of files to copy for
    each tile, copy those files into dst_bucket. """
def copy_to_s3(tile_list, dst_bucket, files, prefix="s2"):
    s3 = boto3.resource('s3')
    sqs = boto3.resource("sqs", region_name=REGION)
    q = sqs.get_queue_by_name(QueueName=QUEUE)

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
        (?:/)
        (?P<sequence>\d{1})             # match the sequence, if there is more than one image per day
        """, re.VERBOSE)
    
    for tile in tile_list:
        id = tile[0] # use tile id when naming output files
        path = tile[1]
        m = s2_name_pattern.match(path)
        # pad month and day with a zero if necessary
        month = pad_zeroes(m.group('month'))
        day = pad_zeroes(m.group('day'))
        tile_prefix = (f"{prefix}/{m.group('utm')}/{m.group('lat')}/{m.group('square')}/"
                        f"{m.group('year')}/{month}/{id}_{m.group('sequence')}/{id}_{m.group('sequence')}")
        print(f"Copying to s3://{dst_bucket}/{tile_prefix}")
        for file in files:
            # split bucket name from key
            copy_key = f"{path[21:]}/{file}"
            copy_source = {
                'Bucket': m.group('bucket'),
                'Key': copy_key
            }
            # construct the appropriate key, removing the /tiles/ prefix and stripping any folders from the
            # individual files (ex. R10m/B04.jp2 -> B04.jp2)
            dst_key = (f"{tile_prefix}_{os.path.basename(file)}")
            s3.meta.client.copy(copy_source, dst_bucket, dst_key, ExtraArgs={'RequestPayer': 'requester'})
        # send message to queue to start processing for this tile
        q.send_message(MessageBody = f"{dst_bucket}/{tile_prefix}")


""" Given a string, return that string padded with zeroes, if necessary.
    Useful for ensuring months/days all have the same length (3 -> 03). """
def pad_zeroes(string):
    if len(string) < 2:
        string = f"0{string}"
    return string


# download tiles locally
def download(downloads, bands=['R10m/B04', 'R10m/B08'], metafiles=['tileInfo', 'qi/MSK_CLOUDS_B00'], data_folder=".", collection="L2A"):
    # by default, select R/NIR bands, tile info metadata file, and cloud mask

    download = input(f"Download {len(downloads)} scene(s)? (Y/N) ")
    if download.lower() not in {'y', 'yes'}:
        return None

    if collection == "L2A":
        data_collection = DataCollection.SENTINEL2_L2A
    elif collection == "L1C":
        data_collection = DataCollection.SENTINEL2_L1C
    else:
        raise ValueError(f"unsupported collection: {collection}")

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
            data_collection = data_collection
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
    parser.add_argument("-cloud-max", "--cm", dest="cloud_max", type=float,
                        help="filter scenes by cloud cover")
    parser.add_argument("-boundary", "--b", metavar="path/to/geojson",
                        dest="boundary", type=Path,
                        help="path to geojson file with boundary of search")
    parser.add_argument("-collection", "--c", dest="collection", choices=["L2A", "L1C"],
                        help="collection of s2 images to choose from (top of atmosphere/surface reflectance")
    parser.add_argument("-dst", metavar="bucket", type=str,
                        help="s3 bucket to store downloaded scenes in")
    args = parser.parse_args()


    # credentials are needed to use SentinelHub API for search functionality.
    # if we can perform searching ourselves, credentials would not be necessary
    config = authenticate()

    print("Fetching scenes...")
    tile_list = search(config, date_range=args.date_range, boundary=args.boundary, collection=args.collection)
    # grab only desired files: R band, NIR band, metadata file, and cloud mask
    # files = ['R10m/B04.jp2', 'R10m/B08.jp2', 'tileInfo.json', 'qi/MSK_CLOUDS_B00.gml']
    files = ['B04.jp2', 'B08.jp2', 'tileInfo.json', 'qi/MSK_CLOUDS_B00.gml']

    if len(tile_list) == 0:
        print("No tiles matching the criteria were found.")
        return
    
    download = input(f"Copy {len(tile_list)} scene(s) to s3://{args.dst}? (Y/N) ")
    if download.lower() not in {'y', 'yes'}:
        return

    # downloaded = download(downloads)
    copy_to_s3(tile_list, args.dst, files, prefix=f"s2-{args.collection.lower()}")
    
    print("Done.")


if __name__ == "__main__":
    main()