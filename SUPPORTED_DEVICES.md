# Supported Devices

Every device below ships a device configuration, so it can be picked from a
config entry's **Device config** selector and used without writing any YAML of
your own. The files live in
[`device_configs/`](custom_components/modbus_local_gateway/device_configs/).

This is a list of _configurations_, not of hardware this project has put on a
bench. Which devices have actually been exercised are listed under
[Tested Devices](README.md#tested-devices) in the README.

## Configurations

| Manufacturer       | Model                                        | Configuration                                                                                                        |
| ------------------ | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Dimplex            | Sole/Wasser-Wärmepumpe SI 11TU               | [`Dimplex-SI-11TU.yaml`](custom_components/modbus_local_gateway/device_configs/Dimplex-SI-11TU.yaml)                 |
| Eastron            | SDM-230                                      | [`SDM230.yaml`](custom_components/modbus_local_gateway/device_configs/SDM230.yaml)                                   |
| Eastron            | SDM-630                                      | [`SDM630.yaml`](custom_components/modbus_local_gateway/device_configs/SDM630.yaml)                                   |
| ebyte              | ME31-AXAX404                                 | [`ME31-AXAX404.yaml`](custom_components/modbus_local_gateway/device_configs/ME31-AXAX404.yaml)                       |
| Finder             | 7M.24                                        | [`7M_24.yaml`](custom_components/modbus_local_gateway/device_configs/7M_24.yaml)                                     |
| Finder             | 7M.38                                        | [`7M_38.yaml`](custom_components/modbus_local_gateway/device_configs/7M_38.yaml)                                     |
| Fröling GmbH       | BWP300 PV                                    | [`Fröling_BWP300PV.yaml`](custom_components/modbus_local_gateway/device_configs/Fr%C3%B6ling_BWP300PV.yaml)          |
| Growatt            | MIC 2500TL-X                                 | [`MIC-2500TL-X.yaml`](custom_components/modbus_local_gateway/device_configs/MIC-2500TL-X.yaml)                       |
| Growatt            | MIN 6000TL-XH                                | [`MIN-6000TL-XH.yaml`](custom_components/modbus_local_gateway/device_configs/MIN-6000TL-XH.yaml)                     |
| Growatt            | MOD 10KTL3-XH                                | [`MOD-10KTL3-XH.yaml`](custom_components/modbus_local_gateway/device_configs/MOD-10KTL3-XH.yaml)                     |
| Growatt            | MOD 6000TL-X                                 | [`MOD-6000TL-X.yaml`](custom_components/modbus_local_gateway/device_configs/MOD-6000TL-X.yaml)                       |
| Growatt            | SPH3600TL BL_UP                              | [`SPH-3600TL-BL_UP.yaml`](custom_components/modbus_local_gateway/device_configs/SPH-3600TL-BL_UP.yaml)               |
| Husdata            | H60                                          | [`Husdata_H60.yaml`](custom_components/modbus_local_gateway/device_configs/Husdata_H60.yaml)                         |
| LAE                | AC1-27                                       | [`LAE_AC1-27.yaml`](custom_components/modbus_local_gateway/device_configs/LAE_AC1-27.yaml)                           |
| Midea              | Air-to-water heat pump (171H120F controller) | [`midea_heat_pump.yaml`](custom_components/modbus_local_gateway/device_configs/midea_heat_pump.yaml)                 |
| Pichler            | Lüftungsgerät LG 150 - LG 250                | [`Pichler-LG150-LG250.yaml`](custom_components/modbus_local_gateway/device_configs/Pichler-LG150-LG250.yaml)         |
| Pichler            | Lüftungsgerät LG 350 - LG 450                | [`Pichler-LG350-LG450.yaml`](custom_components/modbus_local_gateway/device_configs/Pichler-LG350-LG450.yaml)         |
| Salda              | RIS / RIRS (MCB)                             | [`Salda_RIS_MCB.yaml`](custom_components/modbus_local_gateway/device_configs/Salda_RIS_MCB.yaml)                     |
| Schneider Electric | Altivar ATV312                               | [`Schneider_ATV312.yaml`](custom_components/modbus_local_gateway/device_configs/Schneider_ATV312.yaml)               |
| Schneider Electric | Altivar ATV312 Expert                        | [`Schneider_ATV312_expert.yaml`](custom_components/modbus_local_gateway/device_configs/Schneider_ATV312_expert.yaml) |
| Soler&Palau        | Domeo EVO 225 & 315 RD(fr)                   | [`Domeo-EVO-225-fr.yaml`](custom_components/modbus_local_gateway/device_configs/Domeo-EVO-225-fr.yaml)               |
| Varmann            | Qtherm                                       | [`Varmann Qtherm.yaml`](custom_components/modbus_local_gateway/device_configs/Varmann%20Qtherm.yaml)                 |
| Waveshare          | Modbus POE ETH Relay 30CH                    | [`Waveshare_30_POE.yaml`](custom_components/modbus_local_gateway/device_configs/Waveshare_30_POE.yaml)               |
| Waveshare          | Modbus RTU Relay (D)                         | [`Waveshare_RTU_Relay_D.yaml`](custom_components/modbus_local_gateway/device_configs/Waveshare_RTU_Relay_D.yaml)     |

`Test.yaml` ships too, but it is a fixture the test suite loads rather than a
device, so it is not listed here.

## Adding a device

A configuration is a YAML file describing the registers and coils an entity
reads or writes. See
[Creating YAML Device Configurations](YAML_DEVICE_CONFIGURATIONS.md)
for the reference and
[Adding a New Device Configuration](CONTRIBUTING.md#adding-a-new-device-configuration)
for what a contribution has to include - this file among them.
