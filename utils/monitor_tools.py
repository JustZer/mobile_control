# !/usr/bin/env python3
# _*_ coding:utf-8 _*_
"""
@File     : monitor_tools.py
@Project  : mobile_control
@Time     : 2023/8/22 11:56
@Author   : Zhang ZiXu
@Software : PyCharm
@Desc     :  
@Last Modify Time          @Version        @Author
--------------------       --------        -----------
2023/8/22 11:56            1.0             Zhang ZiXu
"""

import hmac
import hashlib
import base64
import logging
import urllib.parse
import time
import requests

from utils.log_tools import LoggerTool


class DingTalkBot:
    """
    钉钉机器人
    """

    def __init__(self, webhook_url, secret):
        # 适配钉钉机器人的加签模式和关键字模式/白名单IP模式
        if secret:
            timestamp = str(round(time.time() * 1000))
            sign = self.get_sign(secret, timestamp)
            self.webhook_url = webhook_url + f'&timestamp={timestamp}&sign={sign}'  # 最终url，url+时间戳+签名
        else:
            self.webhook_url = webhook_url
        self.headers = {
            "Content-Type": "application/json",
            "Charset": "UTF-8"
        }
        self.logger = LoggerTool(logger_name="Logger")

    def get_sign(self, secret, timestamp):
        """
        根据时间戳 + "sign" 生成密钥
        把timestamp+"\n"+密钥当做签名字符串，使用HmacSHA256算法计算签名，然后进行Base64 encode，最后再把签名参数再进行urlEncode，得到最终的签名（需要使用UTF-8字符集）。
        :return:
        """
        string_to_sign = f'{timestamp}\n{secret}'.encode('utf-8')
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign,
            digestmod=hashlib.sha256).digest()

        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign

    def send_text(self, content, mobiles=None, is_at_all=False):
        """
        发送文本消息
        :param content: 发送的内容
        :param mobiles: 被艾特的用户的手机号码，格式是列表，注意需要在content里面添加@人的手机号码
        :param is_at_all: 是否艾特所有人，布尔类型，true为艾特所有人，false为不艾特
        """
        if mobiles:
            if isinstance(mobiles, list):
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    },
                    "at": {
                        "atMobiles": mobiles,
                        "isAtAll": False
                    }
                }
                for mobile in mobiles:
                    payload["text"]["content"] += f"@{mobile}"
            else:
                raise TypeError("mobiles类型错误 不是list类型.")
        else:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": content
                },
                "at": {
                    "atMobiles": "",
                    "isAtAll": is_at_all
                }
            }
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_text发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_text发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False

    def send_link(self, title, text, message_url, pic_url=None):
        """
        发送链接消息
        :param title: 消息标题
        :param text: 消息内容，如果太长只会部分展示
        :param message_url: 点击消息跳转的url地址
        :param pic_url: 图片url
        """
        payload = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": text,
                "picUrl": pic_url,
                "messageUrl": message_url
            }
        }
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_link发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_link发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False

    def send_markdown(self, title, text, mobiles=None, is_at_all=False):
        """
        发送markdown消息
        目前仅支持md语法的子集，如标题，引用，文字加粗，文字斜体，链接，图片，无序列表，有序列表
        :param title: 消息标题，首屏回话透出的展示内容
        :param text: 消息内容，markdown格式
        :param mobiles: 被艾特的用户的手机号码，格式是列表，注意需要在text里面添加@人的手机号码
        :param is_at_all: 是否艾特所有人，布尔类型，true为艾特所有人，false为不艾特
        """
        if mobiles:
            if isinstance(mobiles, list):
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,
                        "text": text
                    },
                    "at": {
                        "atMobiles": mobiles,
                        "isAtAll": False
                    }
                }
                for mobile in mobiles:
                    payload["markdown"]["text"] += f" @{mobile}"
            else:
                raise TypeError("mobiles类型错误 不是list类型.")
        else:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text
                },
                "at": {
                    "atMobiles": "",
                    "isAtAll": is_at_all
                }
            }
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_markdown发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_markdown发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False

    def send_action_card_single(self, title, text, single_title, single_url, btn_orientation=0):
        """
        发送消息卡片(整体跳转ActionCard类型)
        :param title: 消息标题
        :param text: 消息内容，md格式消息
        :param single_title: 单个按钮的标题
        :param single_url: 点击singleTitle按钮后触发的URL
        :param btn_orientation: 0-按钮竖直排列，1-按钮横向排列
        """
        payload = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "singleTitle": single_title,
                "singleURL": single_url,
                "btnOrientation": btn_orientation,
            }

        }
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_action_card_single发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_action_card_single发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False

    def send_action_card_split(self, title, text, btns, btn_orientation=0):
        """
        发送消息卡片(独立跳转ActionCard类型)
        :param title: 消息标题
        :param text: 消息内容，md格式消息
        :param btns: 列表嵌套字典类型，"btns": [{"title": "内容不错", "actionURL": "https://www.dingtalk.com/"}, ......]
        :param btn_orientation: 0-按钮竖直排列，1-按钮横向排列
        """
        payload = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": text,
                "btns": [],
                "btnOrientation": btn_orientation,
            }

        }
        for btn in btns:
            payload["actionCard"]["btns"].append({
                "title": btn.get("title"),
                "actionURL": btn.get("action_url")
            })
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_action_card_split发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_action_card_split发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False

    def send_feed_card(self, links_msg):
        """
        发送多组消息卡片(FeedCard类型)
        :param links_msg: 列表嵌套字典类型，每一个字段包括如下参数：title(单条信息文本), messageURL(点击单条信息后的跳转链接), picURL(单条信息后面图片的url)
        """
        payload = {
            "msgtype": "feedCard",
            "feedCard": {
                "links": []
            }
        }
        for link in links_msg:
            payload["feedCard"]["links"].append(
                {
                    "title": link.get("title"),
                    "messageURL": link.get("messageURL"),
                    "picURL": link.get("picURL")
                }
            )
        response = requests.post(url=self.webhook_url, json=payload, headers=self.headers)
        if response.json().get("errcode") == 0:
            self.logger.log(f"send_feed_card发送钉钉消息成功：{response.json()}")
            return True
        else:
            self.logger.log(f"send_feed_card发送钉钉消息失败：{response.text}", level=logging.WARNING)
            return False


if __name__ == '__main__':
    my_secret = 'SECe6012755c7c77d6f5780cfa69fdae9f0304722f1b4c8c69586c93954b80cb1f3'
    my_url = 'https://oapi.dingtalk.com/robot/send?access_token=3e39e86815aa18c6524a3d58fb8d494b82992b644153a3cb72545167c19d2d62'

    dingding = DingTalkBot(secret=my_secret, webhook_url=my_url)
    dingding.send_text(content="发送钉钉消息的响应数据12", mobiles=['13971573117'], is_at_all=True)
    dingding.send_link(title="chytest", text="时代的长河", message_url="https://www.gitlink.org.cn/chenyh")
    dingding.send_markdown(title="test markdown",
                           text="# 一级标题 \n## 二级标题 \n> 引用文本  \n**加粗**  \n*斜体*  \n[百度链接](https://www.baidu.com)\n\n\n\n",
                           mobiles=['1877497****'])
    dingding.send_action_card_single(title="测试消息的标题",
                                     text="### 乔布斯 20 年前想打造的苹果咖啡厅 Apple Store 的设计正从原来满满的科技感走向生活化，而其生活化的走向其实可以追溯到 20 年前苹果一个建立咖啡馆的计划",
                                     single_title="阅读全文", single_url="https://www.gitlink.org.cn/chenyh",
                                     btn_orientation=0)
    dingding.send_action_card_split(title="测试消息的标题", text="### 乔布斯 20 年前想打造的苹果咖啡厅 Apple Store",
                                    btns=[{"title": "内容不错", "actionURL": "https://www.dingtalk.com/"},
                                          {"title": "不感兴趣", "actionURL": "https://www.dingtalk.com/"}],
                                    btn_orientation=1)
    links = [
        {
            "title": "时代的火车向前开",
            "messageURL": "https://www.dingtalk.com/s?__biz=MzA4NjMwMTA2Ng==&mid=2650316842&idx=1&sn=60da3ea2b29f1dcc43a7c8e4a7c97a16&scene=2&srcid=09189AnRJEdIiWVaKltFzNTw&from=timeline&isappinstalled=0&key=&ascene=2&uin=&devicetype=android-23&version=26031933&nettype=WIFI",
            "picURL": "https://tse1-mm.cn.bing.net/th/id/OIP-C.nelCIKYD30NJW6W68-ZHxAHaJA?pid=ImgDet&rs=1"
        },
        {
            "title": "工作厌倦了怎么办？",
            "messageURL": "https://www.dingtalk.com/s?__biz=MzA4NjMwMTA2Ng==&mid=2650316842&idx=1&sn=60da3ea2b29f1dcc43a7c8e4a7c97a16&scene=2&srcid=09189AnRJEdIiWVaKltFzNTw&from=timeline&isappinstalled=0&key=&ascene=2&uin=&devicetype=android-23&version=26031933&nettype=WIFI",
            "picURL": "https://tse1-mm.cn.bing.net/th/id/OIP-C.nelCIKYD30NJW6W68-ZHxAHaJA?pid=ImgDet&rs=1"
        },
        {
            "title": "也许你对于选用的字体的选择应该更慎重一点",
            "messageURL": "https://www.dingtalk.com/s?__biz=MzA4NjMwMTA2Ng==&mid=2650316842&idx=1&sn=60da3ea2b29f1dcc43a7c8e4a7c97a16&scene=2&srcid=09189AnRJEdIiWVaKltFzNTw&from=timeline&isappinstalled=0&key=&ascene=2&uin=&devicetype=android-23&version=26031933&nettype=WIFI",
            "picURL": "https://tse1-mm.cn.bing.net/th/id/OIP-C.nelCIKYD30NJW6W68-ZHxAHaJA?pid=ImgDet&rs=1"
        },

    ]
    dingding.send_feed_card(links)
