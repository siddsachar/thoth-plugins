"""My Plugin — a starter template for Thoth plugins.

Rename this file and update the classes to build your plugin.
"""

from plugins.api import PluginAPI, PluginTool


class MyTool(PluginTool):
    """Example tool that echoes a query."""

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def display_name(self) -> str:
        return "🔌 My Tool"

    @property
    def description(self) -> str:
        return "An example tool. Describe what it does for the AI agent."

    def execute(self, query: str) -> str:
        # Access plugin config and secrets via self.plugin_api:
        #   api_key = self.plugin_api.get_secret("MY_API_KEY")
        #   setting = self.plugin_api.get_config("my_setting", "default")
        #
        # Always return a string result. Handle errors gracefully.
        return f"MyTool received: {query}"


def register(api: PluginAPI):
    """Called by Thoth when the plugin loads.

    Register your tools here. Skills in the skills/ directory
    are auto-discovered.
    """
    api.register_tool(MyTool(api))
