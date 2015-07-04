import socket
import http.client
import io
from remotetrain.mylogger import getLogger

logger = getLogger(__name__)

class NoDeviceFoundError(Exception):
    pass

class SSDPResponse(object):
    """
    SSDPレスポンスクラス
    """
    class _FakeSocket(io.BytesIO):
        def makefile(self, *args, **kw):
            return self
    def __init__(self, response):
        # ヘッダ構造がHTTPレスポンスと類似しているので利用する
        r = http.client.HTTPResponse(self._FakeSocket(response))
        r.begin()
#         print(r.getheaders())
        self.headers = dict(r.getheaders())
    def __repr__(self):
        return "<SSDPResponse({LOCATION}, {ST}, {USN})>".format(**self.headers)

def discover(service, timeout=2, retries=10):
    """
    SSDP Discoverを実行する
    :param str service: Service Target
    :param int timeout: タイムアウト（秒）
    :param int retries: 最大リトライ回数
    :rtype: list
    :return: SSDPレスポンスヘッダ(辞書)のリスト
    :raise: URLError
    """
    
    logger.info("SSDP discovery. Search target: {0}".format(service))
    
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: {0}:{1}',
        'MAN: "ssdp:discover"',
        'ST: {st}',
        'MX: 3',
        '',''])
    socket.setdefaulttimeout(timeout)
    responses = []
    for i in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(message.format(*group, st=service).encode(), group)
        while True:
            logger.debug('SSDP discover try {0}.'.format(i+1))
            try:
                res = SSDPResponse(sock.recv(1024))
                responses.append(res.headers)
                logger.debug(responses)
            except socket.timeout:
                break
        if len(responses) > 0:
            break
    else:
        raise NoDeviceFoundError("Device not found.")
    
    return responses
    