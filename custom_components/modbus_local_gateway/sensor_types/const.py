"""Sensor type constants"""

from enum import StrEnum

from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    DEGREE,
    POWER_VOLT_AMPERE_REACTIVE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

MODEL = "model"
MANUFACTURER = "manufacturer"
DEVICE = "device"
ENTITIES = "entities"
REGISTER_ADDRESS = "address"
REGISTER_COUNT = "size"
REGISTER_MULTIPLIER = "multiplier"
REGISTER_MAP = "map"
ICON = "icon"
PRECISION = "precision"
IS_STRING = "string"
IS_FLOAT = "float"
UOM = "unit_of_measurement"
DEVICE_CLASS = "device_class"
STATE_CLASS = "state_class"
TITLE = "title"
UNIT = "unit"
MAX_READ = "max_register_read"
BITS = "bits"
SHIFT = "shift_bits"
CONTROL_TYPE = "control"
FLAGS = "flags"
MAX_READ_DEFAULT = 8
CATEGORY = "category"
NEVER_RESETS = "never_resets"
DEFAULT_STATE_CLASS = SensorStateClass.MEASUREMENT
OPTIONS = "options"


class ControlType(StrEnum):
    """Valid control types"""

    SENSOR = "sensor"
    SWITCH = "switch"
    SELECT = "select"
    TEXT = "text"
    NUMBER = "number"


class Units(StrEnum):
    """Valid unit types for yaml definition"""

    CELSIUS = "Celsius"
    VOLTS = "Volts"
    AMPS = "Amps"
    KWH = "kWh"
    VAR = "VAr"
    KVARH = "kVArh"
    DEGREES = "Degrees"
    HZ = "Hz"
    WATTS = "Watts"
    VA = "VoltAmps"
    SECONDS = "Seconds"


UOM_MAPPING = {
    Units.CELSIUS: {
        UNIT: UnitOfTemperature.CELSIUS,
        DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.VOLTS: {
        UNIT: UnitOfElectricPotential.VOLT,
        DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.AMPS: {
        UNIT: UnitOfElectricCurrent.AMPERE,
        DEVICE_CLASS: SensorDeviceClass.CURRENT,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.KWH: {
        UNIT: UnitOfEnergy.KILO_WATT_HOUR,
        DEVICE_CLASS: SensorDeviceClass.ENERGY,
        STATE_CLASS: SensorStateClass.TOTAL_INCREASING,
    },
    Units.HZ: {
        UNIT: UnitOfFrequency.HERTZ,
        DEVICE_CLASS: SensorDeviceClass.FREQUENCY,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.WATTS: {
        UNIT: UnitOfPower.WATT,
        DEVICE_CLASS: SensorDeviceClass.POWER,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.DEGREES: {
        UNIT: DEGREE,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.KVARH: {
        UNIT: "kVArh",
        STATE_CLASS: SensorStateClass.TOTAL_INCREASING,
    },
    Units.VAR: {
        UNIT: POWER_VOLT_AMPERE_REACTIVE,
        DEVICE_CLASS: SensorDeviceClass.REACTIVE_POWER,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.VA: {
        UNIT: UnitOfApparentPower.VOLT_AMPERE,
        DEVICE_CLASS: SensorDeviceClass.APPARENT_POWER,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
    Units.SECONDS: {
        UNIT: UnitOfTime.SECONDS,
        DEVICE_CLASS: SensorDeviceClass.DURATION,
        STATE_CLASS: SensorStateClass.TOTAL_INCREASING,
    },
}
