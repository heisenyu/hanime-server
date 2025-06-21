from DrissionPage.common import make_session_ele

from app.models.video import *
from app.config import settings, logger
from app.utils.cloudflare_bypass import CloudflareBypasser

import re
import json


class PreviewService:
    def __init__(self):
        """初始化视频预览服务"""
        self.cf_bypasser = CloudflareBypasser()

