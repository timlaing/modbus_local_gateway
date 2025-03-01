"""Loading YAML device definitions from disk"""

import glob
import logging
import os.path

from homeassistant.core import HomeAssistant

from ..device_configs import CONFIG_DIR
from .modbus_device_info import ModbusDeviceInfo

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def load_devices(hass: HomeAssistant) -> dict[str, ModbusDeviceInfo]:
    """Find and load files from disk"""
    filenames: list[str] = await hass.loop.run_in_executor(None, lambda: glob.glob(f"{CONFIG_DIR}/*.yaml"))
    devices: dict[str, ModbusDeviceInfo] = {}
    for filename in filenames:
        try:
            devices[os.path.basename(filename)] = await hass.async_add_executor_job(
                create_device_info, filename
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Error loading device from YAML file: %s - %s", filename, err)

    return devices


def create_device_info(filename: str) -> ModbusDeviceInfo:
    """Create the ModbusDeviceInfo object"""
    return ModbusDeviceInfo(filename)
