import os

from dotenv import load_dotenv

load_dotenv()
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

 # Setup the HTTP client API from user-password
http_api_client =  MerossHttpClient.async_from_user_password(email=os.getenv("email"), password=os.getenv("password"))

async def get_manager() -> MerossManager:
    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

async def get_plugs(manager : MerossManager) -> list:
    # Retrieve all the devices that implement the electricity mixin
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    if len(plugs) < 1:
        print("No electricity-capable device found...")
    else:
       return plugs
    
async def get_device_power(plug):
    # Update device status: this is needed only the very first time we play with this device (or if the
    #  connection goes down)
    await plug.async_update()

    # Read the electricity power/voltage/current
    instant_consumption = await plug.async_get_instant_metrics()
    print(f"Current consumption data: {instant_consumption}")

async def close_manager(manager : MerossManager):
    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()