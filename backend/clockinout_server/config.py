import configparser
from config_path import ConfigPath
from typing import Optional
import os

class ClockinoutConfig:
    def __init__(self, custom_path: Optional[str] = None):
        if custom_path:
            self.config_dir_path = custom_path
        else:
            self.config_dir_path = self.default_config_folder
    
    @property
    def default_config_folder(self):
        cpath = ConfigPath("EOF", "clockinout", ".ini")
        conf_folder = cpath.readFolderPath(mkdir=True)
        return conf_folder

    @property
    def server_config_file(self):
        conf_file = self.config_dir_path / "server_config.ini"

    def write_server_config(self, confobg: configparser.ConfigParser, overwrite:bool = False):
        if os.path.exists(self.server_config_file) and not overwrite:
            raise RuntimeError("refusing to overwrite existing config file")
        with open(self.server_config_file, "w") as f:
            confobg.write(f)

    def read_server_config(self) -> configparser.ConfigParser:
        if not os.path.exists(self.server_config_file):
            raise ValueError("server config file does not exist!")
        cfg = configparser.ConfigParser()
        with open(self.server_config_file, "r") as f:
            cfg.read_file(f)
        return cfg

