# -*- coding: utf-8 -*-
# from cqhttp import CQHttp
import json
import time
import setting
import requests
import urllib3
from CQLog import WARN, INFO
import random
import hashlib
from base64 import b64encode
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Koudai:
    """docstring for Koudai"""
    response = {}
    # 系统时间
    sysTime13 = 0
    # 配置文件记录时间
    cfgTime13 = 0
    # 口袋房间消息时间
    kdmsgTime13 = 0

    # 初始化
    def __init__(self):
        super(Koudai, self).__init__()
        # 获取系统时间和配置文件时间
        self.sysTime13 = self.getSysTime13()
        self.cfgTime13 = self.getCfgTime13()
        # 请求一次口袋房间
        res = self.getMainpage()
        # 请求成功
        if res['status'] == 200:
            # 获取response
            self.response = res
            # 获取最新口袋消息时间
            self.kdmsgTime13 = self.getKdmsgTime13()
        elif res['status'] >= 401000:
            WARN('koudai48.py授权验证失败', res)
            if not setting.token_verify():
                WARN('token失效，尝试获取新token')
                refresh_token = setting.getNewToken()
                INFO("get new token ->", refresh_token)
        else:
            WARN('获取口袋房间信息出错', res['message'])

    def stamp_to_str(self, timestamp):
        x = time.localtime(timestamp / 1000)
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', x)
        return time_str

    def getPa(self):
        t = int(time.time())*1000
        r = random.randint(1000, 9999)
        salt = "K4bMWJawAtnyyTNOa70S"
        s = "{}{}{}".format(t, r, salt).encode("utf-8")
        m = hashlib.md5(s).hexdigest()
        pa = b64encode("{},{},{}".format(t, r, m).encode("utf-8"))
        return pa

    def commonHeader(self, hasToken=True, hasPa=True):
        header = {
            'Host': 'pocketapi.48.cn',
            'accept': '*/*',
            'Accept-Language': 'zh-Hans-CN;q=1',
            'User-Agent': 'PocketFans201807/6.0.13 (iPhone; iOS 10.3.3; Scale/2.00)',
            'Accept-Encoding': 'gzip, deflate',
            'appInfo': '{"osType":"ios","vendor":"apple","os":"ios","appVersion":"6.0.13","osVersion":"10.3.3","deviceName":"iPhone 5","appBuild":"200513","deviceId":"DDDD-DDDD-DDDD-DDDD-DDDD"}',
            'Content-Type': 'application/json;charset=utf-8',
            'Connection': 'keep-alive',
        }
        if hasToken:
            header['token'] = setting.token()
        if hasPa:
            header['pa'] = self.getPa()
        return header

    # 请求口袋房间
    def getMainpage(self):
        roomId, ownerId = setting.roomId()
        url = "https://pocketapi.48.cn/im/api/v1/chatroom/msg/list/homeowner"
        form = {
            'ownerId': int(ownerId),
            'roomId': int(roomId)
        }
        header = self.commonHeader()
        try:
            response = requests.post(
                url,
                data=json.dumps(form),
                headers=header,
                verify=False,
                timeout=15).json()
            return response
        except Exception as e:
            raise e

    def getSysTime13(self):
        t = int(time.time() * 1000)
        return t

    def getCfgTime13(self):
        t = setting.read_kdmsg_time13()
        return t

    # 写配置文件时间
    def writeCfgTime13(self, t):
        setting.write_kdmsg_time13(t)

    def getKdmsgTime13(self):
        t = self.response['content']['message'][0]['msgTime']
        return t

    # 检查新消息
    def checkNew(self):
        # 判断response非空
        if self.response:
            # 忽略超过60秒的消息
            if self.sysTime13 > self.cfgTime13 + 60000:
                # 将配置文件时间设置为 系统时间 - 60s
                self.writeCfgTime13(self.sysTime13 - 60000)
                # 更新cfgTime13
                self.cfgTime13 = self.sysTime13 - 60000
            elif self.cfgTime13 == self.kdmsgTime13:
                pass
            elif self.cfgTime13 > self.kdmsgTime13:
                # 说明有撤回消息
                pass
            if self.cfgTime13 < self.kdmsgTime13:
                # 有新消息
                # 将配置文件时间设置为 最新一条消息的时间
                self.writeCfgTime13(self.kdmsgTime13)
                return True

    # 酷Qair消息
    def msgAir(self):
        msg_array = []
        datas = self.response['content']['message']
        for data in datas:
            # 判断重复
            if data['msgTime'] <= self.cfgTime13:
                continue
            #
            # 文字消息
            extInfo = json.loads(data['extInfo'])
            if data['msgType'] == 'TEXT':
                if extInfo['messageType'] == 'TEXT':
                    msg = ('%s：%s\n%s' % (
                        extInfo['user']['nickName'],
                        extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'REPLY':
                    msg = ('%s：%s\n%s：%s\n%s' % (
                        extInfo['replyName'], extInfo['replyText'],
                        extInfo['user']['nickName'], extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'LIVEPUSH':
                    playStreamPath, playDetail = self.getlivedetail(extInfo['liveId'])
                    if not playStreamPath:
                        playStreamPath = "暂无"
                    if playDetail['content']['type'] == 1:
                        msg = ('小偶像开直播啦 \n直播标题：%s \n直播封面：https://source.48.cn%s \n直播地址：https://h5.48.cn/2019appshare/memberLiveShare/index.html?id=%s \n推流地址：%s\n%s' % (
                            extInfo['liveTitle'],
                            extInfo['liveCover'], extInfo['liveId'],
                            playStreamPath, self.stamp_to_str(data['msgTime'])))
                    elif playDetail['content']['type'] == 2:
                        msg = ('小偶像开电台啦 \n电台标题：%s \n电台封面：https://source.48.cn%s \n电台地址：https://h5.48.cn/2019appshare/memberLiveShare/index.html?id=%s \n推流地址：%s\n%s' % (
                            extInfo['liveTitle'],
                            extInfo['liveCover'], extInfo['liveId'],
                            playStreamPath, self.stamp_to_str(data['msgTime'])))
                    else:
                        msg = '有未知格式的直播消息'
                        INFO('有未知格式的直播消息')
                elif extInfo['messageType'] == 'VOTE':
                    msg = ('%s：发起了投票：\n%s\n%s' % (
                        extInfo['user']['nickName'], extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'FLIPCARD':
                    # INFO('idol翻牌')
                    msg = ('%s：%s\n问题内容：%s\n%s' % (
                        extInfo['user']['nickName'], extInfo['answer'],
                        extInfo['question'], self.stamp_to_str(data['msgTime'])))
                else:
                    msg = '有未知格式的文字消息'
                    INFO('有未知格式的文字消息')
                    INFO(data)
            # image
            elif data['msgType'] == 'IMAGE':
                bodys = json.loads(data['bodys'])
                msg = ('%s：图片消息：%s\n%s' % (
                    extInfo['user']['nickName'], bodys['url'], self.stamp_to_str(data['msgTime'])))
            # voice
            elif data['msgType'] == 'VIDEO':
                bodys = json.loads(data['bodys'])
                msg = ('%s：视频消息：%s\n%s' % (
                    extInfo['user']['nickName'], bodys['url'], self.stamp_to_str(data['msgTime'])))
            # video
            elif data['msgType'] == 'AUDIO':
                bodys = json.loads(data['bodys'])
                msg = ('%s：语音消息：%s\n%s' % (
                    extInfo['user']['nickName'], bodys['url'], self.stamp_to_str(data['msgTime'])))
            elif data['msgType'] == 'EXPRESS':
                msg = ("%s: 发送了表情\n%s" % (extInfo['user']['nickName'], self.stamp_to_str(data['msgTime'])))
            else:
                msg = '有未知类型的消息'
                INFO('有未知类型的消息')
                INFO(data)
            msg_array.append(msg)
        return msg_array

    # 酷QPro消息
    def msgPro(self):
        msg_array = []
        datas = self.response['content']['message']
        for data in datas:
            # 判断重复
            if data['msgTime'] <= self.cfgTime13:
                continue
            #
            # 文字消息
            extInfo = json.loads(data['extInfo'])
            if data['msgType'] == 'TEXT':
                if extInfo['messageType'] == 'TEXT':
                    msg = ('%s：%s\n%s' % (
                        extInfo['user']['nickName'],
                        extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'REPLY':
                    msg = ('%s：%s\n%s：%s\n%s' % (
                        extInfo['replyName'], extInfo['replyText'],
                        extInfo['user']['nickName'], extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'LIVEPUSH':
                    playStreamPath, playDetail = self.getlivedetail(extInfo['liveId'])
                    if not playStreamPath:
                        playStreamPath = "暂无"
                    if playDetail['content']['type'] == 1:
                        msg = [{'type': 'text', 'data': {
                            'text': '小偶像开直播啦 \n 直播标题：%s \n直播封面：' % extInfo['liveTitle']}},
                            {'type': 'image', 'data': {
                                'file': 'https://source.48.cn%s' % extInfo['liveCover']}},
                            {'type': 'text', 'data': {
                                'text': '直播地址https://h5.48.cn/2019appshare/memberLiveShare/index.html?id=%s \n推流地址：%s开始时间：%s' % (
                                    extInfo['liveId'],
                                    playStreamPath,
                                    self.stamp_to_str(data['msgTime']))}}
                        ]
                    elif playDetail['content']['type'] == 2:
                        msg = [{'type': 'text', 'data': {
                            'text': '小偶像开电台啦 \n 电台标题：%s \n电台封面：' % extInfo['liveTitle']}},
                            {'type': 'image', 'data': {
                                'file': 'https://source.48.cn%s' % extInfo['liveCover']}},
                            {'type': 'text', 'data': {
                                'text': '电台地址https://h5.48.cn/2019appshare/memberLiveShare/index.html?id=%s \n推流地址：%s开始时间：%s' % (
                                    extInfo['liveId'],
                                    playStreamPath,
                                    self.stamp_to_str(data['msgTime']))}}
                        ]
                    else:
                        msg = '有未知格式的直播消息'
                        INFO('有未知格式的直播消息')
                elif extInfo['messageType'] == 'VOTE':
                    msg = ('%s：发起了投票：\n%s\n%s' % (
                        extInfo['user']['nickName'], extInfo['text'],
                        self.stamp_to_str(data['msgTime'])))
                elif extInfo['messageType'] == 'FLIPCARD':
                    # INFO('idol翻牌')
                    msg = ('%s：%s\n问题内容：%s\n%s' % (
                        extInfo['user']['nickName'], extInfo['answer'],
                        extInfo['question'], self.stamp_to_str(data['msgTime'])))
                else:
                    msg = '有未知格式的文字消息'
                    INFO('有未知格式的文字消息')
                    INFO(extInfo)
            # image extInfo['user']['nickName'], bodys['url'], self.stamp_to_str(data['msgTime'])
            elif data['msgType'] == 'IMAGE':
                bodys = json.loads(data['bodys'])
                msg = [{'type': 'text', 'data': {
                    'text': '%s：图片消息' % extInfo['user']['nickName']}},
                    {'type': 'image', 'data': {
                        'file': '%s' % bodys['url']}},
                    {'type': 'text', 'data': {
                        'text': '%s' % self.stamp_to_str(data['msgTime'])}}
                ]
            # voice extInfo['user']['nickName'], bodys['url'], self.stamp_to_str(data['msgTime'])
            elif data['msgType'] == 'AUDIO':
                bodys = json.loads(data['bodys'])
                msg = [{'type': 'text', 'data': {
                    'text': '%s：语音消息' % extInfo['user']['nickName']}},
                    {'type': 'record', 'data': {
                        'file': '%s' % bodys['url']}},
                    {'type': 'text', 'data': {
                        'text': '\n%s' % self.stamp_to_str(data['msgTime'])}}
                ]
            # video
            elif data['msgType'] == 'VIDEO':
                bodys = json.loads(data['bodys'])
                msg = [{'type': 'text', 'data': {
                    'text': '%s：视频消息' % extInfo['user']['nickName']}},
                    {'type': 'text', 'data': {
                        'text': '%s' % bodys['url']}},
                    {'type': 'text', 'data': {
                        'text': '\n%s' % self.stamp_to_str(data['msgTime'])}}
                ]
            elif data['msgType'] == 'EXPRESS':
                msg = ("%s: 发送了表情\n%s" % (extInfo['user']['nickName'], self.stamp_to_str(data['msgTime'])))
            else:
                msg = '有未知类型的消息'
                INFO('有未知类型的消息')
                INFO(data)
            msg_array.append(msg)
        return msg_array

    def getlivedetail(self, liveId):
        url = "https://pocketapi.48.cn/live/api/v1/live/getLiveOne"
        form = {
            "liveId": str(liveId)
        }
        header = self.commonHeader(False, False)
        try:
            response = requests.post(
                url,
                data=json.dumps(form),
                headers=header,
                verify=False,
                timeout=15).json()
            if response['status'] == 200:
                playStreamPath = response['content']['playStreamPath']
                return playStreamPath, response
            else:
                return False, False
        except Exception as e:
            # raise e
            WARN("error when getlivedetail", e)
            return False, False

    def getAllPage(self):
        roomId, ownerId = setting.roomId()
        url = "https://pocketapi.48.cn/im/api/v1/chatroom/msg/list/all"
        form = {
            'ownerId': int(ownerId),
            'roomId': int(roomId)
        }
        header = self.commonHeader()
        try:
            response = requests.post(
                url,
                data=json.dumps(form),
                headers=header,
                verify=False,
                timeout=15).json()
            # return response
        except Exception as e:
            WARN("Error when Koudai48.getAllPage", e)
            return False
        else:
            if int(response['status']) != 200:
                INFO("request fail when Koudai48.getAllPage.status", response)
                return False
        return response

    def getVoteMsg(self, interval_sec):
        response = self.getAllPage()
        if not response:
            return False
        datas = response['content']['message']
        msg_array = []
        try:
            for data in datas:
                # 去掉旧于大于一个查询间隔的消息
                if data['msgTime'] <= self.sysTime13 - 1000.0*interval_sec:
                    continue
                msg = ""
                extInfo = json.loads(data['extInfo'])
                if data['msgType'] == 'TEXT' and extInfo['messageType'] == 'PRESENT_TEXT':
                    # present msg
                    if extInfo['giftInfo']['isVote']:
                        # vote msg
                        msg = [{'type': 'text', 'data': {
                            'text': '%s：投出了%d票' % (extInfo['user']['nickName'], int(extInfo['giftInfo']['giftNum']))}},
                            {'type': 'text', 'data': {
                                'text': '\n%s' % self.stamp_to_str(data['msgTime'])}}]
                        msg_array.append(msg)
        except Exception as e:
            WARN("Error when Koudai48.getAllPage.cmts_array", e)
            return False
        else:
            if msg_array:
                return msg_array
            else:
                return False
