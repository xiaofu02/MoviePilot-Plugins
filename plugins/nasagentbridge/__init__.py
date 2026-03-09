from typing import Any, Dict, List

from app.plugins import _PluginBase


class Nasagentbridge(_PluginBase):
    # 插件基础信息
    plugin_name = "NAS Agent Bridge"
    plugin_desc = "为外部 NAS Agent 提供 MoviePilot 事件桥接能力"
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main/icons/plugin.png"
    plugin_version = "1.0.0"
    plugin_author = "XIAO FU"
    author_url = ""
    plugin_config_prefix = "nasagentbridge_"
    plugin_order = 99
    auth_level = 1

    def init_plugin(self, config: dict = None):
        self._enabled = False
        self._max_events = 100

        if config:
            self._enabled = config.get("enabled", False)
            self._max_events = int(config.get("max_events", 100) or 100)

    def get_state(self) -> bool:
        return self._enabled

    def stop_service(self):
        pass

    def get_form(self) -> tuple[list, dict]:
        """
        插件配置页
        """
        return [
            {
                "component": "VForm",
                "content": [
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
                            "model": "max_events",
                            "label": "最大缓存事件数",
                            "type": "number"
                        }
                    }
                ]
            }
        ], {
            "enabled": False,
            "max_events": 100
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页
        """
        return [
            {
                "component": "VAlert",
                "props": {
                    "type": "info",
                    "variant": "tonal",
                    "text": "NAS Agent Bridge 已加载。下一步可继续接入事件监听和对外 API。"
                }
            }
        ]

    def get_api(self) -> List[dict]:
        """
        对外暴露 API
        """
        return [
            {
                "path": "/status",
                "endpoint": self.api_status,
                "methods": ["GET"],
                "summary": "获取桥接插件状态"
            }
        ]

    def api_status(self):
        return {
            "ok": True,
            "plugin": self.plugin_name,
            "enabled": self._enabled,
            "max_events": self._max_events,
        }

    def get_command(self) -> List[Dict[str, Any]]:
        """
        暂不提供命令
        """
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """
        暂不注册后台服务
        """
        return []

    def get_dashboard(self, key: str, **kwargs) -> List[dict]:
        """
        暂不提供仪表板卡片
        """
        return []