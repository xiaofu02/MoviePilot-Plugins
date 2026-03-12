from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel

try:
    from app.core.config import settings
except Exception:
    settings = None


class SearchRequest(BaseModel):
    keyword: str
    media_type: Optional[str] = None
    year: Optional[int] = None


class SubscribeRequest(BaseModel):
    keyword: str
    media_type: Optional[str] = None
    season: Optional[int] = None
    year: Optional[int] = None
    auto_download: bool = True


class DownloadRequest(BaseModel):
    keyword: str
    media_type: Optional[str] = None
    season: Optional[int] = None
    year: Optional[int] = None


class MpControl:
    plugin_name = "MoviePilot 控制插件"
    plugin_desc = "为 CLI / Agent 暴露搜索、订阅、下载、状态接口"
    plugin_icon = "plugin.png"
    plugin_version = "0.1.0"
    plugin_author = "XIAO FU"
    plugin_config_prefix = "mpcontrol_"
    auth_level = 1

    def __init__(self):
        self._enabled = True
        self._api_token = None

    def init_plugin(self, config: dict = None):
        config = config or {}
        self._enabled = config.get("enabled", True)
        config_token = config.get("api_token", "").strip()
        system_token = getattr(settings, "API_TOKEN", None) if settings else None
        self._api_token = config_token or system_token

    def get_state(self) -> bool:
        return self._enabled

    def get_command(self) -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/search",
                "endpoint": self.api_search,
                "methods": ["POST"],
                "summary": "搜索媒体",
                "description": "搜索 MoviePilot 可识别的媒体信息"
            },
            {
                "path": "/subscribe",
                "endpoint": self.api_subscribe,
                "methods": ["POST"],
                "summary": "添加订阅",
                "description": "新增一个媒体订阅任务"
            },
            {
                "path": "/download",
                "endpoint": self.api_download,
                "methods": ["POST"],
                "summary": "立即下载",
                "description": "搜索并立即发起下载"
            },
            {
                "path": "/status",
                "endpoint": self.api_status,
                "methods": ["GET"],
                "summary": "查看状态",
                "description": "获取插件和基础服务状态"
            }
        ]

    def get_form(self) -> List[Dict[str, Any]]:
        return [
            {
                "component": "VSwitch",
                "props": {
                    "model": "enabled",
                    "label": "启用插件"
                }
            },
            {
                "component": "VTextField",
                "props": {
                    "model": "api_token",
                    "label": "API Token（留空则使用系统 API_TOKEN）"
                }
            }
        ]

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "api_token": ""
        }

    def stop_service(self):
        pass

    def _verify_token(self, authorization: Optional[str] = None, x_api_token: Optional[str] = None):
        expected = self._api_token
        if not expected:
            return

        bearer = None
        if authorization and authorization.lower().startswith("bearer "):
            bearer = authorization[7:].strip()

        token = bearer or x_api_token
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid API token")

    def _ok(self, action: str, data: Any = None) -> Dict[str, Any]:
        return {
            "ok": True,
            "plugin": "MpControl",
            "action": action,
            "data": data
        }

    def _err(self, action: str, message: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "plugin": "MpControl",
            "action": action,
            "error": message
        }

    async def api_search(
        self,
        body: SearchRequest,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None)
    ):
        self._verify_token(authorization, x_api_token)
        try:
            result = self._search_media(
                keyword=body.keyword,
                media_type=body.media_type,
                year=body.year
            )
            return self._ok("search", result)
        except Exception as e:
            return self._err("search", str(e))

    async def api_subscribe(
        self,
        body: SubscribeRequest,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None)
    ):
        self._verify_token(authorization, x_api_token)
        try:
            result = self._create_subscription(
                keyword=body.keyword,
                media_type=body.media_type,
                season=body.season,
                year=body.year,
                auto_download=body.auto_download
            )
            return self._ok("subscribe", result)
        except Exception as e:
            return self._err("subscribe", str(e))

    async def api_download(
        self,
        body: DownloadRequest,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None)
    ):
        self._verify_token(authorization, x_api_token)
        try:
            result = self._download_now(
                keyword=body.keyword,
                media_type=body.media_type,
                season=body.season,
                year=body.year
            )
            return self._ok("download", result)
        except Exception as e:
            return self._err("download", str(e))

    async def api_status(
        self,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None)
    ):
        self._verify_token(authorization, x_api_token)
        return self._ok(
            "status",
            {
                "enabled": self._enabled,
                "api_token_configured": bool(self._api_token)
            }
        )

    def _search_media(self, keyword: str, media_type: Optional[str], year: Optional[int]) -> Dict[str, Any]:
        return {
            "items": [
                {
                    "title": keyword,
                    "year": year,
                    "type": media_type or "unknown",
                    "score": 0.0,
                    "source": "placeholder"
                }
            ]
        }

    def _create_subscription(
        self,
        keyword: str,
        media_type: Optional[str],
        season: Optional[int],
        year: Optional[int],
        auto_download: bool
    ) -> Dict[str, Any]:
        return {
            "created": True,
            "keyword": keyword,
            "media_type": media_type,
            "season": season,
            "year": year,
            "auto_download": auto_download
        }

    def _download_now(
        self,
        keyword: str,
        media_type: Optional[str],
        season: Optional[int],
        year: Optional[int]
    ) -> Dict[str, Any]:
        return {
            "started": True,
            "keyword": keyword,
            "media_type": media_type,
            "season": season,
            "year": year
        }