#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

from lib.core.exception import SqlmapConnectionException
from urllib import request as _urllib_request
from urllib import response as _urllib_response


class HTTPRangeHandler(_urllib_request.BaseHandler):
    """
    Handler that enables HTTP Range headers.

    Reference: http://stackoverflow.com/questions/1971240/python-seek-on-remote-file
    """

    def http_error_206(self, req, fp, code, msg, hdrs):
        # 206 Partial Content Response
        r = _urllib_response.addinfourl(fp, hdrs, req.get_full_url())
        r.code = code
        r.msg = msg
        return r

    def http_error_416(self, req, fp, code, msg, hdrs):
        # HTTP's Range Not Satisfiable error
        errMsg = "there was a problem while connecting "
        errMsg += "target ('406 - Range Not Satisfiable')"
        raise SqlmapConnectionException(errMsg)
