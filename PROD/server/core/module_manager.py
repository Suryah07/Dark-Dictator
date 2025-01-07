import importlib
import os
import sys

class ModuleManager:
    def __init__(self):
        self.modules = {}
        self.libs = {}
        self.load_modules()
        self.load_libs()
        
    def load_modules(self):
        modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modules')
        sys.path.append(modules_dir)
        
        for file in os.listdir(modules_dir):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.endswith('Module'):
                        instance = attr()
                        self.modules[instance.name] = instance.get_code()
                        print(f"[+] Loaded module: {instance.name} v{instance.version}")
    
    def load_libs(self):
        libs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
        for file in os.listdir(libs_dir):
            if file.endswith('.py') and not file.startswith('__'):
                lib_name = file[:-3]
                with open(os.path.join(libs_dir, file), 'r') as f:
                    self.libs[lib_name] = f.read()
                    
    def get_tool(self, tool_name):
        return self.modules.get(tool_name)
        
    def get_lib(self, lib_name):
        return self.libs.get(lib_name) 