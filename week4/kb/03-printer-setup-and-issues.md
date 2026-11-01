# Printer Setup and Issues

## Finding your printer

Every office printer has a label on the front with its name and IP address. Printer names follow the pattern SITE-FLOOR-NUMBER, for example AUS-02-03 is the third printer on the second floor in Austin. Always add printers by IP address rather than by name. Name-based discovery depends on a directory service that is often slow and sometimes lists printers that have been retired.

## Adding a printer

### Windows

1. Open Settings, then Bluetooth and devices, then Printers and scanners.
2. Click Add device, wait ten seconds, then click Add manually.
3. Choose Add a printer using an IP address or hostname.
4. Enter the IP address from the label. Leave the port name as suggested.
5. When asked for a driver, choose the generic PCL6 driver. Do not download a manufacturer driver; the generic one is faster and is the only one the print server supports.
6. Print a test page.

### macOS

1. Open System Settings, then Printers and Scanners.
2. Click Add Printer, Scanner, or Fax.
3. Select the IP tab.
4. Enter the IP address. Protocol should be IPP. Leave Queue empty.
5. For Use, pick Generic PostScript Printer.
6. Click Add and print a test page.

## Common problems

### Printer shows offline

Remove the printer and re-add it using the IP address. This fixes the problem in nine cases out of ten. If the printer is offline for everyone, check the outage board before filing a ticket; the printer may be under maintenance.

### Jobs stuck in the queue

Open the print queue, cancel all documents, then turn the printer off and on at the power switch. Wait for it to finish warming up before sending anything new. On Windows, if the queue will not clear, restart the Print Spooler service.

### Prints are blank or streaked

This is a hardware issue. Do not try to fix it yourself. Note the printer name and file a ticket with priority low. Facilities replaces toner and drums on a schedule and will pull it forward if a ticket is open.

## Printing from a personal device

Not supported. Email the document to yourself and print from your company laptop.
