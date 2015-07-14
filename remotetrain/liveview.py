# -*- coding: utf-8 -*-

from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory
from construct import Struct, Array, UBInt8, UBInt16, UBInt32
import asyncio
import logging
import multiprocessing
import os
import requests
import threading
import time

logger = logging.getLogger(__name__)


# コモンヘッダの構造
common_header_struct = Struct("CommonHeader",
       UBInt8("startByte"),
       UBInt8("payloadType"),
       UBInt16("sequenceNumber"),
       UBInt32("timeStamp")
)

# ペイロードヘッダの構造
payload_header_struct = Struct("PayloadHeader",
                        UBInt32("startCode"),
                        UBInt32("payloadDataSize"),
                        Array(4, UBInt8("reserved_1")),
                        UBInt8("flag"),
                        Array(115, UBInt8("reserved_2"))
                        )

# ペイロードデータの構造（不使用）
# payload_data = Struct("PayloadData",
#                         Array(lambda ctx: ctx.payloadDataSize >> 8, UBInt8("JpegData")),
#                         Array(lambda ctx: ctx.payloadDataSize & 0x000000FF, UBInt8("PaddingData"))
#                         )



class LiveviewServerProtocol(WebSocketServerProtocol):
    """
    ライブビューWebSocketサーバーのプロトコルクラス
    """
        
    def onConnect(self, request):    
        logger.info("Client connecting: {0}".format(request.peer))


    def onOpen(self):
        logger.info("WebSocket connection open.")
        self.liveview_thread = LiveviewDownloadingThread(self.factory.endpoint_url, 
                                                         self.factory.dst_dir, 
                                                         self.onDownload)
        self.liveview_thread.start()
        logger.info("Started LiveviewDownloadingThread.")


    def onDownload(self, jpeg_path):
        logger.debug("Notify '{0}' to client.".format(jpeg_path))
        
        self.sendMessage(jpeg_path.encode('utf-8'))
    
        
    def onMessage(self, payload, isBinary):
        logger.info("Client say: {0}".format(payload))
    
    
    def onClose(self, wasClean, code, reason):
        logger.info("WebSocket connection closed: {0}".format(reason))
        self.liveview_thread.stop()


class LiveviewServerFactory(WebSocketServerFactory):
    """
    ライブビューWebSocketサーバーのファクトリクラス
    """
    
    protocol = LiveviewServerProtocol
    
    def __init__(self, endpoint_url, dst_dir, *args, **kwargs):
        self.endpoint_url = endpoint_url
        self.dst_dir = dst_dir
        super().__init__(*args, **kwargs)





class LiveviewDownloadingThread(threading.Thread):
    """
    ライブビューをダウンロードするスレッドクラス
    """
    def __init__(self, endpoint_url, dst_dir, callback):
        """
        :param str endpoint_url: ライブビューのURL
        :param str dst_dir: ダウンロード先のディレクトリパス
        :param func callback: ライブビュー画像のダウンロードが完了した際に呼ばれるコールバック関数
        """
        
        self.endpoint_url = endpoint_url
        self.dst_dir = dst_dir
        self.callback = callback
        self.stop_event = threading.Event()
        
        super().__init__()

    
    def run(self):
        logger.info("Starting liveview downloading thread.")
        try:
            self.liveview_main()
        except Exception:
            logger.exception("Failed to start downloading liveview.")
            return
        logger.info("Liveview downloading thread finished.")
    
    def stop(self):
        self.stop_event.set()
        
    
    def liveview_main(self):
        """
        ライブビュー画像ダウンロードのメインループ関数
        """
    
        logger.info("Current dir: {0}".format(os.getcwd()))
        
        
        try:
            # GETリクエストを送り、ストリームとしてレスポンスを順次読み込んでいく
            rsp = requests.get(self.endpoint_url, stream=True)
        except Exception as e:
            logger.error("GET Request to '{0}' failed.".format(self.endpoint_url))
            raise
        
        buffer = b''
        last_time = 0
        count = 10
        try:
            # 128バイトずつ読み込む
            for data in rsp.iter_content(128):
                if self.stop_event.is_set():
                    logger.info("Received Stop event.")
                    break
                if not data:
                    break
                buffer += data
                # ペイロードヘッダの開始コードを探す
                payload_start = buffer.find(b'\x24\x35\x68\x79')
                if payload_start >= 0:
                    if count > 0:
                        count -= 1
                        continue
                    else:
                        count = 10
                    common_start = payload_start - 8
                    if common_start < 0:
                        logger.error('Something wrong occured!')
                    else:
                        common_header = common_header_struct.parse(buffer[common_start:payload_start])
                        
                        logger.debug(common_header)
                    
                    # ペイロードヘッダの残りを読み込む
                    bytes_rest = 128 - ( len(buffer) - payload_start )
                    if bytes_rest > 0:
                        payload_header_data = next(rsp.iter_content(bytes_rest))
                        if payload_header_data:
                            buffer += payload_header_data
                    # ペイロードヘッダをパースし、ペイロードデータ(jpeg)のサイズを調べる
#                     logger.debug('Parsing payload header...')
                    payload_header = payload_header_struct.parse(buffer[payload_start:payload_start+128])
                    jpeg_data_size = ( payload_header.payloadDataSize & 0xFFFFFF00 ) >> 8
                    padding_size = payload_header.payloadDataSize & 0x000000FF
#                     logger.debug('start code: 0x%x' % (payload_header.startCode))
#                     logger.debug('jpeg size: %d, padding: %d)' % (jpeg_data_size, padding_size))
                    # ペイロードデータを読み込む
                    jpeg_data = next(rsp.iter_content(jpeg_data_size))
                    if jpeg_data:
                        # jpegのファイル名はコモンヘッダのシーケンス番号を使用する
                        jpeg_name = "{0}/{1}.jpg".format(self.dst_dir, common_header.sequenceNumber)
                        write_start = time.time()
                        try:
                            with open(jpeg_name, 'wb') as f:
                                f.write(jpeg_data)
                        except IOError as e:
                            logger.exception("Failed to open file '{0}'.".format(jpeg_name))
                            raise
                        write_interval = time.time() - write_start
                        # 1つ前のペイロードとの時間間隔
                        payload_interval = common_header.timeStamp - last_time
                        logger.debug("Got liveview image '{0}', write-time={1:.1f} ms, interval: {2} ms.".format(jpeg_name, write_interval*1000, payload_interval))
                        last_time = common_header.timeStamp
                        # バッファをリセット
                        buffer = b''
                        # コールバック
                        self.callback(jpeg_name.lstrip("remotetrain/"))
        
        except Exception as e:
            logger.error("Error occurred during downloading liveview images.")
            raise
        
        logger.info("Liveview downloading finished.")
    
    


class LiveviewServerProccess(multiprocessing.Process):
    """
    ライブビュー画像をダウンロードし、ブラウザに通知するWebSocketサーバークラス
    """
    def __init__(self, liveview_url, download_path, address, port):
        """
        :param str endpoint_url: ライブビューのURL
        :param str dst_dir: ライブビュー画像のダウンロード先ディレクトリパス
        :param func callback: ライブビュー画像のダウンロードが完了した際に呼ばれるコールバック関数
        """
        self.liveview_url = liveview_url
        self.download_path = download_path
        self.address = address
        self.port = port
        self.loop = None
        self.server = None
        super().__init__()

    def run(self):
        logger.info("Starting liveview server on 'ws://{0}:{1}'...".format(self.address, self.port))
        try:
            self.run_liveview_server()
        except Exception:
            logger.exception("Failed to start liveview server.")
            return
        logger.info("Liveview server finished.")
    
    def stop(self):
        logger.info("Stopping...")
        if self.server:
            self.server.close()
        if self.loop:
            logger.info("Stopping liveview server...")
            self.loop.stop()
            self.server.close()
            self.loop.close()
            logger.info("Liveview server stopped.")


    def run_liveview_server(self):
        """
        ライブビューサーバーを開始する
        """
        
        # サブプロセスを立ち上げるとデフォルトイベントループが未設定なので、新しく作って設定する
        asyncio.set_event_loop(asyncio.new_event_loop())
        
        factory = LiveviewServerFactory(self.liveview_url, 
                                        self.download_path,
                                        "ws://{0}:{1}".format(self.address, self.port), 
                                        debug=False)
        
        self.loop = asyncio.get_event_loop()
        coro = self.loop.create_server(factory, self.address, self.port)
        self.server = self.loop.run_until_complete(coro)
        logger.info("Liveview server is now serving.")
        self.loop.run_forever()
        self.server.close()
        self.loop.close()
    


if __name__ == '__main__':

#     def callback1(path):
#         print("callback: {0}".format(path))
#     
#     LiveviewDownloadingThread("http://192.168.122.1:8080/liveview/liveviewstream", "liveview", callback1).start()
    
    p = LiveviewServerProccess("http://192.168.122.1:8080/liveview/liveviewstream", "liveview")
    p.start()                          
    
    
    
