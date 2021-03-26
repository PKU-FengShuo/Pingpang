from PyQt5.QtCore import QObject, pyqtSignal

'''
信息提示
'''
class OutputInfoHandler(QObject):
    
    r'''
    将需要展示的信息传递给前端显示。
    '''
    raiseToUser = pyqtSignal(str,str,str)
    r'''
    raiseToUser会传递给前端三个string参数，第一个参数是信息类型，有Error，Debug，Waring和Info，
    第二个参数是传递的信息的内容，第三个参数是要显示的信息的字体颜色。
    '''

outputInfoHandler = OutputInfoHandler()

def raiseError(info):
    r'''
    向用户报告错误。
    '''
    outputInfoHandler.raiseToUser.emit("Error: ",info,"red")

def raiseDebug(info):
    r'''
    显示Debug信息。
    '''
    outputInfoHandler.raiseToUser.emit("Debug: ",info,"limegreen")

def raiseWarning(info):
    r'''
    显示Warning信息。
    '''
    outputInfoHandler.raiseToUser.emit("Warning: ",info,"yellow")

def raiseInfo(info):
    r'''
    显示状态信息。
    '''
    outputInfoHandler.raiseToUser.emit("",info,"whitesmoke")
