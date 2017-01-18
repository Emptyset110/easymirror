# encoding: utf-8

import time
import threading
import traceback

import zmq

from rpc import RpcObject, RemoteException


########################################################################
class Client(RpcObject):
    """RPC客户端"""

    def __init__(self, reqAddress, subAddress):
        """Constructor"""
        super(Client, self).__init__()

        # 使用 JSON 解包
        self.useMsgpack()

        # zmq端口相关
        self.__reqAddress = reqAddress
        self.__subAddress = subAddress

        self.__context = zmq.Context()
        self.__socketREQ = self.__context.socket(zmq.REQ)  # 请求发出socket
        self.__socketSUB = self.__context.socket(zmq.SUB)  # 广播订阅socket

        # 工作线程相关，用于处理服务器推送的数据
        self.__active = False  # 客户端的工作状态
        self.__thread = threading.Thread(target=self.run)  # 客户端的工作线程

    # ----------------------------------------------------------------------


    # ----------------------------------------------------------------------
    def __getattr__(self, name):
        """实现远程调用功能"""

        # 执行远程调用任务
        def dorpc(*args, **kwargs):
            # 生成请求
            req = [name, args, kwargs]

            # 序列化打包请求
            reqb = self.pack(req)

            # 发送请求并等待回应
            self.__socketREQ.send(reqb)
            repb = self.__socketREQ.recv()

            # 序列化解包回应
            rep = self.unpack(repb)

            # 若正常则返回结果，调用失败则触发异常
            if rep[0]:
                return rep[1]
            else:
                raise RemoteException(rep[1])

        return dorpc

    # ----------------------------------------------------------------------
    def start(self):
        """启动客户端"""
        # 连接端口
        self.__socketREQ.connect(self.__reqAddress)
        self.__socketSUB.connect(self.__subAddress)

        # 将服务器设为启动
        self.__active = True

        # 启动工作线程
        if not self.__thread.isAlive():
            self.__thread.start()

    # ----------------------------------------------------------------------
    def stop(self):
        """停止客户端"""
        # 将客户端设为停止
        self.__active = False

        # 等待工作线程退出
        if self.__thread.isAlive():
            self.__thread.join()

    def run(self):
        while self.__active:
            # 接受广播
            self.subRev()
            # 发送数据
            try:
                self.reqSend()
            except:
                traceback.print_exc()



    # ----------------------------------------------------------------------
    def subRev(self):
        """客户端运行函数"""
        # 使用poll来等待事件到达，等待1秒（1000毫秒）
        if not self.__socketSUB.poll(1000):
            return

        # 从订阅socket收取广播数据
        topic, datab = self.__socketSUB.recv_multipart()

        # 序列化解包
        data = self.unpack(datab)

        # 调用回调函数处理
        self.callback(topic, data)

    def reqSend(self):
        """
        发送数据
        :return:
        """
        req = ['foo', ('argg'), {"kwargs": 1}]

        # 序列化
        reqb = self.pack(req)

        self.__socketREQ.send(reqb)

        datab = self.__socketREQ.recv_json()

        # 序列化解包
        rep = self.unpack(datab)

        if rep[0]:
            return rep[1]
        else:
            raise RemoteException(rep[1])


            # ----------------------------------------------------------------------

    def callback(self, topic, data):
        """回调函数，必须由用户实现"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def subscribeTopic(self, topic):
        """
        订阅特定主题的广播数据

        可以使用topic=''来订阅所有的主题
        """
        self.__socketSUB.setsockopt(zmq.SUBSCRIBE, topic)

    # ----------------------------------------------------------------------
    def callback(self, topic, data):
        """回调函数"""
        print("回调函数")
        print(data)


# ----------------------------------------------------------------------
def runClient():
    """客户端主程序入口"""

    # 创建客户端
    reqAddress = 'tcp://localhost:8889'
    subAddress = 'tcp://localhost:8890'
    client = Client(reqAddress, subAddress)

    client.subscribeTopic(b'')
    client.start()
    while 1:
        time.sleep(1)


if __name__ == '__main__':
    runClient()
