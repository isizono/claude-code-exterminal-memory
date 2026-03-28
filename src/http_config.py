"""HTTP transport 共通設定

launcher.py と main.py の両方から参照される定数を集約する。
"""

import os

HTTP_HOST = "localhost"
HTTP_PORT = int(os.environ.get("CCM_HTTP_PORT", "52837"))
