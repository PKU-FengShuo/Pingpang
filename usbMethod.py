import usb
from PyQt5.QtCore import pyqtSlot, QObject
import outputInfoMethod
import time

'''
***********************USB(find/write/read)***********************
目前主要數據傳輸方式
'''
class USBHandler(QObject):

    device = []
    deviceW = None
    deviceR = None
    inPoint = None
    outPoint = None
    usbReady = False

    #******************************** USB-find（仅找到目标设备）**********************************
    @pyqtSlot(str,str,result=bool)
    def findUSB(self,VID,PID):
        r'''
        连接指定VID/PID的USB设备。
        '''
        if not self.usbReady:
            #查找usb設備
            #self.device = list(usb.core.find(find_all=True))                                     #windows
            self.device = list(usb.core.find(idVendor=0x04B4, idProduct=0x00F1, find_all=True))   #linux
            usbDeviceNum = len(self.device)
            #print(usbDeviceNum)
            
            if usbDeviceNum == 0:
                self.usbReady = False
                outputInfoMethod.raiseError("Can not find the USB device!")
            
            #一块FPGA（下行+上行）
            elif usbDeviceNum == 1:
                self.deviceW = usb.core.find()
                self.deviceW.set_configuration()
                cfgW = self.deviceW.get_active_configuration()
                intfW = cfgW[(0,0)]
                self.outPoint = usb.util.find_descriptor(intfW,
                    # match the first OUT endpoint
                    custom_match = lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_OUT)
                self.inPoint = usb.util.find_descriptor(intfW,
                    # match the first IN endpoint
                    custom_match = lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)
                self.usbReady = True
                outputInfoMethod.raiseInfo("USB device-out is ready.")
            
            #两块FPGA（一块上行、一块下行）
            elif usbDeviceNum == 2:
                self.deviceW = self.device[0]#w_下行
                self.deviceR = self.device[1]#e_上行

                self.deviceW.set_configuration()
                cfgW = self.deviceW.get_active_configuration()
                intfW = cfgW[(0,0)]
        
                self.deviceR.set_configuration()
                cfgR = self.deviceR.get_active_configuration()
                intfR = cfgR[(0,0)]

                self.outPoint = usb.util.find_descriptor(intfW,
                    # match the first OUT endpoint
                    custom_match = lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_OUT)
            
                self.inPoint = usb.util.find_descriptor(intfR,
                    # match the first IN endpoint
                    custom_match = lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

                self.usbReady = True
                outputInfoMethod.raiseInfo("USB devices are ready.")
            else:
                self.usbReady = False
                outputInfoMethod.raiseError("!!!There are more than 2 usb devices!!!")
            return self.usbReady
        else:
            return self.usbReady

    #********************************** USB-write ************************************
    def writeToUSB(self,data):
        r"""Write data to usbDevice.
        The data parameter should be a sequence like type convertible to
        the array type (see array module).
        """
        if self.usbReady:
            try:
                #print('!!!usb write data!!!')
                self.deviceW.write(self.outPoint.bEndpointAddress, data)
            except BaseException as e:
                outputInfoMethod.raiseError("Failed to write to USB.")
                outputInfoMethod.raiseError(str(e))
                return False
            else:
                return True
        else:
            outputInfoMethod.raiseError("USB device is not ready.")
            return False

    # ********************************** USB-read ************************************
    def readFromUSB(self,bulksNum=1):
        r"""Read data from usbDevice.
        The bulksNum parameter should be the amount of bulks to be readed.
        One bulk is wMaxPacketSize(512) bytes.
        The method returns the data readed as an array. If read nothing, return None.
        """
        if self.usbReady:
            try:
                #tempData = self.inPoint.read(self.inPoint.wMaxPacketSize*bulksNum)
                tempData = self.deviceR.read(self.inPoint.bEndpointAddress,self.inPoint.wMaxPacketSize*bulksNum)
                return tempData
            except BaseException as e:
                outputInfoMethod.raiseError("Failed to read from USB.")
                outputInfoMethod.raiseError(str(e))
                return None
        else:
            outputInfoMethod.raiseError("USB device is not ready.")
            return None

usbHandler = USBHandler()
