import os

from osgeo import gdal
from sklearn.naive_bayes import GaussianNB
from sklearn import tree
import numpy as np
import boto3
import pickle


bucket = "processed-granules"
s3 = boto3.client('s3')


def get_data(file, bands):
    basename = os.path.basename(file)
    filepath = file.split('/')
    path = filepath[2]
    frame = filepath[3]
    year = filepath[4]

    tree_cover = f"/vsis3/{bucket}/tree_cover/{path}/{frame}/tree_cover_{year}_projected.tif"
    
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
    # randomly sample 50% of data, with replacement
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

    return data_labels


def main():
    files = []
    for file in s3.list_objects(Bucket=bucket, Prefix='s1/77/1191')['Contents']:
        # we have vv and vh both stored in a single folder. we want to process them at the same time
        # this will get us the directory that contains them
        file = os.path.dirname(f"{bucket}/{file['Key']}")
        if file not in files:
            files.append(file)
    # files = ["s1/77/1191/2020/12/S1B_IW_20201219T230453_DVP_RTC30_G_gpunem_62AC",
    #         "s1/77/1191/2020/06/S1B_IW_20200622T230450_DVP_RTC30_G_gpunem_CF74",
    #         "s1/77/1191/2021/12/S1B_IW_20211214T230459_DVP_RTC30_G_gpunem_0F44",
    #         "s1/77/1191/2021/06/S1B_IW_20210629T230456_DVP_RTC30_G_gpunem_D958"]

    # bands = ['VV', 'VH', 'INC'] # TODO: include inc
    bands = ['VV', 'VH']
    # data = []
    train_test_split = 0.9
    all_test_data = None
    all_test_labels = None
    model = GaussianNB()
    for file in files:
        # file = f"{bucket}/{file}"
        print(f"Fetching data for {file}...")
        data = get_data(file, bands)
        splitpoint = int(data.shape[0] * train_test_split)
        np.random.shuffle(data)
        train_data = data[:splitpoint, 1:]
        train_labels = data[:splitpoint, 0].astype(np.int16)
        test_data = data[splitpoint:, 1:]
        test_labels = data[splitpoint:, 0].astype(np.int16)

        model.partial_fit(train_data, train_labels, classes=[0, 1])

        if all_test_data is None:
            all_test_data = test_data
            all_test_labels = test_labels
        else:
            all_test_data = np.concatenate((all_test_data, test_data))
            all_test_labels = np.concatenate((all_test_labels, test_labels))

        # data.extend(get_data(file, bands))

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

    # # TODO: fine tune these
    # vv_threshold = 1.7
    # vh_threshold = 0.15
    # num_samples = 0
    # num_correct = 0
    # for features, label in zip(test_data, test_labels):
    #     if features[0] > vv_threshold and features[1] > vh_threshold:
    #         prediction = 1
    #     else:
    #         prediction = 0

    #     if prediction == label:
    #         num_correct += 1
    #     num_samples += 1
    
    # print(num_correct / num_samples)
    # model = tree.DecisionTreeClassifier()
    model.fit(train_data, train_labels)
    print(model.score(test_data, test_labels))
    
    model_filename = "s1_classifier_nb_all_vv-vh.pkl"
    with open(model_filename, 'wb') as file:
        pickle.dump(model, file)


if __name__ == "__main__":
    main()