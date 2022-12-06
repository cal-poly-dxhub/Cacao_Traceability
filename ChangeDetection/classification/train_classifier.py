import os
import re

from osgeo import gdal
from sklearn.naive_bayes import GaussianNB
from sklearn import tree
import numpy as np
import boto3
import pickle


bucket = "processed-granules"
s3 = boto3.client('s3')

# avoid using granules we don't have labels for
tc_labels = s3.list_objects(Bucket='processed-granules', Prefix='tree-cover')['Contents']
tc_labels = set([os.path.basename(file['Key']) for file in tc_labels])

def get_data(file, bands):
    basename = os.path.basename(file)
    filepath = file.split('/')
    path = filepath[2]
    frame = filepath[3]
    year = filepath[4]

    tc_basename = f"tree_cover_{path}_{frame}_{year}.tif"
    if tc_basename not in tc_labels:
        print(f"No tree cover labels found for {file}. Skipping...")
        return None, None

    tree_cover = f"/vsis3/{bucket}/tree-cover/{path}/{frame}/{tc_basename}"
    
    vrt_files = [tree_cover]
    for band in bands:
        vrt_files.append(f"/vsis3/{file}/{basename}_{band}_FILTERED.tif")

    # build temp vrt to handle differences in spatial extent
    combined_file = "combined.vrt"
    combined_vrt = gdal.BuildVRT(combined_file, vrt_files, separate=True)
    # flush cache
    combined_vrt = None

    combined = gdal.Open(combined_file)
    tc = combined.GetRasterBand(1).ReadAsArray().reshape(-1)
    # randomly sample 10% of data, with replacement
    sample_pct = 0.1
    num_samples = int(tc.size * sample_pct)
    rng = np.random.default_rng()
    samples = rng.integers(low=0, high=tc.size, size=num_samples)

    tc = tc[samples]

    imgs = [tc]
    for i in range(2, len(bands) + 2):
        imgs.append(combined.GetRasterBand(i).ReadAsArray().reshape(-1)[samples])
    
    # drop all nan values
    data_labels = np.column_stack(imgs)
    mask = np.any(np.isnan(data_labels), axis=1)
    data_labels = data_labels[~mask]

    return data_labels[:, 1:], data_labels[:, 0]


def main():
    files = set()
    for file in s3.list_objects(Bucket=bucket, Prefix='s1')['Contents']:
        # we have vv and vh both stored in a single folder. we want to process them at the same time
        # this will get us the directory that contains them
        files.add(os.path.dirname(f"{bucket}/{file['Key']}"))

    # bands = ['VV', 'VH', 'INC'] # TODO: include inc
    bands = ['VV', 'VH']
    # data = []
    all_test_data = None
    all_test_labels = None
    model = GaussianNB()

    for file in files:
        print(f"Fetching data for {file}...")
        data, labels = get_data(file, bands)
        if data is None or labels is None:
            continue

        year = file.split('/')[4]
        if year == 2021: # use 2021 as testing data
            if all_test_data is None:
                all_test_data = test_data  
                all_test_labels = test_labels
            else:
                all_test_data = np.concatenate((all_test_data, test_data))
                all_test_labels = np.concatenate((all_test_labels, test_labels))
        else:
            # data.extend(get_data(file, bands))
            model.partial_fit(data, labels, classes=[0, 1])

    test_data = all_test_data
    test_labels = all_test_labels
    # data = np.asarray(data)
    # np.random.shuffle(data)
    
    # # train_test_split = 0.9
    # splitpoint = int(data.shape[0] * train_test_split)
    
    # train_data = data[:splitpoint, 1:]
    # train_labels = data[:splitpoint, 0].astype(np.int16)
    # test_data = data[splitpoint:, 1:]
    # test_labels = data[splitpoint:, 0].astype(np.int16)

    # print(train_data)
    # print(train_labels)
    # print(test_data)
    # print(test_labels)

    # print(num_correct / num_samples)
    # model = tree.DecisionTreeClassifier()
    # model.fit(train_data, train_labels)
    print(model.score(test_data, test_labels))
    
    model_filename = "s1_classifier_nb_all_vv-vh.pkl"
    with open(model_filename, 'wb') as file:
        pickle.dump(model, file)


if __name__ == "__main__":
    main()