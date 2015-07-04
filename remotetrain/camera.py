from remotetrain.liveview import LiveviewServerProccess
from remotetrain.mylogger import getLogger
from remotetrain.ssdp import discover, NoDeviceFoundError
from urllib.error import URLError
import bs4
import json
import re
import requests
import subprocess
import urllib.request
import os
import netifaces

logger = getLogger(__name__)


def check_connection(iface):
    """
    インターフェースの接続先を確認する。
    :param str iface: インターフェース名
    :param str ssid: SSID
    :rtype: str
    :return: 接続済みのAPのSSID。非接続状態なら空文字。
    :raise: SystemError
    """
    
    # for Linux
    try:
        output = subprocess.check_output(['iwconfig', iface], stderr=subprocess.STDOUT).decode('utf-8')
        match_o = re.search(r'^{0}.*ESSID:"(\S+)"'.format(iface), output, re.MULTILINE)
        logger.debug("iwconfig:" + os.linesep + output)
    except Exception as e:
        # for MaxOS
        try:
            output = subprocess.check_output(['networksetup', '-getairportnetwork', iface], stderr=subprocess.STDOUT).decode('utf-8')
            match_o = re.search(r'^Current Wi-Fi Network: (\S+)', output, re.MULTILINE)
            logger.debug("networksetup:" + os.linesep + output)
        except Exception as e:
            # コマンドの実行に失敗。コマンドが無い、存在しないインターフェースを指定した、など。
            raise SystemError("Failed to check connection.")
    
    if match_o:
        return match_o.group(1)
    else:
        return ""

def connect_iface(iface):
    """
    インターフェースを起動して接続する。
    接続先はwpa_supplicantで設定済みとする。
    :param str iface: インターフェース名 
    :rtype: None
    :raise: ConnectionError
    """
    
    logger.debug(("Checking connection of interface '{0}'...".format(iface)))
    try:
        ssid = check_connection(iface)
    except Exception as e:
        raise
    
    if ssid:
        logger.info("'{0}' is already connected to SSID: {1}".format(iface, ssid))
        return ssid
    else:
        # 接続していない場合、インターフェースを再起動してリトライ
        logger.debug("'{0}' is not connected yet. Restarting it...".format(iface))
        try:
            output = subprocess.check_output(['sudo', 'ifdown', iface], stderr=subprocess.STDOUT)
            logger.debug(output.decode('utf-8'))
            output = subprocess.check_output(['sudo', 'ifup', iface], stderr=subprocess.STDOUT)
            logger.debug(output.decode('utf-8'))
        except Exception as e:
            raise
        
        try:
            ssid = check_connection(iface)
        except Exception as e:
            raise
        if ssid:
            logger.info("Connected '{0}' to SSID: {1}".format(iface, ssid))
            return ssid
        else:
            raise ConnectionError("Failed to connect interface {0}".format(iface))

class CameraConnectionError(Exception):
    pass

def discover_sony_camera(iface):
    """
    カメラに接続し、探索して各サービスAPIのURLを取得する。
    接続先はwpa_supplicantで設定済みとする。
    :param str iface: インターフェース名
    :rtype: str and dict
    :return: カメラ機種名、サービスAPI名とURLの辞書
    """
    
    model_name = ""
    service_and_url = {}
    
    try:
        connect_iface(iface)
        responses = discover(iface, "urn:schemas-sony-com:service:ScalarWebAPI:1", timeout=2, retries=8)
        dd_location = responses[0]["LOCATION"]
        logger.debug(dd_location)
        with urllib.request.urlopen(dd_location) as page:
            content = page.read().decode()
    except (ConnectionError, NoDeviceFoundError, URLError) as e:
        logger.error("Failed to connect to camera.")
        raise
    
    logger.debug(content)
    
    try:
        soup = bs4.BeautifulSoup(content, 'xml')
        logger.debug(soup.prettify())
        model_name = soup.find('friendlyName').text
        service_and_url['name'] = model_name
        liveview_url = soup.find('X_ScalarWebAPI_LiveView_URL').text
        service_and_url['liveview'] = liveview_url
        for e in soup.find_all('X_ScalarWebAPI_Service'):
            name = e.find('X_ScalarWebAPI_ServiceType').text
            url = e.find('X_ScalarWebAPI_ActionList_URL').text +'/' + name
            service_and_url[name] = url
    except Exception as e: 
        logger.error("Failed to parse the device descriptor XML.")
        raise
                
    logger.info("Camera is discovered. Model-name: {0}.".format(model_name)) 
    return model_name, service_and_url



class CameraAPI:
    """
    カメラAPアクセスクラス
    """
    json_request = {
        "method": "",
        "params": [],
        "id": 1,
        "version": "1.0"
    }
    
#     liveview_server_address = "192.168.1.18"
    liveview_server_address = "127.0.0.1"
    liveview_server_port = 9000
    
    def __init__(self, iface):
        self.iface = iface
        self.liveview_server_proc = None
        self.is_available = False
    
    def __del__(self):
        logger.info("Destructing camera API...")
        if self.liveview_server_proc:
            self.liveview_server_proc.stop()
        logger.info("Camera API has been destructed.")
        
    def initialize(self):
        logger.info("Initializing camera API...")
        try:
            self.model_name, self.endpoints = discover_sony_camera(self.iface)
            self.is_available = True
            self.start_liveview_server_process()
            self.camera_api('startRecMode', [])
        except Exception as e:
            self.is_available = False
            logger.exception("Camera API is not available now.")
            return None
        
        logger.info("Camera API is ready to use.")
        
    def reinitialize(self):
        self.__del__()
        self.initialize()
    
    
    def camera_api(self, method, params):
        if self.is_available:
            self.json_request['method'] = method
            self.json_request['params'] = params
            try:
                res = requests.post(self.endpoints['camera'], data=json.dumps(self.json_request))
            except Exception as e:
                logger.excepton("No response.")
                return None
            else:
                return json.loads(res.content.decode('utf-8'))
        else:
            logger.error("Camera API is not available. method='{0}, params={1}'".format(method, params))
    
    def avContent_api(self, method, params):
        if self.is_available:
            self.json_request['method'] = method
            self.json_request['params'] = params
            try:
                res = requests.post(self.endpoints['avContent'], data=self.json_request)
            except Exception as e:
                logger.excepton("No response.")
                return None
            else:
                return json.loads(res.content.decode('utf-8'))
        else:
            logger.error("Camera API is not available. method='{0}, params={1}'".format(method, params))
    
    def start_liveview_server_process(self):
        
        try:
            res = self.camera_api('startLiveview', [])
            self.liveview_server_proc = LiveviewServerProccess(res['result'][0], 
                                                               "remotetrain/liveview",
                                                               self.liveview_server_address,
                                                               self.liveview_server_port)
            self.liveview_server_proc.start()
        except Exception as e:
            logger.exception("Failed to start liveview streaming.")
        else:
            logger.info("Liveview server started.")
    

# 
# if __name__ == '__main__':
#     endpoints = discover_sony_camera('en0')
#     print(endpoints)
    

