# encoding: utf-8
from PyQt5.QtCore import pyqtSlot, QObject,QPropertyAnimation, QSequentialAnimationGroup, QRect, QAbstractAnimation, QPoint
import sys
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtQml import *


import numpy as np
from PIL import Image
import os
#import win32com.client
import threading
import logging
import outputInfoMethod
import frameMethod
import phonenumMethod
import portMethod
import time
import usbMethod
import numpy

class Runnable(QRunnable):
    def __init__(self, obj,inputs):
        QRunnable.__init__(self)
        # main thread
        self.obj = obj
        self.inputs=inputs
        self.result=-1

    def run(self):
        # another thread
        self.result=self.obj.writeMnistImgToUSB(self.inputs)


class PongHandler(QObject):
    def __init__(self, *args, **kwags):
        QObject.__init__(self, *args, **kwags)
        #self._signal.connect(self.mySignal)               #将信号连接到函数mySignal
        self.result=-1


    # ****************************input转成input_frame格式***************************
    def setInputData(self,input):
        ''' input转input_frame格式
        Args:
            input: 一个list，包含多个含有12个像素值的list，即多Tick的3x4的输入图像。像素是二值（0、1）的。例如：
            [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1], ...]

        Returns:
            一个list，包含多个字符串，每个字符串都代表输入list中的对应图像的工作帧格式。图像中每有一个值为1的像素，就会产生一个工作帧。例如：
            ["0100000000000000000000000000001100000000",
             "0100000000000000000000000000001110100000",
             "0100000000000000000000000000010001100000",
             ...]

        AXON: [['C0A48'], ['C0A50'], ['C0A52'], ['C0A54'], ['C0A56'], ['C0A58'], ['C0A60'], ['C0A62'], ['C0A64'], ['C0A66'], ['C0A68'], ['C0A70']]
        FrameHead: 01000000000000000000000000
        '''

        framehead = '01000000000000000000000000'
        frame_list = []
        for tick, img in enumerate(input):
            for idx, pix in enumerate(img):
                if pix == 1:
                    frame = framehead + bin(48 + idx * 2)[2:].zfill(10) + bin(tick)[2:].zfill(4)
                    frame_list.append(frame)

        return frame_list

    def setOutputData(self, input):
        ''' output_frame转output格式

        Args:
            一个list，包含多个字符串，每个字符串都代表输出list中的对应图像的工作帧格式。例如：
            ["0100000000000000000000000000001100000000",
             "0100000000000000000000000000001110100000",
             "0100000000000000000000000000010001100000",
             ...]

        Returns:
            output: int，3个值，0往左，1不动，2往右。

        AXON: ['C2N0', 'C2N1', 'C2N2']
        '''
        result0=0
        result1=0
        result2=0
        for tick, img in enumerate(input):
            if img[-6:-4]=="00":
                result0+=1
            elif img[-6:-4]=="01":
                result1+=1
            elif img[-6:-4]=="10":
                result2+=1

        list_temp=[result0,result1,result2]
        list_max=list_temp.index(max(list_temp))
        return list_max

    def frameDataTo8Bytes(self, frameData):
        r'''
        把文件中40个字节的原始帧数据转换成FPGA需要的帧格式，首先从字符串转换为数字，然后在最高位添加5bit的coreY，
        代表数据从chip的左侧送入，然后在高位补零，补成8 bytes数据，以bytes数据类型返回。

        frameData参数为string类型，是以‘0’、‘1’字符串表示的原始帧数据。
        '''
        tempData = numpy.zeros(1).astype('uint64')
        data =  frameData[32:40]+frameData[24:32]+frameData[16:24]+frameData[8:16]+frameData[0:8]+'000'+frameData[21:26]+'0000000000000000'
        tempData[0] = int(data,2)
        tempData.dtype = 'uint8'
        return bytes(tempData[0:8])

    # *************************MNIST(分類)：工作帧生成|发送、等待读取、最终计算|识别*************************
    # USB傳輸
    # @pyqtSlot(list,result=int)
    # def writeMnistImgToUSB(self,inputs):
    #
    #     # 把图片整理成工作帧发送给USB设备，并开始读取输出，计算识别结果。返回值为最终识别的数字的字符串。
    #     usbStatus = usbMethod.usbHandler.findUSB('', '')
    #     self.InputFrameList = []
    #     inputs_temp=inputs[:]
    #     inputs=[inputs_temp]*16
    #     inputFrameNoList=self.setInputData(inputs)
    #     # *******************************工作帧-write(下行)********************************
    #     workStartFramestr="0110000000000000000000000000000000000000"
    #     #workStartFrame=bytes(workStartFrame.encode('utf-8'))
    #     workFrame = bytes(0)
    #     for no in inputFrameNoList:
    #         # ***********************在fullInputFrame中查找当前输入的输入脉冲数据（类似查找表，以空间换时间，加速工作输入帧的生成）******************************
    #         frameDataTemp = bytes(0)
    #         frameDataTemp += self.frameDataTo8Bytes(no[0:40])
    #         self.InputFrameList.append(frameDataTemp)
    #     for no in self.InputFrameList:
    #         workFrame += no
    #
    #     self.workStartFrame = bytes(0)
    #     frameDataTemp = bytes(0)
    #     frameDataTemp += self.frameDataTo8Bytes(workStartFramestr)
    #     self.workStartFrame += frameDataTemp
    #
    #     workFrame += self.workStartFrame
    #     bytesOneTime = 24 * 1024  # 每次发送24k字节的数据，最后不足24k的部分以全1补齐
    #     length = len(workFrame)
    #
    #     bytesAppend = 255 * (numpy.ones(bytesOneTime - length).astype('uint8'))
    #     usbMethod.usbHandler.writeToUSB(workFrame + bytes(bytesAppend))
    #
    #     # *******************************工作幀-read(上行,等待读取)、最终计算|识别*******************************
    #     result = self.readOutWorkFrameData()
    #
    #     return result

    # *******************************等待读取、最终计算|识别*******************************
    def readOutWorkFrameData(self):
        r'''
        处理读出的工作帧
        返回最终识别结果。
        '''

        # 4 通过usb从snn中读出输出工作帧

        time.sleep(0.25)

        frameList = frameMethod.frameHandler.readWorkFrameFromUSB(delay=192000)
        # framesValid = frameMethod.frameHandler.readWorkFrameFromUSB(delay=512)
        print('frameListlen: ', len(frameList))
        if frameList == []:
            print("No out frame!")
            return 100
        else:
            frameList=frameList[:15]


            inputs=[]
            print(frameList)
            fcInput = np.zeros(1024)
            i = 0
            for frame in frameList:
                str = ''
                for b in frame:
                    str += format(b, '0>8b')
                print(str[24:64])
                inputs.append(str[24:64])

            result=self.setOutputData(inputs)
        return result

    progressChanged = pyqtSignal(int, arguments=['result'])

    @pyqtSlot(list)
    def run_bar(self,inputs):
        #self.progressChanged.connect(self.progress)
        self.runnable = Runnable(self,inputs)
        QThreadPool.globalInstance().start(self.runnable)

    #@pyqtProperty(int, notify=ProgressChanged)
    # @pyqtSlot(int)
    # def progress(self,result):
    #     print("3. progress")
    #     return result

    @pyqtSlot(int)
    def mainthread(self,result):
        self.result=result
        print("2. emit")
        self.progressChanged.emit(result)

    @pyqtSlot(list)
    def writeMnistImgToUSB(self,inputs):
        self.result = -1
        # 把图片整理成工作帧发送给USB设备，并开始读取输出，计算识别结果。返回值为最终识别的数字的字符串。
        usbStatus = usbMethod.usbHandler.findUSB('', '')
        self.InputFrameList = []
        inputs_temp = inputs[:]
        inputs = [inputs_temp] * 16
        inputFrameNoList = self.setInputData(inputs)
        # *******************************工作帧-write(下行)********************************
        workStartFramestr = "0110000000000000000000000000000000000000"
        # workStartFrame=bytes(workStartFrame.encode('utf-8'))
        workFrame = bytes(0)
        for no in inputFrameNoList:
            # ***********************在fullInputFrame中查找当前输入的输入脉冲数据（类似查找表，以空间换时间，加速工作输入帧的生成）******************************
            frameDataTemp = bytes(0)
            frameDataTemp += self.frameDataTo8Bytes(no[0:40])
            self.InputFrameList.append(frameDataTemp)
        for no in self.InputFrameList:
            workFrame += no

        self.workStartFrame = bytes(0)
        frameDataTemp = bytes(0)
        frameDataTemp += self.frameDataTo8Bytes(workStartFramestr)
        self.workStartFrame += frameDataTemp

        workFrame += self.workStartFrame
        bytesOneTime = 24 * 1024  # 每次发送24k字节的数据，最后不足24k的部分以全1补齐
        length = len(workFrame)

        bytesAppend = 255 * (numpy.ones(bytesOneTime - length).astype('uint8'))
        usbMethod.usbHandler.writeToUSB(workFrame + bytes(bytesAppend))

        # *******************************工作幀-read(上行,等待读取)、最终计算|识别*******************************
        result = self.readOutWorkFrameData()

        QMetaObject.invokeMethod(self, "mainthread",
                                 Qt.QueuedConnection,
                                 Q_ARG(int, result))

        #print("result_temp",result_temp)
        return result

pongHandler = PongHandler()
qmlRegisterType(PongHandler, 'Foo', 1, 0, 'Foo')
# app = QApplication(sys.argv)
# demo = Demo()
# demo.show()
# sys.exit(app.exec_())