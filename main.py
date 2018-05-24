#!exif_flask/bin/python
from flask import Flask, render_template, request
import glob,requests,json
from PIL import Image
from PIL.ExifTags import TAGS,GPSTAGS
from flask_googlemaps import GoogleMaps, Map, icons
from collections import OrderedDict
from helper import convertToDegree
from wtforms import Form, StringField

app = Flask(__name__, static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD']=True
GoogleMaps(app, key="AIzaSyDGL7SEwEfA5FiBl20amqHJx2_Z_yAbEg4")
GMAPS_API_KEY = "AIzaSyDGL7SEwEfA5FiBl20amqHJx2_Z_yAbEg4"

def getImageData():
    gps_datas = []
    for f in glob.glob('./img/*.jpg'):
        data = Image.open(f)._getexif()
        if data:
            for tag, val in data.items():
                decoded = TAGS.get(tag,tag)
                gps_data = {}
                if decoded == "DateTimeOriginal": 
                    gps_data['datetime'] = val
                if decoded == "GPSInfo":
                    for t in val:
                        sub_decoded = GPSTAGS.get(t,t)
                        gps_data[sub_decoded] = val[t]
                    gps_data['infobox'] = "<img src='/static%s' style='height:100px;width:auto;'/>" % f[1:]
                    print(gps_data)
                    gps_datas.append(gps_data)
    return gps_datas; # as [ {"datetime": 4398024, "gpslat": 234938, gpslatref:234923, ...}, {file}, {file}]

def getCoordinates(data):
    lat = None
    lon = None
    coords = []
    if data:
        for item in data:
            if "GPSLatitude" in item: lat = item["GPSLatitude"] 
            if "GPSLatitudeRef" in item: lat_ref = item["GPSLatitudeRef"]
            if "GPSLongitude" in item: lon = item["GPSLongitude"] 
            if "GPSLongitudeRef" in item: lon_ref = item["GPSLongitudeRef"]
 
            if lat and lat_ref and lon and lon_ref:
                lat = convertToDegree(lat)
                if lat_ref != "N":                     
                    lat = 0 - lat

                lon = convertToDegree(lon)
                if lon_ref != "E":
                    lon = 0 - lon
            coords.append({"infobox": item["infobox"], "date": item["GPSDateStamp"],"lat":lat, "lon":lon})
        return coords
    else:
        return None;

def getAddresses(coords):
    for coord in coords:
        req = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&key=%s" % (str(coord["lat"]), str(coord["lon"]), GMAPS_API_KEY)).json()['results'][1]
        coord['address'] = req['formatted_address']
    return coords

def sortVisits(info):
    addrs = {}
    for curr in info:
        if curr['address'] in addrs:
            addrs[curr['address']]['visits'] += 1
            addrs[curr['address']]['infobox'] += curr['infobox']
        else:
            addrs[curr['address']] = curr
            addrs[curr['address']]['visits'] = 1
    ordered_addrs = OrderedDict(sorted(addrs.items(), key=lambda t: t[1]['visits'], reverse=True))
    return ordered_addrs

def sortDates(info):
    addrs = sorted(info, key=lambda k: k['date'], reverse=True)
    addrs_dict = {}

    for curr in addrs:
        addrs_dict[curr['address']] = curr
    return addrs_dict

@app.route('/', methods=['GET', 'POST'])
def main():
    data = getImageData()
    coords = getCoordinates(data)
    print(coords)
    info = getAddresses(coords)
    print(info)

    # do the sorting
    sortby = request.args.get('sort', '')
    if sortby == 'visits':
        info=sortVisits(info)
    else: 
        info=sortDates(info)

    for key, val in info.items():
        print(val)
    # make map
    gmap = Map(
        identifier="gmap",
        varname="gmap",
        lat=coords[0]["lat"],
        lng=coords[0]["lon"],
        markers=[(val["lat"], val["lon"], val["infobox"]) for key,val in info.items()],
        zoom=12,
        fit_markers_to_bounds=True,
        cluster=True,
        style="width:75vw;height:100vh;margin:0;float:right;",
        zoom_control=True,
        maptype_control=True,
        scale_control=True,
        streetview_control=True,
        rotate_control=True,
        fullscreen_control=True,
        scroll_wheel=True
    )

    return render_template(
        'index.html',
        gmap=gmap,
        info=info,
        sortby=sortby
    )


if __name__ == "__main__":
    app.run(debug=True)
