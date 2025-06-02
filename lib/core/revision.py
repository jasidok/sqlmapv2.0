#!/usr/bin/env python

"""
Copyright (c) 2006-2025 sqlmap developers (https://sqlmap.org)
See the file 'LICENSE' for copying permission
"""

import re
import subprocess
from pathlib import Path

from lib.core.common import openFile
from lib.core.convert import getText

def getRevisionNumber():
    """
    Returns abbreviated commit hash number as retrieved with "git rev-parse --short HEAD"

    >>> len(getRevisionNumber() or (' ' * 7)) == 7
    True
    """

    retVal = None
    filePath = None
    current_path = Path(__file__).parent

    while True:
        filePath = current_path / ".git" / "HEAD"
        if filePath.exists():
            break
        else:
            filePath = None
            if current_path == current_path.parent:
                break
            else:
                current_path = current_path.parent

    while True:
        if filePath and filePath.is_file():
            with openFile(str(filePath), "r") as f:
                content = getText(f.read())
                filePath = None

                if content.startswith("ref: "):
                    try:
                        filePath = current_path / ".git" / content.replace("ref: ", "").strip()
                    except UnicodeError:
                        pass

                if filePath is None:
                    match = re.match(r"(?i)[0-9a-f]{32}", content)
                    retVal = match.group(0) if match else None
                    break
        else:
            break

    if not retVal:
        try:
            process = subprocess.Popen("git rev-parse --verify HEAD", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            match = re.search(r"(?i)[0-9a-f]{32}", getText(stdout or ""))
            retVal = match.group(0) if match else None
        except:
            pass

    return retVal[:7] if retVal else None
