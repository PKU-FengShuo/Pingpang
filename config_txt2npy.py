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

# 1 从txt读取出配置帧、启动帧、工作帧，并转成64bit倒序的形式
filePath = './configFiles/Pingpang3Config.txt'
netName = 'Pingpang'
# netName = 'lpr'
# .txt ——> .npy(转换，将配置帧文件.txt，40bits——>64bits,并倒序，然后保存为{netName}.npy)
frameMethod.frameHandler.readFromConfigFile(filePath, netName) #生成netName.npy的配置帧文件