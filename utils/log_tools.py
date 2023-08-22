# !/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
@File     : log_tools.py
@Project  : mobile_control
@Time     : 2023/8/22 10:25
@Author   : Zhang ZiXu
@Software : PyCharm
@Desc     :  
@Last Modify Time          @Version        @Author
--------------------       --------        -----------
2023/8/22 10:25            1.0             Zhang ZiXu
"""
import logging
import os
from logging.handlers import RotatingFileHandler
import configparser


class LoggerTool:
    script_gen_directory = None
    script_logs_directory = None

    def __init__(self, logger_name, config_file='../configs/files/base_logger_config.ini'):
        self.logger_name = logger_name
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # 日志大小不设置就默认 5M
        self.log_max_size = int(self.config.get(logger_name, 'log_max_size') or 1048576)
        # 日志数量默认 1 个
        self.log_backup_count = int(self.config.get(logger_name, 'log_backup_count') or 1)

        self._init_save_path()

        self.logger = self._init_logger()

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        rotating_handler = RotatingFileHandler(
            self.script_logs_directory, maxBytes=self.log_max_size, backupCount=self.log_backup_count
        )
        rotating_handler.setFormatter(formatter)

        logger.addHandler(rotating_handler)

        return logger

    def log(self, message, level=logging.INFO):
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.CRITICAL:
            self.logger.critical(message)
        else:
            self.logger.log(level, message)

    def _init_save_path(self):
        """
        初始化存储目录, 作者认为日志细化对待后续的问题排查以及优化更加油耗，所以明确输出、明确分级
        整体存储目录结构如下
        项目根目录
            - logs (日志根目录)
                - {logger_name} (脚本文件日志目录)
                    - {logger_name}.log (脚本日志)
                    - {logger_name}.log2 (脚本日志2)
                    - ...
        :return: 
        """
        script_path = os.path.abspath(__file__)
        self.script_gen_directory = os.path.dirname(os.path.dirname(script_path))
        # 初始化项目根目录
        if not os.path.exists(os.path.join(self.script_gen_directory, "logs")):
            os.mkdir(os.path.join(self.script_gen_directory, "logs"))
        # logs_directory 是 logs 根目录
        logs_directory = os.path.join(self.script_gen_directory, "logs")
        # 初始化脚本 Log 输出目录
        if not os.path.exists(os.path.join(logs_directory, self.logger_name)):
            os.mkdir(os.path.join(logs_directory, self.logger_name))
        # script_logs_directory 是脚本输出目录
        script_logs_directory = os.path.join(logs_directory, self.logger_name)
        self.script_logs_directory = os.path.join(script_logs_directory, f"{self.logger_name}.log")


if __name__ == "__main__":
    logger_tool = LoggerTool(logger_name="Logger")
    for i in range(10000):
        logger_tool.log(f"This is an example log message. for {i} <<<<<<<<<<<<<<<<", level=logging.WARNING)
