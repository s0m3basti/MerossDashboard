import csv
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

#setup app
app = FastAPI()

load_dotenv()

# all meross vars
my_meross_stuff = {}

# create meross client & manager on app startup
@app.on_event("startup")
async def setup_meross():
    # setup the meross client
    http_api_client =  await MerossHttpClient.async_from_user_password(email=os.getenv("email"), password=os.getenv("password"))
    my_meross_stuff["http_api_client"] = http_api_client

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    my_meross_stuff["manager"] = manager

    # Retrieve all the devices that implement the electricity mixin
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    # exit if no plugs available
    if len(plugs) < 1:
        print("No electricity-capable device found...")
        exit()
    
    # initialize every plug found
    for plug in plugs:
        # Update device status: this is needed only the very first time we play with this device (or if the
        #  connection goes down)
        await plug.async_update()
     
    my_meross_stuff["plugs"] = plugs


# check for power every 60 seconds
@app.on_event("startup")
@repeat_every(seconds=60)
async def get_power():
    timestamp = datetime.now()

    #based on the plug get the power and save it to a csv file based on the day
    for plug in my_meross_stuff["plugs"]:
        instant_consumption = await plug.async_get_instant_metrics()
        power = instant_consumption.power

        if "PC" in plug.name:
            with open("data/pc_"+timestamp.strftime("%Y-%m-%d")+".csv", "a+") as f:
                f.write("{}, {}\n".format(timestamp, power))
        elif "TV" in plug.name:
            with open("data/tv_"+timestamp.strftime("%Y-%m-%d")+".csv", "a+") as f:
                f.write("{}, {}\n".format(timestamp, power)) 

# close the meross connection on shutdown
@app.on_event("shutdown")
async def shutdown():
    # Close the manager and logout from http_api
    my_meross_stuff["manager"].close()
    await my_meross_stuff["http_api_client"].async_logout()
       

@app.get("/")
async def root():
    return "Hello World"

@app.get("/get_data/{type}")
async def get_data(type, date : str = datetime.today().strftime("%Y-%m-%d")) -> list:
    result = []

    
    if type == "pc":
        with open("data/pc_"+date+".csv", "r") as f:
            csvreader = csv.reader(f)
            for row in csvreader:
                result.append(row)
    elif type == "tv":
        with open("data/tv_"+date+".csv", "r") as f:
            csvreader = csv.reader(f)
            for row in csvreader:
                result.append(row)

    return result
