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


from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory
import asyncio
from multiprocessing import Process, Queue

class LiveviewServerProtocol(WebSocketServerProtocol):
    
    def __init__(self, endpoint_url):
        print("LiveviewServerProtocol init.")
        self.endpoint_url = endpoint_url
    
    
    def onConnect(self, request):    
        print("Client connecting: {0}".format(request.peer))
        self.queue = Queue()
        self.process = Process(target=liveview_main, args=(self.endpoint_url, self.queue))
        self.process.start()

#     @asyncio.coroutine 
    def onOpen(self):
        while True:
            self.sendMessage("UNCHI".encode('utf-8'), False)
            time.sleep(0.001)
        print("WebSocket connection open.")
        if self.process and self.process.is_alive():
            while True:
                if not self.queue.empty():
                    payload = self.queue.get()
                    print(payload)
                    self.sendMessage(payload)
#                 yield from asyncio.sleep(0.001)
            

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
        if self.process and self.process.is_alive():
            self.process.terminate()
    
    # this is hack that enables dynamic protocol initialization
    def __call__(self):
        return self



def liveview_main(endpoint_url, queue):
    
    rsp = requests.get(endpoint_url, stream=True)
    
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
                    jpeg_name = 'liveview/%s.jpg' % (common_header.sequenceNumber)
                    import os
                    print(os.getcwd())
                    
                    with open(jpeg_name, 'wb') as f:
                        f.write(jpeg_data)
                    interval = common_header.timeStamp - last_time
                    print('wrote: %s, interval: %d ms.' % (jpeg_name, interval))
                    last_time = common_header.timeStamp
            
#                     jpeg_name = jpeg_name.lstrip('remotetrain')
            
                    queue.put(jpeg_name.encode())                    
                    
                    buffer = b''





def run_liveview_server(liveview_url):
    
    # set new event loop because there is no default event loop.
#     asyncio.set_event_loop(asyncio.new_event_loop())
        
    factory = WebSocketServerFactory("ws://localhost:9000",
                                     debug=False)
    
    factory.protocol = LiveviewServerProtocol(liveview_url)
        
    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, '127.0.0.1', 9000)
    server = loop.run_until_complete(coro)
    loop.run_forever()
    server.close()
    loop.close()



if __name__ == '__main__':
    
    import sys
    print(sys.version)
    run_liveview_server('http://192.168.122.1:8080/liveview/liveviewstream')
