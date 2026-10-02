# Growatt Inverter Modbus RTU Protocol

V1.20

**Source:** Growatt PV Inverter Modbus RS485 RTU Protocol v120 4.pdf (65 pages).

> Conversion notes: Original section headings, register addresses, units, permissions, reserved ranges, spelling and inconsistencies are retained. `<br>` preserves text inside a cell, including wrapped identifiers. Rows split across pages are joined. Repeated table headers are supplied at page boundaries for navigation. Shared vertically merged cell text is repeated where needed; text spanning multiple columns is placed in the leftmost covered column and identified where material. Blank cells remain blank. Source strikethroughs in the hybrid bit definitions are preserved; the highlighted replacement “BMS Battery Open” is bolded. Empty change-record rows and repeated company headers/footers are omitted. The command tables on pages 5-7 were transcribed from page images.

## Change Record

Source page: 2.

| Index | Version | Change Content | Make       | Make date |
| ----- | ------- | -------------- | ---------- | --------- |
| 1     | 00      | First Republic | Weiwei.shi | 2020.4.28 |

## Instruction：Register range for various types of inverter

Source page: 3.

TL-X（MIN Type）：03 register range：0~~124,3000~~3124；04 register
range：3000~~3124,3125~~3249
TL3-X(MAX、MID、MAC Type)：03 register range：0~~124,125~~249；
04 register range：0~~124,125~~249
Storage(MIX Type)：03 register range：0~~124,1000~~1124；04 register
range：0~~124,1000~~1124
Storage(SPA Type)：03 register range：0~~124,1000~~1124；04 register
range：1000~~1124,2000~~2124
Storage(SPH Type)：03 register range：0~~124,1000~~1124；04 register
range：0~~124,1000~~1124

## catalog

Source page: 4.

| Section                                      | Source page |
| -------------------------------------------- | ----------- |
| 1 Data format                                | 5           |
| 2 Command Format                             | 5           |
| 3 Device Message Transmission Mode / Framing | 8           |
| 4 Register map                               | 9           |
| 4.1 Holding Reg                              | 9           |
| 4.2 Input Reg                                | 33          |
| 5 Set address                                | 65          |
| 6 Notice                                     | 65          |

## 1 Data format

Source page: 5.

| Address | Function | Data    | CRC check |
| ------- | -------- | ------- | --------- |
| 8 bits  | 8 bits   | N×8bits | 16bits    |

Valid slave device addresses are in the range of 0 - 254 decimal.

The individual slave devices are assigned addresses in the range of 1 - 254.

0 is the broadcast address.

It is 16bits (two bytes) unsigned integer for each holding and input register;

## 2 Command Format

### Function 3 Read holding register

Source pages: 5-6.

#### QUERY

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 03            |
| Starting Address Hi      | 00            |
| Starting Address Lo      | 6B            |
| No. of Points Hi         | 00            |
| No. of Points Lo         | 03            |
| Error Check (LRC or CRC) | —             |

#### RESPONSE

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 03            |
| Byte Count               | 06            |
| Data Hi (Register 40108) | 02            |
| Data Lo (Register 40108) | 2B            |
| Data Hi (Register 40109) | 00            |
| Data Lo (Register 40109) | 00            |
| Data Hi (Register 40110) | 00            |
| Data Lo (Register 40110) | 64            |
| Error Check (LRC or CRC) | —             |

Response Error: `11 0x80|0x03 ErrornumCRC` (Errornum as a byte).

### Function 4 Read input register

Source pages: 6.

#### QUERY

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 04            |
| Starting Address Hi      | 00            |
| Starting Address Lo      | 08            |
| No. of Points Hi         | 00            |
| No. of Points Lo         | 01            |
| Error Check (LRC or CRC) | —             |

#### RESPONSE

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 04            |
| Byte Count               | 02            |
| Data Hi (Register 30009) | 00            |
| Data Lo (Register 30009) | 0A            |
| Error Check (LRC or CRC) | —             |

Response Error: `11 0x80|0x04 ErrornumCRC` (Errornum as a byte).

### Function 6 Preset single register

Source pages: 6-7.

#### QUERY

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 06            |
| Register Address Hi      | 00            |
| Register Address Lo      | 01            |
| Preset Data Hi           | 00            |
| Preset Data Lo           | 03            |
| Error Check (LRC or CRC) | —             |

#### RESPONSE

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 06            |
| Register Address Hi      | 00            |
| Register Address Lo      | 01            |
| Preset Data Hi           | 00            |
| Preset Data Lo           | 03            |
| Error Check (LRC or CRC) | —             |

Response Error: `11 0x80|0x06 ErrornumCRC` (Errornum as a byte).

### Function 16 Preset multiple register

Source pages: 7.

#### QUERY

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 10            |
| Starting Address Hi      | 00            |
| Starting Address Lo      | 01            |
| No. of Registers Hi      | 00            |
| No. of Registers Lo      | 02            |
| Byte Count               | 04            |
| Data Hi                  | 00            |
| Data Lo                  | 0A            |
| Data Hi                  | 01            |
| Data Lo                  | 02            |
| Error Check (LRC or CRC) | —             |

#### RESPONSE

| Field Name               | Example (Hex) |
| ------------------------ | ------------- |
| Slave Address            | 11            |
| Function                 | 10            |
| Starting Address Hi      | 00            |
| Starting Address Lo      | 01            |
| No. of Registers Hi      | 00            |
| No. of Registers Lo      | 02            |
| Error Check (LRC or CRC) | —             |

Response Error: `11 0x80|0x10 ErrornumCRC` (Errornum as a byte).

## 3 Device Message Transmission Mode / Framing

Source page: 8.

RTU Mode
When controllers are setup to communicate on a Modbus network using RTU (Remote
Terminal Unit) mode, each 8–bit byte in a message contains two 4–bit hexadecimal
characters. Each message must be transmitted in a continuous stream.
The format for each byte in RTU mode is:
Coding System: 8–bit binary, hexadecimal 0–9, A–F
Two hexadecimal characters contained in each
8–bit field of the message
Bits per Byte:
1 start bit
8 data bits, least significant bit sent first
None parity
1 stop bit
Error Check Field: Cyclical Redundancy Check (CRC)
The baud rate of the transmission is:
Default Baud Rate: 9600 bps
Can be set through hold register 22
Minimum CMD period (RS485 Time out): 850ms.
Wait for minimum850ms to send a new CMD after last CMD. Suggestion is 1s;
Maximum Data Length Define:
Maximum read data length is 125 words in read command;
Maximum update data length is 125 words in preset command;
Note:
Except the CEI0-21 and VDE-AR-N 4105 power management registers, you should refer the
manufactory’s suggestion when writing other registers;

## 4 Register map

It is 16bits (two bytes) unsigned integer for each holding and input register;

### 4.1 Holding Reg

**Source page 9**

#### First group

| Register NO. | Variable Name             | Description                                                                                                                                                                                                                                                                            | Write or not | Value                                                                         | Unit | Initial value | Note                                                                          |
| ------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------- | ---- | ------------- | ----------------------------------------------------------------------------- |
| 00           | OnOff                     | Remote On/Off .<br>On（1）；Off（0）                                                                                                                                                                                                                                                   | W            | 0or1                                                                          |      | 1             | When PV restart, recover 1.                                                   |
| 01           | SaftyFuncEn               | Bit0: SPI enable<br>Bit1: AutoTestStart<br>Bit2: LVFRT enable<br>Bit3:FreqDerating<br>Enable<br>Bit4: Softstart enable<br>Bit5: DRMS enable<br>Bit6:PowerVoltFunc<br>Enable<br>Bit7: HVFRT enable<br>Bit8:ROCOF enable<br>Bit9: Recover<br>FreqDeratingMode<br>Enable<br>Bit10~15:预留 | W            | 0 :<br>disable<br>1: enable                                                   |      |               | SPI: system protection<br>interface<br>Bit0~~3:for CEI0-21<br>Bit4~~6:for SAA |
| 02           | PF CMD<br>memory<br>state | Set Holding<br>register3,4,5,99 CMD<br>will be memory or<br>not(1/0), if not, these<br>settings are the<br>initial value.                                                                                                                                                              | W            | 0or1                                                                          |      | 0             | Means these settings will be<br>acting or not when next<br>power on           |
| 03           | Active P<br>Rate          | Inverter Max output<br>active power percent                                                                                                                                                                                                                                            | W            | 0-100 or<br>255                                                               | %    | 255           | 255: power is not be limited                                                  |
| 04           | Reactive P<br>Rate        | Inverter max output<br>reactive power percent                                                                                                                                                                                                                                          | W            | -100-100<br>or 255                                                            | %    | 255           | 255: power is not be limited                                                  |
| 05           | Power factor              | Inverter output power<br>factor’s 10000 times                                                                                                                                                                                                                                          | W            | 0-20000,<br>0-10000<br>is<br>underexci<br>ted, other<br>is<br>overexcit<br>ed |      | 0             |                                                                               |

**Source page 10**

| Register NO. | Variable Name            | Description                                                     | Write or not | Value                                        | Unit  | Initial value | Note                                                                                                                            |
| ------------ | ------------------------ | --------------------------------------------------------------- | ------------ | -------------------------------------------- | ----- | ------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 06           | Pmax H                   | Normal power (high)                                             |              |                                              | 0.1VA |               |                                                                                                                                 |
| 07           | Pmax L                   | Normal power (low)                                              |              |                                              | 0.1VA |               |                                                                                                                                 |
| 08           | Vnormal                  | Normal work PV<br>voltage                                       |              |                                              | 0.1V  |               |                                                                                                                                 |
| 09           | Fw version H             | Firmware version<br>(high)                                      |              |                                              | ASCII |               |                                                                                                                                 |
| 10           | Fw version<br>M          | Firmware version<br>(middle)                                    |              |                                              |       |               |                                                                                                                                 |
| 11           | Fw version L             | Firmware version (low)                                          |              |                                              |       |               |                                                                                                                                 |
| 12           | Fw version2<br>H         | Control Firmware<br>version (high)                              |              |                                              | ASCII |               |                                                                                                                                 |
| 13           | Fw version2<br>M         | Control Firmware<br>version (middle)                            |              |                                              |       |               |                                                                                                                                 |
| 14           | Fw version2<br>L         | Control Firmware<br>version (low)                               |              |                                              |       |               |                                                                                                                                 |
| 15           | LCD<br>language          | LCD language                                                    | W            | 0-5                                          |       |               | 0: Italian;<br>1: English;<br>2: German;<br>3: Spanish;<br>4: French;<br>5: Chinese;<br>6：Polish<br>7：Portugues<br>8：Hungary |
| 16           | CountrySele<br>cted      | Country Selected or<br>not                                      | W            | 0: need<br>to select;<br>1: have<br>selected |       |               |                                                                                                                                 |
| 17           | Vpv start                | Input start voltage                                             | W            |                                              | 0.1V  |               |                                                                                                                                 |
| 18           | Time start               | Start time                                                      | W            |                                              | 1s    |               |                                                                                                                                 |
| 19           | RestartDelay<br>Time     | Restart Delay Time<br>after fault back;                         | W            |                                              | 1s    |               |                                                                                                                                 |
| 20           | wPowerStart<br>Slope     | Power start slope                                               | W            | 1-1000                                       | 0.1%  |               |                                                                                                                                 |
| 21           | wPowerRest<br>artSlopeEE | Power restart slope                                             | W            | 1-1000                                       | 0.1%  |               |                                                                                                                                 |
| 22           | wSelectBaudrate          | Select<br>communicationbaudrat<br>e<br>0: 9600bps<br>1:38400bps | W            | 0-1                                          |       | 0             |                                                                                                                                 |

**Source page 11**

| Register NO. | Variable Name           | Description                               | Write or not | Value                                             | Unit  | Initial value | Note                       |
| ------------ | ----------------------- | ----------------------------------------- | ------------ | ------------------------------------------------- | ----- | ------------- | -------------------------- |
| 23           | Serial NO               | Serial number 1-2                         |              |                                                   | ASCII |               |                            |
| 24           | Serial NO               | Serial number 3-4                         |              |                                                   |       |               |                            |
| 25           | Serial NO               | Serial number 5-6                         |              |                                                   |       |               |                            |
| 26           | Serial NO               | Serial number 7-8                         |              |                                                   |       |               |                            |
| 27           | Serial NO               | Serial number 9-10                        |              |                                                   |       |               |                            |
| 28           | Module H                | Inverter Module (high)                    |              | &amp;*5                                           |       |               |                            |
| 29           | Module L                | Inverter Module (low)                     |              | &amp;*5                                           |       |               |                            |
| 30           | Com<br>Address          | Communicate address                       | W            | 1-254                                             |       | 1             |                            |
| 31           | FlashStart              | Update firmware                           | W            | 1                                                 |       |               |                            |
| 32           | Reset User<br>Info      | Reset User Information                    | W            | 0x0001                                            |       |               |                            |
| 33           | Reset to<br>factory     | Reset to factory                          | W            | 0x0001                                            |       |               |                            |
| 34           | Manufacture<br>r Info 8 | Manufacturer<br>information (high)        |              |                                                   | ASCII |               |                            |
| 35           | Manufacture<br>r Info 7 | Manufacturer<br>information (middle)      |              |                                                   |       |               |                            |
| 36           | Manufacture<br>r Info 6 | Manufacturer<br>information (low)         |              |                                                   |       |               |                            |
| 37           | Manufacture<br>r Info 5 | Manufacturer<br>information (high)        |              |                                                   |       |               |                            |
| 38           | Manufacture<br>r Info 4 | Manufacturer<br>information (middle)      |              |                                                   |       |               |                            |
| 39           | Manufacture<br>r Info3  | Manufacturer<br>information (low)         |              |                                                   |       |               |                            |
| 40           | Manufacture<br>r Info 2 | Manufacturer<br>information (low)         |              |                                                   |       |               |                            |
| 41           | Manufacture<br>r Info 1 | Manufacturer<br>information (high)        |              |                                                   |       |               |                            |
| 42           | bfailsafeEn;            | G100 fail safe                            | W            | Enable:1<br>Disable:0                             |       |               | English G100 fail safe set |
| 43           | DTC                     | Device Type Code                          |              | &amp;*6                                           |       |               |                            |
| 44           | TP                      | Input tracker num and<br>output phase num |              | Eg:0x020<br>3 is two<br>MPPT<br>and 3ph<br>output |       |               |                            |

**Source page 12**

| Register NO. | Variable Name    | Description                                  | Write or not | Value               | Unit       | Initial value | Note       |
| ------------ | ---------------- | -------------------------------------------- | ------------ | ------------------- | ---------- | ------------- | ---------- |
| 45           | Sys Year         | System time-year                             | W            | Year<br>offset is 0 |            |               | Local time |
| 46           | Sys Month        | System time- Month                           | W            |                     |            |               |            |
| 47           | Sys Day          | System time- Day                             | W            |                     |            |               |            |
| 48           | Sys Hour         | System time- Hour                            | W            |                     |            |               |            |
| 49           | Sys Min          | System time- Min                             | W            |                     |            |               |            |
| 50           | Sys Sec          | System time- Second                          | W            |                     |            |               |            |
| 51           | Sys Weekly       | System Weekly                                | W            | 0-6                 |            |               |            |
| 52           | Vac low          | Grid voltage low limit<br>protect            | W            |                     | 0.1V       |               |            |
| 53           | Vac high         | Grid voltage high limit<br>protect           | W            |                     | 0.1V       |               |            |
| 54           | Fac low          | Grid frequency low<br>limit protect          | W            |                     | 0.01<br>Hz |               |            |
| 55           | Fac high         | Grid high<br>frequencylimit protect          | W            |                     | 0.01<br>Hz |               |            |
| 56           | Vac low 2        | Grid voltage low limit<br>protect 2          | W            |                     | 0.1V       |               |            |
| 57           | Vac high 2       | Grid voltage high limit<br>protect 2         | W            |                     | 0.1V       |               |            |
| 58           | Fac low 2        | Grid frequency low<br>limit protect 2        | W            |                     | 0.01<br>Hz |               |            |
| 59           | Fac high 2       | Grid high frequency<br>limit protect 2       | W            |                     | 0.01<br>Hz |               |            |
| 60           | Vac low 3        | Grid voltage low limit<br>protect 3          | W            |                     | 0.1V       |               |            |
| 61           | Vac high 3       | Grid voltage high limit<br>protect 3         | W            |                     | 0.1V       |               |            |
| 62           | Fac low 3        | Grid frequency low<br>limit protect 3        | W            |                     | 0.01Hz     |               |            |
| 63           | Fac high 3       | Grid frequency high<br>limit protect 3       | W            |                     | 0.01Hz     |               |            |
| 64           | Vac low C        | Grid low voltage limit<br>connect to Grid    | W            |                     | 0.1V       |               |            |
| 65           | Vac high C       | Grid high voltage limit<br>connect to Grid   | W            |                     | 0.1V       |               |            |
| 66           | Fac low C        | Grid low frequency<br>limit connect to Grid  | W            |                     | 0.01<br>Hz |               |            |
| 67           | Fac high C       | Grid high frequency<br>limit connect to Grid | W            |                     | 0.01<br>Hz |               |            |
| 68           | Vac low1<br>time | Grid voltage low limit<br>protect time 1     | W            |                     | Cycle      |               |            |

**Source page 13**

| Register NO. | Variable Name            | Description                                                                                                                                                                                                               | Write or not | Value               | Unit            | Initial value | Note |
| ------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------- | --------------- | ------------- | ---- |
| 69           | Vac high1<br>time        | Grid voltage high limit<br>protect time 1                                                                                                                                                                                 | W            |                     | Cycle           |               |      |
| 70           | Vac low2<br>time         | Grid voltage low limit<br>protect time 2                                                                                                                                                                                  | W            |                     | Cycle           |               |      |
| 71           | Vac high2<br>time        | Grid voltage high limit<br>protect time 2                                                                                                                                                                                 | W            |                     | Cycle           |               |      |
| 72           | Fac low1<br>time         | Grid frequency low<br>limit protect time 1                                                                                                                                                                                | W            |                     | Cycle           |               |      |
| 73           | Fac high1<br>time        | Grid frequency high<br>limit protect time 1                                                                                                                                                                               | W            |                     | Cycle           |               |      |
| 74           | Fac low2<br>time         | Grid frequency low<br>limit protect time 2                                                                                                                                                                                | W            |                     | Cycle           |               |      |
| 75           | Fac high2<br>time        | Grid frequency high<br>limit protect time 2                                                                                                                                                                               | W            |                     | Cycle           |               |      |
| 76           | Vac low3<br>time         | Grid voltage low limit<br>protect time 3                                                                                                                                                                                  | W            |                     | Cycle           |               |      |
| 77           | Vac high3<br>time        | Grid voltage high limit<br>protect time 3                                                                                                                                                                                 | W            |                     | Cycle           |               |      |
| 78           | Fac low3<br>time         | Grid frequency low<br>limit protect time 3                                                                                                                                                                                | W            |                     | Cycle           |               |      |
| 79           | Fac high3<br>time        | Grid frequency high<br>limit protect time 3                                                                                                                                                                               | W            |                     | Cycle           |               |      |
| 80           | U10min                   | Volt protection for 10<br>min                                                                                                                                                                                             | W            |                     | 0.1V            | 1.1Vn         |      |
| 81           | PV Voltage<br>High Fault | PV Voltage High Fault                                                                                                                                                                                                     | W            |                     | 0.1V            |               |      |
| 82           | FW Build No.<br>5        | FW Build version                                                                                                                                                                                                          |              |                     | ASCII           |               |      |
| 83           | FW Build No.<br>4        | FW Build version                                                                                                                                                                                                          |              |                     | ASCII           |               |      |
| 84           | FW Build No.<br>3        | DSP1 FW Build No.                                                                                                                                                                                                         |              |                     | ASCII           |               |      |
| 85           | FW Build No.<br>2        | DSP2 FW Build No.                                                                                                                                                                                                         |              |                     | ASCII           |               |      |
| 86           | FW Build No.<br>1        | M3 FW Build No.                                                                                                                                                                                                           |              |                     | ASCII           |               |      |
| 87           | FW Build No.<br>0        | CPLD FW Build No.                                                                                                                                                                                                         |              |                     | ASCII           |               |      |
| 88           | ModbusVers<br>ion        | Modbus Version                                                                                                                                                                                                            |              | Eg：207 is<br>V2.07 | Int(16<br>bits) |               |      |
| 89           | PFModel                  | Set PF function Model<br>0: PF=1<br>1: PF by set<br>2: default PF line<br>3: User PF line<br>4: UnderExcited (Inda)<br>Reactive Power<br>5: OverExcited(Capa)<br>Reactive Power<br>6：Q(v)model<br>7：Direct Control mode | W            |                     |                 |               |      |

**Source page 14**

| Register NO. | Variable Name         | Description                                                                                       | Write or not | Value                                                                  | Unit        | Initial value | Note |
| ------------ | --------------------- | ------------------------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------- | ----------- | ------------- | ---- |
| 90           | GPRS IP Flag          | Bit0-3:read:1;Set GPRS<br>IP Successed<br>Write:2;Read GPRS IP<br>Successed<br>Bit4-7:GPRS status | W            | Bit0-3:ab<br>out GPRS<br>IP SET<br>Bit4-7:ab<br>out<br>GRPRS<br>Status |             |               |      |
| 91           | FreqDerateS<br>tart   | Frequency derating<br>start point                                                                 | W            |                                                                        | 0.01H<br>Z  |               |      |
| 92           | FLrate                | Frequency – load limit<br>rate                                                                    | W            | 0-100                                                                  | 10tim<br>es |               |      |
| 93           | V1S                   | CEI021 V1S Q(v)                                                                                   | W            | V1S&lt;V2S                                                             | 0.1V        |               |      |
| 94           | V2S                   | CEI021 V2S Q(v)                                                                                   | W            |                                                                        | 0.1V        |               |      |
| 95           | V1L                   | CEI021 V1L Q(v)                                                                                   | W            | V1L&lt;V1S                                                             | 0.1V        |               |      |
| 96           | V2L                   | CEI021 V2L Q(v)                                                                                   | W            | V2L&lt;V1L                                                             | 0.1V        |               |      |
| 97           | Qlockinpow<br>er      | Q(v) lock in active<br>power of CEI021                                                            | W            | 0-100                                                                  | Percen<br>t |               |      |
| 98           | QlockOutpo<br>wer     | Q(v) lock Out active<br>power of CEI021                                                           | W            | 0-100                                                                  | Percen<br>t |               |      |
| 99           | LIGridV               | Lock in gird volt of<br>CEI021 PF line                                                            | W            | nVn                                                                    | 0.1V        |               |      |
| 100          | LOGridV               | Lock out gird volt of<br>CEI021 PF line                                                           | W            | nVn                                                                    | 0.1V        |               |      |
| 101          | PFAdj1                | PF adjust value 1                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 102          | PFAdj2                | PF adjust value 2                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 103          | PFAdj3                | PF adjust value 3                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 104          | PFAdj4                | PF adjust value 4                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 105          | PFAdj5                | PF adjust value 5                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 106          | PFAdj6                | PF adjust value 6                                                                                 |              | 4096 is 1                                                              |             |               |      |
| 107          | QVRPDelayTi<br>meEE   | QV Reactive Power<br>delaytime                                                                    | W            | 0-30                                                                   | 1S          | 3S            |      |
| 108          | OverFDeratDelayTimeEE | Overfrequency derati<br>ngdelaytime                                                               | W            | 0-20                                                                   | 50ms        | 0             |      |

**Source page 15**

| Register NO. | Variable Name            | Description                           | Write or not | Value           | Unit        | Initial value | Note                                                                                                                                    |
| ------------ | ------------------------ | ------------------------------------- | ------------ | --------------- | ----------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 109          | QpercentMa<br>x          | Qmax for Q(V) curve                   | W            | 0-1000          | 0.1%        |               |                                                                                                                                         |
| 110          | PFLineP1_LP              | PF limit line point 1<br>load percent | W            | 0-255           | percen<br>t |               | 255 means no this point                                                                                                                 |
| 111          | PFLineP1_PF              | PF limit line point 1<br>power factor | W            | 0-20000         |             |               |                                                                                                                                         |
| 112          | PFLineP2_LP              | PF limit line point 2<br>load percent | W            | 0-255           | percen<br>t |               | 255 means no this point                                                                                                                 |
| 113          | PFLineP2_PF              | PF limit line point<br>2power factor  | W            | 0-20000         |             |               |                                                                                                                                         |
| 114          | PFLineP3_LP              | PF limit line point 3<br>load percent | W            | 0-255           | percen<br>t |               | 255 means no this point                                                                                                                 |
| 115          | PFLineP3_PF              | PF limit line point 3<br>power factor | W            | 0-20000         |             |               |                                                                                                                                         |
| 116          | PFLineP4_LP              | PF limit line point 4<br>load percent | W            | 0-255           | percen<br>t |               | 255 means no this point                                                                                                                 |
| 117          | PFLineP4_PF              | PF limit line point 4<br>power factor | W            | 0-20000         |             |               |                                                                                                                                         |
| 118          | Module 4                 | Inverter Module (4)                   |              | &amp;*11        |             |               | SxxBxx                                                                                                                                  |
| 119          | Module 3                 | Inverter Module (3)                   |              | &amp;*11        |             |               | DxxTxx                                                                                                                                  |
| 120          | Module 2                 | Inverter Module (2)                   |              | &amp;*11        |             |               | PxxUxx                                                                                                                                  |
| 121          | Module 1                 | Inverter Module (1)                   |              | &amp;*11        |             |               | Mxxxx Power                                                                                                                             |
| 122          | ExportLimit_<br>En/dis   | ExportLimit_En/dis                    | R/W          | 1/0             |             |               | ExportLimit enable,<br>0: Disable exportLimit;<br>1: Enable 485 exportLimit;<br>2: Enable 232 exportLimit;<br>3: Enable CT exportLimit; |
| 123          | ExportLimitP<br>owerRate | ExportLimitPowerRate                  | R/W          | -1000~+1<br>000 | 0.1%        |               | ExportLimit PowerRate                                                                                                                   |
| 124          | TrakerModel              | Traker Model                          | W            | 0,1,2           |             |               | 0:Independent<br>1:DC Source<br>2:Parallel                                                                                              |

#### Second group

| Register NO. | Variable Name | Description     | Write or not | Value | Unit  | Initial value | Note     |
| ------------ | ------------- | --------------- | ------------ | ----- | ----- | ------------- | -------- |
| 125          | INV Type-1    | Inverter type-1 | R            |       | ASCII |               | Reserved |
| 126          | INV Type-2    | Inverter type-2 | R            |       | ASCII |               |          |
| 127          | INV Type-3    | Inverter type-3 | R            |       | ASCII |               |          |
| 128          | INV Type-4    | Inverter type-4 | R            |       | ASCII |               |          |
| 129          | INV Type-5    | Inverter type-5 | R            |       | ASCII |               |          |
| 130          | INV Type-6    | Inverter type-6 | R            |       | ASCII |               |          |
| 131          | INV Type-7    | Inverter type-7 | R            |       | ASCII |               |          |
| 132          | INV Type-8    | Inverter type-8 | R            |       | ASCII |               |          |

**Source page 16**

| Register NO. | Variable Name                        | Description                           | Write or not | Value           | Unit       | Initial value | Note                    |
| ------------ | ------------------------------------ | ------------------------------------- | ------------ | --------------- | ---------- | ------------- | ----------------------- |
| 133          | BLVersion1                           | Boot loader version1                  | R            |                 |            |               | Reserved                |
| 134          | BLVersion2                           | Boot loader version2                  | R            |                 |            |               | Reserved                |
| 135          | BLVersion3                           | Boot loader version3                  | R            |                 |            |               | Reserved                |
| 136          | BLVersion4                           | Boot loader version4                  | R            |                 |            |               | Reserved                |
| 137          | Reactive P<br>ValueH                 | Reactive PowerH                       | R/W          |                 | 0.1var     |               |                         |
| 138          | Reactive P<br>ValueL                 | Reactive PowerL                       | R/W          |                 | 0.1var     |               |                         |
| 139          | ReactiveOut<br>putPriorityE<br>nable | ReactiveOutput Priority<br>Enable     | R/W          |                 | 0/1        |               | 0：disable<br>1：enable |
| ……           |                                      |                                       |              |                 |            |               |                         |
| 141          | SvgFunction<br>Enable                | Svg enable on night                   | R/W          |                 | 0/1        |               | 0：disable<br>1：enable |
| 142          | uwUnderFU<br>ploadPoint              | UnderF Upload Point                   | R/W          |                 | 0.01H<br>Z |               |                         |
| 143          | uwOFDerate<br>RecoverPoin<br>t       | OFDerate RecoverPoint                 | R/W          |                 | 0.01H<br>Z |               |                         |
| 144          | uwOFDerate<br>RecoverDela<br>yTime   | OFDerate<br>RecoverDelayTime          | R/W          | 0-30000         | 50ms       |               |                         |
| 145          | ZeroCurrent<br>Enable                | ZeroCurrent Enable                    | R/W          | 0-1             |            |               |                         |
| 146          | uwZeroCurre<br>ntStaticlowV<br>olt   | ZeroCurrent<br>StaticlowVolt          | R/W          | 46-230V         | 0.1V       | 115V          |                         |
| 147          | uwZeroCurre<br>ntStaticHigh<br>Volt  | ZeroCurrent<br>StaticHighVolt         | R/W          | 230-276V        | 0.1V       | 276V          |                         |
| 148          | uwHVoltDer<br>ateHighPoint           | HVoltDerate HighPoint                 | R/W          | 0-1000V         | 0.1V       |               |                         |
| 149          | uwHVoltDer<br>ateLowPoint            | HVoltDerate LowPoint                  | R/W          | 0-1000V         | 0.1V       |               |                         |
| 150          | uwQVPower<br>StableTime              | QVPower Stable Time                   | R/W          | 0-60S           | 0.1S       |               |                         |
| 151          | uwUnderFU<br>ploadStopPo<br>int      | UnderF Upload<br>StopPoint            | R/W          |                 | 0.01H<br>Z |               |                         |
| 152          | fUnderFreqP<br>oint                  | Underfrequency load<br>start point    | R/W          | 46.00-50.<br>00 | 0.01Hz     | 49.80         | CEI                     |
| 153          | fUnderFreqEndPoint                   | Underfrequency down<br>load end point | R/W          | 46.00-50.<br>00 | 0.01Hz     | 49.10         | CEI                     |

**Source page 17**

| Register NO. | Variable Name             | Description                               | Write or not | Value           | Unit        | Initial value | Note |
| ------------ | ------------------------- | ----------------------------------------- | ------------ | --------------- | ----------- | ------------- | ---- |
| 154          | fOverFreqPo<br>int        | Over frequency loading<br>start point     | R/W          | 50.00-52.<br>00 | 0.01Hz      | 50.20         | CEI  |
| 155          | fOverFreqEn<br>dPoint     | Over frequency loading<br>end point       | R/W          | 50.00-52.<br>00 | 0.01Hz      | 51.50         | CEI  |
| 156          | fUnderVoltP<br>oint       | Undervoltage load<br>shedding start point | R/W          | 160-300         | 0.1V        | 220.0         | CEI  |
| 157          | fUnderVoltE<br>ndPoint    | Undervoltage derating<br>end point        | R/W          | 160-300         | 0.1V        | 207.0         | CEI  |
| 158          | fOverVoltPoi<br>nt        | Overvoltage loading<br>start point        | R/W          | 160-300         | 0.1V        | 230.0         | CEI  |
| 159          | fOverVoltEn<br>dPoint     | Overvoltage loading<br>end point          | R/W          | 160-300         | 0.1V        | 245.0         | CEI  |
| 160          | uwNominal<br>GridVolt     | NominalGridVolt Select                    | R/W          | 0~3             |             |               | UL   |
| 161          | uwGridWatt<br>Delay       | GridWatt DelayTime                        | R/W          | 0~3000          | 20ms        |               | UL   |
| 162          | uwReconnec<br>tStartSlope | Reconnect StartSlope                      | R/W          | 1~1000          | 0.1         |               | UL   |
| 163          | uwLFRTEE                  | LFRT1 Freq                                | R/W          | 5500~650<br>0   | 0.01Hz      |               | UL   |
| 164          | uwLFRTTime<br>EE          | LFRT1 Time                                | R/W          |                 | 20ms        |               | UL   |
| 165          | uwLFRT2EE                 | LFRT2 Freq                                | R/W          | 5500~650<br>0   | 0.01Hz      |               | UL   |
| 166          | uwLFRTTime<br>2EE         | LFRT2 Time                                | R/W          |                 | 20ms        |               | UL   |
| 167          | uwHFRTEE                  | HFRT1 Freq                                | R/W          | 5500~650<br>0   | 0.01Hz      |               | UL   |
| 168          | uwHFRTTim<br>eEE          | HFRT1 Time                                | R/W          |                 | 20ms        |               | UL   |
| 169          | uwHFRT2EE                 | HFRT2 Freq                                | R/W          | 5500~650<br>0   | 0.01Hz      |               | UL   |
| 170          | uwHFRTTim<br>e2EE         | HFRT2 Time                                | R/W          |                 | 20ms        |               | UL   |
| 171          | uwHVRTEE                  | HVRT1 Volt                                | R/W          |                 | 0.001<br>Un |               | UL   |
| 172          | uwHVRTTim<br>eEE          | HVRT1 Time                                | R/W          |                 | 20ms        |               | UL   |
| 173          | uwHVRT2EE                 | HVRT2 Volt                                | R/W          |                 | 0.001<br>Un |               | UL   |
| 174          | uwHVRTTime2EE             | HVRT2 Time                                | R/W          |                 | 0.001<br>Un |               | UL   |

**Source page 18**

| Register NO. | Variable Name                    | Description                  | Write or not | Value | Unit   | Initial value | Note  |
| ------------ | -------------------------------- | ---------------------------- | ------------ | ----- | ------ | ------------- | ----- |
| 175          | uwUnderFU<br>ploadDelayTi<br>me  | UnderF<br>UploadDelayTime    | R/W          | 0-2s  | 50ms   | 0s            | 50549 |
| 176          | uwUnderFU<br>ploadRateEE         | UnderF UploadRate            | R/W          |       |        |               | 50549 |
| 177          | uwGridResta<br>rt_H_Freq         | GridRestart HighFreq         | R/W          |       | 0.01Hz |               | 50549 |
| 178          | OverFDeratR<br>esponseTim<br>e   | OverFDerat<br>ResponseTime   | W/R          | 0-500 |        |               |       |
| 179          | UnderFUplo<br>adResponse<br>Time | UnderFUpload<br>ResponseTime | W/R          | 0-500 |        |               |       |

#### Intelligent control reads relevant data, used to identify the logo 180-200

| Register NO. | Variable Name           | Description                                   | Write or not | Value                                                          | Unit | Initial value | Note                                                          |
| ------------ | ----------------------- | --------------------------------------------- | ------------ | -------------------------------------------------------------- | ---- | ------------- | ------------------------------------------------------------- |
| 180          | MeterLink               | Whether to elect the<br>meter                 | R/W          |                                                                |      |               | 0: Missed, 1: Received                                        |
| 181          | OPT Number              | Number of connection<br>optimizers            | R/W          | 0-64                                                           |      |               | The total number of optimizers<br>connected to the inverter   |
| 182          | OPT<br>ConfigOK<br>Flag | Optimizer<br>configuration<br>completion flag | R/W          |                                                                |      |               | 0x00:Not configured success<br>0x01:Configuration is complete |
| 183          | PvStrScan               | String Num                                    | R/W          | 0、8、16、<br>32                                               |      |               | 0：Not support<br>Other：PvString Num                         |
| ……           |                         |                                               |              |                                                                |      |               |                                                               |
| 200          | Reserved                |                                               |              |                                                                |      |               | Reserved                                                      |
| 201          | PID Working<br>Model    | PID Operating mode                            | W            | 0:<br>automati<br>c<br>1:<br>continuo<br>us<br>2: All<br>night |      |               |                                                               |
| 202          | PID On/Off<br>Ctrl      | PID Break control                             | W            | 0:On<br>1:Off                                                  |      |               |                                                               |
| 203          | PID Volt<br>Option      | PID Output voltage<br>option                  | W            | 300~1000                                                       | V    |               |                                                               |

**Source page 19**

| Register NO. | Variable Name    | Description                                                | Write or not | Value | Unit  | Initial value | Note                   |
| ------------ | ---------------- | ---------------------------------------------------------- | ------------ | ----- | ----- | ------------- | ---------------------- |
| ……           |                  |                                                            |              |       |       |               | Reserved               |
| 209          | New<br>Serial NO | Serial number 1-2                                          |              |       | ASCII |               |                        |
| 210          | New<br>Serial NO | Serial number 3-4                                          |              |       | ASCII |               |                        |
| 211          | New<br>Serial NO | Serial number 5-6                                          |              |       | ASCII |               |                        |
| 212          | New<br>Serial NO | Serial number 7-8                                          |              |       | ASCII |               |                        |
| 213          | New<br>Serial NO | Serial number 9-10                                         |              |       | ASCII |               |                        |
| 214          | New<br>Serial NO | Serial number 11-12                                        |              |       | ASCII |               |                        |
| 215          | New<br>Serial NO | Serial number 13-14                                        |              |       | ASCII |               |                        |
| 216          | New<br>Serial NO | Serial number 15-16                                        |              |       | ASCII |               |                        |
| 217          | New<br>Serial NO | Serial number 17-18                                        |              |       | ASCII |               |                        |
| 218          | New<br>Serial NO | Serial number 19-20                                        |              |       | ASCII |               |                        |
| 219          | New<br>Serial NO | Serial number 21-22                                        |              |       | ASCII |               |                        |
| 220          | New<br>Serial NO | Serial number 23-24                                        |              |       | ASCII |               |                        |
| 221          | New<br>Serial NO | Serial number 25-26                                        |              |       | ASCII |               |                        |
| 222          | New<br>Serial NO | Serial number 27-28                                        |              |       | ASCII |               |                        |
| 223          | New<br>Serial NO | Serial number 29-30                                        |              |       | ASCII |               |                        |
| ……           |                  |                                                            |              |       |       |               | Reserved               |
| 229          | EnergyAdjus<br>t | Power generation<br>incremental calibration<br>coefficient | W/R          |       | 0.1%  |               | 1-1000,(Percent ratio) |

#### 230~249 for growatt debug setting

| Register NO. | Variable Name     | Description                                                                                                     | Write or not | Value | Unit | Initial value | Note |
| ------------ | ----------------- | --------------------------------------------------------------------------------------------------------------- | ------------ | ----- | ---- | ------------- | ---- |
| 230          | IslandDisabl<br>e | Island Disable or not.<br>1:disable 0:Enable                                                                    | W            | 0,1   |      | 0             |      |
| 231          | FanCheck          | Start Fan Check                                                                                                 | W            | 1     |      |               |      |
| 232          | EnableNLine       | Enable N Line of grid                                                                                           | W            | 1     |      | 0             |      |
| 233          | wCheckHardware    | wCheckHardware<br>Bit0: GFCIBreak;<br>Bit1:SPSDamage<br>Bit8:EepromReadWarni<br>ng<br>Bit9:EEWriteWarning<br>…… |              |       |      |               |      |

**Source page 20**

| Register NO. | Variable Name       | Description                                         | Write or not | Value                 | Unit   | Initial value | Note                                                     |
| ------------ | ------------------- | --------------------------------------------------- | ------------ | --------------------- | ------ | ------------- | -------------------------------------------------------- |
| 234          | wCheckHard<br>ware2 |                                                     |              |                       |        |               | reserved                                                 |
| 235          | ubNToGNDD<br>etect  | Dis/enable N to GND<br>detect function              | W            | 1:enable<br>0:disable |        | 1             |                                                          |
| 236          | NonStdVacE<br>nable | Enable/Disable<br>Nonstandard<br>Grid voltage range | W            | 0-2                   |        | 0             | 0:Disable;<br>1:Enable Voltgrade1<br>2:Enable Voltgrade2 |
| 237          | uwEnableSp<br>ecSet | Disablse/enable<br>appointed spec setting           | W            | 1:enable<br>0:disable | Binary | 0x000<br>0    | Bit 0: Hungary                                           |
| 238          | Fast MPPT<br>enable | About Fast mppt                                     |              | 0,1,2                 |        | 0             | Reserved                                                 |
| 239          | /                   | /                                                   | /            | /                     |        | /             | Reserved                                                 |
| 240          | Check Step          |                                                     | W            |                       |        |               |                                                          |
| 241          | INV-Lng             | Inverter Longitude                                  | W            |                       |        |               | Longitude                                                |
| 242          | INV-Lat             | Inverter Latitude                                   | W            |                       |        |               | Latitude                                                 |
| ……           |                     |                                                     |              |                       |        |               | Reserved                                                 |
| 249          |                     |                                                     |              |                       |        |               | Reserved                                                 |

#### Six group for Storage Power

| Register NO. | Variable Name                        | Description                                                                                                      | Write or not | Value | Unit | Initial value | Note                                                                           |
| ------------ | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ------------ | ----- | ---- | ------------- | ------------------------------------------------------------------------------ |
| 1000.        | F loat<br>charge<br>current<br>limit | When charge current<br>battery need is lower<br>than this value, enter<br>into float charge                      | W            |       | 0.1A | 600           | CC current                                                                     |
| 1001.        | P F CMD<br>memory<br>state           | Set the following 19-22<br>CMD will be memory<br>ornot(1/0), if not, these<br>settings are the initial<br>value. | W            | 0or1, |      | 0             | Means these settings will be<br>acting or not when next<br>power on(02 repeat) |
| 1002.        | V batStartF<br>orDischarg<br>e       | LV Vbat                                                                                                          | R/W          |       | 0.1V |               | Lead-acid battery LV voltage                                                   |
| 1003.        | V batlowWa<br>rnClr                  | LoadPercent(only<br>lead-Acid):<br>45.5V<br>&lt;20%<br>48.0V<br>20%~50%<br>49.0V<br>&gt;50                       | W            |       | 0.1V |               | Clear battery low voltage error<br>voltage point                               |

**Source page 21**

| Register NO. | Variable Name                   | Description                                                                                                                                                                                                                                                                                                                    | Write or not | Value                                    | Unit  | Initial value | Note               |
| ------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | ---------------------------------------- | ----- | ------------- | ------------------ |
| 1004.        | V batstopfo<br>rdischarge       | Should stop discharge<br>when lower than this<br>voltage(only lead-Acid):<br>46.0V<br>&lt;20%<br>44.8V<br>20%~50%<br>44.2V<br>&gt;50%                                                                                                                                                                                          | W            |                                          | 0.01V |               |                    |
| 1005.        | V bat stop<br>for charge        | Should stop charge<br>when higher than this<br>voltage                                                                                                                                                                                                                                                                         | W            |                                          | 0.01V | 5800          |                    |
| 1006.        | V bat start<br>for<br>discharge | Should not discharge<br>when lower than this<br>voltage                                                                                                                                                                                                                                                                        | W            |                                          | 0.01V | 4800          |                    |
| 1007.        | V bat<br>constant<br>charge     | can charge when lower<br>than this voltage                                                                                                                                                                                                                                                                                     | W            |                                          | 0.01V | 5800          | CV voltage（acid） |
| 1008.        | E ESysInfo.S<br>ysSetEn         | Bit0：Resved;<br>Bit1：Resved;<br>Bit2：Resved;<br>Bit3：Resved;<br>Bit4：Resved;<br>Bit5：bDischargeEn；<br>Bit6：ForceDischrEn；<br>Bit7：ChargeEn；<br>Bit8：bForceChrEn；<br>Bit9：bBackUpEn；<br>Bit10：bInvLimitLoadE；<br>Bit11：bSpLimitLoadEn；<br>Bit12：bACChargeEn；<br>Bit13：bPVLoadLimitEn;<br>Bit14,15:UnUsed; | W            |                                          |       |               | System Enable      |
| 1009.        | B attemp<br>lower limit<br>d    | Battery temperature<br>lower limit for discharge                                                                                                                                                                                                                                                                               | W            | 0-200:0-2<br>0℃<br>1000-140<br>0：-40-0℃ | 0.1℃  | 1170          |                    |

**Source page 22**

| Register NO. | Variable Name                        | Description                                      | Write or not | Value                                    | Unit | Initial value | Note                    |
| ------------ | ------------------------------------ | ------------------------------------------------ | ------------ | ---------------------------------------- | ---- | ------------- | ----------------------- |
| 1010.        | B at temp<br>upper limit<br>d        | Battery temperature<br>upper limit for discharge | W            | 200-1000                                 | 0.1℃ | 420           |                         |
| 1011.        | B at temp<br>lower limit<br>c        | Battery temperature<br>lower limit for charge    | W            | 0-200:0-2<br>0℃<br>1000-140<br>0：-40-0℃ | 0.1℃ | 30            | Lower temperature limit |
| 1012.        | B at temp<br>upper limit<br>c        | Battery temperature<br>upper limit for charge    | W            | 200-1000                                 | 0.1℃ | 370           | Upper temperature limit |
| 1013.        | u wUnderFr<br>eDischarge<br>DelyTime | Under Fre Delay Time                             | s            | 0-20                                     | 50ms |               | Under Fre Delay Time    |
| 1014.        | B atMdlSeri<br>alNum                 | Battery serial number                            | W            | 00:00                                    |      |               | SPH4-11K used           |
| 1015.        | B atMdlPara<br>llNum                 | Battery parallel section                         | W            | 00:00                                    |      |               | SPH4-11K used           |
| 1016.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1017.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1018.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1019.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1020.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1021.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1022.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1023.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1024.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |
| 1025.        | /                                    | /                                                | /            | /                                        | /    | /             | Reserve                 |

**Source page 23**

| Register NO. | Variable Name | Description                                                  | Write or not | Value                                          | Unit | Initial value | Note    |
| ------------ | ------------- | ------------------------------------------------------------ | ------------ | ---------------------------------------------- | ---- | ------------- | ------- |
| 1026.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1027.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1028.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1029.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1030.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1031.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1032.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1033.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1034.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1035.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1036.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1037.        | bCTMode       | Use the CTMode to<br>Choose RFCT &#92; Cable<br>CT&#92;METER | W            | 2:METER<br>1:cWirele<br>ssCT<br>0:cWiredC<br>T |      | 0             |         |
| 1038.        | C TAdjust     | CTAdjust enable                                              | W            | 0:disable<br>1:enable                          |      | 0             |         |
| 1039.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1040.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1041.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |
| 1042.        | /             | /                                                            | /            | /                                              | /    |               | Reserve |
| 1043.        | /             | /                                                            | /            | /                                              | /    | /             | Reserve |

**Source page 24**

| Register NO. | Variable Name             | Description                                                         | Write or not | Value                                        | Unit | Initial value | Note                                  |
| ------------ | ------------------------- | ------------------------------------------------------------------- | ------------ | -------------------------------------------- | ---- | ------------- | ------------------------------------- |
| 1044.        | P riority                 | ForceChrEn/ForceDischr<br>En<br>Load first/bat first /grid<br>first | R            | 0.Load(de<br>fault)/1.B<br>attery/2.G<br>rid |      |               | bForceChrEn/disbForceDischrE<br>n/dis |
| 1045.        | /                         | /                                                                   | /            | /                                            | /    | /             | Reserve                               |
| 1046.        | /                         | /                                                                   | /            | /                                            | /    | /             | Reserve                               |
| 1047.        | A gingTestSt<br>ep<br>Cmd | Command for aging test                                              |              | 0: default<br>1: charge<br>2:<br>discharge   |      |               | Cmd for aging test                    |
| 1048.        | B atteryTyp<br>e          | Battery type choose of<br>buck-boost input                          |              | 0:Lithium<br>1:Lead-aci<br>d<br>2:other      |      | 0             | Battery type                          |
| 1049.        | /                         | /                                                                   | /            | /                                            | /    |               | Reserve                               |
| 1050.        | /                         | /                                                                   | /            | /                                            | /    | /             | Reserve                               |
| 1051.        | /                         | /                                                                   | /            | /                                            | /    |               | Reserve                               |
| 1052.        | /                         | /                                                                   | /            | /                                            | /    |               | Reserve                               |
| 1053.        | /                         | /                                                                   | /            | /                                            | /    |               | Reserve                               |
| 1054.        | /                         | /                                                                   | /            | /                                            | /    | /             | Reserve                               |
| 1060.        | B uckUpsFunE<br>n         | Ups function enable or<br>disable                                   |              | 0:disable<br>1:enable                        |      |               |                                       |
| 1061.        | B uckUPSVoltS<br>et       | UPS output voltage                                                  |              | 0:230<br>1:208<br>2:240                      |      | 230V          |                                       |
| 1062.        | U PSFreqSet               | UPS output frequency                                                |              | 0:50Hz<br>1:60Hz                             |      | 50Hz          |                                       |
| ...          | /                         | /                                                                   | /            | /                                            | /    | /             | reverse                               |

#### Priority set

**Source page 25**

| Register NO.  | Variable Name                        | Description                                                                    | Write or not | Value        | Unit | Initial value                                 | Note                                        |
| ------------- | ------------------------------------ | ------------------------------------------------------------------------------ | ------------ | ------------ | ---- | --------------------------------------------- | ------------------------------------------- |
| 1070.         | G ridFirstDisch<br>argePowerRat<br>e | Discharge Power Rate<br>when Grid First                                        | W            | 0-100        | 1%   | Discharge<br>Power Rate<br>when Grid<br>First |                                             |
| 1071.         | G ridFirstStopS<br>OC                | Stop Discharge soc when<br>Grid First                                          | W            | 0-100        | 1%   | Stop<br>Discharge<br>soc when<br>Grid First   |                                             |
| 1072…<br>1079 | /                                    | /                                                                              | /            | /            | /    | /                                             | reverse                                     |
| 1080.         | G rid First<br>Start Time 1          | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1081.         | G rid First Stop<br>Time 1           | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1082.         | G rid First Stop<br>Switch 1         | Enable :1<br>Disable:0                                                         |              | 0 or 1       |      | Grid First<br>enable                          |                                             |
| 1083.         | G rid First<br>Start Time 2          | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1084.         | G rid First Stop<br>Time 2           | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1085.         | G rid First Stop<br>Switch 2         | ForceDischarge.bSwitch&amp;L<br>CD_SET_FORCE_TRUE_2)=<br>=LCD_SET_FORCE_TRUE_2 |              | 0 or 1       |      | Grid First<br>enable                          | ForceDischarge;<br>LCD_SET_FORCE_T<br>RUE_2 |
| 1086.         | G rid First<br>Start Time 3          | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1087.         | G rid First Stop<br>Time 3           | High eight bit：hour<br>Low eight bit：minute                                  |              | 0-23<br>0-59 |      |                                               |                                             |
| 1088.         | G rid First Stop<br>Switch 3         | Enable :1<br>Disable:0                                                         |              | 0 or 1       |      | Grid First<br>enable                          |                                             |
| 1089.         | /                                    | /                                                                              | /            | /            | /    | /                                             | reserve                                     |
| 1090.         | B atFirstPower<br>Rate               | Charge Power Rate when<br>Bat First                                            | W            | 0-100        | 1%   | Charge<br>Power Rate<br>when Bat<br>First     |                                             |
| 1091.         | w BatFirst stop<br>SOC               | Stop Charge soc when Bat<br>First                                              | W            | 0-100        | 1%   | Stop<br>Charge soc<br>when Bat<br>First       |                                             |

**Source page 26**

| Register NO.  | Variable Name                   | Description                                   | Write or not | Value                 | Unit | Initial value        | Note         |
| ------------- | ------------------------------- | --------------------------------------------- | ------------ | --------------------- | ---- | -------------------- | ------------ |
| 1092.         | A C charge<br>Switch            | When Bat First<br>Enable:1<br>Disable:0       |              | Enable:1<br>Disable:0 |      | AC Charge<br>Enable  |              |
| 1093…<br>1099 |                                 |                                               |              |                       |      |                      |              |
| 1100.         | B at First Start<br>Time 1      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1101.         | B at First Stop<br>Time 1       | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1102.         | B atFirst<br>on/off<br>Switch 1 | Enable :1<br>Disable:0                        |              | 0 or 1                |      | Bat First<br>Enable1 |              |
| 1103.         | B at First Start<br>Time 2      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1104.         | B at First Stop<br>Time 2       | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1105.         | B atFirston/off<br>Switch 2     | Enable :1<br>Disable:0                        |              | 0 or 1                |      | Bat First<br>Enable2 |              |
| 1106.         | B at First Start<br>Time 3      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1107.         | B at First Stop<br>Time 3       | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      |              |
| 1108.         | B atFirston/off<br>Switch 3     | Enable :1<br>Disable:0                        |              | 0 or 1                |      | Bat First<br>Enable3 |              |
| 1109.         | /                               | /                                             | /            | /                     | /    | /                    | reserve      |
| 1110.         | L oad First<br>Start Time 1     | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      | SPA/ reserve |
| 1111.         | L oad First<br>Stop Time 1      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      | SPA/ reserve |
| 1112.         | L oad First<br>Switch 1         | Enable :1<br>Disable:0                        |              | 0 or 1                |      | Load First<br>Enable | SPA/ reserve |
| 1113.         | L oad First<br>Start Time2      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      | SPA/ reserve |
| 1114.         | L oad First<br>Stop Time 2      | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59          |      |                      | SPA/ reserve |
| 1115.         | L oad First<br>Switch 2         | Enable :1<br>Disable:0                        |              | 0 or 1                |      | Load First<br>Enable | SPA/ reserve |

**Source page 27**

| Register NO. | Variable Name               | Description                                   | Write or not | Value        | Unit | Initial value        | Note         |
| ------------ | --------------------------- | --------------------------------------------- | ------------ | ------------ | ---- | -------------------- | ------------ |
| 1116.        | L oad First<br>Start Time 3 | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59 |      |                      | SPA/ reserve |
| 1117.        | L oad First<br>Stop Time 3  | High eight bit：hour<br>Low eight bit：minute |              | 0-23<br>0-59 |      |                      | SPA/ reserve |
| 1118.        | L oad First<br>Switch 3     | Enable :1<br>Disable:0                        |              | 0 or 1       |      | Load First<br>Enable | SPA/ reserve |
| 1119.        | /                           | /                                             | /            | /            | /    | /                    | reserve      |
| 1120.        | B ackUpEn                   | BackUp Enable                                 |              |              |      |                      | MIX US       |
| 1121.        | S GIPEn                     | SGIP Enable                                   |              |              |      |                      | MIX US       |
| ………          | 1122~1124                   | /                                             | /            | /            | /    | /                    | reserve      |

#### Use for TL-X and TL-XH

| Register NO. | Variable Name                      | Description                               | Write or not | Value | Unit  | Initial value | Note                                                                                                                                                                                                                                   |
| ------------ | ---------------------------------- | ----------------------------------------- | ------------ | ----- | ----- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3000         | ExportLimitFa<br>iledPowerRat<br>e | The power rate when<br>exportLimit failed | R/W          |       | 0.1%  |               | The power rate<br>when exportLimit<br>failed                                                                                                                                                                                           |
| 3001         | New<br>Serial NO                   | Serial number 1-2                         | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3002         | New<br>Serial NO                   | Serial number 3-4                         | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3003         | New<br>Serial NO                   | Serial number 5-6                         | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3004         | New<br>Serial NO                   | Serial number 7-8                         | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3005         | New<br>Serial NO                   | Serial number 9-10                        | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3006         | New<br>Serial NO                   | Serial number 11-12                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3007         | New<br>Serial NO                   | Serial number 13-14                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3008         | New<br>Serial NO                   | Serial number 15-16                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3009         | New<br>Serial NO                   | Serial number 17-18                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3010         | New<br>Serial NO                   | Serial number 19-20                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |
| 3011         | New<br>Serial NO                   | Serial number 21-22                       | R/W          |       | ASCII |               | The new model<br>uses the following<br>registers to record<br>the serial number;<br>The<br>representation is<br>the same as the<br>original: one<br>register holds two<br>characters and the<br>new serial number<br>is 30 characters. |

**Source page 28**

| Register NO. | Variable Name                 | Description                                                                                 | Write or not                                 | Value                  | Unit       | Initial value | Note                                                                                                                                                                               |
| ------------ | ----------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------------- | ---------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3012         | New<br>Serial NO              | Serial number 23-24                                                                         | R/W                                          |                        | ASCII      |               |                                                                                                                                                                                    |
| 3013         | New<br>Serial NO              | Serial number 25-26                                                                         | R/W                                          |                        | ASCII      |               |                                                                                                                                                                                    |
| 3014         | New<br>Serial NO              | Serial number 27-28                                                                         | R/W                                          |                        | ASCII      |               |                                                                                                                                                                                    |
| 3015         | New<br>Serial NO              | Serial number 29-30                                                                         | R/W                                          |                        | ASCII      |               |                                                                                                                                                                                    |
| 3016         | DryContactFu<br>ncEn          | DryContact function enable                                                                  | R/W                                          | 0:Disable<br>1: Enable |            |               | DryContact<br>function enable                                                                                                                                                      |
| 3017         | DryContactOn<br>Rate          | The power rate of<br>drycontact turn on                                                     | R/W                                          | 0~1000                 | 0.1%       |               | The power rate of<br>drycontact turn on                                                                                                                                            |
| 3018         | Reserved                      |                                                                                             |                                              |                        |            |               |                                                                                                                                                                                    |
| 3019         | DryContactOf<br>fRate         | DryContactOffRate                                                                           | Dry<br>contact<br>closure<br>power           | R/W                    | 0~100<br>0 | 0.1%          | Dry contact<br>closure power pe<br>rcentage                                                                                                                                        |
| 3020         | BoxCtrlInvOrd<br>er           | BoxCtrlInvOrder                                                                             | Off-net<br>box<br>control<br>instruct<br>ion | R/W                    |            |               |                                                                                                                                                                                    |
| 3021         | ExterCommOf<br>fGridEn        | External communication<br>setting manual off-network<br>enable                              | R/W                                          |                        |            |               | 0x00: Disable;<br>（default）<br>0x01: Enable;                                                                                                                                     |
| 3022         | Reserved                      |                                                                                             |                                              |                        |            |               |                                                                                                                                                                                    |
| 3023         | Reserved                      |                                                                                             |                                              |                        |            |               |                                                                                                                                                                                    |
| 3024         | Float charge<br>current limit | When charge current<br>battery need is lower than<br>this value, enter into float<br>charge | R/W                                          |                        | 0.1A       | 600           | CC current                                                                                                                                                                         |
| 3025         | VbatWarning                   | "Battery-low" warning<br>setup voltage                                                      | R/W                                          |                        | 0.1V       | 4800          | Lead acid battery<br>LV voltage                                                                                                                                                    |
| 3026         | VbatlowWarn<br>Clr            | "Battery-low" warning<br>clear voltage                                                      | R/W                                          |                        | 0.1V       |               | Clear battery low<br>voltage error<br>voltage point<br>LoadPercent(only<br>lead-Acid):<br>45.5V(Load &lt;<br>20%);<br>48.0V(20%&lt;=Load<br>&lt;=50%);<br>49.0V(Load &gt;<br>50%); |

**Source page 29**

| Register NO. | Variable Name               | Description                                      | Write or not | Value | Unit  | Initial value | Note                                                                                                                                                                        |
| ------------ | --------------------------- | ------------------------------------------------ | ------------ | ----- | ----- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3027         | Vbatstopfordi<br>scharge    | Battery cut off voltage                          | R/W          |       | 0.1V  |               | Should stop<br>discharge when<br>lower than this<br>voltage(only<br>lead-Acid):<br>46.0V(Load &lt;<br>20%);<br>44.8V(20%&lt;=Load<br>&lt;=50%);<br>44.2V(Load &gt;<br>50%); |
| 3028         | Vbat stop for<br>charge     | Battery over charge voltage                      | R/W          |       | 0.01V | 5800          | Should stop<br>charge when<br>higher than this<br>voltage                                                                                                                   |
| 3029         | Vbat start for<br>discharge | Battery start discharge<br>voltage               | R/W          |       | 0.01V | 4800          | Should not<br>discharge when<br>lower than this<br>voltage                                                                                                                  |
| 3030         | Vbat constant<br>charge     | Battery constant charge<br>voltage               | R/W          |       | 0.01V | 5800          | CV voltage（acid）<br>can charge when<br>lower than this<br>voltage                                                                                                         |
| 3031         | Battemp<br>lower limit d    | Battery temperature lower<br>limit for discharge | R/W          |       | 0.1℃  | 1170          | 0-200:0-20℃<br>1000-1400：<br>-40-0℃                                                                                                                                        |
| 3032         | Bat temp<br>upper limit d   | Battery temperature upper<br>limit for discharge | R/W          |       | 0.1℃  | 420           |                                                                                                                                                                             |
| 3033         | Bat temp<br>lower limit c   | Battery temperature lower<br>limit for charge    | R/W          |       | 0.1℃  | 30            | Battery<br>temperature lower<br>limit<br>0-200:0-20℃<br>1000-1400：<br>-40-0℃                                                                                               |

**Source page 30**

| Register NO. | Variable Name                       | Description                                                                                                                                                     | Write or not | Value | Unit | Initial value | Note                                                                                                                                                           |
| ------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ----- | ---- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3034         | Bat temp<br>upper limit c           | Battery temperature upper<br>limit for charge                                                                                                                   | R/W          |       | 0.1℃ | 370           | Battery<br>temperature<br>upper limit                                                                                                                          |
| 3035         | uwUnderFreD<br>ischargeDelyT<br>ime | Under Fre Delay Time                                                                                                                                            | R/W          |       | 50ms |               | Under Fre Delay<br>Time                                                                                                                                        |
| 3036         | GridFirstDisch<br>argePowerRat<br>e | Discharge Power Rate<br>when Grid First                                                                                                                         |              |       |      | 1-255         |                                                                                                                                                                |
| 3037         | GridFirstStopS<br>OC                | Stop Discharge soc when<br>Grid First                                                                                                                           |              |       |      | 1-100         |                                                                                                                                                                |
| 3038         | Time 1(xh)                          | Period 1: [Start Time ~ End<br>Time], [Charge/Discharge],<br>[Disable/Enable]<br>3038 enable, charge and<br>discharge, start time, end<br>time 3039             | R/W          |       |      |               | Bit0~~7: minutes;<br>Bit8~~12: hour;<br>Bit13~14,<br>0: load priority;<br>1: battery priority;<br>2: Grid priority;<br>Bit15,<br>0: prohibited; 1:<br>enabled; |
| 3039         | Time 1(xh)                          | Period 1: [Start Time ~ End<br>Time], [Charge/Discharge],<br>[Disable/Enable]<br>3038 enable, charge and<br>discharge, start time, end<br>time 3039             | R/W          |       |      |               | Bit0~~7: minutes;<br>Bit8~~12: hour;<br>Bit13~15: reserved                                                                                                     |
| 3040         | Time 2(xh)                          | Time period 2: [start time ~<br>end time], [charge /<br>discharge], [disable /<br>enable]<br>3040 enable, charge and<br>discharge, start time, 3041<br>end time | R/W          |       |      |               | Bit0~~7: minutes;<br>Bit8~~12: hour;<br>Bit13~14,<br>0: load priority;<br>1: battery priority;<br>2: Grid priority;<br>Bit15,<br>0: prohibited; 1:<br>enabled; |
| 3041         | Time 2(xh)                          | Time period 2: [start time ~<br>end time], [charge /<br>discharge], [disable /<br>enable]<br>3040 enable, charge and<br>discharge, start time, 3041<br>end time | R/W          |       |      |               | Bit0~~7: minutes;<br>Bit8~~12: hour;<br>Bit13~15: reserved                                                                                                     |
| 3042         | Time 3(xh)                          | With Time1                                                                                                                                                      | R/W          |       |      |               | With Time1                                                                                                                                                     |
| 3043         | Time 3(xh)                          | With Time1                                                                                                                                                      | R/W          |       |      |               | With Time1                                                                                                                                                     |
| 3044         | Time 4(xh)                          | With Time1                                                                                                                                                      | R/W          |       |      |               | With Time1                                                                                                                                                     |
| 3045         | Time 4(xh)                          | With Time1                                                                                                                                                      | R/W          |       |      |               | With Time1                                                                                                                                                     |
| 3046         | Grid First Stop<br>Switch 3         | Grid first time-3 enable                                                                                                                                        |              |       |      |               | Enable :1<br>Disable:0                                                                                                                                         |

**Source page 31**

| Register NO.  | Variable Name            | Description                                | Write or not | Value | Unit | Initial value | Note                                                                                                                                                                                    |
| ------------- | ------------------------ | ------------------------------------------ | ------------ | ----- | ---- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3047          | BatFirstPower<br>Rate    | Charge Power Rate when<br>Bat First        |              |       |      | 1-100         |                                                                                                                                                                                         |
| 3048          | wBatFirst stop<br>SOC    | Stop Charge soc when Bat<br>First          |              |       |      | 1-100         |                                                                                                                                                                                         |
| 3049          | AcChargeEna<br>ble       | AcChargeEnable                             |              |       |      |               | Enable :1<br>Disable:0                                                                                                                                                                  |
| 3050          | Time 5(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3051          | Time 5(xh)               |                                            | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3052          | Time 6(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3053          | Time 6(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3054          | Time 7(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3055          | Time 7(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3056          | Time 8(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3057          | Time 8(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3058          | Time 9(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3059          | Time 9(xh)               | 同 Time1                                   | R/W          |       |      |               | With Time1                                                                                                                                                                              |
| 3060~<br>3069 | Reserved                 |                                            |              |       |      |               |                                                                                                                                                                                         |
| 3070          | BatteryType              | Battery type choose of<br>buck-boost input | R/W          |       |      |               | Battery type<br>0:Lithium<br>1:Lead-acid<br>2:other                                                                                                                                     |
| 3071          | BatMdlSeria/<br>ParalNum | BatMdlSeria/ParalNum                       | R/W          |       |      |               | BatMdlSeria/Paral<br>Num;<br>SPH4-11K used<br>The upper 8 bits<br>indicate the<br>number of series<br>segments；<br>The lower 8 bits<br>indicate the<br>number of parallel<br>sections; |

**Source page 32**

| Register NO. | Variable Name            | Description                       | Write or not | Value | Unit  | Initial value | Note                                                                    |
| ------------ | ------------------------ | --------------------------------- | ------------ | ----- | ----- | ------------- | ----------------------------------------------------------------------- |
| 3072         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3073         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3074         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3075         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3076         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3077         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3078         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3079         | UpsFunEn                 | Ups function enable or<br>disable | R/W          |       |       | 0             | 0:disable<br>1:enable                                                   |
| 3080         | UPSVoltSet               | UPS output voltage                | R/W          |       |       | 0             | 0:230V<br>1:208V<br>2:240V                                              |
| 3081         | UPSFreqSet               | UPS output frequency              | R/W          |       |       | 0             | 0:50Hz<br>1:60Hz                                                        |
| 3082         | bLoadFirstSto<br>pSocSet | StopSoc When LoadFirst            | R/W          |       |       | 13-100        | ratio                                                                   |
| 3083         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3084         | Reserved                 |                                   |              |       |       |               |                                                                         |
| 3085         | Com Address              | Communication addr                | R/W          |       |       | 1             | 1 : Communication<br>addr=1<br>1 ~ 254 :<br>Communication<br>addr=1~254 |
| 3086         | BaudRate                 | Communication BaudRate            | R/W          |       |       | 0             | 0: 9600 bps<br>1: 38400 bps                                             |
| 3087         | Serial NO                | Serial Number 1-2                 | R/W          |       | ASCII |               | For battery                                                             |
| 3088         | Serial No                | Serial Number 3-4                 | R/W          |       | ASCII |               |                                                                         |
| 3089         | Serial No                | Serial Number 5-6                 | R/W          |       | ASCII |               |                                                                         |
| 3090         | Serial No                | Serial Number 7-8                 | R/W          |       | ASCII |               |                                                                         |
| 3091         | Serial No                | Serial Number 9-10                | R/W          |       | ASCII |               |                                                                         |
| 3092         | Model H                  | Model H                           | R/W          |       |       |               |                                                                         |
| 3093         | Model L                  | Model L                           | R/W          |       |       |               |                                                                         |
| 3094         | Pdischr max H            | Max Discharge Power               | R            |       | 0.1W  |               |                                                                         |
| 3095         | Pdischr max<br>L         | Max Discharge Power               | R            |       | 0.1W  |               |                                                                         |
| 3096         | Pchr max H               | Max Charge Power                  | R            |       | 0.1W  |               |                                                                         |
| 3097         | Pchr max L               | Max Charge Power                  | R            |       | 0.1W  |               |                                                                         |
| 3098         | DTC                      | DTC                               | R            |       |       |               |                                                                         |

**Source page 33**

| Register NO.      | Variable Name           | Description          | Write or not | Value | Unit  | Initial value | Note |
| ----------------- | ----------------------- | -------------------- | ------------ | ----- | ----- | ------------- | ---- |
| 3099              | FW Code1                | FW Code1             | R            |       | ASCII |               |      |
| 3100              | FW Code2                | FW Code2             | R            |       | ASCII |               |      |
| 3101              | Processor1<br>FW Vision | Processor1 FW Vision | R            |       | ASCII |               |      |
| 3102              | Reset User<br>Info      | Reset User Info      | W            |       |       |               |      |
| 3103              | Reset to<br>factory     | Reset to factory     | W            |       |       |               |      |
| 3104<br>~<br>3124 | Reserved                |                      |              |       |       |               |      |

#### First group

### 4.2 Input Reg

**Source page 33**

| NO. | Variable Name   | Description            | Value                              | Unit | Note |
| --- | --------------- | ---------------------- | ---------------------------------- | ---- | ---- |
| 0.  | Inverter Status | Inverter run state     | 0:waiting,<br>1:normal,<br>3:fault |      |      |
| 1.  | Ppv H           | Input power (high)     |                                    | 0.1W |      |
| 2.  | Ppv L           | Input power (low)      |                                    | 0.1W |      |
| 3.  | Vpv1            | PV1 voltage            |                                    | 0.1V |      |
| 4.  | PV1Curr         | PV1 input current      |                                    | 0.1A |      |
| 5.  | Ppv1 H          | PV1 input power(high)  |                                    | 0.1W |      |
| 6.  | Ppv1 L          | PV1 input power(low)   |                                    | 0.1W |      |
| 7.  | Vpv2            | PV2 voltage            |                                    | 0.1V |      |
| 8.  | PV2Curr         | PV2 input current      |                                    | 0.1A |      |
| 9.  | Ppv2 H          | PV2 input power (high) |                                    | 0.1W |      |
| 10. | Ppv2 L          | PV2 input power (low)  |                                    | 0.1W |      |
| 11. | Vpv3            | PV3 voltage            |                                    | 0.1V |      |
| 12. | PV3Curr         | PV3 input current      |                                    | 0.1A |      |
| 13. | Ppv3 H          | PV3 input power (high) |                                    | 0.1W |      |
| 14. | Ppv3 L          | PV3 input power (low)  |                                    | 0.1W |      |
| 15. | Vpv4            | PV4 voltage            |                                    | 0.1V |      |
| 16. | PV4Curr         | PV4 input current      |                                    | 0.1A |      |
| 17. | Ppv4 H          | PV4 input power (high) |                                    | 0.1W |      |
| 18. | Ppv4 L          | PV4 input power (low)  |                                    | 0.1W |      |
| 19. | Vpv5            | PV5 voltage            |                                    | 0.1V |      |
| 20. | PV5Curr         | PV5 input current      |                                    | 0.1A |      |
| 21. | Ppv5H           | PV5 input power(high)  |                                    | 0.1W |      |

**Source page 34**

| NO. | Variable Name | Description                                      | Value | Unit   | Note         |
| --- | ------------- | ------------------------------------------------ | ----- | ------ | ------------ |
| 22. | Ppv5 L        | PV5 input power(low)                             |       | 0.1W   |              |
| 23. | Vpv6          | PV6 voltage                                      |       | 0.1V   |              |
| 24. | PV6Curr       | PV6 input current                                |       | 0.1A   |              |
| 25. | Ppv6 H        | PV6 input power (high)                           |       | 0.1W   |              |
| 26. | Ppv6 L        | PV6 input power (low)                            |       | 0.1W   |              |
| 27. | Vpv7          | PV7 voltage                                      |       | 0.1V   |              |
| 28. | PV7Curr       | PV7 input current                                |       | 0.1A   |              |
| 29. | Ppv7 H        | PV7 input power (high)                           |       | 0.1W   |              |
| 30. | Ppv7 L        | PV7 input power (low)                            |       | 0.1W   |              |
| 31. | Vpv8          | PV8 voltage                                      |       | 0.1V   |              |
| 32. | PV8Curr       | PV8 input current                                |       | 0.1A   |              |
| 33. | Ppv8 H        | PV8 input power (high)                           |       | 0.1W   |              |
| 34. | Ppv8 L        | PV8 input power (low)                            |       | 0.1W   |              |
| 35. | Pac H         | Output power (high)                              |       | 0.1W   |              |
| 36. | Pac L         | Output power (low)                               |       | 0.1W   |              |
| 37. | Fac           | Grid frequency                                   |       | 0.01Hz |              |
| 38. | Vac1          | Three/single phase grid voltage                  |       | 0.1V   |              |
| 39. | Iac1          | Three/single phase grid output current           |       | 0.1A   |              |
| 40. | Pac1 H        | Three/single phase grid output watt<br>VA (high) |       | 0.1VA  |              |
| 41. | Pac1 L        | Three/single phase grid output watt<br>VA(low)   |       | 0.1VA  |              |
| 42. | Vac2          | Three phase grid voltage                         |       | 0.1V   |              |
| 43. | Iac2          | Three phase grid output current                  |       | 0.1A   |              |
| 44. | Pac2 H        | Three phase grid output power (high)             |       | 0.1VA  |              |
| 45. | Pac2 L        | Three phase grid output power (low)              |       | 0.1VA  |              |
| 46. | Vac3          | Three phase grid voltage                         |       | 0.1V   |              |
| 47. | Iac3          | Three phase grid output current                  |       | 0.1A   |              |
| 48. | Pac3 H        | Three phase grid output power (high)             |       | 0.1VA  |              |
| 49. | Pac3 L        | Three phase grid output power (low)              |       | 0.1VA  |              |
| 50. | Vac_RS        | Three phase grid voltage                         |       | 0.1V   | Line voltage |
| 51. | Vac_ST        | Three phase grid voltage                         |       | 0.1V   | Line voltage |
| 52. | Vac_TR        | Three phase grid voltage                         |       | 0.1V   | Line voltage |
| 53. | Eactoday H    | Today generate energy (high)                     |       | 0.1kWH |              |
| 54. | Eac today L   | Today generate energy (low)                      |       | 0.1kWH |              |
| 55. | Eac total H   | Total generate energy (high)                     |       | 0.1kWH |              |
| 56. | Eac total L   | Total generate energy (low)                      |       | 0.1kWH |              |
| 57. | Time total H  | Work time total (high)                           |       | 0.5s   |              |
| 58. | Time total L  | Work time total (low)                            |       | 0.5s   |              |
| 59. | Epv1_today H  | PV1Energy today(high)                            |       | 0.1kWh |              |
| 60. | Epv1_today L  | PV1Energy today (low)                            |       | 0.1kWh |              |

**Source page 35**

| NO. | Variable Name | Description                            | Value | Unit   | Note         |
| --- | ------------- | -------------------------------------- | ----- | ------ | ------------ |
| 61. | Epv1_total H  | PV1Energy total(high)                  |       | 0.1kWh |              |
| 62. | Epv1_total L  | PV1Energy total (low)                  |       | 0.1kWh |              |
| 63. | Epv2_today H  | PV2Energy today(high)                  |       | 0.1kWh |              |
| 64. | Epv2_today L  | PV2Energy today (low)                  |       | 0.1kWh |              |
| 65. | Epv2_total H  | PV2Energy total(high)                  |       | 0.1kWh |              |
| 66. | Epv2_total L  | PV2Energy total (low)                  |       | 0.1kWh |              |
| 67. | Epv3_today H  | PV3 Energy today(high)                 |       | 0.1kWh |              |
| 68. | Epv3_today L  | PV3 Energy today (low)                 |       | 0.1kWh |              |
| 69. | Epv3_total H  | PV3 Energy total(high)                 |       | 0.1kWh |              |
| 70. | Epv3_total L  | PV3 Energy total (low)                 |       | 0.1kWh |              |
| 71. | Epv4_today H  | PV4Energy today(high)                  |       | 0.1kWh |              |
| 72. | Epv4_today L  | PV4Energy today (low)                  |       | 0.1kWh |              |
| 73. | Epv4_total H  | PV4Energy total(high)                  |       | 0.1kWh |              |
| 74. | Epv4_total L  | PV4Energy total (low)                  |       | 0.1kWh |              |
| 75. | Epv5_today H  | PV5Energy today(high)                  |       | 0.1kWh |              |
| 76. | Epv5_today L  | PV5Energy today (low)                  |       | 0.1kWh |              |
| 77. | Epv5_total H  | PV5Energy total(high)                  |       | 0.1kWh |              |
| 78. | Epv5_total L  | PV5Energy total (low)                  |       | 0.1kWh |              |
| 79. | Epv6_today H  | PV6Energy today(high)                  |       | 0.1kWh |              |
| 80. | Epv6_today L  | PV6Energy today (low)                  |       | 0.1kWh |              |
| 81. | Epv6_total H  | PV6Energy total(high)                  |       | 0.1kWh |              |
| 82. | Epv6_total L  | PV6Energy total (low)                  |       | 0.1kWh |              |
| 83. | Epv7_today H  | PV7Energy today(high)                  |       | 0.1kWh |              |
| 84. | Epv7_today L  | PV7Energy today (low)                  |       | 0.1kWh |              |
| 85. | Epv7_total H  | PV7 Energy total(high)                 |       | 0.1kWh |              |
| 86. | Epv7_total L  | PV7Energy total (low)                  |       | 0.1kWh |              |
| 87. | Epv8_today H  | PV8Energy today(high)                  |       | 0.1kWh |              |
| 88. | Epv8_today L  | PV8Energy today (low)                  |       | 0.1kWh |              |
| 89. | Epv8_total H  | PV8Energy total(high)                  |       | 0.1kWh |              |
| 90. | Epv8_total L  | PV8Energy total (low)                  |       | 0.1kWh |              |
| 91. | Epv_total H   | PV Energy total(high)                  |       | 0.1kWh |              |
| 92. | Epv_total L   | PV Energy total (low)                  |       | 0.1kWh |              |
| 93. | Temp1         | Inverter temperature                   |       | 0.1C   |              |
| 94. | Temp2         | The inside IPM in inverter Temperature |       | 0.1C   |              |
| 95. | Temp3         | Boost temperature                      |       | 0.1C   |              |
| 96. | Temp4         |                                        |       |        | reserved     |
| 97. | uwBatVolt_DSP | BatVolt_DSP                            |       | 0.1V   | BatVolt(DSP) |
| 98. | P Bus Voltage | P Bus inside Voltage                   |       | 0.1V   |              |
| 99. | N Bus Voltage | N Bus inside Voltage                   |       | 0.1V   |              |

**Source page 36**

| NO.  | Variable Name                                   | Description                                   | Value                                                                                                                     | Unit        | Note                    |
| ---- | ----------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------- |
| 100. | IPF                                             | Inverter output PF now                        | 0-20000                                                                                                                   |             |                         |
| 101. | RealOPPercent                                   | Real Output power Percent                     |                                                                                                                           | 1%          |                         |
| 102. | OPFullwatt H                                    | Output Maxpower Limited high                  |                                                                                                                           |             |                         |
| 103. | OPFullwatt L                                    | Output Maxpower Limited low                   |                                                                                                                           | 0.1W        |                         |
| 104. | DeratingMode                                    | DeratingMode                                  | 0:no derate;<br>1:PV;<br>2:_;<br>3:Vac;<br>4:Fac;<br>5:Tboost;<br>6:Tinv;<br>7:Control;<br>8:_;<br>9:*OverBack<br>ByTime; |             |                         |
| 105. | Fault code                                      | Inverter fault code                           | &amp;*1                                                                                                                   |             | MAX                     |
| 106. | Fault Bitcode H                                 | Inverter fault code high                      | &amp;*8                                                                                                                   |             | MAX                     |
| 107. | Fault Bitcode L                                 | Inverter fault code low                       | &amp;*8                                                                                                                   |             |                         |
| 108. | RemoteCtrlEn                                    | /                                             | 0.Load First<br>1.BatFirst<br>2.Grid                                                                                      | /           | StoragePow<br>er (SPA)  |
| 109. | RemoteCtrlPow<br>er                             | /                                             | 0.Load First<br>1.BatFirst<br>2.Grid                                                                                      | /           | StoragePow<br>er (SPA)  |
| 110. | Warning bit H                                   | Warning bit H                                 | &amp;*8                                                                                                                   |             |                         |
| 111. | Warning bit L                                   | Warning bit L                                 | &amp;*8                                                                                                                   |             |                         |
| 112. | bINVWarnCode<br>EACharge_Today<br>_H            | bINVWarnCode<br>ACCharge energy today         |                                                                                                                           | 0.1kwh      | MAX<br>Storage<br>Power |
| 113. | real Power<br>Percent<br>EACharge_Today<br>_L   | real Power Percent<br>ACCharge energy today   | 0-100                                                                                                                     | %<br>0.1kwh | MAX<br>Storage<br>Power |
| 114. | inv start delay<br>time<br>EACharge_Total<br>_H | inv start delay time<br>ACCharge energy total |                                                                                                                           | 0.1kwh      | MAX<br>Storage<br>Power |
| 115. | bINVAllFaultCod<br>e<br>EACharge_Total<br>_L    | bINVAllFaultCode<br>ACCharge energy total     |                                                                                                                           | 0.1kwh      | MAX<br>Storage<br>Power |
| 116. | AC charge<br>Power_H                            | Grid power to local load                      |                                                                                                                           | 0.1kwh      | Storage<br>Power        |

**Source page 37**

| NO.  | Variable Name        | Description                                     | Value | Unit   | Note             |
| ---- | -------------------- | ----------------------------------------------- | ----- | ------ | ---------------- |
| 117. | AC charge<br>Power_L | Grid power to local load                        |       | 0.1kwh | Storage<br>Power |
| 118. | Priority             | 0:Load First<br>1:Battery First<br>2:Grid First |       |        | Storage<br>Power |
| 119. | Battery Type         | 0：Lead-acid<br>1：Lithium battery              |       |        | Storage<br>Power |
| 120. | AutoProofreadC<br>MD | Aging mode 自动校准命令                         |       |        | Storage<br>Power |
| …    | reserved             |                                                 |       |        | reserved         |
| 124. | reserved             |                                                 |       |        | reserved         |

#### Second group

| NO.  | Variable Name    | Description                                                                                           | Value    | Unit  | Note |
| ---- | ---------------- | ----------------------------------------------------------------------------------------------------- | -------- | ----- | ---- |
| 125. | PID PV1+ Voltage | PID PV1PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 126. | PID PV1+ Current | PID PV1PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 127. | PID PV2+ Voltage | PID PV2PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 128. | PID PV2+ Current | PID PV2PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 129. | PID PV3+ Voltage | PID PV3PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 130. | PID PV3+ Current | PID PV3PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 131. | PID PV4+ Voltage | PID PV4PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 132. | PID PV4+ Current | PID PV4PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 133. | PID PV5+ Voltage | PID PV5PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 134. | PID PV5+ Current | PID PV5PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 135. | PID PV6+ Voltage | PID PV6PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 136. | PID PV6+ Current | PID PV6PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 137. | PID PV7+ Voltage | PID PV7PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 138. | PID PV7+ Current | PID PV7PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 139. | PID PV8+ Voltage | PID PV8PE Volt                                                                                        | 0~1000V  | 0.1V  |      |
| 140. | PID PV8+ Current | PID PV8PE Curr                                                                                        | -10~10mA | 0.1mA |      |
| 141. | PID Status       | Bit0~~7:PID Working Status<br>1:Wait Status<br>2:Normal Status<br>3:Fault Status<br>Bit8~~15:Reversed | 0~3      |       |      |
| 142. | V _String1       | PV String1 voltage                                                                                    |          | 0.1V  |      |
| 143. | Curr _String1    | PV String1 current                                                                                    | -15~15A  | 0.1A  |      |
| 144. | V _String2       | PV String2 voltage                                                                                    |          | 0.1V  |      |
| 145. | Curr _String2    | PV String2 current                                                                                    | -15~15A  | 0.1A  |      |
| 146. | V _String3       | PV String3 voltage                                                                                    |          | 0.1V  |      |
| 147. | Curr _String3    | PV String3 current                                                                                    | -15~15A  | 0.1A  |      |
| 148. | V _String4       | PV String4 voltage                                                                                    |          | 0.1V  |      |

**Source page 38**

| NO.  | Variable Name           | Description                                                                                               | Value    | Unit | Note       |
| ---- | ----------------------- | --------------------------------------------------------------------------------------------------------- | -------- | ---- | ---------- |
| 149. | Curr _String4           | PV String4 current                                                                                        | -15~15A  | 0.1A |            |
| 150. | V _String5              | PV String5 voltage                                                                                        |          | 0.1V |            |
| 151. | Curr _String5           | PV String5 current                                                                                        | -15~15A  | 0.1A |            |
| 152. | V _String6              | PV String6 voltage                                                                                        |          | 0.1V |            |
| 153. | Curr _String6           | PV String6 current                                                                                        | -15~15A  | 0.1A |            |
| 154. | V _String7              | PV String7 voltage                                                                                        |          | 0.1V |            |
| 155. | Curr _String7           | PV String7 current                                                                                        | -15~15A  | 0.1A |            |
| 156. | V _String8              | PV String8 voltage                                                                                        |          | 0.1V |            |
| 157. | Curr _String8           | PV String8 current                                                                                        | -15A~15A | 0.1A |            |
| 158. | V _String9              | PV String9 voltage                                                                                        |          | 0.1V |            |
| 159. | Curr _String9           | PV String9 current                                                                                        | -15A~15A | 0.1A |            |
| 160. | V _String10             | PV String10 voltage                                                                                       |          | 0.1V |            |
| 161. | Curr _String10          | PV String10 current                                                                                       | -15~15A  | 0.1A |            |
| 162. | V _String11             | PV String11 voltage                                                                                       |          | 0.1V |            |
| 163. | Curr _String11          | PV String11 current                                                                                       | -15~15A  | 0.1A |            |
| 164. | V _String12             | PV String12 voltage                                                                                       |          | 0.1V |            |
| 165. | Curr _String12          | PV String12 current                                                                                       | -15~15A  | 0.1A |            |
| 166. | V _String13             | PV String13 voltage                                                                                       |          | 0.1V |            |
| 167. | Curr _String13          | PV String13 current                                                                                       | -15A~15A | 0.1A |            |
| 168. | V _String14             | PV String14 voltage                                                                                       |          | 0.1V |            |
| 169. | Curr _String14          | PV String14 current                                                                                       | -15~15A  | 0.1A |            |
| 170. | V _String15             | PV String15 voltage                                                                                       |          | 0.1V |            |
| 171. | Curr _String15          | PV String15 current                                                                                       | -15~15A  | 0.1A |            |
| 172. | V _String16             | PV String16 voltage                                                                                       |          | 0.1V |            |
| 173. | Curr _String16          | PV String16 current                                                                                       | -15~15A  | 0.1A |            |
| 174. | StrUnmatch              | Bit0~~15: String1~~16 unmatch                                                                             |          |      | suggestive |
| 175. | StrCurrentUnblan<br>ce  | Bit0~~15: String1~~16 current unblance                                                                    |          |      | suggestive |
| 176. | StrDisconnect           | Bit0~~15: String1~~16 disconnect                                                                          |          |      | suggestive |
| 177. | PIDFaultCode            | Bit0:Output over voltage<br>Bit1: ISO fault<br>Bit2: BUS voltage abnormal<br>Bit3~15:reserved             |          |      |            |
| 178. | String Prompt           | String Prompt<br>Bit0:String Unmatch<br>Bit1:StrDisconnect<br>Bit2:StrCurrentUnblance<br>Bit3~15:reserved |          |      |            |
| 179  | PV Warning Value        | PV Warning Value                                                                                          |          |      |            |
| 180  | DSP075 Warning<br>Value | DSP075 Warning Value                                                                                      |          |      |            |

**Source page 39**

| NO. | Variable Name              | Description           | Value | Unit  | Note |
| --- | -------------------------- | --------------------- | ----- | ----- | ---- |
| 181 | DSP075 Fault<br>Value      | DSP075 Fault Value    |       |       |      |
| 182 | DSP067 Debug<br>Data1      | DSP067 Debug Data1    |       |       |      |
| 183 | DSP067 Debug<br>Data2      | DSP067 Debug Data2    |       |       |      |
| 184 | DSP067 Debug<br>Data3      | DSP067 Debug Data3    |       |       |      |
| 185 | DSP067 Debug<br>Data4      | DSP067 Debug Data4    |       |       |      |
| 186 | DSP067 Debug<br>Data5      | DSP067 Debug Data5    |       |       |      |
| 187 | DSP067 Debug<br>Data6      | DSP067 Debug Data6    |       |       |      |
| 188 | DSP067 Debug<br>Data7      | DSP067 Debug Data7    |       |       |      |
| 189 | DSP067 Debug<br>Data8      | DSP067 Debug Data8    |       |       |      |
| 190 | DSP075 Debug<br>Data1      | DSP075 Debug Data1    |       |       |      |
| 191 | DSP075 Debug<br>Data2      | DSP075 Debug Data2    |       |       |      |
| 192 | DSP075 Debug<br>Data3      | DSP075 Debug Data3    |       |       |      |
| 193 | DSP075 Debug<br>Data4      | DSP075 Debug Data4    |       |       |      |
| 194 | DSP075 Debug<br>Data55     | DSP075 Debug Data5    |       |       |      |
| 195 | DSP075 Debug<br>Data6      | DSP075 Debug Data6    |       |       |      |
| 196 | DSP075 Debug<br>Data7      | DSP075 Debug Data7    |       |       |      |
| 197 | DSP075 Debug<br>Data8      | DSP075 Debug Data8    |       |       |      |
| 198 | bUSBAgingTestOk<br>Flag    | USBAgingTestOkFlag    | 0-1   |       |      |
| 199 | bFlashEraseAging<br>OkFlag | FlashEraseAgingOkFlag | 0-1   |       |      |
| 200 | PVISO                      | PVISOValue            |       | KΩ    |      |
| 201 | R_DCI                      | R DCI Curr            |       | 0.1mA |      |
| 202 | S_DCI                      | S DCI Curr            |       | 0.1mA |      |
| 203 | T_DCI                      | T DCI Curr            |       | 0.1mA |      |

**Source page 40**

| NO. | Variable Name                          | Description                                              | Value                                                                                                                            | Unit   | Note |
| --- | -------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------ | ---- |
| 204 | PID_Bus                                | PIDBusVolt                                               |                                                                                                                                  | 0.1V   |      |
| 205 | GFCI                                   | GFCI Curr                                                |                                                                                                                                  | mA     |      |
| 206 | SVG/APF<br>Status+SVGAPFEq<br>ualRatio | SVG/APF Status+SVGAPFEqualRatio                          | High 8 bit：<br>SVGAPFEqua<br>lRatio<br>Low 8 bit：<br>SVG/APF<br>Status<br>0:None<br>1:SVG Run<br>2:APF Run<br>3:SVG/APF<br>Run |        |      |
| 207 | CT_I _R                                | R phase load side current for SVG                        |                                                                                                                                  | 0.1A   |      |
| 208 | CT_I _S                                | S phase load side current for SVG                        |                                                                                                                                  | 0.1A   |      |
| 209 | CT_I _T                                | T phase load side current for SVG                        |                                                                                                                                  | 0.1A   |      |
| 210 | CT_Q _R H                              | R phase load side output reactive<br>power for SVG(High) |                                                                                                                                  | 0.1Var |      |
| 211 | CT_Q _R L                              | R phase load side output reactive<br>power for SVG(low)  |                                                                                                                                  | 0.1Var |      |
| 212 | CT_Q _S H                              | S phase load side output reactive<br>power for SVG(High) |                                                                                                                                  | 0.1Var |      |
| 213 | CT_Q _S L                              | S phase load side output reactive<br>power for SVG(low)  |                                                                                                                                  | 0.1Var |      |
| 214 | CT_Q _T H                              | T phase load side output reactive<br>power for SVG(High) |                                                                                                                                  | 0.1Var |      |
| 215 | CT_Q _T L                              | T phase load side output reactive<br>power for SVG(low)  |                                                                                                                                  | 0.1Var |      |
| 216 | CT HAR_I_R                             | R phase load side harmonic                               |                                                                                                                                  | 0.1A   |      |
| 217 | CT HAR_I_S                             | S phase load side harmonic                               |                                                                                                                                  | 0.1A   |      |
| 218 | CT HAR_I_T                             | T phase load side harmonic                               |                                                                                                                                  | 0.1A   |      |
| 219 | COMP_Q _R H                            | R phase compensate reactive power<br>for SVG(High)       |                                                                                                                                  | 0.1Var |      |
| 220 | COMP_Q _R L                            | R phase compensate reactive power<br>for SVG(low)        |                                                                                                                                  | 0.1Var |      |
| 221 | COMP_Q _S H                            | S phase compensate reactive power<br>for SVG(High)       |                                                                                                                                  | 0.1Var |      |
| 222 | COMP_Q _S L                            | S phase compensate reactive power<br>for SVG(low)        |                                                                                                                                  | 0.1Var |      |
| 223 | COMP_Q _T H                            | T phase compensate reactive power<br>for SVG(High)       |                                                                                                                                  | 0.1Var |      |
| 224 | COMP_Q _T L                            | T phase compensate reactive power<br>for SVG(low)        |                                                                                                                                  | 0.1Var |      |

**Source page 41**

| NO. | Variable Name             | Description                                                                                                          | Value | Unit   | Note     |
| --- | ------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----- | ------ | -------- |
| 225 | COMP HAR_I_R              | R phase compensate harmonic for<br>SVG                                                                               |       | 0.1A   |          |
| 226 | COMP HAR_I_S              | S phase compensate harmonic for<br>SVG                                                                               |       | 0.1A   |          |
| 227 | COMP HAR_I_T              | T phase compensate harmonic for<br>SVG                                                                               |       | 0.1A   |          |
| 228 | bRS232AgingTest<br>OkFlag | RS232AgingTestOkFlag                                                                                                 | 0-1   |        |          |
| 229 | bFanFaultBit              | Bit0: Fan 1 fault bit<br>Bit1: Fan 2 fault bit<br>Bit2: Fan 3 fault bit<br>Bit3: Fan 4 fault bit<br>Bit4-7: Reserved |       |        |          |
| 230 | Sac H                     | Output apparent power H                                                                                              |       | 0.1W   |          |
| 231 | Sac L                     | Output apparent power L                                                                                              |       | 0.1W   |          |
| 232 | ReActPowerH               | Real Output Reactive Power H                                                                                         | Int32 | 0.1W   |          |
| 233 | ReActPowerL               | Real Output Reactive Power L                                                                                         |       |        |          |
| 234 | ReActPowerMaxH            | Nominal Output Reactive Power H                                                                                      |       | 0.1var |          |
| 235 | ReActPowerMaxL            | Nominal Output Reactive Power L                                                                                      |       |        |          |
| 236 | ReActPower_Total<br>H     | Reactive power generation                                                                                            |       | 0.1kwh |          |
| 237 | ReActPower_Total<br>L     | Reactive power generation                                                                                            |       |        |          |
| …   | 238~249                   |                                                                                                                      |       |        | reserved |

#### Ninth group for Storage power

| NO.   | Variable Name  | Description      | Value                                                                                                                                                                                                                                                                                              | Unit | Note                                                                                                                                                                                                                                       |
| ----- | -------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1000. | u wSysWorkMode | System work mode | 0x00:waiting<br>module<br>0x01: Self-test<br>mode,<br>optional<br>0x02 :<br>Reserved<br>0x03：SysFault<br>module<br>0x04: Flash<br>module<br>0x05 ：<br>PVBATOnline<br>module,<br>0x06 ：<br>BatOnline<br>module,<br>0x07 ：<br>PVOfflineMod<br>e module,<br>0x08 ：<br>BatOfflineMo<br>de module, |      | Theworkingmode<br>displayed by the<br>monitoring to the<br>customer is：<br>0x00: waiting<br>module<br>0x01: Self-test<br>mode,<br>0x03:fault<br>module<br>0x04:flash<br>module<br>0x05&#124;0x06&#124;0x07&#124;0<br>x08:normal<br>module |

**Source page 42**

| NO.   | Variable Name      | Description               | Value | Unit | Note                                                    |
| ----- | ------------------ | ------------------------- | ----- | ---- | ------------------------------------------------------- |
| 1001. | Sy stemfault word0 | System fault word0        |       |      | Please refer to<br>thefault<br>description of<br>Hybrid |
| 1002. | Sy stemfault word1 | System fault word1        |       |      |                                                         |
| 1003. | Sy stemfault word2 | System fault word2        |       |      |                                                         |
| 1004. | Sy stemfault word3 | System fault word3        |       |      |                                                         |
| 1005. | Sy stemfault word4 | System fault word4        |       |      |                                                         |
| 1006. | Sy stemfault word5 | System fault word5        |       |      |                                                         |
| 1007. | Sy stemfault word6 | System fault word6        |       |      |                                                         |
| 1008. | Sy stemfault word7 | System fault word7        |       |      |                                                         |
| 1009. | P discharge1 H     | Discharge power(high)     |       | 0.1W |                                                         |
| 1010. | P discharge1 L     | Discharge power (low)     |       | 0.1W |                                                         |
| 1011. | P charge1 H        | Charge power(high)        |       | 0.1W |                                                         |
| 1012. | P charge1 L        | Charge power (low)        |       | 0.1W |                                                         |
| 1013. | V bat              | Battery voltage           |       | 0.1V |                                                         |
| 1014. | SO C               | State of charge Capacity  | 0-100 | 1%   | lith/leadacid                                           |
| 1015. | P actouser R H     | AC power to user H        |       | 0.1w |                                                         |
| 1016. | P actouser R L     | AC power to user L        |       | 0.1w |                                                         |
| 1017. | P actouser S H     | Pactouser S H             |       | 0.1w |                                                         |
| 1018. | P actouser S L     | Pactouser S L             |       | 0.1w |                                                         |
| 1019. | P actouser T H     | Pactouser T H             |       | 0.1w |                                                         |
| 1020. | P actouser T L     | Pactouser T H             |       | 0.1w |                                                         |
| 1021. | P actouserTotal H  | AC power to user total H  |       | 0.1w |                                                         |
| 1022. | P actouserTotal L  | AC power to user total L  |       | 0.1w |                                                         |
| 1023. | P ac to grid R H   | AC power to grid H        |       | 0.1w | Ac output                                               |
| 1024. | P ac to grid R L   | AC power to grid L        |       | 0.1w |                                                         |
| 1025. | P actogrid S H     |                           |       | 0.1w |                                                         |
| 1026. | P actogrid S L     |                           |       | 0.1w |                                                         |
| 1027. | P actogrid T H     |                           |       | 0.1w |                                                         |
| 1028. | P actogrid T L     |                           |       | 0.1w |                                                         |
| 1029. | P actogrid total H | AC power to grid total H  |       | 0.1w |                                                         |
| 1030. | P actogrid total L | AC power to grid total L  |       | 0.1w |                                                         |
| 1031. | P LocalLoad R H    | INV power to local load H |       | 0.1w |                                                         |

**Source page 43**

| NO.   | Variable Name          | Description                        | Value | Unit | Note                              |
| ----- | ---------------------- | ---------------------------------- | ----- | ---- | --------------------------------- |
| 1032. | P LocalLoad R L        | INV power to local load L          |       | 0.1w |                                   |
| 1033. | P LocalLoad S H        |                                    |       | 0.1w |                                   |
| 1034. | P LocalLoad S L        |                                    |       | 0.1w |                                   |
| 1035. | P LocalLoadT H         |                                    |       | 0.1w |                                   |
| 1036. | P LocalLoadT L         |                                    |       | 0.1w |                                   |
| 1037. | P LocalLoad total H    | INV power to local load total H    |       | 0.1w |                                   |
| 1038. | P LocalLoad total L    | INV power to local load total<br>L |       | 0.1w |                                   |
| 1039. | IPM Temperature        | REC Temperature                    |       | 0.1℃ | No use                            |
| 1040. | Battery<br>Temperature | Battery Temperature                |       | 0.1℃ | Lead acid/lithium<br>battery temp |
| 1041. | SP DSP Status          | SP state                           |       |      | CHG/DisCHG                        |
| 1042. | SP Bus Volt            | SP BUS2 Volt                       |       | 0.1V |                                   |
| 1043  |                        |                                    |       |      |                                   |

#### 发电量数据

| NO.   | Variable Name                | Description                    | Value | Unit   | Note |
| ----- | ---------------------------- | ------------------------------ | ----- | ------ | ---- |
| 1044. | Eto user_today H             | Energy to user today high      |       | 0.1kWh |      |
| 1045. | Eto user_today L             | Energy to user today low       |       | 0.1kWh |      |
| 1046. | Eto user_total H             | Energy to user total high      |       | 0.1kWh |      |
| 1047. | Eto user_ total L            | Energy to user total high      |       | 0.1kWh |      |
| 1048. | Eto grid_today H             | Energy to grid today high      |       | 0.1kWh |      |
| 1049. | Eto grid _today L            | Energy to grid today low       |       | 0.1kWh |      |
| 1050. | Eto grid _total H            | Energy to grid total high      |       | 0.1kWh |      |
| 1051. | Eto grid _ total L           | Energy to grid total high      |       | 0.1kWh |      |
| 1052. | Edi scharge1_today<br>y H    | Discharge energy1 today        |       | 0.1kWh |      |
| 1053. | Edi scharge1_today<br>y L    | Discharge energy1 today        |       | 0.1kWh |      |
| 1054. | Edi scharge1_total<br>H      | Total discharge energy1 (high) |       | 0.1kWh |      |
| 1055. | Edi scharge1_total<br>L<br>L | Total discharge energy1 (low)  |       | 0.1kWh |      |
| 1056. | Ech arge1_today H            | Charge1 energy today           |       | 0.1kWh |      |
| 1057. | Ech arge1_today<br>L<br>L    | Charge1 energy today           |       | 0.1kWh |      |
| 1058. | Ech arge1_total H            | Charge1 energy total           |       | 0.1kWh |      |
| 1059. | Ech arge1_total L            | Charge1 energy total           |       | 0.1kWh |      |
| 1060. | ELo calLoad_Today<br>H       | Local load energy today        |       | 0.1kWh |      |
| 1061. | ELo calLoad_Today<br>L<br>L  | Local load energy today        |       | 0.1kWh |      |
| 1062. | ELo calLoad_TotalH           | Local load energy total        |       | 0.1kWh |      |

**Source page 44**

| NO.   | Variable Name                   | Description                | Value | Unit   | Note          |
| ----- | ------------------------------- | -------------------------- | ----- | ------ | ------------- |
| 1063. | ELo calLoad_Total<br>L          | Local load energy total    |       | 0.1kWh |               |
| 1064. | dw ExportLimitAp<br>parentPower | ExportLimitApparentPower H |       | 0.1kWh | ApparentPower |
| 1065. | dw ExportLimitAp<br>parentPower | ExportLimitApparentPower L |       | 0.1kWh | ApparentPower |
| 1066. | /                               | /                          | /     | /      | reserved      |

#### Ups information (offline)

| NO.   | Variable Name | Description                  | Value     | Unit   | Note            |
| ----- | ------------- | ---------------------------- | --------- | ------ | --------------- |
| 1067. | EPS Fac       | UPSfrequency                 | 5000/6000 | 0.01Hz |                 |
| 1068. | EPS Vac1      | UPS phase R output voltage   | 2300      | 0.1V   |                 |
| 1069. | EPS Iac1      | UPS phase R output current   |           | 0.1A   |                 |
| 1070. | EPS Pac1 H    | UPS phase R output power (H) |           | 0.1VA  |                 |
| 1071. | EPS Pac1 L    | UPS phase R output power (L) |           | 0.1VA  |                 |
| 1072. | EPS Vac2      | UPS phase S output voltage   |           | 0.1V   |                 |
| 1073. | EPS Iac2      | UPS phase S output current   |           | 0.1A   | No use          |
| 1074. | EPS Pac2 H    | UPS phase S output power (H) |           | 0.1VA  |                 |
| 1075. | EPS Pac2 L    | UPS phase S output power (L) |           | 0.1VA  |                 |
| 1076. | EPS Vac3      | UPS phase T output voltage   |           | 0.1V   |                 |
| 1077. | EPS Iac3      | UPS phase T output current   |           | 0.1A   | No use          |
| 1078. | EPS Pac3 H    | UPS phase T output power (H) |           | 0.1VA  |                 |
| 1079. | EPS Pac3 L    | UPS phase T output power (L) |           | 0.1VA  |                 |
| 1080. | Loa dpercent  | Load percent of UPS ouput    | 0-100     | 1%     |                 |
| 1081. | PF            | Power factor                 | 0-2       | 0.1    | Primary Value+1 |

#### BMS Infomation

| NO.   | Variable Name       | Description                                       | Value                                                                       | Unit | Note    |
| ----- | ------------------- | ------------------------------------------------- | --------------------------------------------------------------------------- | ---- | ------- |
| 1082. | B MS_StatusOld      | StatusOld from BMS                                | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1083. | B MS_Status         | Status from BMS                                   | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      | W/R     |
| 1084. | B MS_ErrorOld       | Error info Old from BMS                           | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1085. | B MS_Error          | Errorinfomation from BMS                          | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1086. | B MS_SOC            | SOC from BMS                                      | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      | R SPH6K |
| 1087. | BMS_BatteryVol<br>t | Battery voltage from BMS                          | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      | R SPH6K |
| 1088. | BMS_BatteryCur<br>r | Battery current from BMS                          | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1089. | BMS_BatteryTe<br>mp | Battery temperature from BMS                      | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1090. | BMS_MaxCurr         | Max. charge/discharge current<br>from BMS (pylon) | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1091. | B MS_GaugeRM        | Gauge RM from BMS                                 | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1092. | B MS_GaugeFCC       | Gauge FCC from BMS                                | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |
| 1093. | B MS_FW             |                                                   | Detail information, refer<br>to<br>document:GrowattxxSxx<br>P ESS Protocol; |      |         |

**Source page 45**

| NO.   | Variable Name               | Description                   | Value | Unit | Note         |
| ----- | --------------------------- | ----------------------------- | ----- | ---- | ------------ |
| 1094. | B MS_DeltaVolt              | Delta V from BMS              |       |      |              |
| 1095. | B MS_CycleCnt               | Cycle Count from BMS          |       |      |              |
| 1096. | B MS_SOH                    | SOH from BMS                  |       |      |              |
| 1097. | BMS_ConstantV<br>olt        | CV voltage from BMS           |       |      |              |
| 1098. | BMS_WarnInfoO<br>ld         | Warning info old from BMS     |       |      |              |
| 1099. | B MS_WarnInfo               | Warning info from BMS         |       |      |              |
| 1100. | BMS_GaugeICCu<br>rr         | Gauge IC current from BMS     |       |      |              |
| 1101. | BMS_MCUVersi<br>on          | MCU Software version from BMS |       |      |              |
| 1102. | BMS_GaugeVers<br>ion        | Gauge Version from BMS        |       |      |              |
| 1103. | BMS_wGaugeFR<br>Version_ L  | Gauge FR Version L16 from BMS |       |      |              |
| 1104. | BMS_wGaugeFR<br>Version_H   | Gauge FR Version H16 from BMS |       |      |              |
| 1105. | B MS_BMSInfo                | BMSInformation from BMS       |       |      |              |
| 1106. | B MS_PackInfo               | Pack Information from BMS     |       |      |              |
| 1107. | B MS_UsingCap               | Using Cap from BMS            |       |      |              |
| 1108. | B MS_ Cell1_Volt            | Cell1_Voltage from BMS        |       |      |              |
| 1109. | B MS_ Cell2_Volt            | Cell_Voltage from BMS         |       |      |              |
| …     |                             |                               |       |      |              |
| 1123  | BMS_<br>Cell16_Volt         | Cell16_Voltage from BMS       |       |      |              |
| 1124  | AC Charge<br>Energy Today H | AC Charge Energy today        | kwh   |      | Energy today |

#### Ninth group reserved for storage power

| NO.   | Variable Name               | Description             | Value | Unit | Note         |
| ----- | --------------------------- | ----------------------- | ----- | ---- | ------------ |
| 1125. | A CCharge<br>Energy TodayL  | AC Charge Energy today  | kwh   |      |              |
| 1126. | A CCharge<br>Energy Total H |                         |       |      | Energy total |
| 1127. | A CCharge<br>Energy Total L |                         |       |      |              |
| 1128. | A C Charge<br>Power H       | AC Charge Power         | W     |      |              |
| 1129. | A C Charge<br>Power L       | AC Charge Power         | w     |      |              |
| 1130. | 7 0% INV Power<br>adjust    | uwGridPower_70_AdjEE_SP | W     |      |              |

**Source page 46**

| NO.   | Variable Name                | Description                                      | Value                          | Unit   | Note                                          |
| ----- | ---------------------------- | ------------------------------------------------ | ------------------------------ | ------ | --------------------------------------------- |
| 1131. | E xtra AC Power<br>to grid_H | Extra inverte AC Power to grid<br>High           | For SPA<br>connect<br>inverter |        | SPA used                                      |
| 1132. | E xtra AC Power<br>to grid_L | Extrainverte AC Power to grid Low                |                                |        | SPA used                                      |
| 1133. | E extra_today H              | Extra inverter PowerTOUser_Extra<br>today (high) | R                              | 0.1kWh | SPA used                                      |
| 1134. | E extra_today L              | Extra inverter PowerTOUser_Extra<br>today (low)  | R                              | 0.1kWh | SPA used                                      |
| 1135. | E extra_total H              | Extra inverter PowerTOUser_Extra<br>total(high)  |                                | 0.1kWh | SPA used                                      |
| 1136. | E extra_total L              | Extra inverter PowerTOUser_Extra<br>total(low)   |                                | 0.1kWh | SPA used                                      |
| 1137. | E system_today<br>H          | System electric energy today H                   |                                | 0.1kWh | SPA used<br>System electric<br>energy today H |
| 1138. | E system_ today<br>L         | System electric energy today L                   |                                | 0.1kWh | SPA used<br>System electric<br>energy today L |
| 1139. | E system_total H             | System electric energy total H                   |                                | 0.1kWh | SPA used<br>System electric<br>energy total H |
| 1140. | E system_ total L            | System electric energy total L                   |                                | 0.1kWh | SPA used<br>System electric<br>energy total L |
| ……    | /                            | /                                                | /                              | /      | reversed                                      |
| 1249. | /                            | /                                                | /                              | /      | reversed                                      |

#### thirteen group for Storage power’s SPA

| NO.  | Variable Name   | Description                                      | Value                              | Unit   | Note |
| ---- | --------------- | ------------------------------------------------ | ---------------------------------- | ------ | ---- |
| 2000 | Inverter Status | Inverter run state                               | 0:waiting,<br>1:normal,<br>3:fault |        | SPA  |
| ……   | reversed        |                                                  |                                    |        |      |
| 2035 | Pac H           | Output power (high)                              |                                    | 0.1W   | SPA  |
| 2036 | Pac L           | Output power (low)                               |                                    | 0.1W   | SPA  |
| 2037 | Fac             | Grid frequency                                   |                                    | 0.01Hz | SPA  |
| 2038 | Vac1            | Three/single phase grid voltage                  |                                    | 0.1V   | SPA  |
| 2039 | Iac1            | Three/single phase grid output current           |                                    | 0.1A   | SPA  |
| 2040 | Pac1 H          | Three/single phase grid output watt<br>VA (high) |                                    | 0.1VA  | SPA  |
| 2041 | Pac1 L          | Three/single phase grid output watt<br>VA(low)   |                                    | 0.1VA  | SPA  |

**Source page 47**

| NO.  | Variable Name               | Description                                      | Value                                | Unit   | Note                                                |
| ---- | --------------------------- | ------------------------------------------------ | ------------------------------------ | ------ | --------------------------------------------------- |
| ……   | reversed                    |                                                  |                                      |        |                                                     |
| 2053 | Eac today H                 | Today generate energy (high)                     |                                      | 0.1kWH | SPA                                                 |
| 2054 | Eac today L                 | Today generate energy (low)                      |                                      | 0.1kWH | SPA                                                 |
| 2055 | Eac total H                 | Total generate energy (high)                     |                                      | 0.1kWH | SPA                                                 |
| 2056 | Eac total L                 | Total generate energy (low)                      |                                      | 0.1kWH | SPA                                                 |
| 2057 | Time total H                | Work time total (high)                           |                                      | 0.5s   | SPA                                                 |
| 2058 | Time total L                | Work time total (low)                            |                                      | 0.5s   | SPA                                                 |
| ……   | reversed                    |                                                  |                                      |        |                                                     |
| 2093 | Temp1                       | Inverter temperature                             |                                      | 0.1C   | SPA                                                 |
| 2094 | Temp2                       | The inside IPM in inverter Temperature           |                                      | 0.1C   | SPA                                                 |
| 2095 | Temp3                       | Boost temperature                                |                                      | 0.1C   | SPA                                                 |
| 2096 | Temp4                       |                                                  |                                      |        | reserved                                            |
| 2097 | uwBatVolt_DSP               | BatVolt_DSP                                      |                                      | 0.1V   | BatVolt(DSP)                                        |
| 2098 | P Bus Voltage               | P Bus inside Voltage                             |                                      | 0.1V   | SPA                                                 |
| 2099 | N Bus Voltage               | N Bus inside Voltage                             |                                      | 0.1V   | SPA                                                 |
| 2100 | RemoteCtrlEn                | /                                                | 0.Load First<br>1.BatFirst<br>2.Grid | /      | Remote<br>setup<br>enable                           |
| 2101 | RemoteCtrlPow<br>er         | /                                                | 0.Load First<br>1.BatFirst<br>2.Grid | /      | Remotely<br>set power                               |
| 2102 | Extra AC Power<br>to grid_H | Extra inverte AC Power to grid High              | For SPA<br>connect<br>inverter       |        | SPA used                                            |
| 2103 | Extra AC Power<br>to grid_L | Extrainverte AC Power to grid Low                |                                      |        | SPA used                                            |
| 2104 | Eextra_today H              | Extra inverter PowerTOUser_Extra<br>today (high) | R                                    | 0.1kWh | SPA used                                            |
| 2105 | Eextra_today L              | Extra inverter PowerTOUser_Extra<br>today (low)  | R                                    | 0.1kWh | SPA used                                            |
| 2106 | Eextra_total H              | Extra inverter<br>PowerTOUser_Extratotal(high)   |                                      | 0.1kWh | SPA used                                            |
| 2107 | Eextra_total L              | Extra inverter PowerTOUser_Extra<br>total(low)   |                                      | 0.1kWh | SPA used                                            |
| 2108 | Esystem_today<br>H          | System electric energy today H                   |                                      | 0.1kWh | SPA used<br>System<br>electric<br>energy<br>today H |
| 2109 | Esystem_ today<br>L         | System electric energy today L                   |                                      | 0.1kWh | SPA used<br>System<br>electric<br>energy<br>today L |

**Source page 48**

| NO.   | Variable Name        | Description                                     | Value | Unit   | Note                                                |
| ----- | -------------------- | ----------------------------------------------- | ----- | ------ | --------------------------------------------------- |
| 2110  | Esystem_total H      | System electric energy total H                  |       | 0.1kWh | SPA used<br>System<br>electric<br>energy total<br>H |
| 2111  | Esystem_ total L     | System electric energy total L                  |       | 0.1kWh | SPA used<br>System<br>electric<br>energy total<br>L |
| 2112  | EACharge_Today<br>_H | ACCharge energy today                           |       | 0.1kwh | Storage<br>Power                                    |
| 2113  | EACharge_Today<br>_L | ACCharge energy today                           |       | 0.1kwh | Storage<br>Power                                    |
| 2114  | EACharge_Total<br>_H | ACCharge energy total                           |       | 0.1kwh | Storage<br>Power                                    |
| 2115  | EACharge_Total<br>_L | ACCharge energy total                           |       | 0.1kwh | Storage<br>Power                                    |
| 2116  | AC charge<br>Power_H | Grid power to local load                        |       | 0.1kwh | Storage<br>Power                                    |
| 2117  | AC charge<br>Power_L | Grid power to local load                        |       | 0.1kwh | Storage<br>Power                                    |
| 2118  | Priority             | 0:Load First<br>1:Battery First<br>2:Grid First |       |        | Storage<br>Power                                    |
| 2119  | Battery Type         | 0：Lead-acid<br>1：Lithium battery              |       |        | Storage<br>Power                                    |
| 2120  | AutoProofreadC<br>MD | Aging mode                                      |       |        | Storage<br>Power                                    |
| …     | reserved             |                                                 |       |        | reserved                                            |
| 2124. | re served            |                                                 |       |        | reserved                                            |

#### Use for TL-X and TL-XH

| NO.  | Variable Name   | Description                                                                                                                                                                                                                                                                                                                                                                                                      | Value | Unit | Note |
| ---- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ---- | ---- |
| 3000 | Inverter Status | Inverter run state<br>High 8 bits mode (specific mode)<br>0: Waiting module<br>1: Self-test mode, optional<br>2: Reserved<br>3：SysFault module<br>4: Flash module<br>5：PVBATOnline module:<br>6：BatOnline module<br>7：PVOfflineMode<br>8：BatOfflineMode<br>The lower 8 bits indicate the machine<br>status (web page display)<br>0: StandbyStatus;<br>1: NormalStatus;<br>3: FaultStatus<br>4：FlashStatus; |       |      |      |

**Source page 49**

| NO.  | Variable Name | Description                     | Value | Unit   | Note                                  |
| ---- | ------------- | ------------------------------- | ----- | ------ | ------------------------------------- |
| 3001 | Ppv H         | PV total power                  |       | 0.1W   |                                       |
| 3002 | Ppv L         | PV total power                  |       | 0.1W   |                                       |
| 3003 | Vpv1          | PV1 voltage                     |       | 0.1V   |                                       |
| 3004 | Ipv1          | PV1 input current               |       | 0.1A   |                                       |
| 3005 | Ppv1 H        | PV1 power                       |       | 0.1W   |                                       |
| 3006 | Ppv1 L        | PV1 power                       |       | 0.1W   |                                       |
| 3007 | Vpv2          | PV2 voltage                     |       | 0.1V   |                                       |
| 3008 | Ipv2          | PV2 input current               |       | 0.1A   |                                       |
| 3009 | Ppv2 H        | PV2 power                       |       | 0.1W   |                                       |
| 3010 | Ppv2 L        | PV2 power                       |       | 0.1W   |                                       |
| 3011 | Vpv3          | PV3 voltage                     |       | 0.1V   |                                       |
| 3012 | Ipv3          | PV3 input current               |       | 0.1A   |                                       |
| 3013 | Ppv3 H        | PV3 power                       |       | 0.1W   |                                       |
| 3014 | Ppv3 L        | PV3 power                       |       | 0.1W   |                                       |
| 3015 | Vpv4          | PV4 voltage                     |       |        |                                       |
| 3016 | Ipv4          | PV4 input current               |       |        |                                       |
| 3017 | Ppv4H         | PV4 power                       |       |        |                                       |
| 3018 | Ppv4L         |                                 |       |        |                                       |
| 3019 | Reserved      |                                 |       |        |                                       |
| 3020 | Reserved      |                                 |       |        |                                       |
| 3021 | Reserved      |                                 |       |        |                                       |
| 3022 | Reserved      |                                 |       |        |                                       |
| 3023 | Pac H         | Output power                    |       | 0.1W   | Output<br>power                       |
| 3024 | Pac L         | Output power                    |       | 0.1W   | Output<br>power                       |
| 3025 | Fac           | Grid frequency                  |       | 0.01Hz | Grid<br>frequency                     |
| 3026 | Vac1          | Three/single phase grid voltage |       | 0.1V   | Three/single<br>phase grid<br>voltage |

**Source page 50**

| NO.  | Variable Name   | Description                               | Value | Unit   | Note                                            |
| ---- | --------------- | ----------------------------------------- | ----- | ------ | ----------------------------------------------- |
| 3027 | Iac1            | Three/single phase grid output current    |       | 0.1A   | Three/single<br>phase grid<br>output<br>current |
| 3028 | Pac1 H          | Three/single phase grid output watt<br>VA |       | 0.1VA  | Three/single<br>phase grid<br>output watt<br>VA |
| 3029 | Pac1 L          | Three/single phase grid output watt<br>VA |       | 0.1VA  | Three/single<br>phase grid<br>output watt<br>VA |
| 3030 | Vac2            | Three phase grid voltage                  |       | 0.1V   | Three phase<br>grid voltage                     |
| 3031 | Iac2            | Three phase grid output current           |       | 0.1A   | Three phase<br>grid output<br>current           |
| 3032 | Pac2 H          | Three phase grid output power             |       | 0.1VA  | Three phase<br>grid output<br>power             |
| 3033 | Pac2 L          | Three phase grid output power             |       | 0.1VA  | Three phase<br>grid output<br>power             |
| 3034 | Vac3            | Three phase grid voltage                  |       | 0.1V   | Three phase<br>grid voltage                     |
| 3035 | Iac3            | Three phase grid output current           |       | 0.1A   | Three phase<br>grid output<br>current           |
| 3036 | Pac3 H          | Three phase grid output power             |       | 0.1VA  | Three phase<br>grid output<br>power             |
| 3037 | Pac3 L          | Three phase grid output power             |       | 0.1VA  | Three phase<br>grid output<br>power             |
| 3038 | Vac_RS          | Three phase grid voltage                  |       | 0.1V   |                                                 |
| 3039 | Vac_ST          | Three phase grid voltage                  |       | 0.1V   |                                                 |
| 3040 | Vac_TR          | Three phase grid voltage                  |       | 0.1V   |                                                 |
| 3041 | Ptouser total H | Total forward power                       |       | 0.1W   | Total forward<br>power                          |
| 3042 | Ptouser total L | Total forward power                       |       | 0.1W   | Total forward<br>power                          |
| 3043 | Ptogrid total H | Total reverse power                       |       | 0.1W   | Total reverse<br>power                          |
| 3044 | Ptogrid total L |                                           |       |        | Total reverse<br>power                          |
| 3045 | Ptoload total H | Total load power                          |       | 0.1W   | Total load<br>power                             |
| 3046 | Ptoload total L | Total load power                          |       | 0.1W   | Total load<br>power                             |
| 3047 | Time total H    | Work time total                           |       | 0.5s   |                                                 |
| 3048 | Time total L    | Work time total                           |       | 0.5s   |                                                 |
| 3049 | Eac today H     | Today generate energy                     |       | 0.1kWh | Today<br>generate<br>energy                     |
| 3050 | Eac today L     | Today generate energy                     |       | 0.1kWh | Today<br>generate<br>energy                     |

**Source page 51**

| NO.  | Variable Name   | Description               | Value | Unit   | Note                         |
| ---- | --------------- | ------------------------- | ----- | ------ | ---------------------------- |
| 3051 | Eac total H     | Total generate energy     |       | 0.1kWh | Total<br>generate<br>energy  |
| 3052 | Eac total L     | Total generate energy     |       | 0.1kWh | Total<br>generate<br>energy  |
| 3053 | Epv_total H     | PV energy total           |       | 0.1kWh | PV energy<br>total           |
| 3054 | Epv_total L     | PV energy total           |       | 0.1kWh | PV energy<br>total           |
| 3055 | Epv1_today H    | PV1 energy today          |       | 0.1kWh |                              |
| 3056 | Epv1_today L    | PV1 energy today          |       | 0.1kWh |                              |
| 3057 | Epv1_total H    | PV1 energy total          |       | 0.1kWh |                              |
| 3058 | Epv1_total L    | PV1 energy total          |       | 0.1kWh |                              |
| 3059 | Epv2_today H    | PV2 energy today          |       | 0.1kWh |                              |
| 3060 | Epv2_today L    | PV2 energy today          |       | 0.1kWh |                              |
| 3061 | Epv2_total H    | PV2 energy total          |       | 0.1kWh |                              |
| 3062 | Epv2_total L    | PV2 energy total          |       | 0.1kWh |                              |
| 3063 | Epv3_today H    | PV3 energy today          |       | 0.1kWh |                              |
| 3064 | Epv3_today L    | PV3 energy today          |       | 0.1kWh |                              |
| 3065 | Epv3_total H    | PV3 energy total          |       | 0.1kWh |                              |
| 3066 | Epv3_total L    | PV3 energy total          |       | 0.1kWh |                              |
| 3067 | Etouser_today H | Today energy to user      |       | 0.1kWh | Today energy<br>to user      |
| 3068 | Etouser_today L | Today energy to user      |       | 0.1kWh | Today energy<br>to user      |
| 3069 | Etouser_total H | Total energy to user      |       | 0.1kWh | Total energy<br>to user      |
| 3070 | Etouser_total L | Total energy to user      |       | 0.1kWh | Total energy<br>to user      |
| 3071 | Etogrid_today H | Today energy to grid      |       | 0.1kWh | Today energy<br>to grid      |
| 3072 | Etogrid_today L | Today energy to grid      |       | 0.1kWh | Today energy<br>to grid      |
| 3073 | Etogrid_total H | Total energy to grid      |       | 0.1kWh | Total energy<br>to grid      |
| 3074 | Etogrid_total L | Total energy to grid      |       | 0.1kWh | Total energy<br>to grid      |
| 3075 | Eload_today H   | Today energy of user load |       | 0.1kWh | Today energy<br>of user load |
| 3076 | Eload_today L   | Today energy of user load |       | 0.1kWh | Today energy<br>of user load |
| 3077 | Eload_total H   | Total energy of user load |       | 0.1kWh | Total energy<br>of user load |
| 3078 | Eload_total L   | Total energy of user load |       | 0.1kWh | Total energy<br>of user load |
| 3079 | Reserved        |                           |       |        |                              |
| 3080 | Reserved        |                           |       |        |                              |
| 3081 | Reserved        |                           |       |        |                              |
| 3082 | Reserved        |                           |       |        |                              |
| 3083 | Reserved        |                           |       |        |                              |
| 3084 | Reserved        |                           |       |        |                              |

**Source page 52**

| NO.  | Variable Name | Description  | Value | Unit  | Note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---- | ------------- | ------------ | ----- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3085 | Reserved      |              |       |       |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3086 | DeratingMode  | DeratingMode |       |       | 0:cNOTDerate<br>1:cPVHighDer<br>ate<br>2: cPowerCon<br>stantDerate<br>3: cGridVHigh<br>Derate<br>4:cFreqHighD<br>erate<br>5:cDcSoureM<br>odeDerate<br>6:cInvTemprD<br>erate<br>7:cActivePow<br>erOrder<br>8:cLoadSpeed<br>Process<br>9:cOverBack<br>byTime<br>10:cInternalT<br>emprDerate<br>11:cOutTemp<br>rDerate<br>12:cLineImpe<br>CalcDerate<br>13: cParallelA<br>ntiBackflowD<br>erate<br>14:cLocalAnti<br>BackflowDera<br>te<br>15:cBdcLoadP<br>riDerate<br>16:cChkCTErr<br>Derate |
| 3087 | ISO           | PV ISO value |       | 1KΩ   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3088 | DCI_R         | R DCI Curr   |       | 0.1mA |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3089 | DCI_S         | S DCI Curr   |       | 0.1mA |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3090 | DCI_T         | T DCI Curr   |       | 0.1mA |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3091 | GFCI          | GFCI Curr    |       | 1mA   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3092 | Reserved      |              |       |       |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

**Source page 53**

| NO.  | Variable Name           | Description                            | Value | Unit     | Note                                                                                                            |
| ---- | ----------------------- | -------------------------------------- | ----- | -------- | --------------------------------------------------------------------------------------------------------------- |
| 3093 | Temp1                   | Inverter temperature                   |       | 0.1℃     |                                                                                                                 |
| 3094 | Temp2                   | The inside IPM in inverter temperature |       | 0.1℃     |                                                                                                                 |
| 3095 | Temp3                   | Boost temperature                      |       | 0.1℃     |                                                                                                                 |
| 3096 | Temp4                   | Reserved                               |       | 0.1℃     |                                                                                                                 |
| 3097 | Temp5                   | Commmunication broad temperature       |       | 0.1℃     |                                                                                                                 |
| 3098 | P Bus Voltage           | P Bus inside Voltage                   |       | 0.1V     |                                                                                                                 |
| 3099 | N Bus Voltage           | N Bus inside Voltage                   |       | 0.1V     |                                                                                                                 |
| 3100 | IPF                     | Inverter output PF now                 |       |          | 0-20000                                                                                                         |
| 3101 | RealOPPercent           | Real Output power Percent              |       | 1%       | 1~100                                                                                                           |
| 3102 | OPFullwatt H            | Output Maxpower Limited                |       | 0.1W     | Output<br>Maxpower<br>Limited                                                                                   |
| 3103 | OPFullwatt L            | Output Maxpower Limited                |       | 0.1W     | Output<br>Maxpower<br>Limited                                                                                   |
| 3104 | StandbyFlag             | Inverter standby flag                  |       | bitfield | bit0:turn off<br>Order；<br>bit1:PV Low；<br>bit2:AC<br>Volt/Freq<br>out of scope；<br>bit3~bit7 ：<br>Reserved |
| 3105 | Fault code              | Inverter fault code                    |       |          |                                                                                                                 |
| 3106 | Warning code            | Inverter Warning code                  |       |          |                                                                                                                 |
| 3107 | Systemfault<br>word0    | System fault word0                     |       | bitfield |                                                                                                                 |
| 3108 | Systemfault<br>word1    | System fault word1                     |       | bitfield |                                                                                                                 |
| 3109 | Systemfault<br>word2    | System fault word2                     |       | bitfield |                                                                                                                 |
| 3110 | Systemfault<br>word3    | System fault word3                     |       | bitfield |                                                                                                                 |
| 3111 | Systemfault<br>word4    | System fault word4                     |       | bitfield |                                                                                                                 |
| 3112 | Systemfault<br>word5    | System fault word5                     |       | bitfield |                                                                                                                 |
| 3113 | Systemfault<br>word6    | System fault word6                     |       | bitfield |                                                                                                                 |
| 3114 | Systemfault<br>word7    | System fault word7                     |       | bitfield |                                                                                                                 |
| 3115 | inv start delay<br>time | inv start delay time                   |       | 1S       | inv start delay<br>time                                                                                         |
| 3116 | Reserved                |                                        |       |          |                                                                                                                 |
| 3117 | Reserved                |                                        |       |          |                                                                                                                 |

**Source page 54**

| NO.  | Variable Name   | Description                  | Value | Unit   | Note                                                                                    |
| ---- | --------------- | ---------------------------- | ----- | ------ | --------------------------------------------------------------------------------------- |
| 3118 | BDC_OnOffState  | BDC connect state            |       |        | 0:No BDC<br>Connect<br>1:BDC1<br>Connect<br>2:BDC2<br>Connect<br>3:BDC1+BDC2<br>Connect |
| 3119 | DryContactState | Current status of DryContact |       |        | Current<br>status of<br>DryContact<br>0: turn off;<br>1: turn on;                       |
| 3120 | Reserved        |                              |       |        |                                                                                         |
| 3121 | Reserved        |                              |       |        |                                                                                         |
| 3122 | Reserved        |                              |       |        |                                                                                         |
| 3123 | Reserved        |                              |       |        |                                                                                         |
| 3124 | Reserved        |                              |       |        |                                                                                         |
| 3125 | Edischr_today H | Today discharge energy       |       | 0.1kWh | Today<br>discharge<br>energy                                                            |
| 3126 | Edischr_today L | Today discharge energy       |       | 0.1kWh | Today<br>discharge<br>energy                                                            |
| 3127 | Edischr_total H | Total discharge energy       |       | 0.1kWh | Total<br>discharge<br>energy                                                            |
| 3128 | Edischr_total L | Total discharge energy       |       | 0.1kWh | Total<br>discharge<br>energy                                                            |
| 3129 | Echr_today H    | Charge energy today          |       | 0.1kWh | Charge<br>energy today                                                                  |
| 3130 | Echr_today L    | Charge energy today          |       | 0.1kWh | Charge<br>energy today                                                                  |
| 3131 | Echr_total H    | Charge energy total          |       | 0.1kWh | Charge<br>energy total                                                                  |
| 3132 | Echr_total L    | Charge energy total          |       | 0.1kWh | Charge<br>energy total                                                                  |
| 3133 | Eacchr_today H  | Today energy of AC charge    |       | 0.1kWh | Today energy<br>of AC charge                                                            |
| 3134 | Eacchr_today L  | Today energy of AC charge    |       | 0.1kWh | Today energy<br>of AC charge                                                            |
| 3135 | Eacchr_total H  | Total energy of AC charge    |       | 0.1kWh | Total energy<br>of AC charge                                                            |
| 3136 | Eacchr_total L  | Total energy of AC charge    |       | 0.1kWh | Total energy<br>of AC charge                                                            |
| 3137 | Reserved        |                              |       |        |                                                                                         |
| 3138 | Reserved        |                              |       |        |                                                                                         |
| 3139 | Reserved        |                              |       |        |                                                                                         |
| 3140 | Reserved        |                              |       |        |                                                                                         |
| 3141 | Reserved        |                              |       |        |                                                                                         |
| 3142 | Reserved        |                              |       |        |                                                                                         |
| 3143 | Reserved        |                              |       |        |                                                                                         |
| 3144 | Priority        | Word Mode                    |       |        | 0 LoadFirst<br>1<br>BatteryFirs<br>t<br>2 GridFirst                                     |

**Source page 55**

| NO.  | Variable Name | Description                                                                                                                                                                                                          | Value | Unit   | Note |
| ---- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------ | ---- |
| 3145 | EPS Fac       | UPS frequency                                                                                                                                                                                                        |       | 0.01Hz |      |
| 3146 | EPS Vac1      | UPS phase R output voltage                                                                                                                                                                                           |       | 0.1V   |      |
| 3147 | EPS Iac1      | UPS phase R output current                                                                                                                                                                                           |       | 0.1A   |      |
| 3148 | EPS Pac1 H    | UPS phase R output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3149 | EPS Pac1 L    | UPS phase R output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3150 | EPS Vac2      | UPS phase S output voltage                                                                                                                                                                                           |       | 0.1V   |      |
| 3151 | EPS Iac2      | UPS phase S output current                                                                                                                                                                                           |       | 0.1A   |      |
| 3152 | EPS Pac2 H    | UPS phase S output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3153 | EPS Pac2 L    | UPS phase S output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3154 | EPS Vac3      | UPS phase T output voltage                                                                                                                                                                                           |       | 0.1V   |      |
| 3155 | EPS Iac3      | UPS phase T output current                                                                                                                                                                                           |       | 0.1A   |      |
| 3156 | EPS Pac3 H    | UPS phase T output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3157 | EPS Pac3 L    | UPS phase T output power                                                                                                                                                                                             |       | 0.1VA  |      |
| 3158 | EPS Pac H     | UPS output power                                                                                                                                                                                                     |       | 0.1VA  |      |
| 3159 | EPS Pac L     | UPS output power                                                                                                                                                                                                     |       | 0.1VA  |      |
| 3160 | Loadpercent   | Load percent of UPS ouput                                                                                                                                                                                            |       | 0.10%  |      |
| 3161 | PF            | Power factor                                                                                                                                                                                                         |       | 0.1    |      |
| 3162 | DCV           | DC voltage                                                                                                                                                                                                           |       | 1mV    |      |
| 3163 | Reserved      |                                                                                                                                                                                                                      |       |        |      |
| 3164 | Reserved      |                                                                                                                                                                                                                      |       |        |      |
| 3165 | Reserved      |                                                                                                                                                                                                                      |       |        |      |
| 3166 | SysState_Mode | System work State and mode 高 8 位表<br>示模式；<br>0：No charge and discharge；<br>1：charge；<br>2：Discharge；<br>低 8 位表示状态；<br>0: StandbyStatus;<br>1: NormalStatus;<br>2: FaultStatus<br>3：FlashStatus; |       |        | BDC1 |
| 3167 | FaultCode     | Storge device fault code                                                                                                                                                                                             |       |        | BDC1 |
| 3168 | WarnCode      | Storge device warning code                                                                                                                                                                                           |       |        | BDC1 |
| 3169 | Vbat          | Battery voltage                                                                                                                                                                                                      |       | 0.01V  | BDC1 |
| 3170 | Ibat          | Battery current                                                                                                                                                                                                      |       | 0.1A   | BDC1 |
| 3171 | SOC           | State of charge Capacity                                                                                                                                                                                             |       | 1%     | BDC1 |
| 3172 | Vbus1         | BUS1 voltage                                                                                                                                                                                                         |       | 0.1V   | BDC1 |

**Source page 56**

| NO.  | Variable Name   | Description                                                                                                                                                                                                                                                              | Value | Unit   | Note |
| ---- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- | ------ | ---- |
| 3173 | Vbus2           | BUS2 voltage                                                                                                                                                                                                                                                             |       | 0.1V   |      |
| 3174 | Ibb             | BUCK-BOOST Current                                                                                                                                                                                                                                                       |       | 0.1A   |      |
| 3175 | Illc            | LLC Current                                                                                                                                                                                                                                                              |       | 0.1A   |      |
| 3176 | TempA           | Temperture A                                                                                                                                                                                                                                                             |       | 0.1℃   |      |
| 3177 | TempB           | Temperture B                                                                                                                                                                                                                                                             |       | 0.1℃   |      |
| 3178 | Pdischr H       | Discharge power                                                                                                                                                                                                                                                          |       | 0.1W   |      |
| 3179 | Pdischr L       | Discharge power                                                                                                                                                                                                                                                          |       | 0.1W   |      |
| 3180 | Pchr H          | Charge power                                                                                                                                                                                                                                                             |       | 0.1W   |      |
| 3181 | Pchr L          | Charge power                                                                                                                                                                                                                                                             |       | 0.1W   |      |
| 3182 | Edischr_total H | Discharge total energy of storge device                                                                                                                                                                                                                                  |       | 0.1kWh |      |
| 3183 | Edischr_total L | Discharge total energy of storge device                                                                                                                                                                                                                                  |       | 0.1kWh |      |
| 3184 | Echr_total H    | Charge total energy of storge device                                                                                                                                                                                                                                     |       | 0.1kWh |      |
| 3185 | Echr_total L    |                                                                                                                                                                                                                                                                          |       |        |      |
| 3186 | Reserved        | Reserved                                                                                                                                                                                                                                                                 |       |        |      |
| 3187 | BDC1_Flag       | BDC mark (charge and discharge,<br>fault alarm code)<br>Bit0: ChargeEn; BDC allows charging<br>Bit1: DischargeEn; BDC allows<br>discharge<br>Bit2~~7: Resvd; reserved<br>Bit8~~11: WarnSubCode; BDC<br>sub-warning code<br>Bit12~15: FaultSubCode; BDC<br>sub-error code |       |        |      |
| 3188 | Reserved        |                                                                                                                                                                                                                                                                          |       |        |      |
| 3189 | SysState_Mode   | System work State and mode<br>高 8 位表示模式；<br>0：No charge and discharge；<br>1：charge；<br>2：Discharge；<br>低 8 位表示状态；<br>0: StandbyStatus;<br>1: NormalStatus;<br>2: FaultStatus<br>3：FlashStatus；                                                     |       |        |      |
| 3190 | FaultCode       | Storge device fault code                                                                                                                                                                                                                                                 |       |        | BDC2 |
| 3191 | WarnCode        | Storge device warning code                                                                                                                                                                                                                                               |       |        | BDC2 |
| 3192 | Vbat            | Battery voltage                                                                                                                                                                                                                                                          |       | 0.01V  | BDC2 |
| 3193 | Ibat            | Battery current                                                                                                                                                                                                                                                          |       | 0.1A   | BDC2 |
| 3194 | SOC             | State of charge Capacity                                                                                                                                                                                                                                                 |       | 1%     | BDC2 |

**Source page 57**

| NO.  | Variable Name       | Description                                                                                                                                                                                                                                                              | Value | Unit   | Note |
| ---- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- | ------ | ---- |
| 3195 | Vbus1               | BUS1 voltage                                                                                                                                                                                                                                                             |       | 0.1V   |      |
| 3196 | Vbus2               | BUS2 voltage                                                                                                                                                                                                                                                             |       | 0.1V   |      |
| 3197 | Ibb                 | BUCK-BOOST Current                                                                                                                                                                                                                                                       |       | 0.1A   |      |
| 3198 | Illc                | LLC Current                                                                                                                                                                                                                                                              |       | 0.1A   |      |
| 3199 | TempA               | Temperture A                                                                                                                                                                                                                                                             |       | 0.1℃   |      |
| 3200 | TempB               | Temperture B                                                                                                                                                                                                                                                             |       | 0.1℃   |      |
| 3201 | Pdischr H           | Discharge power                                                                                                                                                                                                                                                          |       | 0.1W   |      |
| 3202 | Pdischr L           | Discharge power                                                                                                                                                                                                                                                          |       | 0.1W   |      |
| 3203 | Pchr H              | Charge power                                                                                                                                                                                                                                                             |       | 0.1W   |      |
| 3204 | Pchr L              | Charge power                                                                                                                                                                                                                                                             |       | 0.1W   |      |
| 3205 | Edischr_total H     | Discharge total energy of storge device                                                                                                                                                                                                                                  |       | 0.1kWh |      |
| 3206 | Edischr_total L     | Discharge total energy of storge device                                                                                                                                                                                                                                  |       | 0.1kWh |      |
| 3207 | Echr_total H        | Charge total energy of storge device                                                                                                                                                                                                                                     |       | 0.1kWh |      |
| 3208 | Echr_total L        | Charge total energy of storge device                                                                                                                                                                                                                                     |       | 0.1kWh |      |
| 3209 | reserved            | reserved                                                                                                                                                                                                                                                                 |       |        |      |
| 3210 | BDC2_Flag           | BDC mark (charge and discharge,<br>fault alarm code)<br>Bit0: ChargeEn; BDC allows charging<br>Bit1: DischargeEn; BDC allows<br>discharge<br>Bit2~~7: Resvd; reserved<br>Bit8~~11: WarnSubCode; BDC<br>sub-warning code<br>Bit12~15: FaultSubCode; BDC<br>sub-error code |       |        |      |
| 3211 | Reserved            |                                                                                                                                                                                                                                                                          |       |        |      |
| 3212 | BMS_Status          | Status from BMS                                                                                                                                                                                                                                                          | R     | 1      |      |
| 3213 | BMS_Error           | Error information from BMS                                                                                                                                                                                                                                               | R     | 1      |      |
| 3214 | BMS_WarnInfo        | Warning information from BMS                                                                                                                                                                                                                                             | R     | 1      |      |
| 3215 | BMS_SOC             | SOC from BMS                                                                                                                                                                                                                                                             | R     | 1%     |      |
| 3216 | BMS_BatteryVol<br>t | Battery voltage from BMS                                                                                                                                                                                                                                                 | R     | 0.01V  |      |
| 3217 | BMS_BatteryCur<br>r | Battery current from BMS                                                                                                                                                                                                                                                 | R     | 0.01A  |      |
| 3218 | BMS_BatteryTe<br>mp | Battery temperature from BMS                                                                                                                                                                                                                                             | R     | 0.1℃   |      |
| 3219 | BMS_MaxCurr         | Max. charge/discharge current from<br>BMS (pylon)                                                                                                                                                                                                                        | R     | 0.01A  |      |
| 3220 | BMS_DeltaVolt       | Delta V from BMS                                                                                                                                                                                                                                                         | R     | 0.01A  |      |
| 3221 | BMS_CycleCnt        | Cycle Count from BMS                                                                                                                                                                                                                                                     | R     | 1      |      |

**Source page 58**

| NO.               | Variable Name        | Description                   | Value | Unit  | Note                                                  |
| ----------------- | -------------------- | ----------------------------- | ----- | ----- | ----------------------------------------------------- |
| 3222              | BMS_SOH              | SOH from BMS                  | R     | 1     |                                                       |
| 3223              | BMS_ConstantV<br>olt | CV voltage from BMS           | R     | 0.01V |                                                       |
| 3224              | BMS_BMSInfo          | BMSInformation from BMS       | R     | 1     |                                                       |
| 3225              | BMS_PackInfo         | Pack Information from BMS     | R     | 1     |                                                       |
| 3226              | BMS_UsingCap         | Using Cap from BMS            | R     | 1     |                                                       |
| 3227              | BMS_FW               |                               | R     | 1     |                                                       |
| 3228              | BMS_MCUVersi<br>on   | MCU Software version from BMS | R     | 1     |                                                       |
| 3229              | BMSCommType          | BMS Communication Type        |       |       | BMS<br>Communicati<br>on Type<br>0: RS485;<br>1: CAN; |
| 3230<br>~<br>3233 | Reserved             |                               |       |       |                                                       |
| 3234<br>~<br>3249 | Debug data           | Debug data                    |       |       |                                                       |

**Source layout notes:** Input registers 112-115 each contain two variable/description entries in the PDF; both are preserved in their cells. On page 28, Holding registers 3019-3020 shift content one column to the right (for example, `Dry contact closure power` occupies the “Write or not” column); the transcription retains that placement. The BMS reference at Input registers 1082-1093 spans the Value and Unit columns in the PDF and is reproduced in Value. Source addresses, including repeated “System fault word6” below, are not corrected.

#### &*1: Inverter fault code Bit:

Source page: 58.

| Fault type value | Means(The message showed on the inverter when the inverter has<br>fault) |
| ---------------- | ------------------------------------------------------------------------ |
| 1~23             | " Error: 99+x ",                                                         |
| 24               | "Auto Test Failed",                                                      |
| 25               | "No AC Connection",                                                      |
| 26               | "PV Isolation Low",                                                      |
| 27               | " Residual I High",                                                      |
| 28               | " Output High DCI",                                                      |
| 29               | " PV Voltage High",                                                      |
| 30               | " AC V Outrange ",                                                       |
| 31               | " AC F Outrange ",                                                       |
| 32               | " Module Hot "                                                           |

#### &*2:

The value is 0.1V when the fault is the voltage, is 0.01Hz when the fault is the frequency;

#### &*3:

Source pages: 58-59.

| High byte value | Means              | low byte value | Means                              |
| --------------- | ------------------ | -------------- | ---------------------------------- |
| 0               | Auto test stop     | 0              | No test                            |
| 1               | Auto test starting | 1              | Testing grid volt high pro         |
| 2               | Auto testing       | 2              | Testing grid volt low pro          |
|                 |                    | 3              | Testing grid frequency high<br>pro |
|                 |                    | 4              | Testing grid frequency low pro     |

#### &*4:

The variable “wAutoTestResult” and “cTestStepStop”: wAutoTestResult is the step test time
counter, when it reach cTestStepStop, this step test will stop and fail.

#### &*5:

Inverter Model: A , could be show: “A1 B0 D0 T0 PF U1 M5 S1” or “1000F151”

Ax=(A&0XF00000000)>>28
Bx=(A&0XF0000000)>>24
Dx=(A&0XF000000)>>20
Tx=(A&0XF00000)>>16
Px=(A&0x00F000)>>12
Ux=(A&0x000F00)>>8
Mx=(A&0x0000F0)>>4
Sx=(A&0x00000F)

#### &*6: DTC(Device type code)

Source page: 59.

| Code No. | Device type    | Note                                             |
| -------- | -------------- | ------------------------------------------------ |
| 001xx    | Inverter       | 1 tracker and 1phase Grid connect PV inverter TL |
| 002xx    | Inverter       | 2 tracker and 1phase Grid connect PV inverter TL |
| 003xx    | Inverter       | 1 tracker and 1phase Grid connect PV inverter HF |
| 004xx    | Inverter       | 2 tracker and 1phase Grid connect PV inverter HF |
| 005xx    | Inverter       | 1 tracker and 1phase Grid connect PV inverter LF |
| 006xx    | Inverter       | 2 tracker and 1phase Grid connect PV inverter LF |
| 007xx    | Inverter       | 1 tracker and 3phase Grid connect PV inverter TL |
| 008xx    | Inverter       | 2 tracker and 3phase Grid connect PV inverter TL |
| 009xx    | Inverter       | 1 tracker and 3phase Grid connect PV inverter LF |
| 010xx    | Inverter       | 2 tracker and 3phase Grid connect PV inverter LF |
| ……       |                |                                                  |
| 10001    | Data logger    | RF-ShineVersion                                  |
| 10002    | Data logger    | Web-ShinePano                                    |
| 10003    | Data logger    | Web-ShineWebBox                                  |
| 10004    | Data logger    | WL-WIFI Module                                   |
| ……       |                |                                                  |
| 11001    | Confluence box | Confluence box 1                                 |
| ……       |                |                                                  |

#### &*7: Grid network power control command password:

Source pages: 59-60.

Inverter is in lock state after power on; change the power control by network command should unlock inverter
first; default pw is XXXXXX;
Unlock: send 0 to 3-135, then send password to 3-136~~138; inverter will auto lock in 5min after
unlocked;
Change PW: unlock first, then send 1 to 3-135, then send new password to 3-136~~138;
Lock: send 0 or 2 to 3-135;

#### &*8: Inverter fault code and warning code

Source page: 60.

| Fault code | Meaning                      | Warning code | Meaning                        |
| ---------- | ---------------------------- | ------------ | ------------------------------ |
| 0x00000001 | &#92;                        | 0x0001       | Fan warning                    |
| 0x00000002 | Communication error          | 0x0002       | String communication abnormal  |
| 0x00000004 | &#92;                        | 0x0004       | StrPIDconfig Warning           |
| 0x00000008 | StrReverse or StrShort fault | 0x0008       | &#92;                          |
| 0x00000010 | Model Init fault             | 0x0010       | DSP and COM firmware unmatch   |
| 0x00000020 | Grid Volt Sample diffirent   | 0x0020       | &#92;                          |
| 0x00000040 | ISO Sample diffirent         | 0x0040       | SPD abnormal                   |
| 0x00000080 | GFCI Sample diffirent        | 0x0080       | GND and N connect abnormal     |
| 0x00000100 | &#92;                        | 0x0100       | PV1 or PV2 circuit short       |
| 0x00000200 | &#92;                        | 0x0200       | PV1 or PV2 boost driver broken |
| 0x00000400 | &#92;                        | 0x0400       | &#92;                          |
| 0x00000800 | &#92;                        | 0x0800       | &#92;                          |
| 0x00001000 | AFCI Fault                   | 0x1000       | &#92;                          |
| 0x00002000 | &#92;                        | 0x2000       | &#92;                          |
| 0x00004000 | AFCI Module fault            | 0x4000       | &#92;                          |
| 0x00008000 | &#92;                        | 0x8000       | &#92;                          |
| 0x00010000 | &#92;                        |              |                                |
| 0x00020000 | Relay check fault            |              |                                |
| 0x00040000 | &#92;                        |              |                                |
| 0x00080000 | &#92;                        |              |                                |
| 0x00100000 | &#92;                        |              |                                |
| 0x00200000 | Communication error          |              |                                |
| 0x00400000 | Bus Voltage error            |              |                                |
| 0x00800000 | AutoTest fail                |              |                                |
| 0x01000000 | No Utility                   |              |                                |
| 0x02000000 | PV Isolation Low             |              |                                |
| 0x04000000 | Residual I High              |              |                                |
| 0x08000000 | Output High DCI              |              |                                |
| 0x10000000 | PV Voltage high              |              |                                |
| 0x20000000 | AC V Outrange                |              |                                |
| 0x40000000 | AC F Outrange                |              |                                |
| 0x80000000 | TempratureHigh               |              |                                |

#### &*9 Warning Value

Source page: 61.

|        | Warning Value 1  | Warning Value 2 | Warning Value 3 |
| ------ | ---------------- | --------------- | --------------- |
| 0x0001 | String1abnormal  | PV1ShortCircuit | AC SPD abnormal |
| 0x0002 | String2abnormal  | PV2ShortCircuit | DC SPD abnormal |
| 0x0004 | String3abnormal  | PV3ShortCircuit |                 |
| 0x0008 | String4abnormal  | PV4ShortCircuit |                 |
| 0x0010 | String5abnormal  | PV5ShortCircuit |                 |
| 0x0020 | String6abnormal  | PV6ShortCircuit |                 |
| 0x0040 | String7abnormal  | PV7ShortCircuit |                 |
| 0x0080 | String8abnormal  | PV8ShortCircuit |                 |
| 0x0100 | String9abnormal  | BT1DriverFault  |                 |
| 0x0200 | String10abnormal | BT2DriverFault  |                 |
| 0x0400 | String11abnormal | BT3DriverFault  |                 |
| 0x0800 | String12abnormal | BT4DriverFault  |                 |
| 0x1000 | String13abnormal | BT5DriverFault  |                 |
| 0x2000 | String14abnormal | BT6DriverFault  |                 |
| 0x4000 | String15abnormal | BT7DriverFault  |                 |
| 0x8000 | String16abnormal | BT8DriverFault  |                 |

#### &*11:

Inverter Model: A , could be show: “S0A D01 B01 T06 P0F U01 M03E8” or
“0A0101060F0103E8”
Sx=(A&0XFF00000000000000)>>56
Dx=(A&0X00FF000000000000)>>48
Bx=(A&0X0000FF0000000000)>>40
Tx=(A&0X000000FF00000000)>>32
Px=(A&0x00000000FF000000)>>24
Ux=(A&0x0000000000FF0000)>>16
Mx=(A&0x000000000000FFFF)

#### HybridAbnoram/Fault/warning bit definition

Source pages: 61-64.

(Abnormal:record event for debug,continueworking;fault:record event and show for debug,stopworking;Warning:record event and show,continue working)

The PDF groups the first two columns under **Word definition**, and the next two under **Bit definition**. The Byte and Bit subcolumns are named below to preserve the five-column structure. Vertically merged labels and comments are repeated.

| Word definition       | Byte   | Bit definition                              | Bit | comment            |
| --------------------- | ------ | ------------------------------------------- | --- | ------------------ |
| System fault<br>word0 | Byte0  | MasterForceINVFault                         | 0.  | M3 on/off control  |
| System fault<br>word0 | Byte0  | MasterForceSPFault                          | 1.  | M3 on/off control  |
| System fault<br>word0 | Byte0  | BusVoltHigh_TZ                              | 2.  | restart PWM        |
| System fault<br>word0 | Byte0  | BusVoltHigh_ISR                             | 3.  | restartPWM         |
| System fault<br>word0 | Byte0  | reserved                                    | 4.  |                    |
| System fault<br>word0 | Byte0  | reserved                                    | 5.  |                    |
| System fault<br>word0 | Byte0  | reserved                                    | 6.  |                    |
| System fault<br>word0 | Byte0  | reserved                                    | 7.  |                    |
| System fault<br>word0 | Byte1  | GridZClossFault                             | 8.  | Grid side abnormal |
| System fault<br>word0 | Byte1  | reserved                                    | 9.  | Grid side abnormal |
| System fault<br>word0 | Byte1  | reserved                                    | 10. | Grid side abnormal |
| System fault<br>word0 | Byte1  | GFCIHigh                                    | 11. | Grid side abnormal |
| System fault<br>word0 | Byte1  | GridR_VFault                                | 12. | Grid side abnormal |
| System fault<br>word0 | Byte1  | GridS_VFault                                | 13. | Grid side abnormal |
| System fault<br>word0 | Byte1  | GridT_VFault                                | 14. | Grid side abnormal |
| System fault<br>word0 | Byte1  | GridFFault                                  | 15. | Grid side abnormal |
| System fault<br>word1 | Byte2  | RelayFault                                  | 0.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GFCIDamage                                  | 1.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridR_VLowFault                             | 2.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridR_VHighFault                            | 3.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridS_VLowFault                             | 4.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridS_VHighFault                            | 5.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridT_VLowFault                             | 6.  | Grid side abnormal |
| System fault<br>word1 | Byte2  | GridT_VHighFault                            | 7.  | Grid side abnormal |
| System fault<br>word1 | Byte3  | INVCurrOCP_ISR                              | 8.  | Grid side abnormal |
| System fault<br>word1 | Byte3  | INVCurrOCP_TZ                               | 9.  | Grid side abnormal |
| System fault<br>word1 | Byte3  | DCIHigh                                     | 10. | Grid side abnormal |
| System fault<br>word1 | Byte3  | reserved                                    | 11. | Grid side abnormal |
| System fault<br>word1 | Byte3  | INVR_CurrOCP_Rms                            | 12. | Grid side abnormal |
| System fault<br>word1 | Byte3  | INVS_CurrOCP_Rms                            | 13. | Grid side abnormal |
| System fault<br>word1 | Byte3  | INVT_CurrOCP_Rms                            | 14. | Grid side abnormal |
| System fault<br>word1 | Byte3  | NoUtility                                   | 15. | Grid side abnormal |
| System fault<br>word2 | Byte4  | GridFLowFault                               | 0.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | GridFHighFault                              | 1.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | GridVolt_Unbalance_Fault                    | 2.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | AC_PLL_Fault                                | 3.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | OverLoadFault                               | 4.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | reserved                                    | 5.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | reserved                                    | 6.  | Grid side abnormal |
| System fault<br>word2 | Byte4  | reserved                                    | 7.  | Grid side abnormal |
| System fault<br>word2 | Byte5  | EPS_LineVoltR_Loss                          | 8.  | EPS side abnormal  |
| System fault<br>word2 | Byte5  | EPS_LineVoltS_Loss                          | 9.  | EPS side abnormal  |
| System fault<br>word2 | Byte5  | EPS_LineVoltT_Loss                          | 10. | EPS side abnormal  |
| System fault<br>word2 | Byte5  | reserved                                    | 11. | EPS side abnormal  |
| System fault<br>word2 | Byte5  | reserved                                    | 12. | EPS side abnormal  |
| System fault<br>word2 | Byte5  | reserved                                    | 13. | EPS side abnormal  |
| System fault<br>word2 | Byte5  | reserved                                    | 14. | EPS side abnormal  |
| System fault<br>word2 | Byte5  | reserved                                    | 15. | EPS side abnormal  |
| System fault<br>word3 | Byte6  | BatTerminalReversed                         | 0.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | ~~BatTerminalOpen~~<br>**BMS Battery Open** | 1.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | BatteryVoltageLow                           | 2.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | ~~BatteryVoltageHigh~~                      | 3.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | reserved                                    | 4.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | reserved                                    | 5.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | reserved                                    | 6.  | BAT Side abnormal  |
| System fault<br>word3 | Byte6  | reserved                                    | 7.  | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 8.  | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 9.  | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 10. | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 11. | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 12. | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 13. | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 14. | BAT Side abnormal  |
| System fault<br>word3 | Byte7  | reserved                                    | 15. | BAT Side abnormal  |
| System fault<br>word4 | Byte8  | reserved                                    | 0.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | reserved                                    | 1.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | reserved                                    | 2.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | reserved                                    | 3.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | reserved                                    | 4.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | PV1_VoltLowWarn                             | 5.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | PV2-VoltLowWarn                             | 6.  | PV Side Abnormal   |
| System fault<br>word4 | Byte8  | reserved                                    | 7.  | PV Side Abnormal   |
| System fault<br>word4 | Byte9  |                                             | 8.  | PV Side Abnormal   |
| System fault<br>word4 | Byte9  |                                             | 9.  | PV Side Abnormal   |
| System fault<br>word4 | Byte9  |                                             | 10. | PV Side Abnormal   |
| System fault<br>word4 | Byte9  | reserved                                    | 11. | PV Side Abnormal   |
| System fault<br>word4 | Byte9  | reserved                                    | 12. | PV Side Abnormal   |
| System fault<br>word4 | Byte9  | reserved                                    | 13. | PV Side Abnormal   |
| System fault<br>word4 | Byte9  | reserved                                    | 14. | PV Side Abnormal   |
| System fault<br>word4 | Byte9  | reserved                                    | 15. | PV Side Abnormal   |
| System fault<br>word5 | Byte10 | NEDetectFault                               | 0.  | Sytem fault        |
| System fault<br>word5 | Byte10 | PVISOFault                                  | 1.  | Sytem fault        |
| System fault<br>word5 | Byte10 | reserved                                    | 2.  | Sytem fault        |
| System fault<br>word5 | Byte10 | BusVoltHighFault_ISR                        | 3.  | Sytem fault        |
| System fault<br>word5 | Byte10 | BusSampleFault                              | 4.  | Sytem fault        |
| System fault<br>word5 | Byte10 | UHCTFault                                   | 5.  | Sytem fault        |
| System fault<br>word5 | Byte10 | AComFault                                   | 6.  | Sytem fault        |
| System fault<br>word5 | Byte10 | BComFault                                   | 7.  | Sytem fault        |
| System fault<br>word5 | Byte11 | ~~BusVoltHighFault_TZ~~                     | 8.  | Sytem fault        |
| System fault<br>word5 | Byte11 | AuotTestFault                               | 9.  | Sytem fault        |
| System fault<br>word5 | Byte11 | ~~DCIHigh~~                                 | 10. | Sytem fault        |
| System fault<br>word5 | Byte11 | NTCOpenFault                                | 11. | Sytem fault        |
| System fault<br>word5 | Byte11 | reserved                                    | 12. | Sytem fault        |
| System fault<br>word5 | Byte11 | BBHeatsink_TempOver                         | 13. | Sytem fault        |
| System fault<br>word5 | Byte11 | BBOCP_FaultISR                              | 14. | Sytem fault        |
| System fault<br>word5 | Byte11 | BBOCP_FaultTZ                               | 15. | Sytem fault        |
| System fault<br>word6 | Byte12 | PV1_VoltHighFault                           | 0.  | Sytem fault        |
| System fault<br>word6 | Byte12 | PV2_VoltHighFault                           | 1.  | Sytem fault        |
| System fault<br>word6 | Byte12 | BTHeatsink_Overtemp                         | 2.  | Sytem fault        |
| System fault<br>word6 | Byte12 | INVHeatsink_Overtemp                        | 3.  | Sytem fault        |
| System fault<br>word6 | Byte12 | reserved                                    | 4.  | Sytem fault        |
| System fault<br>word6 | Byte12 | reserved                                    | 5.  | Sytem fault        |
| System fault<br>word6 | Byte12 | reserved                                    | 6.  | Sytem fault        |
| System fault<br>word6 | Byte12 | reserved                                    | 7.  | Sytem fault        |
| System fault<br>word6 | Byte13 | BoostDriver1Warn                            | 8.  | System warning     |
| System fault<br>word6 | Byte13 | BoostDriver2Warn                            | 9.  | System warning     |
| System fault<br>word6 | Byte13 | WARN104                                     | 10. | System warning     |
| System fault<br>word6 | Byte13 | PV1_ShortFault                              | 11. | System warning     |
| System fault<br>word6 | Byte13 | PV2_ShortFault                              | 12. | System warning     |
| System fault<br>word6 | Byte13 | Meter Comm Loss                             | 13. | System warning     |
| System fault<br>word6 | Byte13 | PairingTimeOut                              | 14. | System warning     |
| System fault<br>word6 | Byte13 | CT LN Reversed                              | 15. | System warning     |
| System fault<br>word6 | Byte14 | BMS COM Fault                               | 0.  |                    |
| System fault<br>word6 | Byte14 | BMS Error: xxx                              | 1.  |                    |
| System fault<br>word6 | Byte14 | ~~Battery reversed~~                        | 2.  |                    |
| System fault<br>word6 | Byte14 | BAT NTC Open                                | 3.  |                    |
| System fault<br>word6 | Byte14 | SS Timeout                                  | 4.  |                    |
| System fault<br>word6 | Byte14 | Bat voltage low                             | 5.  |                    |
| System fault<br>word6 | Byte14 | Bat T Outrange                              | 6.  |                    |
| System fault<br>word6 | Byte14 | BATOutput_Overload                          | 7.  |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 8.  |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 9.  |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 10. |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 11. |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 12. |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 13. |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 14. |                    |
| System fault<br>word6 | Byte15 | reserved                                    | 15. |                    |
| System fault word7    |        | reserved                                    |     |                    |

## 5 Set address

Source page: 65.

Refer to the Inverter user manual. Always is :
Knock the pv inverter to let the lcd display to the “COM Addr: xxx”, then double knock, if displays
“Move”, you should another double knock, until it displays a address number, then you can give a
single knock to change the address, this address will be remembered when the lcd backlight off.

## 6 Notice

Source page: 65.

1. It can drive mostly 32 pv inverters for one rs485 comport.
2. There are only read input and hold registers commands even the newest version.
3. App user could only care the input register.
4. App user could not care the holding registers.
5. Except the CEI0-21 and VDE-AR-N 4105 power management registers, you should refer the
   manufactory’s suggestion when writing the other registers;
