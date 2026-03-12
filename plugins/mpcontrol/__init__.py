from typing import Any, Dict, List, Optional, Tuple

from fastapi import Body, Header, HTTPException
from app.log import logger
from app.plugins import _PluginBase


class MpControl(_PluginBase):
    # 插件名称
    plugin_name = "MoviePilot 控制插件"
    # 插件描述
    plugin_desc = "为 CLI / Agent 提供搜索、订阅、下载、状态 API"
    # 插件图标
    plugin_icon = "command.png"
    # 插件版本
    plugin_version = "0.1.0"
    # 插件作者
    plugin_author = "XIAO FU"
    # 作者主页
    author_url = "https://github.com/xiaofu02"
    # 插件配置项 ID 前缀
    plugin_config_prefix = "mpcontrol_"
    # 加载顺序
    plugin_order = 98
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled: bool = False
    _api_token: str = ""
    _allow_guest_status: bool = True

    def init_plugin(self, config: dict = None):
        """
        初始化插件
        """
        logger.info(f"初始化 MpControl 插件，配置: {config}")

        if config:
            self._enabled = config.get("enable", False)
            self._api_token = (config.get("api_token") or "").strip()
            self._allow_guest_status = config.get("allow_guest_status", True)
        else:
            self._enabled = False
            self._api_token = ""
            self._allow_guest_status = True

        self.update_config(
            {
                "enable": self._enabled,
                "api_token": self._api_token,
                "allow_guest_status": self._allow_guest_status,
            }
        )

        logger.info(
            f"MpControl 插件初始化完成 - 启用: {self._enabled}, "
            f"API Token 已配置: {bool(self._api_token)}, "
            f"允许匿名 status: {self._allow_guest_status}"
        )

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        return self._enabled

    def get_command(self) -> List[Dict[str, Any]]:
        """
        注册远程命令
        这里先不注册聊天命令，后续你要接 Telegram / 微信 / Discord 再加
        """
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件 API
        """
        return [
            {
                "path": "/status",
                "endpoint": self.api_status,
                "methods": ["GET"],
                "summary": "获取 MpControl 状态",
                "description": "用于 CLI / Agent 检查插件在线状态",
            },
            {
                "path": "/search",
                "endpoint": self.api_search,
                "methods": ["POST"],
                "summary": "搜索媒体",
                "description": "搜索电影/剧集/动漫，占位实现，后续接 MoviePilot 内部搜索",
            },
            {
                "path": "/subscribe",
                "endpoint": self.api_subscribe,
                "methods": ["POST"],
                "summary": "添加订阅",
                "description": "添加订阅，占位实现，后续接 MoviePilot 内部订阅",
            },
            {
                "path": "/download",
                "endpoint": self.api_download,
                "methods": ["POST"],
                "summary": "立即下载",
                "description": "立即下载，占位实现，后续接 MoviePilot 内部下载",
            },
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册公共服务
        当前版本不需要定时服务
        """
        return []

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """
        插件配置页面
        """
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enable",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "allow_guest_status",
                                            "label": "允许匿名访问状态接口",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "api_token",
                                            "label": "API Token",
                                            "placeholder": "留空表示不校验；建议设置给 CLI / Agent 使用",
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ], {
            "enable": self._enabled,
            "api_token": self._api_token,
            "allow_guest_status": self._allow_guest_status,
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页
        """
        return [
            {
                "component": "VCard",
                "props": {
                    "variant": "tonal",
                },
                "content": [
                    {
                        "component": "VCardText",
                        "text": f"插件状态：{'已启用' if self._enabled else '未启用'}"
                    },
                    {
                        "component": "VCardText",
                        "text": f"API Token：{'已配置' if self._api_token else '未配置'}"
                    },
                    {
                        "component": "VCardText",
                        "text": "已提供接口：/status /search /subscribe /download"
                    },
                ],
            }
        ]

    def stop_service(self):
        """
        退出插件
        """
        logger.info("MpControl 插件停止")

    # =========================
    # 内部辅助方法
    # =========================

    def _verify_token(
        self,
        authorization: Optional[str] = None,
        x_api_token: Optional[str] = None,
        allow_guest: bool = False,
    ):
        """
        校验 Token
        """
        expected = (self._api_token or "").strip()

        if not expected:
            return

        if allow_guest:
            return

        bearer = None
        if authorization and authorization.lower().startswith("bearer "):
            bearer = authorization[7:].strip()

        token = bearer or (x_api_token.strip() if x_api_token else None)
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid API token")

    @staticmethod
    def _ok(action: str, data: Any = None) -> Dict[str, Any]:
        return {
            "ok": True,
            "plugin": "MpControl",
            "action": action,
            "data": data,
        }

    @staticmethod
    def _err(action: str, message: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "plugin": "MpControl",
            "action": action,
            "error": message,
        }

    # =========================
    # API 实现
    # =========================

    async def api_status(
        self,
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None),
    ):
        """
        获取状态
        """
        try:
            self._verify_token(
                authorization=authorization,
                x_api_token=x_api_token,
                allow_guest=self._allow_guest_status,
            )
            return self._ok(
                "status",
                {
                    "enabled": self._enabled,
                    "api_token_configured": bool(self._api_token),
                    "allow_guest_status": self._allow_guest_status,
                    "version": self.plugin_version,
                },
            )
        except Exception as e:
            logger.error(f"status 接口异常: {str(e)}", exc_info=True)
            return self._err("status", str(e))

    async def api_search(
        self,
        body: Dict[str, Any] = Body(...),
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None),
    ):
        """
        搜索媒体
        """
        try:
            self._verify_token(authorization=authorization, x_api_token=x_api_token)

            keyword = (body.get("keyword") or "").strip()
            media_type = body.get("media_type")
            year = body.get("year")

            if not keyword:
                return self._err("search", "keyword 不能为空")

            result = self._search_media(
                keyword=keyword,
                media_type=media_type,
                year=year,
            )
            return self._ok("search", result)
        except Exception as e:
            logger.error(f"search 接口异常: {str(e)}", exc_info=True)
            return self._err("search", str(e))

    async def api_subscribe(
        self,
        body: Dict[str, Any] = Body(...),
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None),
    ):
        """
        添加订阅
        """
        try:
            self._verify_token(authorization=authorization, x_api_token=x_api_token)

            keyword = (body.get("keyword") or "").strip()
            media_type = body.get("media_type")
            season = body.get("season")
            year = body.get("year")
            auto_download = body.get("auto_download", True)

            if not keyword:
                return self._err("subscribe", "keyword 不能为空")

            result = self._create_subscription(
                keyword=keyword,
                media_type=media_type,
                season=season,
                year=year,
                auto_download=auto_download,
            )
            return self._ok("subscribe", result)
        except Exception as e:
            logger.error(f"subscribe 接口异常: {str(e)}", exc_info=True)
            return self._err("subscribe", str(e))

    async def api_download(
        self,
        body: Dict[str, Any] = Body(...),
        authorization: Optional[str] = Header(default=None),
        x_api_token: Optional[str] = Header(default=None),
    ):
        """
        立即下载
        """
        try:
            self._verify_token(authorization=authorization, x_api_token=x_api_token)

            keyword = (body.get("keyword") or "").strip()
            media_type = body.get("media_type")
            season = body.get("season")
            year = body.get("year")

            if not keyword:
                return self._err("download", "keyword 不能为空")

            result = self._download_now(
                keyword=keyword,
                media_type=media_type,
                season=season,
                year=year,
            )
            return self._ok("download", result)
        except Exception as e:
            logger.error(f"download 接口异常: {str(e)}", exc_info=True)
            return self._err("download", str(e))

    # =========================
    # 业务占位实现
    # 后面再替换成真实 MoviePilot 调用
    # =========================

    def _search_media(
        self,
        keyword: str,
        media_type: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        logger.info(f"收到搜索请求 keyword={keyword}, media_type={media_type}, year={year}")
        return {
            "items": [
                {
                    "title": keyword,
                    "year": year,
                    "type": media_type or "unknown",
                    "score": 0.0,
                    "source": "placeholder",
                }
            ]
        }

    def _create_subscription(
        self,
        keyword: str,
        media_type: Optional[str] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
        auto_download: bool = True,
    ) -> Dict[str, Any]:
        logger.info(
            f"收到订阅请求 keyword={keyword}, media_type={media_type}, "
            f"season={season}, year={year}, auto_download={auto_download}"
        )
        return {
            "created": True,
            "keyword": keyword,
            "media_type": media_type,
            "season": season,
            "year": year,
            "auto_download": auto_download,
            "source": "placeholder",
        }

    def _download_now(
        self,
        keyword: str,
        media_type: Optional[str] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        logger.info(
            f"收到立即下载请求 keyword={keyword}, media_type={media_type}, "
            f"season={season}, year={year}"
        )
        return {
            "started": True,
            "keyword": keyword,
            "media_type": media_type,
            "season": season,
            "year": year,
            "source": "placeholder",
        }
