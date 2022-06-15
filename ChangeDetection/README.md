# Forest Cover Change Detection using S1 Imagery -- the Wolf Algorithm

## Contributions

These routines were written by Remy Wolf with contributions from Braden Michelson, Richard Chen, Lemar Popal, and Harmeen Singh. It was developed by Cal Poly's Digital Transformation Hub for use by the World Bank. It borrows some code and concepts from the [VegMapper repo](https://github.com/NaiaraSPinto/VegMapper). Further inspiration and ideas were taken from Andrew Fricker and Jonathan Ventura of Cal Poly, Naiara Pinto of JPL, and Matt Hansen and Amy Pickens of the University of Maryland.

## Motivation

In order to improve traceability and sustainability in the cacao supply chain, we needed a system of monitoring forest canopy cover near cacao plantations to ensure that farmers are not contributing to deforestation. This system would need to 1) detect changes within a few weeks of them occuring, and 2) have a high enough resolution to be useful when monitoring relatively small cacao plantations (sometimes no bigger than one hectare). While already existing tools, like [Global Forest Watch's RADD Alerts](https://www.wur.nl/en/Research-Results/Chair-groups/Environmental-Sciences/Laboratory-of-Geo-information-Science-and-Remote-Sensing/Research/Sensing-measuring/RADD-Forest-Disturbance-Alert.htm), provide similar functionality, they only work in areas with dense forest cover, which did not include our area of interest. Furthermore, initial attempts were made to detect changes in forest cover using Landsat-8 and Sentinel-2, but constant cloud cover in the tropics made obtaining frequent observations difficult. Consequently, we decided to build such a system from the ground up using Sentinel-1 imagery. Sentinel-1, using SAR technology, is able to penetrate through clouds and has a high enoguh spatial (30m) and temporal (1-2 weeks) resolution to be useful for this task.

## Algorithm Overview

1) Define area of interest
2) Search for new Sentinel-1 granules
3) Download/process Sentinel-1 granules, and create 3-band data stack (VV/VH/INC):
   * Perform Radiometric Terrain Calibration (RTC) processing using [ASF's HyP3 API](https://hyp3-docs.asf.alaska.edu/)
   * Reduce speckle on VV/VH bands using an Enhanced Lee Filter
   * Calculate standard deviation of neighborhood of pixels on incidence angle map
5) Train decision tree classifier using random sample of processed pixels, using [Matt Hansen's Global Forest Change Map](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2021_v1_9?hl=en) as training labels
6) Classify new granules on a per-pixel basis as forest/non-forest
7) Compare three most recent observations to known forest basemap to estimate confidence of forest loss

## Walkthrough and Examples

1) Create cacao conda environment:
   * `conda env create -f cacao-env.yml`
   * `conda activate cacao`
3) Search for Sentinel-1 granules and submit jobs for HyP3 RTC processing: 
   * `cd download`
   * `python download_s1_imgs.py [boundary] [start] [end]`
4) Process Sentinel-1 granules using Enhanced Lee Filter (VV/VH bands) and standard deviation of neighborhood of pixels (INC map band): 
   * `cd ../processing/`
   * `python s1_batch.py`
   * NOTE: this step should automatically be handled by the `s1_lambda.py` function deployed to AWS Lambda. However, Lambda occassionally seems to error out or skip granules when a high volume of granules are submitted for processing. If this happens, use `s1_batch.py` to process the remaining granules. This is a known issue and is being investigated.
5) Train decision tree classifier: 
   * `cd ../classification/`
   * `python train_classifier.py`
6) Classify new granules:
   * `python classify.py`
7) Estimate confidence of forest loss:
   * `cd ../util/`
   * `python make_csv.py [bucket] [dataset] [prefix] [-s search-term] [-csv csv-name]`
   * `cd ../classification/`
   * `python forest_change.py [date] [csv]`

More documentation and examples coming soon...

## Future Improvements

* Creating training labels manually using random sampling of data from variety of dates instead of using Hansen's dataset
* Creating our own known forest basemap instead of using Hansen's dataset
* Reduce variance in S1 images, either by considering neighborhood of pixels or by using temporal mean of 2/3 most recent observations
* Improving classifier by incorporating more training data or using more complex classification method (random forest, convolutional neural network, etc)
* Postprocessing classified images to eliminate standalone pixels
* Incorporating [Nasa's NISAR](https://nisar.jpl.nasa.gov/) satellite once it goes online in 2024 
