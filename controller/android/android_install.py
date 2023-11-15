# !/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
@File     : android_install.py
@Project  : mobile_control
@Time     : 2023/8/22 14:25
@Author   : Zhang ZiXu
@Software : PyCharm
@Desc     :  
@Last Modify Time          @Version        @Author
--------------------       --------        -----------
2023/8/22 14:25            1.0             Zhang ZiXu
"""
import json
import os
import re
import time
import zipfile

from common_tools.universal_tools.log_tools import LoggerTool
from common_tools.universal_tools.redis_tools import RedisConnectUtil
from configs.redis_key_configs import RedisKeyConfigs
from controller.android import AndroidBaseControl


class AndroidInstall(AndroidBaseControl):
    def __init__(self, usb_device_id="", logger=LoggerTool("AndroidInstall").logger, aapt_path: str = "aapt"):
        super().__init__(usb_device_id=usb_device_id, logger=logger)
        self.usb_device_id = usb_device_id
        self.logger = logger
        self.aapt_path = aapt_path
        self.pattern_rules = {
            "valid_package_name": re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$'),
            "find_package_name": re.compile(r"package: name='(\S+)'")
        }
        self.start_time = int(time.time())
        # 实例化 redis
        self.redis_conn = RedisConnectUtil.get_redis_con(decode_responses=True)
        # 设备连接
        self._init_device_control()

    def main(self):
        """
        任务起始函数
        :return:
        """
        while self._get_tasks_rules():
            # 初始化设备连接默认是设备列表中第一个
            if not self.usb_device_id:
                self.usb_device_id = self.get_devices()[0]
            # 相关设备安装
            while self.redis_conn.scard(RedisKeyConfigs.ANDROID_INSTALL_QUEUE_KEY.format(self.usb_device_id)):
                apk_file = self.redis_conn.spop(RedisKeyConfigs.ANDROID_INSTALL_QUEUE_KEY.format(self.usb_device_id))
                install_status, apk_package_name = self.install(apk_file)
                if install_status and apk_package_name:
                    self.redis_conn.sadd(
                        RedisKeyConfigs.ANDROID_ANALYSIS_QUEUE_KEY.format(self.usb_device_id), apk_package_name)
            else:
                self.logger.warning(
                    f"## 当前 key: {RedisKeyConfigs.ANDROID_INSTALL_QUEUE_KEY.format(self.usb_device_id)} 没有待处理数据.")
                break

    def install(self, apk_file):
        """
        安装APK文件
        Args:
            apk_file: 完整的 APK 路径

        Returns:
            Bool(函数运行状态, 安装成功返回 True, 否则返回 False) 和 Str(包名)
        """
        xapk_folder_path = None
        try:
            if apk_file.endswith(".apk"):
                cmd = f'{self.adb_path} install -r -g "{apk_file}"'
                apk_package_name = self._get_package_name(apk_file)
            elif apk_file.endswith(".xapk"):
                # 1. 将 XAPK 进行解压
                xapk_folder_path = self._unzip_xapk(apk_file)
                if not xapk_folder_path:
                    # 1.1 将安装失败的文件移动到错误文件夹
                    self.logger.warning(f"## 当前安装包安装失败: {apk_file}")
                    return False, None
                    # 2. 修改解压后的文件内容
                apk_file, apk_package_name = self._get_xapk_sequence(xapk_folder_path)
                if not apk_file:
                    self.logger.warning(f"## 当前文件解压失败:{apk_file}")
                    return False, apk_package_name
                cmd = f'{self.adb_path} install-multiple -r -g -t {apk_file}'
            else:
                self.logger.warning("## 当前不支持该安装包文件类型 .")
                return False, None
            self._run_command(cmd)
            # 3. 删除解压后的文件夹
            if xapk_folder_path:
                self._rm_rf_folder(xapk_folder_path)
            # 4. 给予 APK 相关权限
            # self._grant_apk_permissions(apk_package_name)
            return True, apk_package_name
        except Exception as e:
            self.logger.warning(f"## 当前文件安装失败, 发生了不可预料的错误;"
                                f"\n【文件路径】:{apk_file} "
                                f"\n【错误提示】{e}")
            return False, None

    def _get_tasks_rules(self):
        """
        脚本启动条件
            1. 队列有充足的数据源
            2. 脚本启动时间不超过 1h
            3. 有设备连接
        :return:
        """
        time_now = int(time.time())
        rules = [
            bool(time_now - self.start_time < 60 * 60),
            bool(self.get_devices())
        ]
        return rules.count(True) == len(rules)

    def _get_package_name(self, apk_file_path):
        """
        获取 APK 的包名
        Args:
            apk_file_path: APK 文件路径
        TODO: 文件路径必须要加 '' 括起来, 谨防含有空格等特殊符号的文件名称
        """
        cmd = [self.aapt_path, 'dump', 'badging', f'"{apk_file_path}"']
        output = self._run_command(cmd)
        apk_package_name = re.findall(self.pattern_rules["find_package_name"], output)
        if apk_package_name and self._is_valid_package_name(apk_package_name[0]):
            return apk_package_name[0]
        else:
            return ""

    def _rm_rf_folder(self, folder_path):
        """
        删除文件夹
        TODO: 直接执行 ['rd', '/s', '/q', 路径] 会报错不存在, 很奇怪
        """
        cmd = ['cmd.exe', '/c', 'rd', '/s', '/q', f'"{folder_path}"']
        self._run_command(cmd)

    @staticmethod
    def _get_xapk_sequence(folder_path):
        """
        获取 XAPK 文件的安装顺序
        Args:
            folder_path: 已解压的 XAPK 文件夹路径
        """
        apks = []
        manifest_file = os.path.join(folder_path, "manifest.json")
        with open(manifest_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            if "split_apks" in data and data["split_apks"]:
                for apk in data["split_apks"]:
                    apk_file_name = apk["file"]
                    # TODO: install-multiple 会自动选择安装模式, 不需要过滤非法指令集
                    # 过滤掉非法的指令集apk包
                    # if any(abi_version in apk_file_name for abi_version in self.ABIS):
                    #     continue
                    apk_file_path = '"' + os.path.join(folder_path, apk_file_name) + '"'
                    # base 包必须最先安装，要放在第一位
                    if 'base' == apk['id']:
                        apks.insert(0, apk_file_path)
                    else:
                        apks.append(apk_file_path)
                if not apks:
                    raise ""
                return " ".join(apks), data["package_name"]
            else:
                apk_file_path = '"' + os.path.join(folder_path, data["package_name"] + ".apk") + '"'
                return apk_file_path, data["package_name"]

    def _unzip_xapk(self, xapk_path) -> str:
        """
        解压 XAPK 文件
        Args:
            xapk_path: XAPK 文件路径

        Returns:

        """
        file_dir = os.path.dirname(os.path.abspath(xapk_path))
        file_name, ext = os.path.splitext(xapk_path)
        unzip_target_dir = os.path.join(file_dir, file_name)

        # 重命名为zip包
        zip_path = xapk_path.replace(".xapk", ".zip")
        os.rename(xapk_path, zip_path)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(unzip_target_dir)
        except zipfile.BadZipfile:
            self.logger.info(f"## 当前 XAPK 存在问题，无法通过解压获取 APK 文件. file: {xapk_path}")
            os.rename(zip_path, xapk_path)
            return ""

        os.rename(zip_path, xapk_path)
        return unzip_target_dir

    def _is_valid_package_name(self, package_name) -> bool:
        """
        判断包名是否合法
        """
        return re.match(self.pattern_rules["valid_package_name"], package_name) is not None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--device", "-d", help="指定设备")

    # 解析命令行参数
    args = parser.parse_args()

    _usb_device_id = args.device

    ai = AndroidInstall(usb_device_id=_usb_device_id)
    ai.main()
