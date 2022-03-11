from zipfile import ZipFile
import os
import glob
import kml2geojson
import ee
import json
import time
import math
import copy


datasets = ["LANDSAT/LC08/C01/T1"]
username = "bmiche01"

def kmz_to_geojson(kmz_file_paths):
    '''
    Takes in the kmz file paths, unzips them to kml files, 
        then converts them to geojson files, 
        then returns the new geojson file locations in a list
    '''
    geojson_paths = []
    for path in kmz_file_paths:
        kmz = ZipFile(path, "r")
        # takes the last part of path without the .kmz. Replaced spaces with unscores if necessary
        filename = os.path.split(path)[-1][:-4].replace(" ", "_")   
        new_file_path = ""
        for i, name in enumerate(kmz.namelist()):
            if i > 0:
                new_file_path = os.path.join("kml", filename + f"{i}.kml")
            else:
                new_file_path = os.path.join("kml", filename + ".kml")
            with open(new_file_path, 'wb') as kml_file:
                kml_file.write(kmz.open(name, 'r').read())
            kml2geojson.main.convert(new_file_path, 'geojson')
            geojson_path = os.path.join("geojson", f"{filename}.geojson")
            print("Generated " + geojson_path)
            geojson_paths.append(geojson_path)
    return geojson_paths


def geojson_to_earth_engine(geojson_file_paths):
    '''
    Takes in list file paths for geojson files
    Returns a list of earth engine objects, where each element of the list
        represents the feature or collection of features for each geojson file
    '''
    ee_objects = []
    for geojson_path in geojson_file_paths:
        with open(geojson_path, 'r') as json_file:
            geojson_dict = json.loads(json_file.read())
            if "Tracks" in geojson_path:
                # special dealings with lot file
                feature_type, feature_obj = geojson_feature_parser(geojson_dict, transform_to_polygons=True)
                try:
                    geojson_feature_string = json.dumps(feature_obj.getInfo())
                    # cut off extension and directory for new extension and directory
                    output_geojson_path = os.path.join("output_geojson", os.path.split(geojson_path.split(".")[0])[-1] + ".json")
                    with open(output_geojson_path, 'w') as output_geojson:
                        output_geojson.write(geojson_feature_string)
                except Exception as e:
                    print("Error attempting to convert ee object into geojson: ", e)
            else:
                feature_type, feature_obj = geojson_feature_parser(geojson_dict)
            if feature_type is None or feature_obj is None: # this c
                print(f"Full file {geojson_path} returned invalid features")
                continue
            ee_objects.append(feature_obj)
    return ee_objects


def geojson_feature_parser(gj, transform_to_polygons=False):
    '''
    Takes in full initial geojson and parses it into earth engine types:
        FeatureCollection
        Feature
    Returns object in the form: feature_type : str, feature_object : ee object
    '''
    if type(gj) is not dict:
        print(f"json structure is not a dict it is a {str(type(gj))}")
        return None
    if gj["type"] == "FeatureCollection":
        feature_list = []
        for json_feature in gj["features"]: # assumes it has the features member
            if json_feature["type"] != "Feature":
                raise Exception("geojson_feature_parser: not a feature type: " + json_feature["type"])
                continue
            feature_type, feature_obj = geojson_feature_parser(json_feature)
            if feature_type is None or feature_obj is None:
                continue
            # can check if feature_type is "Feature", but likely unecessary
            feature_list.append(feature_obj)
        if len(feature_list) == 0:
            raise Exception("Attempt to return empty feature collection")
        if transform_to_polygons: # used for the lot data
            feature_list = turn_lots_into_polygons(feature_list)
        return "FeatureCollection", ee.FeatureCollection(feature_list)
    elif gj["type"] == "Feature":
        # Need to turn into Feature object
        geometry_type, geometry = geojson_geometry_parser(gj["geometry"])
        if geometry_type is None or geometry is None: # single point line string
            return None, None
        properties = gj["properties"]
        return "Feature", ee.Feature(geometry, properties)
        # type not used now, but might be useful
    else:
        raise Exception("geojson_feature_parser: unhandled type: " + gj["type"])


class Haversine:
    '''
    from: https://nathanrooy.github.io/posts/2016-09-07/haversine-with-python/

    use the haversine class to calculate the distance between
    two lon/lat coordnate pairs.
    output distance available in kilometers, meters, miles, and feet.
    example usage: Haversine([lon1,lat1],[lon2,lat2]).feet
    
    '''
    def __init__(self,coord1,coord2):
        lon1,lat1=coord1
        lon2,lat2=coord2
        
        R=6371000                               # radius of Earth in meters
        phi_1=math.radians(lat1)
        phi_2=math.radians(lat2)

        delta_phi=math.radians(lat2-lat1)
        delta_lambda=math.radians(lon2-lon1)

        a=math.sin(delta_phi/2.0)**2+\
           math.cos(phi_1)*math.cos(phi_2)*\
           math.sin(delta_lambda/2.0)**2
        c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))
        
        self.meters=R*c                         # output distance in meters
        self.km=self.meters/1000.0              # output distance in kilometers
        self.miles=self.meters*0.000621371      # output distance in miles
        self.feet=self.miles*5280               # output distance in feet

def turn_lots_into_polygons(features):
    '''
    Takes in a list of ee feature objects
    If any objects contain points that are within the tolerance of each other,
        then these objects are combined into one polygon

    TOLERANCE = 10 meters (honestly if I could get this into a reliable lat, long magnitude, that'd be good)

    (broadly going to ignore single points)
    for each feature (f1):
        list_of_points_to_form_polygon = coordinates of feature
        if this feature has been seen or marked off:
            continue
        otherwise:
            mark it as seen
            if its a single point:
                continue
            for each point in f1 (p1):
                for each feature (f2):
                    if this feature has been seen or marked off:
                        continue
                    otherwise:
                        if its a single point:
                            continue
                        for each point in this f2 (p2):
                            if p1 and p2 are within the tolerance (this means we need to combine features):
                                list_of_points_to_form_polygon.extend(all the coordinates from f2)
                                break
    '''
    BUFFER = 10  # buffer to expand lot polygons by (in meters)
    # How far apart lots must be to be combined into one polygon, 2.1*BUFFER as to not have buffered polygons overlap
    TOLERANCE = 2.1 * BUFFER  
    
    temp_list = [12, 20, 79, 91]
    temp_list2 = [902, 1326, 138, 126]
    print('Number of features:', len(features))
    time.sleep(2)
    new_feature_list = []
    skip_dict = {}      # an attempt to not edit the list while iterating through it in order to ignore features we've already turned into polygons
    for i, feature in enumerate(features):
        if i not in temp_list:
            continue
        print('top feature', i)
        if i in skip_dict:
            continue
        feature_info = feature.getInfo()
        skip_dict[i] = True
        coordinates = get_feature_coordinates(feature_info)
        if coordinates is None:
            continue
        coordinates_to_combine = copy.deepcopy(coordinates)    # beware deep copy
        if id(coordinates[0]) == id(coordinates_to_combine[0]):
            print(type(coordinates[0]))
            raise Exception("Deep copy failed")
        t1 = time.perf_counter()
        for j, nested_feature in enumerate(features):
            #print('nested feature', j)
            if j not in temp_list2:
                continue
            if j in skip_dict:
                continue
            nested_feature_info = nested_feature.getInfo()
            nested_coordinates = get_feature_coordinates(nested_feature_info)
            if nested_coordinates is None:
                continue
            coords_combined = False
            for c1 in coordinates:
                if coords_combined:
                    break
                for c2 in nested_coordinates:
                    if within_tolerance(TOLERANCE, c1, c2):
                        print(f'collision between features {i} and {j}:', c1, c2)
                        coordinates_to_combine.extend(nested_coordinates)
                        coords_combined = True
                        skip_dict[j] = True
                        break
        t2 = time.perf_counter()
        print('time elapsed:', t2-t1, 'seconds')
        polygon = ee.Geometry.Polygon(remove_duplicate_coordinates(coordinates_to_combine))
        #polygon = polygon.buffer(BUFFER)
        new_feature_list.append(polygon)
    return new_feature_list

def remove_duplicate_coordinates(coords):
    '''
    Takes in a list of coordinates: [[lat1, long1], [lat2, long2], ...]
    Removes duplicate coordinates in the list,
        then duplicates the first coordinate to complete the polygon path
    '''
    # how close can coords be for them to be the same
    tolerance = 0.0000001 # ~ couple inches max difference, default float eq is more precise
    if len(coords) < 2: # might wanna raise an exception
        return coords
    new_coords = []
    skip_list = []
    for i, c1 in enumerate(coords):
        if i in skip_list:
            continue
        skip_list.append(i)
        new_coords.append(c1)
        for j, c2 in enumerate(coords):
            if j in skip_list:
                continue
            if math.isclose(c1[0], c2[0], rel_tol=tolerance) and math.isclose(c1[1], c2[1], rel_tol=tolerance):
                # c2 is a duplicate of c1
                skip_list.append(j)
    new_coords.append(new_coords[0])
    return new_coords
    

def get_feature_coordinates(feature_info):
    ''' 
    Returns a list of coordinates from a ee feature object's info ( Feature.getInfo() )
    Returns None if the feature is a point or unhandled geometry type or if there is 1 or less coordinates
    '''
    if feature_info['geometry']['type'] == 'Point':  # ignore single points
        return None
    elif feature_info['geometry']['type'] == 'LinearRing':
        coordinates = feature_info['geometry']['coordinates']
        if len(coordinates) > 1:
            return coordinates
        return None
    elif feature_info['geometry']['type'] == 'LineString':
        coordinates = feature_info['geometry']['coordinates']
        if len(coordinates) > 1:
            return coordinates
        return None
    else:
        print("Unhandled geometry: ", feature_info['geometry']['type'])
        return None


def within_tolerance(tolerance, c1, c2):
    ''' Checks if two coordinates are within the tolerance of each other (assumes meters)'''
    if Haversine(c1,c2).meters <= tolerance:
        return True
    return False


def geojson_geometry_parser(geometry):
    ''' 
    Turns GeoJSON geometry into an ee.Geometry() object.
    Our kmz files inlcude elevation data for each coordinate, which GEE does
    not seem to support. Consequently, we must remove this data before
    creating the geometry object.
    '''
    geometry["coordinates"] = remove_altitude(geometry["coordinates"])
    # some of the LineStrings only have one point, GEE will throw an error at this
    if geometry["type"] == "LineString" and len(geometry["coordinates"]) < 2:
        # returning Nones because a single point is not helpful for forming polygons
        return None, None
        #geometry["type"] = "Point"
        #geometry["coordinates"] = geometry["coordinates"][0]
    return geometry["type"], ee.Geometry(geometry)


def remove_altitude(coordinates):
    '''
    Given either a coordinate or a list of coordinates, recursively strip the
    elevation data from each coordinate.
    GeoJSON spec defines a coordinate as a list containing [long, lat, elevation (optional)].
    GEE does not seem to support elevation data, so we must strip it before creating
    GEE objects.
    '''
    stripped_coords = []
    # first, check if we are dealing with a coordinate or list of coordinates
    if type(coordinates[0]) is list:
        for coord in coordinates:
            stripped_coords.append(remove_altitude(coord))
    else:
        # if there is an elevation value, remove it
        if len(coordinates) == 3:
            stripped_coords = coordinates[0:2]
        else:
            stripped_coords = coordinates
    return stripped_coords



def export_ee_assets(ee_obj, name):
    '''
    Given a GEE object in memory and a name, uploads it to GEE so you can access it in the
    code editor.
    NOTE: change {username} to your Google username.
    '''
    name = os.path.split(os.path.splitext(name)[0])[-1] # remove extension and folder
    if "racks" in name:     # temp update to signify line string to polygon conversion in earth engine
        name += "_polygons"
    task = ee.batch.Export.table.toAsset(collection=ee_obj, description=name, assetId=(f"users/{username}/" + name))
    task.start()
    print("Uploading " + name + " to GEE...")


def main():
    ee.Initialize()
    kmz_file_paths = glob.glob(f"kmz{os.path.sep}*")
    print(kmz_file_paths)
    # TODO: only need to generate geojson files once, maybe split into separate script
    print("Converting kmz files to geoJSON files...")
    geojson_file_paths = kmz_to_geojson(kmz_file_paths)
    print("Generating GEE objects...")
    ee_objects = geojson_to_earth_engine(geojson_file_paths)
    for obj, name in zip(ee_objects, geojson_file_paths):
        export_ee_assets(obj, name)
    
    
if __name__ == "__main__":
    main()