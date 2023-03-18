import os
import logging
from datetime import datetime
import importlib
import json
import uuid
import multiprocessing
import queue
import sys
from io import TextIOWrapper
import traceback
from typing import Callable,Any,NoReturn

class PluginHookManager:
    def __init__(self) -> None:
        self.hooktable : dict[str,list[dict[str,Callable[[Any,Any],Any] | int]]] = {}
        self.logger : logging.Logger = logging.getLogger("plugin-hook")
    def create(self,hook_name : str = None,default_handler : Callable[[Any,Any],Any] = None) -> None:
        if hook_name is None:
            self.logger.warn("No hook name was given. Ignored...")
            return
        if hook_name in self.hooktable:
            self.logger.warn("Hook name had been taken. Ignored...")
            return
        self.hooktable[hook_name] = []
        if default_handler is not None:
            self.hooktable[hook_name].append({"function" : default_handler,"priority" : 0})
        self.logger.debug("Creating hook \"%s\" had successfully ended.",hook_name)
        return
    
    def publish(self,hook_name : str = None,args : tuple = None):
        if hook_name is None:
            self.logger.warn("No hook name was given. Ignored...")
            return
        if not hook_name in self.hooktable:
            self.logger.warn("Invaild hook name was given. Ignored...")
            return
        if args is None:
            self.logger.warn("No arguments were given. Setting empty...")
            args = tuple()
        for subscriber in self.hooktable[hook_name]:
            try:
                ret = subscriber['function'](*args)
                if ret == 1:
                    break
            except Exception as e:
                self.logger.exception(e)
                return
        self.logger.debug("Publishing hook \"%s\" had successfully ended.",hook_name)
        return

    def register(self,hook_name : str = None,func : Callable[[Any,Any],Any] = None,priority : int = 1):
        if hook_name is None:
            self.logger.warn("No hook name was given. Ignored...")
            return
        if func is None:
            self.logger.warn("No function was given. Ignored...")
            return
        i = 0
        while True:
            if i == len(self.hooktable[hook_name]):
                self.hooktable[hook_name].append({"function":func,"priority":priority})
                break
            if  priority >= self.hooktable[hook_name][i]['priority']:
                self.hooktable[hook_name] = self.hooktable[hook_name][:i] + [{"function":func,"priority":priority}] + self.hooktable[hook_name][i:]
                break
            i += 1
        self.logger.debug("Registering hook \"%s\" had successfully ended.",hook_name)
        return

def CRASH(message : str = "*NO REASON*") -> NoReturn:
    sys.stderr.flush()
    sys.stderr.write("\033[91m===========================================\n")
    sys.stderr.write("CRITICAL ERROR OCCURRED!\n")
    sys.stderr.write("===========================================\n")
    sys.stderr.write("THIS PROGRAM HAD OCCURRED A CRITICAL ERROR.\n")
    sys.stderr.write("NO HANDLER (FOUND) TO HANDLE THIS ERROR.\n")
    sys.stderr.write("===========================================\n")
    sys.stderr.write("CRASH REASON:\n")
    sys.stderr.write(message + "\n")
    sys.stderr.write("===========================================\033[0m\n")
    sys.stderr.flush()
    raise Exception(globals())
    sys.exit(-1)

class WorkspaceManager:
    def __init__(self,pluginpath : str = "./plugins/",logpath : str = "./logs/") -> None:
        self.plugin_path : str = pluginpath
        self.log_path : str = logpath
        try:
            if not os.path.exists(self.plugin_path):
                os.mkdir(self.plugin_path)
            if not os.path.exists(self.log_path):
                os.mkdir(self.log_path)
        except Exception as e:
            CRASH("CANNOT CREATE WORKSPACE FOLDERS")


class LoggingManager:
    def __init__(self,filepath = "./logs/",level = logging.INFO) -> None:
        self.filename = filepath+datetime.now().strftime("%Y-%m-%d %H-%M-%S")+".log"
        self.level = level
        self.init()
        self.logger = logging.getLogger("logging-mgr")
    def init(self) -> None:
        try:
            filehandler = logging.FileHandler(filename=self.filename,mode="w+",encoding="UTF-8")
            logging.basicConfig(handlers=[logging.StreamHandler(),filehandler],force=True,level = self.level,format = '[%(levelname)s][%(asctime)s][%(name)s]%(message)s')
        except Exception as e:
            CRASH("LOGGING-MGR FAILED TO INIT LOGGING MOUDLE.")

class ConfigManager:
    def __init__(self,config_file : str = "./config.json") -> None:
        self.logger : logging.Logger = logging.getLogger("config-mgr")
        self.logger.info("Initialing Config Manager Subsystem.")
        self.file : str = config_file
        self.config : dict[str,dict | str | int | float] = {}
        self.init()
        self.logger.info("Initialed Config Manager Subsystem.")
    def init(self) -> None:
        if not os.path.exists(self.file):
            self.logger.warn("Config file \"%s\" doesn't exist! Creating...",self.file)
            fp : TextIOWrapper= open(self.file, 'x')
            fp.close()
        fp : TextIOWrapper = open(self.file,"r+",encoding="UTF-8")
        if fp.read() == "":
            self.config : dict = {
                "pypluging":{
                    "version":"a0.0.1"
                },
                "plugin":{
                    "permission":[],
                    "safemode":False,
                    "default_permission":1
                },
                "plugin-data":{}
            }
            json.dump(self.config,fp)
        fp.close()
        
    def save(self) -> None:
        try:
            fp : TextIOWrapper = open(self.file,"r+",encoding="UTF-8")
            json.dump(self.config,fp)
            fp.close()
        except Exception as e:
            self.logger.error("Failed to save config file. Trying reinitialize the file.")
            self.init()
        self.logger.info("Saved Config File.")
    def load(self) -> None:
        try:
            fp : TextIOWrapper = open(self.file,"r+",encoding="UTF-8")
            self.config = json.load(fp)
            fp.close()
        except Exception as e:
            self.logger.error("Failed to load config file. Trying reinitialize the file.")
            self.init()
        self.logger.info("Loaded Config File.")
    def get(self) -> dict:
        return self.config

def initPlugins():
    global data
    logger = logging.getLogger("init")
    plugin_list = os.listdir("./plugins/")
    plugin_priored = []
    i = 0
    while True:
        if i == len(plugin_list):
            break
        if plugin_list[i].endswith(".py"):
            if not plugin_list[i] in data["config"]["plugins"]:
                    logging.info("new plugin find! Recording to config...")
                    data['config']['plugins'][plugin_list[i]] = 0
                    fp = open("./config.json","w+",encoding="UTF-8")
                    json.dump(data["config"],fp)
                    fp.close()
            k = 0
            while True:
                priority = data["config"]["plugins"][plugin_list[i]]
                if k == len(plugin_priored):
                    plugin_priored.append({"name":plugin_list[i],"priority":priority})
                    break
                if  priority >= plugin_priored[k]['priority']:
                    plugin_priored = plugin_priored[:k] + [{"name":plugin_list[i],"priority":priority}] + plugin_priored[k:]
                    break
                k += 1
        else:
            logger.debug("passed file %s",plugin_list[i])
        i += 1
    for i in range(len(plugin_priored)):
        if data["config"]["plugins"][plugin_priored[i]["name"]] > 0:
            logger.info("trying to load plugin \"%s\"...",plugin_priored[i]["name"][:plugin_priored[i]["name"].find(".py")])
            try:
                plugin_object = importlib.import_module('.'+plugin_priored[i]["name"][:plugin_priored[i]["name"].find(".py")],package='plugins')
                info = plugin_object.GetPluginInfo()
                data['plugins'][info['namespace']] = info
                if 'onInit' in info["entrypoints"]:
                    info["entrypoints"]['onInit'](data)
            except Exception as e:
                logger.debug("failed to load plugin using importlib, trying exec")
                try:
                    plugin_global = {}
                    plugin_fp = open("./plugins/"+plugin_priored[i]["name"],"r",encoding="UTF-8")
                    exec(plugin_fp.read(),plugin_global)
                    info = plugin_global["GetPluginInfo"]()
                    data['plugins'][info['namespace']] = info
                    if 'onInit' in info["entrypoints"]:
                        info["entrypoints"]['onInit'](data)
                except Exception as e:
                    logger.exception(e)
                    logger.info("plugin \"%s\" failed to load.",plugin_priored[i]["name"][:plugin_priored[i]["name"].find(".py")])
                    continue
            logger.info("plugin \"%s\" loaded successfully.",plugin_priored[i]["name"][:plugin_priored[i]["name"].find(".py")])


if __name__ == "__main__":
    workspacemgr = WorkspaceManager()
    logmgr = LoggingManager()
    configmgr = ConfigManager()
    CRASH("no functions running at the end")