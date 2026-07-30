# Clear Plate

Natasha's Law-Compliant Label Generator for Brother QL-700

## Dependencies

A reproducible Python virtual machine can be generated using `requirements.txt`. After doing so, the project can be packaged using `package.(bat|sh)` for Microsoft/Linux.

The application also relies on [libusb](https://pypi.org/project/libusb-package/) being installed and available on the path for the application to load and link against at run-time.

## Drivers

Note that this interfaces with the Brother QL series of printers using raw USB HID commands, and will therefore not work with the default USB device driver for the printer, which were not designed with scripted automation in mind.

Instead, the host computer should have a generic "WinUSB" device driver like that provided by [Zadig](https://zadig.akeo.ie/) installed in place of the stock drivers.
