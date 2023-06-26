"""Loading YAML device definitiations from disk"""
import glob
import logging
import os.path


from .modbus_device_info import ModbusDeviceInfo
from ..devices import CONFIG_DIR

_LOGGER = logging.getLogger(__name__)


async def load_devices() ->dict[str, ModbusDeviceInfo]:
    """Find and load files from disk"""
    filenames: list[str] = glob.glob(f"{CONFIG_DIR}/*.yaml")
    devices: dict[str, ModbusDeviceInfo] = {}
    for filename in filenames:
        try:
            devices[os.path.basename(filename)] =  ModbusDeviceInfo(filename)
        except Exception as err: # pylint: disable=broad-exception-caught
            _LOGGER.error("Error loading device from YAML file: %s - %s", filename, err)

    return devices
