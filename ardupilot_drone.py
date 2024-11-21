#!/usr/bin/env python
import atexit
import os
import time

from flask import Flask, request
from dronekit import connect, LocationGlobalRelative

import drone_control
import website_tools


FLIGHT_ALTITUDE = 30  # meters (drone will fly at this altitude)
DELIVERY_ALTITUDE = 10  # meters (drone will descend to this altitude before lowering the cargo)
MAX_DELIVERY_DISTANCE = 1000  # meters (to ensure that we obey line-of-sight rule in this demo)

DRONE_CONNECTION_STRING = ""
# DRONE_CONNECTION_STRING = "tcp:127.0.0.1:15000"  # if connecting to the drone using local MAVProxy on port 15000
# DRONE_CONNECTION_STRING = "COM24"  # if connecting to the drone directly via USB radio at COM24 port


# key for the maps page
MAPS_API_KEY = "AIzaSyDadj41TtmSwuYtWRaz1Yw6tupXZQlf6i"  # < students may need to add number 4 to the end, if not there
assert len(MAPS_API_KEY) == 39, "CAPS students: please make sure number 4 is added to the end of the MAPS_API_KEY"


# domain name for the drone control website (and key for the tunnel to serve this website)
WEBSITE_DOMAIN = "copter.ngrok.io"  # (set WEBSITE_DOMAIN = "", if you don't want to serve at public domain in Internet)
NGROK_API_KEY = "2KcB1EBVKy4WTOTTKLW22gqR7DT_4VTarhtxzRo3HT85j45q"  # < students may need to add letter H to the end
assert len(NGROK_API_KEY) == 49, "CAPS students: please make sure letter H is added to the end of the NGROK_API_KEY"


# start the tunnel to serve that website at public domain on Internet
if WEBSITE_DOMAIN:
    drone_control.start_website_tunnel(NGROK_API_KEY, WEBSITE_DOMAIN)


# connect to the vehicle, if DRONE_CONNECTION_STRING was given
vehicle = None
if DRONE_CONNECTION_STRING:
    print("0. Connecting to vehicle on: " + DRONE_CONNECTION_STRING)
    vehicle = connect(DRONE_CONNECTION_STRING, wait_ready=True)
    atexit.register(vehicle.close)

    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)


# create a web server app with three pages: 'home_page', 'go_page' and 'map_page'
app = Flask(__name__)


@app.route('/')
def home_page():
    if vehicle is None:
        return "Drone is not connected to this website"
    if vehicle.armed:
        return "Drone is already armed"
    return """
<pre>
Drone is not armed
(to request delivery, run same page with your delivery point at the end, like this: /go?point=40.737084,-74.026079)
</pre>
"""


@app.route('/go')
def go_page():
    if vehicle is None:
        return "ERROR: drone is not connected to this website"

    if vehicle.armed:
        return "ERROR: drone is already armed and busy"

    point = request.args.get('point')
    if point is None:
        return "ERROR: point is not given"

    coordinates = point.split(',')
    if len(coordinates) != 2:
        return "ERROR: given point is not made of two coordinates (" + str(point) + ")"

    position = vehicle.location.global_relative_frame
    try:
        destination = LocationGlobalRelative(lat=float(coordinates[0]), lon=float(coordinates[1]))
    except:
        return "ERROR: point does not look like valid coordinates (" + str(point) + ")"

    distance_to_destination = drone_control.get_approx_distance_metres(position, destination)
    if distance_to_destination > MAX_DELIVERY_DISTANCE:
        return "ERROR: destination too far from us (point=" + str(destination) + ", location=" + str(position) + ")"

    print("Trying to deliver to: point=" + str(point) + ", distance=" + str(distance_to_destination))
    drone_control.start_delivery_to_location(vehicle, destination, FLIGHT_ALTITUDE, DELIVERY_ALTITUDE)
    return "Delivering... (" + str(distance_to_destination) + " meters away)"


EXAMPLE_MAPS_API_KEY = 'AIzaSyB41DRUbKWJHPxaFjMAwdrzWzbVKartNGg'  # used in map.html

@app.route('/map')
def map_page():
    # just serve the map.html file (but inside of it replace the example key with the real key instead)
    replacements = {EXAMPLE_MAPS_API_KEY: MAPS_API_KEY}
    maps_file_location = os.path.dirname(os.path.abspath(__file__))
    return website_tools.serve_static_webpage(maps_file_location + '/map.html', replacements)


print("Starting the webserver...")
app.run(host="0.0.0.0", port=80, debug=False)

