import cv2
import numpy as np
import pyautogui
import socket
import pickle
import struct
from threading import Thread
from pynput.mouse import Button, Controller
import lzma
from io import BytesIO
from PIL import Image, ImageGrab
import base64


WIDTH = pyautogui.size()[0]
HEIGHT = pyautogui.size()[1]



metrics = [str(WIDTH), str(HEIGHT)]
dislpay = ":".join(metrics).encode('utf-8')
class RemoteDesktop:
    def __init__(self, host, port):
        self.ip = host
        self.port = port
        self.active = False
        self.socket = socket.socket()
        self.LeftMouseup = False
        self.RightMouseup = False
        self.userinput = False
        self.quality = 30

        
    def record(self):
        if not self.userinput:
            ''' BASE64 IS THE MOUSE IMAGE SO WE CAN DISPLAY IT TO THE SERVER. '''
            data = '''iVBORw0KGgoAAAANSUhEUgAAABEAAAAXCAYAAADtNKTnAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAjnRFWHRDb21tZW50AGNIUk0gY2h1bmtsZW4gMzIgaWdub3JlZA1BU0NJSTogLi56JS4uLi4uLi4lLi4uLi4ubV8uLi5sLi48Li4uLlgNSEVYOiAwMDAwN0EyNTAwMDA4MDgzMDAwMEY0MjUwMDAwODREMTAwMDA2RDVGMDAwMEU4NkMwMDAwM0M4QjAwMDAxQjU4GN773QAAAgFJREFUeJyUlEtLAlEUx0cd7YFagUkvxKIgiB4USEREUNAqWgvtatEnaNVnaVWrNrVoEURFT6JCxBDDIpKScGG5EATR2/9MZ6ZrjjJe+MHMmXt+c+65c0cRQihEuVy2lUolO0HXetwKil31valN3SFFUVygFTQDJ7CBhiSHYA45ncAHvI2INMlH+lNAcgRWkDMI+kCbVZEmwYVg0SlYRc7of5EliSS6AGtIHLMqqpBIoiuwblVUJZFE12Yis+03leBbEanUu2VRlYQExWJRFAoF8fzyWlMkL61CIgvy+bzI5XIiHk/UFdH2GxIzQTabFZlMRkQiUTPR3wdJknqCdDqN/qTE7e2dwNwrJM2AEdDFx8SuSWTB01PSEODZjcQ1uGQJVRMAHuDQJLLA1ezL7ezuaRVw4pbb27OEyfNgGkyAIdAN3IZEEnyDDcQepSXEMHEBzIJxEOSD6uGT/7scFnyBMIJziJ3s7x+KZDJJkmOwyRJaRi8LnJqAd+cIyVmwiNthMIVYGEQTiYQ4OzsnUZTk9KyiF3y69aHy3tPWDThcPX1IPCBBLBYjyT1XEuJ+dHBOxaCymvgN7WikG4kB8AC2wTLik9zUfn5hlUQXqQyValNdfjugb8HPDQ3ydavRD31N8rpMBklb+O1eFlDM+OOZ/2RqV+mQK9Dn/wAAAP//AwCGMlcrSCX+UAAAAABJRU5ErkJggg=='''
            imCursor = Image.open(BytesIO(base64.b64decode(data)))
            im=ImageGrab.grab()
            curX,curY=pyautogui.position()
            im.paste(imCursor,box=(curX,curY),mask=imCursor)
            return np.array(im)
        else:
            return np.array(ImageGrab.grab())
    
    def _get_frame(self):
        return self.record()
    
    def recv_msg(self):
        msg = self.socket.recv(1028).decode()
        return msg
    
    def __servermouse(self):
        debug = False
        if not debug:
            while self.active:
                try:
                    data = self.recv_msg().split(":")
                    if data[0] == "mouse":
                        mouse = Controller()
                        xAxis, yAxis, event, flags = int(data[1]), int(data[2]), int(data[3]), int(data[4])
                        # print(xAxis, yAxis)
                        if xAxis < 0 and yAxis < 0:
                            pass
                        else:
                            mouse.position = (xAxis,yAxis)
                            if flags == 1:
                                if self.LeftMouseup:
                                    pass
                                else:
                                    mouse.press(Button.left)
                                    self.LeftMouseup = True
                            elif flags == 0:
                                if self.LeftMouseup:
                                    mouse.release(Button.left)
                                    self.LeftMouseup = False
                                else:
                                    pass
                            elif event == 2:
                                mouse.click(Button.right)
                            elif event == 7:
                                pyautogui.doubleClick(xAxis,yAxis)
                            elif event == 10:
                                if flags > 0:
                                    mouse.scroll(0, -1)
                                else:
                                    mouse.scroll(0, 1)
                    if data[0] == "keyboard":
                        keys = int(data[1])
                        if keys == 13:
                            pyautogui.press("enter")
                        else:
                            pyautogui.press(chr(keys))
                    elif data[0] == "config":
                        self.quality = int(data[1])
                        if data[2] == "0":
                            self.userinput = False
                        else:
                            self.userinput = True
                except:
                    pass
    def __client_streaming(self):
        self.socket.connect((self.ip, self.port))
        self.socket.send(dislpay)
        while self.active:
            frame = self._get_frame()
            _, frame = cv2.imencode('.jpeg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
            data = pickle.dumps(frame, 0)
            video = lzma.compress(data)
            length = len(video)
            #print("Original: {} Compressed: {}".format(len(data), length))
            try:
                self.socket.sendall(struct.pack('>L', length) + video)
            except ConnectionResetError:
                self.active = False
            except ConnectionAbortedError:
                self.active = False
            except BrokenPipeError:
                self.active = False
        cv2.destroyAllWindows()

    def connect(self):
        if self.active:
            print("Client already up and running")
        else:
            self.active = True
            client_thread = Thread(target=self.__client_streaming)
            client_thread.start()
            controller = Thread(target=self.__servermouse)
            controller.start()

            
    def stop_stream(self):
        if self.active:
            self.active = False
        else:
            print("Client is not active!")

class Control(RemoteDesktop):
    def __init__(self, host, port, x_res=1024, y_res=576):
        self.xResolution = x_res
        self.yResolution = y_res
        super(Control, self).__init__(host, port)

if __name__ == '__main__':
    remote = Control('localhost', 443)
    remote.connect()
