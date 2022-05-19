from pathlib import Path
import os

import numpy as np
import rasterio

# Enhanced Lee filter for speckle reduction.
def enhanced_lee(file, lee_win_size=5, lee_num_looks=1):
    bands = []
    # Process backscatter (VV/VH)
    for pq in ['VV', 'VH']:
        # Read in DN
        basename = os.path.splitext(os.path.basename(file))[0]
        dn_raster = f"{file}/{basename}/{basename}_{pq}.tif"
        with rasterio.open(dn_raster) as dset:
            dn = dset.read(1).astype(np.float64)
            print(dn)
            mask = dset.read_masks(1)
            dn[mask == 0] = np.nan
            profile = dset.profile

        # Convert DN to gamma0
        g0 = dn**2 * 100

        # Filter gamma0 using enhanced Lee filter
        g0_filtered = enhanced_lee(g0, lee_win_size, lee_num_looks, nodata=np.nan)

        # Write to GeoTIFF
        profile.update(driver='GTiff', dtype=np.float32, nodata=np.nan)
        g0_filtered_tif = Path(f'{basename}_{pq}_filtered.tif')
        with rasterio.open(g0_filtered_tif, 'w', **profile) as dset:
            dset.write(g0_filtered.astype(np.float32), 1)

        bands.append(g0_filtered_tif)
    
    return bands


def main():
    # parser = argparse.ArgumentParser(
    #     description='processing ALOS/ALOS-2 yearly mosaic data'
    # )
    # parser.add_argument('proj_dir', metavar='proj_dir',
    #                     type=str,
    #                     help=('project directory (s3:// or gs:// or local dirs); '
    #                           'ALOS/ALOS-2 mosaic data (.tar.gz) are expected '
    #                           'to be found under proj_dir/alos2_mosaic/year/tarfiles/'))
    # parser.add_argument('year', metavar='year',
    #                     type=int,
    #                     help='year')
    # parser.add_argument('--filter_win_size', metavar='win_size',
    #                     type=int,
    #                     default=5,
    #                     help='Filter window size')
    # parser.add_argument('--filter_num_looks', metavar='num_looks',
    #                     type=int,
    #                     default=1,
    #                     help='Filter number of looks')
    # args = parser.parse_args()

    # proc_tiles(args.proj_dir, args.year, args.filter_win_size, args.filter_num_looks)
    # Project directory on S3
    
    # file = "..\\downloaded\\s1_asf\\77_1191\\S1B_IW_20200118T230446_DVP_RTC30_G_gpunem_ED01.zip"
    file = "/vsizip/vsis3/vegmapper-test/colombia/sentinel_1/2020/150_1191/S1B_IW_20201001T231307_DVP_RTC30_G_gpunem_4B05.zip"
    vv, vh = enhanced_lee(file)
    print(vv)
    print(vh)


if __name__ == '__main__':
    main()