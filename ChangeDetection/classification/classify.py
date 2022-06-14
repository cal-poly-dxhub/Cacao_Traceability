import os
import sys

from osgeo import gdal
import boto3
import pickle
import numpy as np

sys.path.insert(0, "../util/")
from arr_to_gtiff import arr_to_gtiff

bucket = "processed-granules"
s3 = boto3.client('s3')

classifier = "s1_classifier_nb_all_vv-vh.pkl"
mode = "nb_all"


def classify(file, bands, model):
    basename = os.path.basename(file)
    print(f"Generating forest mask for {file}...")

    files = []
    for band in bands:
        files.append(f"/vsis3/{file}/{basename}_{band}_FILTERED.tif")

    original_shape = None
    imgs = []
    for i in range(0, len(files)):
        ds = gdal.Open(files[i])
        arr = ds.GetRasterBand(1).ReadAsArray()
        if not original_shape:
            original_shape = arr.shape
        imgs.append(arr.reshape(-1))
        ds = None
    
    # drop all nan values
    data = np.column_stack(imgs)
    length = data.shape[0]
    mask = np.all(np.logical_not(np.isnan(data)), axis=1)
    
    test_data = data[mask]
    preds = model.predict(test_data)
    classified = np.full((length,), np.nan, dtype=np.float32)
    classified[mask] = preds
    classified = classified.reshape(original_shape)
    
    outname = f"{basename}_FMASK_{mode}.tif"
    arr_to_gtiff(classified, outname, files[0], dtype=gdal.GDT_Int16)

    # upload to s3
    bucket = "classified-granules"
    _, key = file.split('/', 1)
    key = f"{key}_FMASK_{mode}.tif"
    s3.upload_file(outname, bucket, key)
    print(f"Uploaded {key} to {bucket}.")
    os.remove(outname)
    


def main():
    files = []
    for file in s3.list_objects(Bucket=bucket, Prefix='s1/77/1191/2021')['Contents']:
        # we have vv and vh both stored in a single folder. we want to process them at the same time
        # this will get us the directory that contains them
        file = os.path.dirname(f"{bucket}/{file['Key']}")
        if file not in files:
            files.append(file)
    
    with open(classifier, 'rb') as clf:
        model = pickle.load(clf)
    
    bands = ['VV', 'VH']
    for file in files:
        classify(file, bands, model)
    

if __name__ == "__main__":
    main()