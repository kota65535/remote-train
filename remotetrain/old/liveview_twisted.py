# -*- coding: utf-8 -*-

import requests
from construct import Struct, Array, UBInt8, UBInt16, UBInt32
import time

common_header_struct = Struct("CommonHeader",
       UBInt8("startByte"),
       UBInt8("payloadType"),
       UBInt16("sequenceNumber"),
       UBInt32("timeStamp")
)

payload_header_struct = Struct("PayloadHeader",
                        UBInt32("startCode"),
                        UBInt32("payloadDataSize"),
                        Array(4, UBInt8("reserved_1")),
                        UBInt8("flag"),
                        Array(115, UBInt8("reserved_2"))
                        )

# payload_data = Struct("PayloadData",
#                         Array(lambda ctx: ctx.payloadDataSize >> 8, UBInt8("JpegData")),
#                         Array(lambda ctx: ctx.payloadDataSize & 0x000000FF, UBInt8("PaddingData"))
#                         )


from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory

class LiveviewServerProtocol(WebSocketServerProtocol):
        
    def onConnect(self, request):    
        print("Client connecting: {0}".format(request.peer))


    def onDownloaded(self, jpeg_path):
        print("Notify {0} is downloaded to client.".format(jpeg_path))
        self.sendMessage(jpeg_path.encode('utf-8'))
    
    
    def onOpen(self):
        print("WebSocket connection open.")
        LiveviewDownloadingThread(self.factory.endpoint_url, 
                                  self.factory.dst_dir, 
                                  self.onDownloaded).start()
        
        print("Started LiveviewDownloadingThread.")
        
    def onMessage(self, payload, isBinary):
        print("Client: {0}".format(payload))
    
    
    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


class LiveviewServerProtocolFactory(WebSocketServerFactory):
    
    protocol = LiveviewServerProtocol
    
    def __init__(self, endpoint_url, dst_dir, *args, **kwargs):
        self.endpoint_url = endpoint_url
        self.dst_dir = dst_dir
        super().__init__(*args, **kwargs)




import threading
import os

class LiveviewDownloadingThread(threading.Thread):
    def __init__(self, endpoint_url, dst_dir, callback):
        self.endpoint_url = endpoint_url
        self.dst_dir = dst_dir
        self.callback = callback
        super().__init__()

    def run(self):
        self.liveview_main()


    def liveview_main(self):
    
        print("Current dir: {0}".format(os.getcwd()))
    
        rsp = requests.get(self.endpoint_url, stream=True)
        
        buffer = b''
        last_time = 0
        for data in rsp.iter_content(128):
            if not data:
                break
            buffer += data
            payload_start = buffer.find(b'\x24\x35\x68\x79')
            if payload_start >= 0:    
                common_start = payload_start - 8
                if common_start < 0:
                    print('is something wrong?')
                else:
                    common_header = common_header_struct.parse(buffer[common_start:payload_start])
    #                 print(common_header)
                
                bytes_rest = 128 - ( len(buffer) - payload_start )
                payload_header_data = next(rsp.iter_content(bytes_rest))
                if payload_header_data:
                    buffer += payload_header_data
    #                 print('parsing header')
                    payload_header = payload_header_struct.parse(buffer[payload_start:payload_start+128])
                    jpeg_data_size = ( payload_header.payloadDataSize & 0xFFFFFF00 ) >> 8
                    padding_size = payload_header.payloadDataSize & 0x000000FF
    #                 print('start code: 0x%x' % (payload_header.startCode))
    #                 print('jpeg size: %d, padding: %d)' % (jpeg_data_size, padding_size))
                    
                    jpeg_data = next(rsp.iter_content(jpeg_data_size))
                    if jpeg_data:
                        jpeg_name = "{0}/{1}.jpg".format(self.dst_dir, common_header.sequenceNumber)
                        
                        with open(jpeg_name, 'wb') as f:
                            f.write(jpeg_data)
                        interval = common_header.timeStamp - last_time
                        print("Wrote: {0}, interval: {1} ms.".format(jpeg_name, interval))
                        last_time = common_header.timeStamp
                
    #                     jpeg_name = jpeg_name.lstrip('remotetrain')
                        
                        buffer = b''
                        
                        self.callback(jpeg_name)


def run_liveview_server(liveview_url, download_path):
     
    from twisted.python import log
    from twisted.internet import reactor
    import sys
 
    log.startLogging(sys.stdout)
 
    factory = LiveviewServerProtocolFactory(liveview_url, download_path, 
                                            "ws://localhost:9000", debug=True)
    
    reactor.listenTCP(9000, factory)
    reactor.run()
    


if __name__ == '__main__':

#     def callback1(path):
#         print("callback: {0}".format(path))
#     
#     LiveviewDownloadingThread("http://192.168.122.1:8080/liveview/liveviewstream", "liveview", callback1).start()
     
                                  
    run_liveview_server("http://192.168.122.1:8080/liveview/liveviewstream", "liveview")
    
    