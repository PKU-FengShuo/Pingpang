# import usbMethod
import frameMethod
import usbMethod
import numpy as np
import argparse
# import configFiles.frame40bTo64b as frame40bTo64b

parser=argparse.ArgumentParser()
parser.add_argument("config_netName",help='netName of config frames',type=str)
args=parser.parse_args()

usbStatus = usbMethod.usbHandler.findUSB('','')

# 2 将配置帧和启动帧通过usb传入snn
netName = args.config_netName
frameMethod.frameHandler.writeConfigFrameToUSB(netName)