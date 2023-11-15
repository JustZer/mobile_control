# !/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
@File     : __init__.py.py
@Project  : mobile_control
@Time     : 2023/8/22 14:28
@Author   : Zhang ZiXu
@Software : PyCharm
@Desc     : Android 控制器 BASE 基类
@Last Modify Time          @Version        @Author
--------------------       --------        -----------
2023/8/22 14:28            1.0             Zhang ZiXu
"""
import subprocess

import frida
import uiautomator2

from common_tools.universal_tools.log_tools import LoggerTool


class AndroidBaseControl:
    frida_device = None
    auto_device = None
    CHARSET = [
        "UTF-8",
        "ISO-8859-1",
        "GBK",
        "GB2312",
    ]

    def __init__(self, logger, usb_device_id: str = "", adb_path: str = "adb"):
        self.logger = logger
        self.adb_path = adb_path
        self.usb_device_id = usb_device_id

    def connect(self, ip_address: str, port: str = "5555", use_other=False):
        """
        连接到指定的ADB设备
        Args:
            ip_address: 设备 IP
            port: 设备端口
            use_other: 是否需要使用其他操作

        Returns:

        """
        count = 0
        while count < 3:
            cmd = [self.adb_path, 'connect', f'{ip_address}:{port}']
            if "already connected" in self._run_command(cmd):
                self.adb_path = f"{self.adb_path} -s {ip_address}:{port}"
                if use_other:
                    self.auto_device = uiautomator2.connect(f"{ip_address}:{port}")
                    # 添加 frida 远程设备
                    # frida-16.1.3 frida-tools-12.2.1 prompt-toolkit-3.0.39 pygments-2.16.1 wcwidth-0.2.6
                    self.frida_device = frida.get_device(f"{ip_address}:{port}")
                return True
            else:
                count += 1
        return False

    def get_devices(self):
        """
        获取连接到计算机的ADB设备列表
        Returns:

        """
        if "-s" in self.adb_path:
            cmd = [self.adb_path.split("-s")[0].strip(), "devices"]
        else:
            cmd = [self.adb_path, 'devices']
        output = self._run_command(cmd)
        devices = [line.strip().split('\t')[0] for line in output.strip().split('\n')[1:] if
                   line and not line.startswith('*')]
        return devices

    def _init_device_control(self):
        """
        初始化设备控制器
        """
        device_control_status = False
        if self.usb_device_id:
            device_ip = self.usb_device_id.split(":")[0]
            device_port = self.usb_device_id.split(":")[1]
            device_control_status = self.connect(ip_address=device_ip, port=device_port)
            self.logger.info(f"已指定设备, 当前设备为: {self.usb_device_id}")
        devices_ids = self.get_devices()
        if not devices_ids:
            self.logger.warning("## 没有连接设备 .")
            return False
        elif device_control_status:
            self.logger.info("二次确认指定设备连接 SUCCESS.")
            return device_control_status
        elif not device_control_status:
            self.logger.info(f"指定设备不存在, 当前可用设备列表: {devices_ids}, 默认选择第一个设备连接 .")
            device_ip = devices_ids[0].split(":")[0]
            device_port = devices_ids[0].split(":")[1]
            device_control_status = self.connect(device_ip, device_port)
            self.logger.info(f"## 当前连接的设备是: {device_ip}:{device_port} ")
            return device_control_status
        self.logger.warning("## 所有设备连接失败 .")
        return device_control_status

    def _run_command(self, cmd, timeout=30):
        """
        运行命令并返回输出
        TODO: subprocess.Popen() 需要将每一个参数作为一个独立的字符串, 无法在一条命令中使用空格分隔的参数
            例如: ["adb -s ip:port", "devices"] 这样的命令无法运行, 因为它会把 "adb -s ip:port" 作为一个整体, 在系统中是不存在这个命令的
        TODO: subprocess.Popen() 需要做子线程清理, 否则会导致子线程无法退出, 运行到一定量级之后就会产生内存溢出，造成大量线程阻塞,
            然后就会造成([Errno 24] Too many open files)这个异常
        TODO: Linux 系统下不支持组合模块, 必须添加 shell=True
        Args:
            cmd: 原始命令

        Returns:

        """
        if isinstance(cmd, list):
            cmd = " ".join(cmd)
        if "nohup" in cmd:
            # TODO: Popen 子线程处理, 启动 server 就不会造成主进程阻塞
            result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, shell=True)
        for charset in self.CHARSET:
            try:
                if "nohup" in cmd:
                    # TODO: server 类都没有返回值, 这个 pid 也不准
                    return result.pid
                if result.returncode != 0:
                    self.logger.warning(f"## 该命令执行失败: {cmd} "
                                        f"\n【错误提示】{result.stderr.decode(charset)}")
                    raise Exception(result.stderr.decode(charset))
                if not result.stdout:
                    return result.stderr.decode(charset)
                return result.stdout.decode(charset)
            except UnicodeDecodeError:
                pass


if __name__ == '__main__':
    logger = LoggerTool("test").logger
    print(AndroidBaseControl(logger=logger).get_devices())
