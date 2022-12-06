import sys
import re
import os

import ee
import boto3
from osgeo import gdal

# allow imports from sibling directories
sys.path.insert(0, "../util/")
from get_bounds import get_bounds

def main():
    ee.Initialize()
    tree_cover = ee.Image('UMD/hansen/global_forest_change_2021_v1_9')
    gain = tree_cover.select('gain')
    loss = tree_cover.select('lossyear')
    fmask = tree_cover.select('treecover2000').gt(10).where(gain.eq(1), gain)

    s3 = boto3.client('s3')
    src_bucket = 'processed-granules'
    s1_name_pattern = re.compile(r"""
                (?:s1/)
                (?P<path>\d{1,4})
                (?:/)
                (?P<frame>\d{1,4})
                (?:/)
                (?P<year>\d{4})
                (?:/)
                (?P<remainder>.*\.tif)
                """, re.VERBOSE)
    
    # export one TC image for every path_frame_year combo
    existing = s3.list_objects(Bucket='processed-granules', Prefix='tree-cover')['Contents']
    existing = set([os.path.basename(file['Key'])[11:-4] for file in existing])
    
    for file in s3.list_objects(Bucket=src_bucket, Prefix='s1')['Contents']:
        m = s1_name_pattern.match(file['Key'])
        if m:
            path = m.group('path')
            frame = m.group('frame')
            year = m.group('year')
            path_frame_year =  path + '_' + frame + '_' + year
            if path_frame_year not in existing:
                existing.add(path_frame_year)
                filename = f"/vsis3/{src_bucket}/{file['Key']}"

                bounds = ee.List(get_bounds(filename))
                ds = gdal.Open(filename)
                proj = ds.GetProjection()
                gt = ds.GetGeoTransform()
                # because gdal and gee having the same transform format would be too easy
                gt_gee = [gt[1], 0, -180, 0, gt[5], 80]
                geom = ee.Geometry.Polygon(bounds, proj, False)

                year_two_digits = int(year) - 2000
                fmask_clipped = fmask.where(loss.lte(year_two_digits), 0).clip(geom)

                task_name = f"tree_cover_{path}_{frame}_{year}"
                print(f"Exporting {task_name}...")
                # GEE doesn't let you export to s3, so files will have to be manually copied
                task = ee.batch.Export.image.toDrive(
                        image=fmask_clipped,
                        description=task_name,
                        folder='tree-cover',
                        crs=proj,
                        crsTransform=gt_gee,
                        region=geom,
                        shardSize=1024,
                        fileDimensions=131072)
                task.start()
    print("All tasks started. Download .tifs from the 'tree-cover'\n"
            "folder in your Google Drive and upload them manually to s3.")


if __name__ == '__main__':
    main()