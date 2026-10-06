"""Device loader Tests"""
# pylint: disable=unexpected-keyword-arg, protected-access

from pathlib import Path
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu.register_message import ReadHoldingRegistersResponse
import pytest

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.conversion import Conversion
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusCompositeEntityDescription,
    ModbusSelectEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.entity_management.device_loader import (
    create_device_info,
    get_config_files,
    load_devices,
)


def test_get_config_files_only_config_dir(tmp_path: Path, hass: HomeAssistant) -> None:
    """Test getting config files from the main config directory."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file2: Path = config_dir / "dev2.yaml"
    file1.write_text("test1")
    file2.write_text("test2")

    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "device_loader.CONFIG_DIR",
        str(config_dir),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert "dev2.yaml" in files
        assert files["dev1.yaml"] == str(file1)
        assert files["dev2.yaml"] == str(file2)


def test_get_config_files_with_extra_dir(tmp_path: Path, hass: HomeAssistant) -> None:
    """Test getting config files from the main and extra config directories."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")
    hass.config.config_dir = str(tmp_path)

    extra_dir: Path = tmp_path / DOMAIN
    extra_dir.mkdir()
    extra_file: Path = extra_dir / "extra.yaml"
    extra_file.write_text("extra")

    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "device_loader.CONFIG_DIR",
        str(config_dir),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert "extra.yaml" in files
        assert files["extra.yaml"] == str(extra_file)


def test_get_config_files_extra_dir_not_exists(
    tmp_path: Path, hass: HomeAssistant
) -> None:
    """Test getting config files when the extra directory does not exist."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    # Do not create extra_dir
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "device_loader.CONFIG_DIR",
            str(config_dir),
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "device_loader.DOMAIN",
            "modbus_local_gateway",
        ),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert len(files) == 1


def test_get_config_files_extra_dir_not_a_dir(
    tmp_path: Path, hass: HomeAssistant
) -> None:
    """Test getting config files when the extra directory is not a directory."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    # Create a file with the same name as the domain, not a directory
    extra_file: Path = tmp_path / "modbus_local_gateway"
    extra_file.write_text("not a dir")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "device_loader.CONFIG_DIR",
            str(config_dir),
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "device_loader.DOMAIN",
            "modbus_local_gateway",
        ),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert len(files) == 1


def test_get_create_device_info_not_found(hass: HomeAssistant) -> None:
    """Test create_device_info raises FileNotFoundError when file is not found."""
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={},
        ),
        pytest.raises(FileNotFoundError),
    ):
        create_device_info(hass, "non_existent.yaml")


def test_get_create_device_info_found(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test create_device_info returns ModbusDeviceInfo when file is found."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1)},
        ),
        patch.object(
            modbus_device_info.ModbusDeviceInfo, "__init__", return_value=None
        ),
    ):
        device_info: modbus_device_info.ModbusDeviceInfo = create_device_info(
            hass, "dev1.yaml"
        )
        assert device_info is not None


@pytest.mark.asyncio
async def test_load_devices(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test load_devices loads all devices from config files."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file2: Path = config_dir / "dev2.yaml"
    file1.write_text("test1")
    file2.write_text("test2")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1), "dev2.yaml": str(file2)},
        ),
        patch.object(
            modbus_device_info.ModbusDeviceInfo, "__init__", return_value=None
        ),
    ):
        devices: dict[str, modbus_device_info.ModbusDeviceInfo] = await load_devices(
            hass
        )
        assert len(devices) == 2
        assert "dev1.yaml" in devices
        assert "dev2.yaml" in devices


@pytest.mark.asyncio
async def test_load_devices_with_error(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test load_devices handles errors when loading device info."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1)},
        ),
        patch.object(
            modbus_device_info.ModbusDeviceInfo,
            "__init__",
            side_effect=Exception("Load error"),
        ),
    ):
        devices: dict[str, modbus_device_info.ModbusDeviceInfo] = await load_devices(
            hass
        )
        assert len(devices) == 0
        assert "dev1.yaml" not in devices


GROWATT_PERIOD_WINDOWS: tuple[tuple[int, int], ...] = (
    (3038, 3039),
    (3040, 3041),
    (3042, 3043),
    (3044, 3045),
    (3050, 3051),
    (3052, 3053),
    (3054, 3055),
    (3056, 3057),
    (3058, 3059),
)

GROWATT_CONFIGS: tuple[str, ...] = (
    "MOD-6000TL-X.yaml",
    "MIN-6000TL-XH.yaml",
    "MOD-10KTL3-XH.yaml",
)


@pytest.mark.parametrize("fname", GROWATT_CONFIGS)
def test_growatt_period_windows_match_the_protocol(fname: str) -> None:
    """The Growatt windows sit where the protocol table says they do.

    Register 3038 of the pair carries the enable flag (bit 15), the charge mode
    (bits 13-14) and the *start* time, and the register after it the *end* time
    with those bits reserved, so the two times and the two switches cannot be
    read off each other's register.
    """
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }

    for period, (start_address, end_address) in enumerate(GROWATT_PERIOD_WINDOWS, 1):
        start = entities[f"period{period}_start"]
        end = entities[f"period{period}_end"]
        mode = entities[f"period{period}_mode"]
        enable = entities[f"period{period}_enable"]

        assert start.register_address == start_address
        assert end.register_address == end_address
        # the mode and the enable share the start time's register
        assert mode.register_address == start_address
        assert enable.register_address == start_address
        assert (mode.conv_bits, mode.conv_shift_bits) == (2, 13)
        assert (enable.conv_bits, enable.conv_shift_bits) == (1, 15)
        # the device will not take one time alone: each window time is written
        # together with its partner register, which keeps its current value
        assert isinstance(start, ModbusCompositeEntityDescription)
        assert isinstance(end, ModbusCompositeEntityDescription)
        assert start.write_with == (end_address,)
        assert end.write_with == (start_address,)
        # the same goes for the mode and the enable on the start-time register:
        # they declare the end-time register too, or their write would be dropped
        assert mode.write_with == (end_address,)
        assert enable.write_with == (end_address,)


@pytest.mark.parametrize("fname", GROWATT_CONFIGS)
def test_growatt_windows_are_writable_holding_registers(fname: str) -> None:
    """A window is set through the holding registers, not read from the input ones.

    The input registers of the same models carry the grid voltages and the
    energy counters at these numbers, so a window that declared the input bank
    would read a voltage and write a voltage.
    """
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }

    for period, (start_address, _) in enumerate(GROWATT_PERIOD_WINDOWS, 1):
        for key in (f"period{period}_start", f"period{period}_end"):
            assert entities[key].data_type == ModbusDataType.HOLDING_REGISTER
        assert entities[f"period{period}_start"].register_address == start_address


EASTRON_METERS: tuple[str, ...] = ("SDM230.yaml", "SDM630.yaml")

# The meter's own settings are 32-bit floats over two registers, like the
# measurement registers they sit beside: the address is a slave id of 1-247, the
# baud rate and the unit prefix indexes into small option lists, each held as a
# float in the register pair the Eastron protocol table gives it.
EASTRON_FLOAT_CONTROLS: tuple[tuple[str, int], ...] = (
    ("com_address", 20),
    ("baud_rate", 28),
)


@pytest.mark.parametrize("fname", EASTRON_METERS)
def test_eastron_settings_are_two_register_floats(fname: str) -> None:
    """The meter's own settings are two-register floats, not single registers.

    Declared as one register each, a read of the address or the baud rate took
    only the first register of the pair and decoded it as a 16-bit value, so a
    float such as 1.0 (0x3F800000) came back as 16256 and never matched the
    option list or the 1-247 range.
    """
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }

    for key, address in EASTRON_FLOAT_CONTROLS:
        assert entities[key].register_address == address
        assert entities[key].register_count == 2
        assert entities[key].is_float


def test_eastron_unit_prefix_is_a_two_register_float() -> None:
    """The SDM630 energy unit prefix is a float pair, like the settings beside it."""
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(
            "SDM630.yaml"
        ).entity_descriptions
    }

    assert entities["unit_prefix"].register_address == 30
    assert entities["unit_prefix"].register_count == 2
    assert entities["unit_prefix"].is_float


@pytest.mark.parametrize("fname", EASTRON_METERS)
@pytest.mark.parametrize("key, _", EASTRON_FLOAT_CONTROLS)
@pytest.mark.parametrize("value", [1.0, 2.0, 247.0])
def test_eastron_settings_decode_as_floats(
    fname: str, key: str, _: int, value: float
) -> None:
    """A setting read back is the float the meter holds, not the raw register.
    This is the regression the declaration above causes: the register pair of
    1.0 is 0x3F800000, and read as a lone 16-bit register the first half is
    16256 rather than 1.
    """
    desc = next(
        desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
        if desc.key == key
    )
    conversion = Conversion(client=AsyncModbusTcpClient)
    decoded = conversion.convert_from_response(
        response=ReadHoldingRegistersResponse(
            registers=AsyncModbusTcpClient.convert_to_registers(
                value, data_type=AsyncModbusTcpClient.DATATYPE.FLOAT32
            )
        ),
        desc=desc,
    )
    assert decoded == pytest.approx(value)


@pytest.mark.parametrize("value", [1.0, 2.0, 247.0])
def test_eastron_unit_prefix_decodes_as_a_float(value: float) -> None:
    """The SDM630 unit prefix decodes as the float the meter holds."""
    desc = next(
        desc
        for desc in modbus_device_info.ModbusDeviceInfo(
            "SDM630.yaml"
        ).entity_descriptions
        if desc.key == "unit_prefix"
    )
    conversion = Conversion(client=AsyncModbusTcpClient)
    decoded = conversion.convert_from_response(
        response=ReadHoldingRegistersResponse(
            registers=AsyncModbusTcpClient.convert_to_registers(
                value, data_type=AsyncModbusTcpClient.DATATYPE.FLOAT32
            )
        ),
        desc=desc,
    )
    assert decoded == pytest.approx(value)


# Every Growatt model here carries its communication address at register 30 and
# its baud rate at register 22, in the common low register group. Register 3085
# is the address and 3086 the baud rate only in the storage family; the TL-X and
# TL-XH models have neither there.
GROWATT_COMMUNICATION_SETTINGS: tuple[str, ...] = (
    "MIC-2500TL-X.yaml",
    "MIN-6000TL-XH.yaml",
    "MOD-10KTL3-XH.yaml",
    "MOD-6000TL-X.yaml",
    "SPH-3600TL-BL_UP.yaml",
)


@pytest.mark.parametrize("fname", GROWATT_COMMUNICATION_SETTINGS)
def test_growatt_communication_settings_match_the_protocol(fname: str) -> None:
    """The address is register 30 and the baud rate 22, as the protocol says.
    Declared at 3085, the address read the storage family's address register,
    which these TL-X and TL-XH models do not answer to, so an inverter on slave
    address 7 reported 0 there.
    """
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }
    assert entities["com_address"].register_address == 30
    assert entities["com_address"].data_type == ModbusDataType.HOLDING_REGISTER
    assert entities["baud_rate"].register_address == 22
    assert entities["baud_rate"].data_type == ModbusDataType.HOLDING_REGISTER


@pytest.mark.parametrize("fname", GROWATT_COMMUNICATION_SETTINGS)
def test_growatt_baud_rate_offers_both_protocol_rates(fname: str) -> None:
    """The baud rate is the option list register 22 defines, not the storage one."""
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }
    baud_rate = entities["baud_rate"]
    assert isinstance(baud_rate, ModbusSelectEntityDescription)
    assert baud_rate.select_options == {0: "9600 bps", 1: "38400 bps"}


@pytest.mark.parametrize("fname", GROWATT_CONFIGS)
def test_growatt_tlx_models_do_not_use_the_storage_address_register(fname: str) -> None:
    """Nothing on a TL-X or TL-XH reads register 3085 as the address.
    The storage family keeps its address at 3085 and its baud rate at 3086; these
    models answer to 30 and 22, so the storage registers belong to the storage
    models alone.
    """
    entities = {
        desc.key: desc
        for desc in modbus_device_info.ModbusDeviceInfo(fname).entity_descriptions
    }
    assert all(desc.register_address != 3085 for desc in entities.values())
