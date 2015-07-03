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
        self.sendOneMessage()
        reactor.callLater(1, self.sendOneMessage)
        reactor.callLater(2, self.sendOneMessage)
    
    def sendOneMessage(self):
        self.sendMessage("KUSO".encode('utf8'))

            

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
     


class LiveviewServerProtocolFactory(WebSocketServerFactory):
     
    protocol = LiveviewServerProtocol
     
    def __init__(self, endpoint_url, download_path, *args, **kwargs):
        self.endpoint_url = endpoint_url
        self.download_path = download_path
        super().__init__(*args, **kwargs)

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
    

if __name__ == '__main__':
    
    run_liveview_server("http://192.168.122.1:8080/liveview/liveviewstream", "liveview")