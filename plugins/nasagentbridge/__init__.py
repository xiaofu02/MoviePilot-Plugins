from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel

# 下面这些 import 名称在不同 MoviePilot 版本里可能有差异
# MVP 先按插件文档的 API / 事件约定实现骨架
try:
    from app.core.event import eventmanager
    from app.schemas.types import EventType
    from app.core.config import settings
except Exception:
    eventmanager = None
    EventType = None
    settings = None


class SearchRequest(BaseModel):
    keyword: str
    media_type: Optional[str] = None   # movie / tv / anime
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
    year: Optional[int] = None
    season: Optional[int] = None


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
        self._api_token = config.get("api_token") or (settings.API_TOKEN if settings else None)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        注册远程命令，供 Telegram/Slack 等渠道触发
        """
        if not EventType:
            return []
        return [{
            "cmd": "/mpctl",
            "event": EventType.PluginAction,
            "desc": "MoviePilot 控制",
            "category": "MoviePilot",
            "data": {
                "action": "mpctl_status"
            }
        }]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        对外暴露 API。MoviePilot 文档规定通过 get_api() 返回 path/endpoint/methods 等信息。
        """
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
        """
        插件设置表单，字段结构你也可以后面改成你常用的样式
        """
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

    def _ok(self, action: str, data: Any = None):
        return {
            "ok": True,
            "plugin": self.__class__.__name__,
            "action": action,
            "data": data
        }

    def _err(self, action: str, message: str):
        return {
            "ok": False,
            "plugin": self.__class__.__name__,
            "action": action,
            "error": message
        }

    # ====== 对外 API ======

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
        return self._ok("status", {
            "enabled": self._enabled,
            "api_token_configured": bool(self._api_token)
        })

    # ====== 远程命令 ======

    if eventmanager and EventType:
        @eventmanager.register(EventType.PluginAction)
        def command_action(self, event):
            event_data = event.event_data
            if not event_data or event_data.get("action") != "mpctl_status":
                return
            channel = event_data.get("channel")
            user = event_data.get("user")
            self.post_message(
                channel=channel,
                title="MoviePilot 控制插件",
                text="插件在线，可通过 CLI/API 调用 search / subscribe / download / status",
                userid=user
            )

    # ====== 下面是适配层：后面接 MoviePilot 内部能力 ======

    def _search_media(self, keyword: str, media_type: Optional[str], year: Optional[int]):
        """
        这里改成调用 MoviePilot 当前版本内部搜索链路。
        先返回一个占位结果，便于把外层 API 和 CLI 跑通。
        """
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
    ):
        """
        这里接 MoviePilot 订阅服务。
        """
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
    ):
        """
        这里接 MoviePilot 搜索并立即下载逻辑。
        """
        return {
            "started": True,
            "keyword": keyword,
            "media_type": media_type,
            "season": season,
            "year": year
        }
