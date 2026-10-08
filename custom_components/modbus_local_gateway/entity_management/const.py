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
PROBE_KEY = "probe_key"

NAME = "name"
CONTROL_TYPE = "control"
REGISTER_ADDRESS = "address"
REGISTER_COUNT = "size"
COMPOSITE = "composite"
COMPOSITE_TYPE = "type"
WRITE_FUNCTION = "write_function"
WRITE_WITH = "write_with"
COMPOSITE_FIELDS = "fields"
CONV_BITS = "bits"
CONV_FLAGS = "flags"
CONV_MAP = "map"
CONV_MULTIPLIER = "multiplier"
CONV_OFFSET = "offset"
CONV_WRITE_OFFSET = "write_offset"
CONV_SHIFT_BITS = "shift_bits"
CONV_SUM_SCALE = "sum_scale"
CONV_SWAP = "swap"
PRECISION = "precision"
IS_FLOAT = "float"
IS_STRING = "string"
IS_SIGNED = "signed"
NEVER_RESETS = "never_resets"
MAX_CHANGE = "max_change"
CONV_UNAVAILABLE_VALUES = "unavailable_values"
NO_FLAG_VALUE = "no_flag_value"
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


class WriteFunction(StrEnum):
    """Modbus function used to write a single holding register"""

    SINGLE = "single"
    MULTIPLE = "multiple"


class CompositeType(StrEnum):
    """Semantic value a set of registers is assembled into"""

    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"

    @property
    def control_type(self) -> ControlType:
        """Platform the value is exposed on.

        A date, a time and a date/time are three different platforms rather than
        three flavours of one: Home Assistant shows and lets each be set as what
        it is, and the entity id says which it is. `datetime` used to take all
        three, so a clock read as a date and time whose date was today's - the
        device's date was never in the value.
        """
        if self is CompositeType.DATE:
            return ControlType.DATE
        if self is CompositeType.TIME:
            return ControlType.TIME
        return ControlType.DATETIME

    @property
    def required_fields(self) -> tuple[str, ...]:
        """Fields the composite cannot be built without.

        `second` is never required: plenty of devices keep minute resolution,
        and a missing field simply leaves that part of the value at zero.
        """
        return _REQUIRED_FIELDS[self]

    @property
    def optional_fields(self) -> tuple[str, ...]:
        """Fields a config may add on top of `required_fields`."""
        return _OPTIONAL_FIELDS[self]


_REQUIRED_FIELDS: dict[CompositeType, tuple[str, ...]] = {
    CompositeType.DATE: ("year", "month", "day"),
    CompositeType.TIME: ("hour", "minute"),
    CompositeType.DATETIME: ("year", "month", "day", "hour", "minute"),
}

_OPTIONAL_FIELDS: dict[CompositeType, tuple[str, ...]] = {
    CompositeType.DATE: (),
    CompositeType.TIME: ("second",),
    CompositeType.DATETIME: ("second",),
}


class ControlType(StrEnum):
    """Valid control types"""

    SENSOR = "sensor"
    SWITCH = "switch"
    SELECT = "select"
    TEXT = "text"
    NUMBER = "number"
    BINARY_SENSOR = "binary_sensor"
    DATETIME = "datetime"
    TIME = "time"
    DATE = "date"


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


class SwapType(StrEnum):
    """Modbus data types"""

    WORD = "word"
    BYTE = "byte"
    WORD_BYTE = "word_byte"


UOM_MAPPING: dict[Units, dict[str, str]] = {
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
