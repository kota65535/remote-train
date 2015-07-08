import serial
import logging

logger = logging.getLogger(__name__)


class Commander:
    def __init__(self, device_name, baud_rate):
        self.device_name = device_name
        self.baud_rate = baud_rate
        self.ser = None
        
    def __del__(self):
        if self.ser:
            self.ser.close()
    
    def initialize(self):
        try:
            self.ser = serial.Serial(self.device_name, self.baud_rate)
        except Exception as e:
            logger.exception("Failed to connect to serial port '{0}'.".format(self.device_name))
            self.is_available = False
        else:
            logger.info("Connected to serial port '{0}'.".format(self.device_name))
            self.is_available = True
            
    def reinitialize(self):
        self.__del__()
        self.initialize()
        
    def send_command(self, name, value):
        """
        シリアルデバイスにコマンドを送信する
        """
        
        if self.is_available:
            string = self._build_command(name, value)
            self._send_string(string)
        else:
            logger.error("Serial port '{0}' is not available.".format(self.device_name))
    
    
    def _build_command(self, name, value):
        """
        シリアルデバイスに送信するコマンド文字列の構築
        """
        command_str = ""
        attr, id = name.split("_")
        
        if (attr == "speed"):
            command_str = "p {0} c {1}".format(id, value)
        elif (attr == "direction"):
            command_str = "p {0} d {1}".format(id, value)
        elif (attr == "feeder"):
            command_str = "f {0} {1}".format(id, value)
        elif (attr == "turnout"):
            command_str = "t {0} {1}".format(id, value)
                
        return command_str


    def _send_string(self, string, strip_echo=True, strip_cr=True):
        """
        コマンドを送信し、次のプロンプト(#)の表示までの出力を得る
        """
        
        self.ser.write(bytearray(string + '\r\n', 'ascii'))
        
        ret_str = '' 
        while (True):
            ret_str += str(self.ser.read(), 'ascii')
            if ret_str.endswith('\r\n#'):
                break
        
        ret_str = ret_str.rstrip('#')
        if strip_echo:
            ret_str = ret_str.lstrip('# ' + string + '\r\n')
        if strip_cr:
            ret_str = ret_str.replace('\r', '')

        return ret_str
