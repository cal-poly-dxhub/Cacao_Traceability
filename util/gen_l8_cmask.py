import argparse

from osgeo import gdal
import numpy as np

from processing_utils import arr_to_gtiff


def main():
    parser = argparse.ArgumentParser(
        description="Generate the cloud mask for a Landsat-8 image.")
    
    parser.add_argument("qa_file", type=str,
                        help="location of the qa_pixel file")
    args = parser.parse_args()

    qa_ds = gdal.Open(args.qa_file)
    qa = qa_ds.GetRasterBand(1).ReadAsArray()
    
    # calculate cloud mask
    # bits 3 and 4 are cloud and cloud shadow, respectively
    dilated_cloud_bit = 1 << 1
    cirrus_bit = 1 << 2
    cloud_bit = 1 << 3
    cloud_shadow_bit = 1 << 4
    bit_mask = dilated_cloud_bit | cirrus_bit | cloud_bit | cloud_shadow_bit
    cloud_mask = ((np.bitwise_and(qa, bit_mask) != 0) * 1).astype(np.int16)

    arr_to_gtiff(cloud_mask, "cloud_mask.tif", args.qa_file)


if __name__ == "__main__":
    main()