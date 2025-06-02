#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

from lib.core.data import logger
from lib.core.dicts import DBMS_DICT
from lib.core.enums import DBMS
from lib.core.settings import IS_WIN

def checkDependencies():
    missing_libraries = set()

    for dbmsName, data in DBMS_DICT.items():
        if data[1] is None:
            continue

        try:
            match dbmsName:
                case DBMS.MSSQL | DBMS.SYBASE:
                    __import__("_mssql")

                    pymssql = __import__("pymssql")
                    if not hasattr(pymssql, "__version__") or pymssql.__version__ < "1.0.2":
                        warnMsg = "'%s' third-party library must be " % data[1]
                        warnMsg += "version >= 1.0.2 to work properly. "
                        warnMsg += "Download from '%s'" % data[2]
                        logger.warning(warnMsg)
                case DBMS.MYSQL:
                    __import__("pymysql")
                case DBMS.PGSQL | DBMS.CRATEDB:
                    __import__("psycopg2")
                case DBMS.ORACLE:
                    __import__("cx_Oracle")
                case DBMS.SQLITE:
                    __import__("sqlite3")
                case DBMS.ACCESS:
                    __import__("pyodbc")
                case DBMS.FIREBIRD:
                    __import__("kinterbasdb")
                case DBMS.DB2:
                    __import__("ibm_db_dbi")
                case DBMS.HSQLDB | DBMS.CACHE:
                    __import__("jaydebeapi")
                    __import__("jpype")
                case DBMS.INFORMIX:
                    __import__("ibm_db_dbi")
                case DBMS.MONETDB:
                    __import__("pymonetdb")
                case DBMS.DERBY:
                    __import__("drda")
                case DBMS.VERTICA:
                    __import__("vertica_python")
                case DBMS.PRESTO:
                    __import__("prestodb")
                case DBMS.MIMERSQL:
                    __import__("mimerpy")
                case DBMS.CUBRID:
                    __import__("CUBRIDdb")
                case DBMS.CLICKHOUSE:
                    __import__("clickhouse_connect")
        except:
            warnMsg = "sqlmap requires '%s' third-party library " % data[1]
            warnMsg += "in order to directly connect to the DBMS "
            warnMsg += "'%s'. Download from '%s'" % (dbmsName, data[2])
            logger.warning(warnMsg)
            missing_libraries.add(data[1])

            continue

        debugMsg = "'%s' third-party library is found" % data[1]
        logger.debug(debugMsg)

    try:
        __import__("impacket")
        debugMsg = "'python-impacket' third-party library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'python-impacket' third-party library for "
        warnMsg += "out-of-band takeover feature. Download from "
        warnMsg += "'https://github.com/coresecurity/impacket'"
        logger.warning(warnMsg)
        missing_libraries.add('python-impacket')

    try:
        __import__("ntlm")
        debugMsg = "'python-ntlm' third-party library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'python-ntlm' third-party library "
        warnMsg += "if you plan to attack a web application behind NTLM "
        warnMsg += "authentication. Download from 'https://github.com/mullender/python-ntlm'"
        logger.warning(warnMsg)
        missing_libraries.add('python-ntlm')

    try:
        __import__("httpx")
        debugMsg = "'httpx[http2]' third-party library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'httpx[http2]' third-party library "
        warnMsg += "if you plan to use HTTP version 2"
        logger.warning(warnMsg)
        missing_libraries.add('httpx[http2]')

    try:
        __import__("websocket._abnf")
        debugMsg = "'websocket-client' library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'websocket-client' third-party library "
        warnMsg += "if you plan to attack a web application using WebSocket. "
        warnMsg += "Download from 'https://pypi.python.org/pypi/websocket-client/'"
        logger.warning(warnMsg)
        missing_libraries.add('websocket-client')

    try:
        __import__("tkinter")
        debugMsg = "'tkinter' library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'tkinter' library "
        warnMsg += "if you plan to run a GUI"
        logger.warning(warnMsg)
        missing_libraries.add('tkinter')

    try:
        __import__("tkinter.ttk")
        debugMsg = "'tkinter.ttk' library is found"
        logger.debug(debugMsg)
    except ImportError:
        warnMsg = "sqlmap requires 'tkinter.ttk' library "
        warnMsg += "if you plan to run a GUI"
        logger.warning(warnMsg)
        missing_libraries.add('tkinter.ttk')

    if IS_WIN:
        try:
            __import__("pyreadline")
            debugMsg = "'python-pyreadline' third-party library is found"
            logger.debug(debugMsg)
        except ImportError:
            warnMsg = "sqlmap requires 'pyreadline' third-party library to "
            warnMsg += "be able to take advantage of the sqlmap TAB "
            warnMsg += "completion and history support features in the SQL "
            warnMsg += "shell and OS shell. Download from "
            warnMsg += "'https://pypi.org/project/pyreadline/'"
            logger.warning(warnMsg)
            missing_libraries.add('python-pyreadline')

    if len(missing_libraries) == 0:
        infoMsg = "all dependencies are installed"
        logger.info(infoMsg)
