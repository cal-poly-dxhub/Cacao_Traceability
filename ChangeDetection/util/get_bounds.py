from osgeo import gdal
from osgeo import osr


# get the corner coordinates of a raster image
def get_bounds(file):
    ds = gdal.Open(file)
    min_x, xres, xskew, max_y, yskew, yres = ds.GetGeoTransform()
    max_x = min_x + (ds.RasterXSize * xres)
    min_y  = max_y + (ds.RasterYSize * yres)

    # upper left, upper right, lower right, lower left, upper left
    return [[[min_x, max_y], [max_x, max_y], [max_x, min_y], [min_x, min_y], [min_x, max_y]]]


# reproject a set of coordinates to a different spatial reference
def reproject(coords, source_img, target_epsg=4326):
    # get the source spatial reference from the image
    ds = gdal.Open(source_img)
    source_ref = osr.SpatialReference()
    source_ref.ImportFromWkt(ds.GetProjection())

    target_ref = osr.SpatialReference()
    target_ref.ImportFromEPSG(target_epsg)

    transform = osr.CoordinateTransformation(source_ref, target_ref)

    transformed_coords = []
    for coord in coords:
        lat, lon, _ = transform.TransformPoint(coord[0], coord[1])
        transformed_coords.append((lon, lat))
    
    return transformed_coords


def main():
    file = "test.tif"
    bounds = get_bounds(file)
    print(bounds)

    coords = reproject(bounds, file)
    print(coords)


if __name__ == "__main__":
    main()