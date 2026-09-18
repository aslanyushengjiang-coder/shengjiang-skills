#!/usr/bin/env python3
"""Read-only environment inventory. Does not install or launch anything."""
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

candidates = [shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome', 'msedge')]
candidates += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
print(json.dumps({'python': sys.version.split()[0], 'python_compatible': sys.version_info >= (3,9), 'platform': platform.system(), 'packages': {p: importlib.util.find_spec(p) is not None for p in ('playwright', 'pypdf')}, 'browser_candidates': [c for c in candidates if c and Path(c).is_file()], 'browser_launch': 'not_tested', 'host_search': 'not_tested', 'host_browser_authorization': 'not_tested', 'notifications_enabled': False}, ensure_ascii=False, indent=2))
