from .module_manager import ModuleManager

class ToolServer:
    def __init__(self):
        self.module_manager = ModuleManager()
        
    def get_tool(self, tool_name):
        return self.module_manager.get_tool(tool_name)
        
    def get_lib(self, lib_name):
        return self.module_manager.get_lib(lib_name) 