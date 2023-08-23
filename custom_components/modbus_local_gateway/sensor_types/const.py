"""Sensor type constants"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    DEGREE,
    POWER_VOLT_AMPERE_REACTIVE,
    StrEnum,
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
FLAGS = "flags"
MAX_READ_DEFAULT = 8
DEFAULT_STATE_CLASS = SensorStateClass.MEASUREMENT


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
    },
    Units.VOLTS: {
        UNIT: UnitOfElectricPotential.VOLT,
        DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
    },
    Units.AMPS: {
        UNIT: UnitOfElectricCurrent.AMPERE,
        DEVICE_CLASS: SensorDeviceClass.CURRENT,
    },
    Units.KWH: {
        UNIT: UnitOfEnergy.KILO_WATT_HOUR,
        DEVICE_CLASS: SensorDeviceClass.ENERGY,
        STATE_CLASS: SensorStateClass.TOTAL_INCREASING,
    },
    Units.HZ: {
        UNIT: UnitOfFrequency.HERTZ,
        DEVICE_CLASS: SensorDeviceClass.FREQUENCY,
    },
    Units.WATTS: {
        UNIT: UnitOfPower.WATT,
        DEVICE_CLASS: SensorDeviceClass.POWER,
    },
    Units.DEGREES: {
        UNIT: DEGREE,
    },
    Units.KVARH: {
        UNIT: "kVArh",
    },
    Units.VAR: {
        UNIT: POWER_VOLT_AMPERE_REACTIVE,
        DEVICE_CLASS: SensorDeviceClass.REACTIVE_POWER,
    },
    Units.VA: {
        UNIT: UnitOfApparentPower.VOLT_AMPERE,
        DEVICE_CLASS: SensorDeviceClass.APPARENT_POWER,
    },
    Units.SECONDS: {
        UNIT: UnitOfTime.SECONDS,
        DEVICE_CLASS: SensorDeviceClass.DURATION,
    },
}
