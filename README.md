# EQUiSat Ground Station (i.e. EQUiStation)
Scripts and utilities to run on a Raspberry Pi for parsing and processing packets as EQUiSat's ground station.

See [brownspace.org](brownspace.org) for more information

## Components
- `groundstation.py` - primary groundstation loop script for receiving and publishing transmissions
- `log-packet-extractor.py` - simple utility to extract sample packets from testing dumps
- `packetparse.py` - full EQUiSat packet parser (outputs JSON)
- `receiveTest.py` - generic utility to receive/log data from a serial port
- `reedsolomon/` - error correcting utilities/scripts (C with python interface)

## Pi Configuration Information
- Instructions for enabling UART Hardware on PI 3 Pins 14&15 https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/
