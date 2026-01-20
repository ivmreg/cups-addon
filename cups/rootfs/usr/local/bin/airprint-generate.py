#!/usr/bin/env python3
"""
Generate Avahi service files for AirPrint from CUPS printers.
Based on https://github.com/chuckcharlie/cups-avahi-airprint
"""

import cups
import os
import sys
from xml.etree import ElementTree as ET

AVAHI_SERVICE_DIR = '/etc/avahi/services'

class AirPrintGenerator:
    def __init__(self):
        self.service_dir = AVAHI_SERVICE_DIR

    def generate(self):
        try:
            conn = cups.Connection()
        except RuntimeError as e:
            print(f"Error connecting to CUPS: {e}", file=sys.stderr)
            return False

        printers = conn.getPrinters()
        
        if not printers:
            print("No printers found in CUPS")
            return True

        for printer_name, printer_attrs in printers.items():
            # Skip non-shared printers
            if not printer_attrs.get('printer-is-shared', False):
                print(f"Skipping {printer_name} - not shared")
                continue

            self._generate_service_file(conn, printer_name, printer_attrs)

        return True

    def _generate_service_file(self, conn, printer_name, printer_attrs):
        # Get printer details
        state = printer_attrs.get('printer-state', 3)
        info = printer_attrs.get('printer-info', printer_name)
        location = printer_attrs.get('printer-location', '')
        make_model = printer_attrs.get('printer-make-and-model', 'Unknown Printer')

        # Analyze PPD for capabilities
        color = False
        duplex = False
        max_dpi = 600  # Default DPI
        
        try:
            ppd_path = conn.getPPD(printer_name)
            if ppd_path:
                with open(ppd_path, 'r', errors='ignore') as f:
                    ppd_content = f.read()
                    # Check for color support
                    color = 'ColorDevice: True' in ppd_content
                    # Check for duplex
                    if '*Duplex' in ppd_content:
                        # Make sure it's not just "Duplex: None"
                        duplex = '*Duplex DuplexNoTumble' in ppd_content or '*Duplex DuplexTumble' in ppd_content
                    # Check for resolution
                    if '1200' in ppd_content:
                        max_dpi = 1200
                    elif '600' in ppd_content:
                        max_dpi = 600
                # Clean up temp PPD
                try:
                    os.unlink(ppd_path)
                except:
                    pass
        except (cups.IPPError, IOError, OSError) as e:
            print(f"Could not read PPD for {printer_name}: {e}", file=sys.stderr)

        # Brother HL-1110 specific: mono laser, no duplex, 600/1200 DPI
        is_brother_hl1110 = 'HL-1110' in make_model or 'HL1110' in printer_name.upper()
        if is_brother_hl1110:
            color = False
            duplex = False
            max_dpi = 1200  # HL-1110 supports 1200x1200 DPI

        # Build URF capabilities string
        # iOS requires proper URF - "none" causes deselection!
        # Format: <colorspace><bitdepth>,CP<copies>,PQ<qualities>,RS<dpi>,DM<duplex>
        urf_parts = []
        
        if color:
            urf_parts.append('SRGB24')  # 24-bit sRGB color
            urf_parts.append('W8')       # 8-bit grayscale
        else:
            urf_parts.append('W8')       # 8-bit grayscale only (mono printer)
        
        urf_parts.append('CP1')          # Copy support
        urf_parts.append('PQ3-4-5')      # Print quality: draft(3), normal(4), high(5)
        urf_parts.append(f'RS{max_dpi}') # Resolution
        urf_parts.append('IS1-2-3')      # Input slot support
        urf_parts.append('MT1-2-3')      # Media type support
        urf_parts.append('OB9')          # Output bin
        
        if duplex:
            urf_parts.append('DM1')       # Duplex mode 1 (long edge)
        
        urf_string = ','.join(urf_parts)

        # PDL (Page Description Languages) supported
        pdl = ','.join([
            'application/octet-stream',
            'application/pdf',
            'application/postscript',
            'image/urf',
            'image/jpeg',
            'image/png',
            'image/pwg-raster',
        ])

        # Create XML service file
        root = ET.Element('service-group')
        
        name_elem = ET.SubElement(root, 'name')
        name_elem.set('replace-wildcards', 'yes')
        name_elem.text = f'AirPrint {info} @ %h'
        
        service = ET.SubElement(root, 'service')
        
        # IPP service type
        type_elem = ET.SubElement(service, 'type')
        type_elem.text = '_ipp._tcp'
        
        # Universal subtype for AirPrint
        subtype = ET.SubElement(service, 'subtype')
        subtype.text = '_universal._sub._ipp._tcp'
        
        # Port
        port = ET.SubElement(service, 'port')
        port.text = '631'

        # TXT records - order matters for some iOS versions
        txt_records = [
            ('txtvers', '1'),
            ('qtotal', '1'),
            ('rp', f'printers/{printer_name}'),
            ('ty', make_model),
            ('note', location if location else info),
            ('product', f'({make_model})'),
            ('pdl', pdl),
            ('Color', 'T' if color else 'F'),
            ('Duplex', 'T' if duplex else 'F'),
            ('URF', urf_string),
            ('printer-state', str(state)),
            ('printer-type', '0x801044' if color else '0x1044'),
            ('Transparent', 'T'),
            ('Binary', 'T'),
            ('PaperMax', 'legal-A4'),
            ('kind', 'document,envelope,photo'),
        ]

        # Add adminurl for network printers (socket://, ipp://, lpd://)
        device_uri = printer_attrs.get('device-uri', '')
        if device_uri:
            # Extract IP from socket://192.168.x.x:9100 or similar
            import re
            ip_match = re.search(r'://([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', device_uri)
            if ip_match:
                printer_ip = ip_match.group(1)
                txt_records.append(('adminurl', f'http://{printer_ip}'))

        for key, value in txt_records:
            txt = ET.SubElement(service, 'txt-record')
            txt.text = f'{key}={value}'

        # Write service file
        filename = f'AirPrint-{printer_name}.service'
        filepath = os.path.join(self.service_dir, filename)
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')
        
        with open(filepath, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)
        
        print(f"Generated {filepath}")
        return True


def main():
    # Ensure service directory exists
    os.makedirs(AVAHI_SERVICE_DIR, exist_ok=True)
    
    generator = AirPrintGenerator()
    success = generator.generate()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
