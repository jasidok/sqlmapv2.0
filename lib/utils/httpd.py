#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

import mimetypes

import gzip
import io
import os
import re
import sys
import threading
import time
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from lib.core.enums import HTTP_HEADER
from lib.core.settings import UNICODE_ENCODING
from lib.core.settings import VERSION_STRING
from http.server import BaseHTTPRequestHandler as _BaseHTTPRequestHandler
from http.server import HTTPServer as _BaseHTTPServer
from http import client as _http_client
from socketserver import ThreadingMixIn as _ThreadingMixIn
from urllib import parse as _urllib_parse

HTTP_ADDRESS = "0.0.0.0"
HTTP_PORT = 8951
DEBUG = True
HTML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "html"))
DISABLED_CONTENT_EXTENSIONS = (".py", ".pyc", ".md", ".txt", ".bak", ".conf", ".zip", "~")


class ThreadingServer(_ThreadingMixIn, _BaseHTTPServer):
    def finish_request(self, *args, **kwargs):
        try:
            _BaseHTTPServer.finish_request(self, *args, **kwargs)
        except Exception:
            if DEBUG:
                traceback.print_exc()


class ReqHandler(_BaseHTTPRequestHandler):
    def do_GET(self):
        path, query = self.path.split('?', 1) if '?' in self.path else (self.path, "")
        params = {}
        content = None

        if query:
            params.update(_urllib_parse.parse_qs(query))

        for key in params:
            if params[key]:
                params[key] = params[key][-1]

        self.url, self.params = path, params

        if path == '/':
            path = "index.html"

        path = path.strip('/')

        path = path.replace('/', os.path.sep)
        path = os.path.abspath(os.path.join(HTML_DIR, path)).strip()

        if not os.path.isfile(path) and os.path.isfile("%s.html" % path):
            path = "%s.html" % path

        if ".." not in os.path.relpath(path, HTML_DIR) and os.path.isfile(path) and not path.endswith(DISABLED_CONTENT_EXTENSIONS):
            content = open(path, "rb").read()
            self.send_response(_http_client.OK)
            self.send_header(HTTP_HEADER.CONNECTION, "close")
            self.send_header(HTTP_HEADER.CONTENT_TYPE, mimetypes.guess_type(path)[0] or "application/octet-stream")
        else:
            content = ("<!DOCTYPE html><html lang=\"en\"><head><title>404 Not Found</title></head><body><h1>Not Found</h1><p>The requested URL %s was not found on this server.</p></body></html>" % self.path.split('?')[0]).encode(UNICODE_ENCODING)
            self.send_response(_http_client.NOT_FOUND)
            self.send_header(HTTP_HEADER.CONNECTION, "close")

        if content is not None:
            for match in re.finditer(b"<!(\\w+)!>", content):
                name = match.group(1)
                _ = getattr(self, "_%s" % name.lower(), None)
                if _:
                    content = self._format(content, **{name: _()})

            if "gzip" in self.headers.get(HTTP_HEADER.ACCEPT_ENCODING):
                self.send_header(HTTP_HEADER.CONTENT_ENCODING, "gzip")
                _ = io.BytesIO()
                compress = gzip.GzipFile("", "w+b", 9, _)
                compress._stream = _
                compress.write(content)
                compress.flush()
                compress.close()
                content = compress._stream.getvalue()

            self.send_header(HTTP_HEADER.CONTENT_LENGTH, str(len(content)))

        self.end_headers()

        if content:
            self.wfile.write(content)

        self.wfile.flush()

    def _format(self, content, **params):
        if content:
            for key, value in params.items():
                content = content.replace("<!%s!>" % key, value)

        return content

    def version_string(self):
        return VERSION_STRING

    def log_message(self, format, *args):
        return

    def finish(self):
        try:
            _BaseHTTPRequestHandler.finish(self)
        except Exception:
            if DEBUG:
                traceback.print_exc()

def start_httpd():
    server = ThreadingServer((HTTP_ADDRESS, HTTP_PORT), ReqHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    print("[i] running HTTP server at '%s:%d'" % (HTTP_ADDRESS, HTTP_PORT))

if __name__ == "__main__":
    try:
        start_httpd()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
