# Modbus Local Gateway component with Prefix

This is a Home Assistant integration to support modbus devices running behind a Modbus TCP gateway.

## Device support

The has been tested with a WaveShare Wi-Fi to RS485 gateway (https://www.waveshare.com/rs485-to-wifi-eth.htm) Configured as a Modbus RTU to Modbus TCP gateway.

Slave devices for testing have been:
* Growatt MIN-6000-TL-XH
* Growatt MIC-2500-TL-X
* Eastron SDM230
* Eastron SDM630 (in progress)
* Finder 7M.38
* Finder 7M.24

Note that devices sometimes get firmware upgrades, or incompatible versions are sold under the same model name, so it is possible that the device will not work despite being listed.

Support for additional devices can be added via yaml configuration files in the devices folder.
Existing configuration files can be used as templates.

---

## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

Installation is easiest via the [Home Assistant Community Store
(HACS)](https://hacs.xyz/), which is the best place to get third-party
integrations for Home Assistant. Once you have HACS set up, simply click the button below (requires My Homeassistant configured) or
follow the [instructions for adding a custom
repository](https://hacs.xyz/docs/faq/custom_repositories) and then
the integration will be available to install like any other.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=timlaing&repository=modbus_local_gateway&category=integration)

## Configuration

After installing, you can easily configure your devices using the Integrations configuration UI.  Go to Settings / Devices & Services and press the Add Integration button, or click the shortcut button below (requires My Homeassistant configured).

[![Add Integration to your Home Assistant
instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=modbus_local_gateway)

### Stage One

The first stage of configuration is to provide the information needed to
connect to the device.

* IP address / hostname
* TCP Port number
* Modbus Slave ID
* Prefix for Sensors

### Stage Two

Select the correct device type.


### Configuration

Configuration of the update frequency can be performed defaults to 30 seconds
