# encoding: utf-8
from PyQt5.QtCore import pyqtSlot, QObject
import numpy
import os
import threading
import time
import array
import logging
import usbMethod
import outputInfoMethod

#**************************frame处理（write/read）*****************************
class FrameHandler(QObject):

    fullInputFrameList = []             #输入特征图为全1时的输入工作帧列表
    originalFullInputFrameList = []     #40bit每组的输入工作帧的列表，用于仿真验证，对硬件工作流程没有影响
    fullInputFrameListReady = False
    workStartFrame = bytes(0)

    def __init__(self):
        QObject.__init__(self)
    #*******************************配置帧——create*********************************
    #.txt ——> .npy(创建)
    @pyqtSlot(str, str, bool, result=bool)
    def readConfigFileThread(self,filePath,netName,doItAnyway=False):
        r'''
        filePath参数为原始帧数据文件的路径，netName参数是网络名称，也是要存储的帧数据文件的名称，
        如果doItAnyway是True，则不判断帧数据文件是否已经存在，直接新建或进行覆盖；
        '''
        if not doItAnyway:
            if os.path.exists('./configFiles/'+netName+'Config.npy'):
                outputInfoMethod.raiseWarning(netName+' config file is already exited!')
                return False
        readConfigThread = threading.Thread(target=self.readFromConfigFile,args=(filePath,netName,))
        readConfigThread.start()
        return True
    # .txt ——> .npy(转换，将配置帧文件.txt，40bits——>64bits,并倒序，然后保存为.npy)
    def readFromConfigFile(self,filePath,netName):
        r'''
        把配置文件中的原始帧数据处理成可直接发送给USB设备的格式，并以.npy的格式存储，以备下次配置使用；
        原始帧数据是以‘0’、‘1’字符串表示的40bytes的字符串，需要处理成8bytes长度的bytes类型；
        filePath参数为原始帧数据文件的路径，netName参数是网络名称，也是要存储的帧数据文件的名称；
        帧数据文件以txt的格式存储，以一行'begin'标志帧数据块的开始，然后每一行的前40个字节包含了配置信息；
        帧数据块最后以一行'end'标志结束；
        帧数据块之外，以及每一行帧数据前40个字节之后可以添加注释。
        '''
        try:
            print('Reading config file.')
            with open(filePath,'r') as frameDataFile:
                frameData = frameDataFile.read().splitlines()
                frameDataNum = len(frameData)
                outputInfoMethod.raiseInfo("Transfroming config file ...")
                isInFrameBulk = False
                tempData = numpy.zeros(frameDataNum-2).astype('uint64')
                for i,line in enumerate(frameData):
                    if isInFrameBulk:
                        if line == 'end':
                            isInFrameBulk = False
                        else:
                            #********************************************************
                            tempData[i-1] = int(self.frame40bTo64b_rever(line[0:40]),2)
                    else:
                        if line == 'begin':
                            isInFrameBulk = True
                tempData.dtype = 'uint8'
                bytesFrameData = bytes(tempData)
        except BaseException as e:
            outputInfoMethod.raiseError("Failed to transform config file.")
            outputInfoMethod.raiseError(str(e))
        else:
            outputInfoMethod.raiseInfo("Transfromed successfully.")
            numpy.save('./configFiles/'+netName+'Config.npy',numpy.array(bytesFrameData))
        finally:
            return True

    # *******************************InputFrame(输入帧+启动帧)——load*********************************
    @pyqtSlot(str, str, result=bool)#!!!!!!注意參數限制!!!!!!
    def readFromInputFile(self,filePath,netName):
        try:
            #with open(filePath,'r') as inputFile:
            with open('./configFiles/'+netName+'FullInputFrame.txt', 'r') as inputFile:
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #with open("configFiles/mnist_numFullInputFrame.txt",'r') as inputFile:
            #with open("configFiles/chepaiFullInputFrame.txt",'r') as inputFile:
                inputFrameData = inputFile.read().splitlines()
            self.fullInputFrameList = []
            self.fullInputFrameListReady = False
            i = 0
            length = len(inputFrameData)
            outputInfoMethod.raiseInfo("Reading "+netName+" input layer file.")
            while i < length:
                if inputFrameData[i] == 'begin':
                    i += 1
                    #读取数据输入工作帧
                    while inputFrameData[i] != 'inputFrameEnd' and i < length:
                        frameDataTemp = bytes(0)
                        for j in range(int(len(inputFrameData[i])/40)):
                            frameDataTemp += self.frameDataTo8Bytes(inputFrameData[i][(40*j):(40*(j+1))])
                        self.fullInputFrameList.append(frameDataTemp)
                        self.originalFullInputFrameList.append(inputFrameData[i])
                        i += 1
                    i += 1
                    #读取启动工作帧
                    self.workStartFrame = bytes(0)
                    while inputFrameData[i] != 'startFrameEnd' and i < length:
                        frameDataTemp = bytes(0)
                        for j in range(int(len(inputFrameData[i])/40)):
                            frameDataTemp += self.frameDataTo8Bytes(inputFrameData[i][(40*j):(40*(j+1))])
                        self.workStartFrame += frameDataTemp
                        i += 1
                    i += 1
                else:
                    i += 1
        except BaseException as e:
            outputInfoMethod.raiseError("Failed to read input layer file.")
            outputInfoMethod.raiseError(str(e))
            return False
        else:
            self.fullInputFrameListReady = True
            #print(self.fullInputFrameList)
            print(len(self.fullInputFrameList))
            outputInfoMethod.raiseInfo("Read "+netName+" input layer file successfully.")
            return True

    # *******************************配置帧—write(下行)********************************
    @pyqtSlot(str,result=bool)
    def writeConfigFrameToUSB(self,netName):
        r'''
        把处理好的帧数据逐帧写入USB设备；
        netName参数为网络的名称，也是帧数据存储文件的名称；
        '''
        try:
            frameData = numpy.load('./configFiles/'+netName+'Config.npy')
            #某些情况下需要降低发送速度，下面将配置帧分块发送；
            frameData = bytes(frameData)
            dataLength = len(frameData)
            bytesOneTime = 8*1024   #每次发送8k字节的数据，有效帧不足8k时，以全1补齐
            bytesValidOneTime = 4*1024  #每次发送的数据中，有效帧的字节数
            onesOneTime = bytes(255*(numpy.ones(bytesOneTime-bytesValidOneTime).astype('uint8')))    #每次发送的字节中，补充的全1的字节
            framesOneTime = int(bytesValidOneTime/8)      #每次发送的帧数，每帧是8个字节
            i = 0
            frameNum = 0
            timeBegin = time.time()
            while (i+bytesValidOneTime) < dataLength:
                #time.sleep(0.001)
                if not usbMethod.usbHandler.writeToUSB(frameData[i:(i+bytesValidOneTime)]+onesOneTime) :
                    return False
                i += bytesValidOneTime
                frameNum += framesOneTime
                #print(frameNum)
            if i < dataLength:
                bytesAppendNum = bytesOneTime - (dataLength-i)
                bytesAppend = 255*(numpy.ones(bytesAppendNum).astype('uint8'))
                usbMethod.usbHandler.writeToUSB(frameData[i:] + bytes(bytesAppend))
            '''
            usbMethod.usbHandler.writeToUSB(bytes(frameData))
            '''
            timeEnd = time.time()
        except BaseException as e:
            outputInfoMethod.raiseError("Failed to deploy the chip.")
            outputInfoMethod.raiseError(str(e))
            return False
        else:
            outputInfoMethod.raiseInfo("Deployed the chip successfully with %.3f S." % (timeEnd-timeBegin))
            return True

    # *******************************配置帧—write(下行)********************************
    @pyqtSlot(str,str,str,result=bool)
    def writeSpecifyConfigFrameToUSB(self,netName,beginFrameNo,endFrameNo):
        r'''
        把处理好的帧数据逐帧写入USB设备；
        netName参数为网络的名称，也是帧数据存储文件的名称；
        '''
        try:
            beginFrame = int(beginFrameNo)
            endFrame = int(endFrameNo)
            if endFrame < beginFrame:
                outputInfoMethod.raiseError("终止帧次序不能小于起始帧次序。")
                return False
            frameData = numpy.load('./configFiles/'+netName+'Config.npy')
            #某些情况下需要降低发送速度，下面将配置帧分块发送；
            frameData = bytes(frameData)
            length = len(frameData)
            if (beginFrame*8) > length:
                outputInfoMethod.raiseError("起始帧次序超出了帧数据的大小。")
            dataLength = min(endFrame*8,length)
            bytesOneTime = 8*1024   #每次发送8k字节的数据，有效帧不足8k时，以全1补齐
            bytesValidOneTime = 4*1024  #每次发送的数据中，有效帧的字节数
            onesOneTime = bytes(255*(numpy.ones(bytesOneTime-bytesValidOneTime).astype('uint8')))    #每次发送的字节中，补充的全1的字节
            framesOneTime = int(bytesValidOneTime/8)      #每次发送的帧数，每帧是8个字节
            i = (beginFrame-1)*8
            frameNum = 0
            timeBegin = time.time()
            while (i+bytesValidOneTime) < dataLength:
                #time.sleep(0.001)
                if(not usbMethod.usbHandler.writeToUSB(frameData[i:(i+bytesValidOneTime)]+onesOneTime)):
                    return False
                i += bytesValidOneTime
                frameNum += framesOneTime
                print(frameNum)
            if i < dataLength:
                bytesAppendNum = bytesOneTime - (dataLength-i)
                bytesAppend = 255*(numpy.ones(bytesAppendNum).astype('uint8'))
                usbMethod.usbHandler.writeToUSB(frameData[i:dataLength] + bytes(bytesAppend))
            '''
            usbMethod.usbHandler.writeToUSB(bytes(frameData))
            '''
            timeEnd = time.time()
        except BaseException as e:
            outputInfoMethod.raiseError("Failed to deploy the chip.")
            outputInfoMethod.raiseError(str(e))
            return False
        else:
            outputInfoMethod.raiseInfo("Deployed the chip successfully with %.3f S." % (timeEnd-timeBegin))
            return True

    # *******************************工作帧—write（下行）********************************
    def writeWorkFrameToUSB(self,inputFrameNoList):
        timeBegin = time.time()
        print('Writting')
        logging.info('Input Frames')
        if self.fullInputFrameListReady:
            workFrame = bytes(0)
            #print(inputFrameNoList)
            #print(len(inputFrameNoList))
            
            for no in inputFrameNoList:
                #***********************在fullInputFrame中查找当前输入的输入脉冲数据（类似查找表，以空间换时间，加速工作输入帧的生成）******************************
                workFrame += self.fullInputFrameList[no]
                logging.info(''.join(['%02x' % b for b in self.fullInputFrameList[no]]))
                logging.info(self.originalFullInputFrameList[no])
            workFrame += self.workStartFrame
            bytesOneTime = 24*1024   #每次发送24k字节的数据，最后不足24k的部分以全1补齐
            length = len(workFrame)
            print('workFrame:', workFrame)
            print('length:', length)
            bytesAppend = 255*(numpy.ones(bytesOneTime-length).astype('uint8'))
            usbMethod.usbHandler.writeToUSB(workFrame+bytes(bytesAppend))
            #print(array.array('B',workFrame))
            #print(len(workFrame))
            #print(bytesAppend)
            #print(len(bytesAppend))
            
        else:
            outputInfoMethod.raiseError('FullInputFrameList not ready.')
        timeEnd = time.time()
        print('Write work frames:',timeEnd-timeBegin)

    def frame40bTo64b_rever(self, frame40b):
        r'''把40b的帧数据转换为字节倒序的64b的帧数据。'''
        return frame40b[32:40]+frame40b[24:32]+frame40b[16:24]+frame40b[8:16]+frame40b[0:8]+'000'+frame40b[21:26]+'0000000000000000'

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

    # *******************************工作帧—read(上行)********************************
    def readWorkFrameFromUSB(self,delay=512):
        r'''
        从USB设备读出数据并判断出工作帧，返回工作帧的列表；
        delay参数代表从第一帧有效数据开始，经过delay帧数据之后，我们认为我们需要的有效帧传输完毕了，
        停止继续接受数据；
        其中有效帧的8 byte以FF FF开头，无效帧数据以00 00开头。
        '''
        timeBegin = time.time()
        print('Reading')
        frameDelay = delay
        framesValid = []    #接收到的有效帧的列表；
        bulksToRead = 8     #每次读出512*bulksToRead个bytes；
        framesToRead = 512*bulksToRead/8    #每次读出的数据中包含的帧数，每帧8个bytes；
        frameReaded = 0
        while frameDelay > 0:
            dataIn = usbMethod.usbHandler.readFromUSB(bulksToRead)
            #**************************************************
            #print("datain: ", dataIn)
            cycles = 512*bulksToRead     #一次读出的字节数
            i = 0
            while i < cycles:
                if  dataIn[i] == 0xff and dataIn[i+1] == 0xff:
                    frameReaded += 1
                    if frameReaded == 1:
                        timeEnd = time.time()
                        print('Work frames writen to first frame out:', timeEnd-timeBegin)
                        timeBegin = timeEnd
                    if (i+8) < cycles:
                        framesValid.append(dataIn[i:(i+8)])
                        i += 8
                    else:
                        r'''
                        如果i+8>cycles,说明这个有效帧只有前4个byte在此次读出的数据块里，
                        而后4个byte仍在USB中未读出，这时需要先将前4个byte暂存，然后继续
                        读出数据。
                        '''
                        tempHalfFrame = dataIn[i:(i+4)]
                        dataIn = usbMethod.usbHandler.readFromUSB(bulksToRead)
                        i = 0
                        framesValid.append(tempHalfFrame+dataIn[i:(i+4)])
                        i += 4
                        frameDelay -= framesToRead
                else:
                    i += 4
            if framesValid == []:
                r'''如果还没有读到有效帧，则不开始计数，即frameDelay不减小。'''
                # **************************************************
                #print('!!!未接收到有效帧!!!')
                continue 
            else:
                frameDelay -= framesToRead
        timeEnd = time.time()
        print('Read out work frames:',timeEnd-timeBegin)
        return framesValid

    # ******************************测试帧—write（下行）********************************
    @pyqtSlot(str,str,str,str,str,str)
    def writeTestFrameToUSB(self,frameTitle,chipX,chipY,coreX,coreY,neuron):
        r'''
        生成测试帧，写入USB设备；各参数都是字符串，需要先转为整数，其中frameTitle是二进制，其余是十进制。
        '''
        if frameTitle == '100000':
            frameOutNum = 5
        elif frameTitle == '100100':
            frameOutNum = 160
        elif frameTitle == '101000':
            frameOutNum = 304
        frameTitle = int(frameTitle,2)
        chipX = int(chipX)
        chipY = int(chipY)
        coreX = int(coreX)
        coreY = int(coreY)
        neuron = int(neuron)
        frameData = numpy.zeros(1).astype('uint64')
        frameToWrite = numpy.zeros(8).astype('uint8')
        frameData[0] = (coreY<<40)+(frameTitle<<34)+(chipX<<29)+(chipY<<24)+\
        (coreX<<19)+(coreY<<14)+(neuron<<4)
        frameData.dtype='uint8'
        for i in range(8):
            frameToWrite[i]=frameData[7-i]
        bytesOneTime = 16*1024   #每次发送数据的字节数，以全1补齐
        bytesAppend = 255*(numpy.ones(bytesOneTime-8).astype('uint8'))
        if usbMethod.usbHandler.writeToUSB(bytes(frameToWrite)+bytes(bytesAppend)):
            frameToWrite.dtype = 'uint64'
            logging.info('Test in:'+'{:0>64b}'.format(frameToWrite[0]))
            outputInfoMethod.raiseInfo("Write test frame to chip successfully.")
            #time.sleep(0.01)
            #print(self.readTestFrameFromUSB(frameOutNum))
            for b in self.readTestFrameFromUSB(frameOutNum):
                logging.info('Test out:'+''.join(['{:0>8b}'.format(outByte) for outByte in b]))
        else:
            outputInfoMethod.raiseError('Failed to write test frame.')

    # ******************************测试帧—read（上行）********************************
    def readTestFrameFromUSB(self,frameNum):
        r'''
        从USB设备读出数据并判断出测试帧，返回测试帧的列表；
        frameNum参数代表需要读出的测试帧的数量；
        其中有效帧的8 byte以FF FF开头，无效帧数据以00 00开头。
        '''
        validFrameToRead = frameNum
        framesValid = []    #接收到的有效帧的列表；
        bulksToRead = 2     #每次读出512*bulksToRead个bytes；
        framesToRead = 512*bulksToRead/8    #每次读出的数据中包含的帧数，每帧8个bytes；
        readTimes = 0
        while validFrameToRead > 0:
            dataIn = usbMethod.usbHandler.readFromUSB(bulksToRead)
            #print(readTimes)
            readTimes += 1
            if dataIn == None:
                return framesValid
            bytesNum = 512*bulksToRead     #每次读出的字节数
            i = 0
            while i < bytesNum:
                if  dataIn[i] == 0xff and dataIn[i+1] == 0xff:
                    if (i+8) < bytesNum:
                        framesValid.append(dataIn[i:(i+8)])
                        #print(dataIn[i:(i+8)])
                        i += 8
                    else:
                        r'''
                        如果i+8>cycles,说明这个有效帧只有前4个byte在此次读出的数据块里，
                        而后4个byte仍在USB中未读出，这时需要先将前4个byte暂存，然后继续
                        读出数据。
                        '''
                        tempHalfFrame = dataIn[i:(i+4)]
                        #print(dataIn[i:(i+4)])
                        dataIn = usbMethod.usbHandler.readFromUSB(bulksToRead)
                        #print(readTimes)
                        readTimes += 1
                        i = 0
                        #print(dataIn[i:(i+4)])
                        framesValid.append(tempHalfFrame+dataIn[i:(i+4)])
                        i += 4
                    validFrameToRead -= 1
                else:
                    #print(dataIn[i:(i+4)])
                    i += 4
        return framesValid

frameHandler = FrameHandler()
