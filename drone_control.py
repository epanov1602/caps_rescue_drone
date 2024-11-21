#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit

from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
from pymavlink import mavutil
import subprocess
import time
import math


def set_delivery_mission(vehicle, location, flight_altitude, delivery_altitude, release_delay_seconds, servo_number):
    """
    adds a mission to go to a point, get lower and release an object
    """

    print(" Clearing any existing commands")
    cmds = vehicle.commands
    cmds.clear()

    print(" Defining new commands.")

    # go to point right above us, at target altitude
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, 0, 0, int(flight_altitude)))

    # go to the point
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, location.lat, location.lon, int(flight_altitude)))

    # descend to the delivery altitude
    cmds.add(Command(0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, location.lat, location.lon, int(delivery_altitude)))

    # release the cargo on a winch number "servo_number" and wait for certain number of seconds
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0, 0, servo_number, 1000, 0, 0, 0, 0, 0))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, int(release_delay_seconds), 0, 0, 0, 0, 0, 0))
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0, 0, servo_number, 2000, 0, 0, 0, 0, 0))

    # go back to the launch location
    cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    print(" Uploading new commands to vehicle")
    cmds.upload()


def arm_and_takeoff(vehicle, target_altitude):
    def altitude(drone):
        return drone.location.global_relative_frame.alt

    # (wait until we can arm)
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)

    # 1. arm the motors
    print("Arming motors")
    vehicle.mode = VehicleMode("GUIDED")  # should be in GUIDED mode to arm
    vehicle.armed = True
    # (wait until armed)
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    # 2. take off!
    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)
    # (wait until the vehicle reaches a safe height before processing the waypoints)
    while altitude(vehicle) < target_altitude * 0.95:
        print(" Altitude: " + str(altitude(vehicle)))
        time.sleep(1)
    print("Reached target altitude")


def get_approx_distance_metres(point_a, point_b):
    """
    Approximation, taken from https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """
    distance_lat = point_b.lat - point_a.lat
    distance_long = point_b.lon - point_a.lon
    return math.sqrt((distance_lat * distance_lat) + (distance_long * distance_long)) * 1.113195e5


def start_delivery_to_location(vehicle, destination, flight_altitude, delivery_altitude):
    print("1. Creating autonomous mission (AUTO)")
    set_delivery_mission(vehicle, destination, flight_altitude, delivery_altitude, release_delay_seconds=5, servo_number=9)

    print("2. Taking off to 3 meters")
    arm_and_takeoff(vehicle, 3)

    print("3. Starting AUTO mission")
    vehicle.commands.next = 0  # reset to the first mission waypoint, to be sure
    vehicle.mode = VehicleMode("AUTO")


def start_website_tunnel(ngrok_api_key, domain):
    print("Adding ngrok API token... " + domain)
    token_added = subprocess.run(["ngrok", "config", "add-authtoken", ngrok_api_key], capture_output=True, text=True)
    if token_added.returncode != 0:
        raise ValueError(
            "Invalid ngrok API key?\nout:\n{}\n\n,err:\n{}\n\n",
            token_added.stdout,
            token_added.stderr
        )
    print("Starting website tunnel for URL... " + domain)
    tunnel = subprocess.Popen(["ngrok", "http", "--url=" + domain, "80"], stdout=subprocess.PIPE)
    atexit.register(tunnel.kill)
    print("Website tunnel started at http://" + domain + ":80")
