import argparse
import os
import re
import boto3


def main():
    parser = argparse.ArgumentParser(
        description="Create a .csv file containing granules that match the criteria.")
    
    parser.add_argument("bucket", type=str,
                        help="s3 bucket granules are stored in (ex. processed-granules)")
    parser.add_argument("dataset", type=str,
                        help="dataset to use (ex. landsat, s2-l2a, s2-l1c)")
    parser.add_argument("prefix", type=str,
                        help="geographical prefix (usually a path/frame combo, like 008/056/)")
    parser.add_argument("-csv", type=str,
                        help="name of output csv file")
    args = parser.parse_args()

    s3 = boto3.client('s3')
    prefix = os.path.join(args.dataset, args.prefix).replace('\\', '/')
    response = s3.list_objects(Bucket=args.bucket, Prefix=prefix)
    
    csv = args.csv
    if not csv:
        csv = f"{args.dataset}-{args.prefix}-granules.csv".replace('/', '-').replace('--', '-')

    with open(csv, 'w') as csv:
        csv.write("bucket,key,date\n")
        count = 0
        for key in response['Contents']:
            granule = key['Key']
            month = os.path.basename(os.path.dirname(granule))
            year = os.path.basename(os.path.dirname(os.path.dirname(granule)))
            
            date_pattern = re.compile(rf"""
                (?P<year>{year})
                (?P<month>{month})
                (?P<day>\w\w)
                """, re.VERBOSE)
            m = date_pattern.search(granule)
            if m:
                date = f"{year}-{month}-{m.group('day')}"
                csv.write(f"{args.bucket},{granule},{date}\n")
                count += 1
            else:
                print(f"Could not find date of {granule}")
        
        print(f"Found {count} granules.")


if __name__ == "__main__":
    main()
