# -*- coding: utf-8 -*-

from construct import Struct, Array, UBInt8, UBInt16, UBInt32

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

import requests
import os, time
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet import defer
from twisted.internet import reactor

class LiveviewServerProtocol(WebSocketServerProtocol):
         
    def onConnect(self, request):    
        print("Client connecting: {0}".format(request.peer))
    
    def onOpen(self):
        print("WebSocket connection open.")
#         from twisted.internet import reactor
#         reactor.callLater(1, self.startLiveviewStreaming)
        self.gen = self.factory.download_liveview()
        self.sendLiveview()
        print("WebSocket connection opena.")
    
    def sendLiveview(self):
        self.sendMessage("BBB".encode('utf-8'))
        reactor.callLater(0.01, self.sendLiveview)
#         d = Deferred(self.factory.download_liveview)
#         
#         def sendOneMessage(path):
#             self.sendMessage(path.encode('utf-8'), False)
#             print("message was sent.")
#             
#         d.addCallback(sendOneMessage)
#         
 
#         reactor.callWhenRunning(self.aaa)
#         reactor.callWhenRunning(self.startLiveviewStreaming)
#         self.aaa()
#         self.startLiveviewStreaming()
#         
#     
#     def aaa(self):
#         for i in range(1, 100):
#             self.sendMessage(str(i).encode('utf-8'), False)
#             time.sleep(1)


    def startLiveviewStreaming(self):
#         self.sendMessage("UNKO".encode(), False)
        for img_path in self.factory.download_liveview():
            print("  Downloaded: '%s'" % (img_path))
            self.sendMessage(img_path.encode('utf-8'), False)
#             self.sendMessage("UNKO".encode(), True)
    
#     def onMessage(self, payload, isBinary):
#         print("onMessage %s" % (payload))
#         for img_path in self.factory.download_liveview():
#             print("  Downloaded: '%s'" % (img_path))
#             self.sendMessage(img_path.encode('utf-8'), isBinary)
#             break

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
     
 
 
class LiveviewServerProtocolFactory(WebSocketServerFactory):
     
    protocol = LiveviewServerProtocol
     
    def __init__(self, endpoint_url, download_path, *args, **kwargs):
        self.endpoint_url = endpoint_url
        self.download_path = download_path
        super().__init__(*args, **kwargs)
    
    def download_liveview(self):
         
        print("Starting download of liveview from '%s'." % (self.endpoint_url))
        print("Download path: '%s'." % (os.path.abspath(self.download_path)))
         
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
                        jpeg_name = '%s/%s.jpg' % (self.download_path, common_header.sequenceNumber)
                         
                        with open(jpeg_name, 'wb') as f:
                            f.write(jpeg_data)
                        interval = common_header.timeStamp - last_time
                        print('wrote: %s, interval: %d ms.' % (jpeg_name, interval))
                        last_time = common_header.timeStamp
                                 
                        yield jpeg_name
 
                        buffer = b''
        
        defer.returnValue(0)
 
 
import sys
 
def run_liveview_server(liveview_url, download_path):
     
    from twisted.python import log
    from twisted.internet import reactor
 
    log.startLogging(sys.stdout)
 
    factory = LiveviewServerProtocolFactory(liveview_url, download_path, 
                                            "ws://localhost:9000", debug=False)
     
    factory.setProtocolOptions(maxConnections=2)
 
    reactor.listenTCP(9000, factory)
    reactor.run()
    

def aa():
    
    for i in range(1, 100):
        yield i

if __name__ == '__main__':
    
    gen = aa()
    print( next(gen) )
    print( next(gen) )
    
    run_liveview_server("http://192.168.122.1:8080/liveview/liveviewstream", "liveview")