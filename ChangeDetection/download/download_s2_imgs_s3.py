import argparse
import boto3
import os
import datetime
from dateutil.parser import parse as parse_date

'''
full example CLI command: aws s3 ls s3://sentinel-s2-l2a/tiles/18/N/WM/2021/10/10/0/R10m/B04.jp2 --request-payer requester --region eu-central-1

prefix defined using: tiles/[UTM code]/latitude band/square/[year]/[month]/[day]/[sequence]/DATA
   from: https://roda.sentinel-hub.com/sentinel-s2-l2a/readme.html

all farm points/geometries exist under the two tiles:
    18NWM (left)
        MULTIPOLYGON(((-75.0001808311513 6.33304216613588,-75.0001805130999 5.33975051433054,-74.0092137321756 5.33895147179259,-74.007468385398 6.33209340998613,-75.0001808311513 6.33304216613588)))
    18NXM (right)
        MULTIPOLYGON(((-74.0958824705718 6.33225490763692,-74.0974723969699 5.33908748516154,-73.1067674643747 5.33683314603249,-73.1034341557557 6.3295781838079,-74.0958824705718 6.33225490763692)))
'''


def checkExistence(s3_client, bucket, target_prefix):
    '''
    Checks if object with given prefix exists in bucket. Assumes request payer.
    '''
    response = s3_client.list_objects_v2(
        Bucket=bucket, 
        MaxKeys=1, 
        Prefix=target_prefix, 
        RequestPayer='requester')
    if 'Contents' in response:
        return True
    else:
        return False


def download(destination_bucket: str, start_date: datetime.datetime, end_date: datetime.datetime, tiles: list, files: list):
    '''
    Downloads the provided files from each of the provided tiles for all the dates in between and including
        the start and end date. Assumes request payer.
    '''
    target_bucket ='sentinel-s2-l2a'    
    
    s3_client = boto3.client("s3")
    temp_date = start_date
    while temp_date.date() <= end_date.date():
        date_str = f"{temp_date.year}/{temp_date.month}/{temp_date.day}/0/"  # 0 indicates it is the first grouping of images (never saw more than one)
        for tile in tiles:
            for file in files:
                target_prefix = f'tiles/{tile}{date_str}{file}'
                destination_prefix = f"sentinel-2/{tile}{date_str}{os.path.basename(file)}"
                if checkExistence(s3_client, target_bucket, target_prefix):
                    s3_client.copy(
                         {
                             'Bucket': target_bucket,
                             'Key': target_prefix
                         },
                        destination_bucket, 
                        destination_prefix,
                        ExtraArgs={'RequestPayer': 'requester'})
                else:
                    print(f"No {file} found within {tile} for {temp_date.date()}")
        temp_date += datetime.timedelta(days=1)
        

def main():
    parser = argparse.ArgumentParser(
        description="Search for and download L8 scenes that match criteria.")
    
    parser.add_argument("-date-range", "--dr", metavar=("start", "end"), 
                        dest="date_range", nargs=2, type=str,
                        help="filter scenes by acquisition date (format: yyyy-mm-dd yyyy-mm-dd)")
    parser.add_argument("-dst", metavar="bucket", type=str,
                        help="s3 bucket to store downloaded scenes in")
    args = parser.parse_args()
    
    start_date = parse_date(args.date_range[0])
    end_date = parse_date(args.date_range[1])
    
    left = '18/N/WM/'   # see note at top of file
    right = '18/N/XM/'
    tiles = [left, right]
    # grab only desired files: R band, NIR band, metadata file, and cloud mask   
    files = ['R10m/B04.jp2', 'R10m/B08.jp2', 'tileInfo.json', 'qi/MSK_CLOUDS_B00.gml']
    
    download(args.dst, start_date, end_date, tiles, files)
    
    print("Done.")

if __name__ == "__main__":
    main()
