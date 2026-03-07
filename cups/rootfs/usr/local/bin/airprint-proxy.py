#!/usr/bin/env python3
"""Serve cached AirPrint IPP responses and forward print jobs to CUPS."""

import http.client
import json
import os
import struct
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

CACHE_DIR = '/data/cups/cache/airprint-proxy'
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8631
CUPS_HOST = '127.0.0.1'
CUPS_PORT = 631
CACHE_DIR_REALPATH = os.path.realpath(CACHE_DIR)

IPP_STATUS_OK = 0x0000
IPP_STATUS_SERVER_ERROR_INTERNAL = 0x0500
IPP_OP_PRINT_JOB = 0x0002
IPP_OP_VALIDATE_JOB = 0x0004
IPP_OP_CREATE_JOB = 0x0005
IPP_OP_SEND_DOCUMENT = 0x0006
IPP_OP_CANCEL_JOB = 0x0008
IPP_OP_GET_JOB_ATTRIBUTES = 0x0009
IPP_OP_GET_JOBS = 0x000A
IPP_OP_GET_PRINTER_ATTRIBUTES = 0x000B

IPP_TAG_OPERATION_ATTRIBUTES = 0x01
IPP_TAG_PRINTER_ATTRIBUTES = 0x04
IPP_TAG_END = 0x03

IPP_TAG_INTEGER = 0x21
IPP_TAG_BOOLEAN = 0x22
IPP_TAG_ENUM = 0x23
IPP_TAG_TEXT = 0x41
IPP_TAG_NAME = 0x42
IPP_TAG_KEYWORD = 0x44
IPP_TAG_URI = 0x45
IPP_TAG_CHARSET = 0x47
IPP_TAG_LANGUAGE = 0x48
IPP_TAG_MIME = 0x49


class IPPRequest:
    def __init__(self, version, operation_id, request_id):
        self.version = version
        self.operation_id = operation_id
        self.request_id = request_id


class IPPResponseBuilder:
    def __init__(self, version, status_code, request_id):
        self.buffer = bytearray()
        self.buffer.extend(struct.pack('>BBHI', version[0], version[1], status_code, request_id))

    def start_group(self, tag):
        self.buffer.append(tag)

    def add_string(self, tag, name, values):
        encoded_name = name.encode('utf-8')
        first = True

        for value in values:
            encoded_value = value.encode('utf-8')
            self.buffer.append(tag)
            if first:
                self.buffer.extend(struct.pack('>H', len(encoded_name)))
                self.buffer.extend(encoded_name)
                first = False
            else:
                self.buffer.extend(struct.pack('>H', 0))
            self.buffer.extend(struct.pack('>H', len(encoded_value)))
            self.buffer.extend(encoded_value)

    def add_integer(self, tag, name, values):
        encoded_name = name.encode('utf-8')
        first = True

        for value in values:
            self.buffer.append(tag)
            if first:
                self.buffer.extend(struct.pack('>H', len(encoded_name)))
                self.buffer.extend(encoded_name)
                first = False
            else:
                self.buffer.extend(struct.pack('>H', 0))
            self.buffer.extend(struct.pack('>H', 4))
            self.buffer.extend(struct.pack('>i', value))

    def add_boolean(self, name, value):
        encoded_name = name.encode('utf-8')
        self.buffer.append(IPP_TAG_BOOLEAN)
        self.buffer.extend(struct.pack('>H', len(encoded_name)))
        self.buffer.extend(encoded_name)
        self.buffer.extend(struct.pack('>H', 1))
        self.buffer.append(1 if value else 0)

    def finish(self):
        self.buffer.append(IPP_TAG_END)
        return bytes(self.buffer)


def parse_ipp_request(data):
    if len(data) < 8:
        raise ValueError('IPP request too short')

    version = (data[0], data[1])
    operation_id = struct.unpack('>H', data[2:4])[0]
    request_id = struct.unpack('>I', data[4:8])[0]

    return IPPRequest(version, operation_id, request_id)


def load_cache(printer_name):
    filepath = os.path.realpath(os.path.join(CACHE_DIR, f'{printer_name}.json'))

    if os.path.commonpath([CACHE_DIR_REALPATH, filepath]) != CACHE_DIR_REALPATH:
        return None

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as cache_file:
            return json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        return None


class AirPrintProxyHandler(BaseHTTPRequestHandler):
    server_version = 'AirPrintProxy/1.0'
    sys_version = ''

    def handle_expect_100(self):
        self.send_response_only(100)
        self.end_headers()
        return True

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(content_length)

        try:
            ipp_request = parse_ipp_request(body)
        except ValueError:
            self.send_error(400, 'Invalid IPP request')
            return

        printer_name = self._printer_name_from_path()

        if not printer_name:
            self._proxy_to_cups(body, ipp_request)
            return

        if ipp_request.operation_id == IPP_OP_GET_PRINTER_ATTRIBUTES:
            if self._serve_cached_printer_attributes(printer_name, ipp_request):
                return

        if ipp_request.operation_id == IPP_OP_VALIDATE_JOB:
            if self._serve_validate_job(ipp_request):
                return

        self._proxy_to_cups(body, ipp_request)

    def do_GET(self):
        printer_name = self._printer_name_from_path()
        cache = load_cache(printer_name) if printer_name else None
        payload_parts = ['<html><body><h1>AirPrint IPP proxy</h1>']

        if cache:
            payload_parts.extend(
                [
                    f"<p>Printer: {cache['printer_name']}</p>",
                    f"<p>Model: {cache['make_model']}</p>",
                    f"<p>Path: {self.path}</p>",
                ]
            )
        else:
            payload_parts.append('<p>POST IPP requests to /printers/&lt;name&gt;.</p>')

        payload_parts.append('</body></html>')
        payload = ''.join(payload_parts).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format_string, *args):
        sys.stdout.write('%s - - [%s] %s\n' % (self.address_string(), self.log_date_time_string(), format_string % args))

    def _printer_name_from_path(self):
        parts = self.path.split('/')
        if len(parts) >= 3 and parts[1] == 'printers' and parts[2]:
            return unquote(parts[2])
        return None

    def _service_host(self):
        host = self.headers.get('Host', f'127.0.0.1:{LISTEN_PORT}')
        if ':' not in host:
            return f'{host}:{LISTEN_PORT}'
        return host

    def _printer_uri(self):
        return f'ipp://{self._service_host()}{self.path}'

    def _printer_more_info(self, printer_name):
        host = self.headers.get('Host', '127.0.0.1')
        hostname = host.rsplit(':', 1)[0]
        return f'http://{hostname}:631/printers/{printer_name}'

    def _send_ipp_response(self, payload):
        self.send_response(200)
        self.send_header('Content-Type', 'application/ipp')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_ipp_error(self, ipp_request, status_code):
        response = IPPResponseBuilder(ipp_request.version, status_code, ipp_request.request_id)
        response.start_group(IPP_TAG_OPERATION_ATTRIBUTES)
        response.add_string(IPP_TAG_CHARSET, 'attributes-charset', ['utf-8'])
        response.add_string(IPP_TAG_LANGUAGE, 'attributes-natural-language', ['en'])
        self._send_ipp_response(response.finish())

    def _serve_cached_printer_attributes(self, printer_name, ipp_request):
        cache = load_cache(printer_name)
        if not cache:
            return False

        response = IPPResponseBuilder(ipp_request.version, IPP_STATUS_OK, ipp_request.request_id)
        response.start_group(IPP_TAG_OPERATION_ATTRIBUTES)
        response.add_string(IPP_TAG_CHARSET, 'attributes-charset', ['utf-8'])
        response.add_string(IPP_TAG_LANGUAGE, 'attributes-natural-language', ['en'])

        response.start_group(IPP_TAG_PRINTER_ATTRIBUTES)
        response.add_string(IPP_TAG_URI, 'printer-uri-supported', [self._printer_uri()])
        response.add_string(IPP_TAG_KEYWORD, 'uri-authentication-supported', ['none'])
        response.add_string(IPP_TAG_KEYWORD, 'uri-security-supported', ['none'])
        response.add_string(IPP_TAG_NAME, 'printer-name', [cache['printer_name']])
        response.add_string(IPP_TAG_TEXT, 'printer-info', [cache['info']])
        response.add_string(IPP_TAG_TEXT, 'printer-location', [cache['location'] or cache['info']])
        response.add_string(IPP_TAG_TEXT, 'printer-make-and-model', [cache['make_model']])
        response.add_integer(IPP_TAG_ENUM, 'printer-state', [3])
        response.add_string(IPP_TAG_KEYWORD, 'printer-state-reasons', ['none'])
        response.add_boolean('printer-is-accepting-jobs', True)
        response.add_integer(IPP_TAG_INTEGER, 'queued-job-count', [0])
        response.add_string(IPP_TAG_CHARSET, 'charset-configured', ['utf-8'])
        response.add_string(IPP_TAG_CHARSET, 'charset-supported', ['utf-8', 'us-ascii'])
        response.add_string(IPP_TAG_KEYWORD, 'ipp-versions-supported', ['1.0', '1.1', '2.0'])
        response.add_string(IPP_TAG_LANGUAGE, 'natural-language-configured', ['en'])
        response.add_string(IPP_TAG_LANGUAGE, 'generated-natural-language-supported', ['en'])
        response.add_string(IPP_TAG_KEYWORD, 'compression-supported', ['none'])
        response.add_string(IPP_TAG_KEYWORD, 'pdl-override-supported', ['not-attempted'])
        response.add_string(IPP_TAG_MIME, 'document-format-default', [cache['pdl'][0]])
        response.add_string(IPP_TAG_MIME, 'document-format-supported', cache['pdl'])
        response.add_string(IPP_TAG_URI, 'printer-more-info', [self._printer_more_info(cache['printer_name'])])
        response.add_boolean('color-supported', bool(cache['color']))
        response.add_boolean('multiple-document-jobs-supported', False)

        sides_supported = ['one-sided']
        if cache['duplex']:
            sides_supported.append('two-sided-long-edge')
        response.add_string(IPP_TAG_KEYWORD, 'sides-supported', sides_supported)
        response.add_integer(
            IPP_TAG_ENUM,
            'operations-supported',
            [
                IPP_OP_PRINT_JOB,
                IPP_OP_VALIDATE_JOB,
                IPP_OP_CREATE_JOB,
                IPP_OP_SEND_DOCUMENT,
                IPP_OP_CANCEL_JOB,
                IPP_OP_GET_JOB_ATTRIBUTES,
                IPP_OP_GET_JOBS,
                IPP_OP_GET_PRINTER_ATTRIBUTES,
            ],
        )
        response.add_integer(IPP_TAG_INTEGER, 'printer-up-time', [int(time.time() - self.server.start_time)])

        payload = response.finish()
        self._send_ipp_response(payload)
        return True

    def _serve_validate_job(self, ipp_request):
        response = IPPResponseBuilder(ipp_request.version, IPP_STATUS_OK, ipp_request.request_id)
        response.start_group(IPP_TAG_OPERATION_ATTRIBUTES)
        response.add_string(IPP_TAG_CHARSET, 'attributes-charset', ['utf-8'])
        response.add_string(IPP_TAG_LANGUAGE, 'attributes-natural-language', ['en'])
        payload = response.finish()

        self._send_ipp_response(payload)
        return True

    def _proxy_to_cups(self, body, ipp_request):
        conn = http.client.HTTPConnection(CUPS_HOST, CUPS_PORT, timeout=60)
        headers = {}

        try:
            for key, value in self.headers.items():
                lower_key = key.lower()
                if lower_key in {'host', 'content-length', 'connection', 'accept-encoding'}:
                    continue
                headers[key] = value

            headers['Host'] = f'{CUPS_HOST}:{CUPS_PORT}'
            headers['Content-Length'] = str(len(body))

            conn.request('POST', self.path, body=body, headers=headers)
            response = conn.getresponse()
            response_body = response.read()

            self.send_response(response.status)
            for key, value in response.getheaders():
                lower_key = key.lower()
                if lower_key in {'content-length', 'transfer-encoding', 'connection', 'server', 'date'}:
                    continue
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except OSError:
            self._send_ipp_error(ipp_request, IPP_STATUS_SERVER_ERROR_INTERNAL)
        finally:
            conn.close()


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), AirPrintProxyHandler)
    server.start_time = time.time()
    print(f'Listening on {LISTEN_HOST}:{LISTEN_PORT}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()