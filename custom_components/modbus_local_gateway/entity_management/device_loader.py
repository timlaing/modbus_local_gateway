"""Loading YAML device definitions from disk"""

import glob
import logging
import os.path
from posixpath import basename

from homeassistant.core import HomeAssistant

from custom_components.modbus_local_gateway.const import DOMAIN

from ..device_configs import CONFIG_DIR
from .modbus_device_info import ModbusDeviceInfo

_LOGGER: logging.Logger = logging.getLogger(__name__)


def get_config_files(hass: HomeAssistant) -> dict[str, str]:
    """Get the list of YAML files in the config directory."""
    filenames: dict[str, str] = {
        os.path.basename(x).lower(): x for x in glob.glob(f"{CONFIG_DIR}/*.yaml")
    }

    # Check for extra config files in the custom_components directory
    extra_config_dir: str = os.path.join(hass.config.config_dir, DOMAIN)
    if os.path.exists(extra_config_dir) and os.path.isdir(extra_config_dir):
        extra_files: dict[str, str] = {
            os.path.basename(x).lower(): x
            for x in glob.glob(f"{extra_config_dir}/*.yaml")
        }
        filenames.update(extra_files)

    return filenames


async def load_devices(hass: HomeAssistant) -> dict[str, ModbusDeviceInfo]:
    """Find and load files from disk"""
    filenames: dict[str, str] = await hass.async_add_executor_job(
        get_config_files, hass
    )

    devices: dict[str, ModbusDeviceInfo] = {}
    for filename, path in filenames.items():
        try:
            devices[filename] = await hass.async_add_executor_job(
                create_device_info, hass, path
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Error loading device from YAML file: %s - %s", filename, err)

    return devices


def create_device_info(hass: HomeAssistant, filename: str) -> ModbusDeviceInfo:
    """Create the ModbusDeviceInfo object"""
    available_files: dict[str, str] = get_config_files(hass)
    name: str = basename(filename).lower()
    if name not in available_files:
        _LOGGER.error("File %s not found in available files: %s", name, available_files)
        raise FileNotFoundError(f"File {name} not found in available files.")

    return ModbusDeviceInfo(fname=available_files[name])
