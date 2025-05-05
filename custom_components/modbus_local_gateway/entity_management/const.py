"""Sensor type constants"""

from enum import StrEnum

from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)

DEVICE = "device"

MODEL = "model"
MANUFACTURER = "manufacturer"
MAX_READ = "max_register_read"
MAX_READ_DEFAULT = 8

NAME = "name"
CONTROL_TYPE = "control"
REGISTER_ADDRESS = "address"
REGISTER_COUNT = "size"
CONV_MULTIPLIER = "multiplier"
CONV_OFFSET = "offset"
CONV_BITS = "bits"
CONV_SHIFT_BITS = "shift_bits"
CONV_SUM_SCALE = "sum_scale"
CONV_MAP = "map"
CONV_FLAGS = "flags"
PRECISION = "precision"
IS_STRING = "string"
IS_FLOAT = "float"
NEVER_RESETS = "never_resets"
MAX_CHANGE = "max_change"
UOM = "unit_of_measurement"
DEVICE_CLASS = "device_class"
STATE_CLASS = "state_class"
DEFAULT_STATE_CLASS = SensorStateClass.MEASUREMENT

UNIT = "unit"


class ModbusDataType(StrEnum):
    """Modbus data types"""

    HOLDING_REGISTER = "read_write_word"
    INPUT_REGISTER = "read_only_word"
    COIL = "read_write_boolean"
    DISCRETE_INPUT = "read_only_boolean"


class ControlType(StrEnum):
    """Valid control types"""

    SENSOR = "sensor"
    SWITCH = "switch"
    SELECT = "select"
    TEXT = "text"
    NUMBER = "number"
    BINARY_SENSOR = "binary_sensor"


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
    PERCENT = "%"


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
        UNIT: UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
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
    Units.PERCENT: {
        UNIT: PERCENTAGE,
        STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
}
