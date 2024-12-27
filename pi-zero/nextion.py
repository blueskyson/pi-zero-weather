from dataclasses import dataclass
import sys
import serial


@dataclass
class Command:
    event: int = -1
    page: int = -1
    component: int = -1
    string_data: str = None

    def __str__(self):
        return f"Command(event=\\x{self.event:02x}, page=\\x{self.page:02x}, component=\\x{self.component:02x})"


class Nextion:
    # Picture ID
    PICTURE_BACKGROUND = 0

    # Event Codes
    EVENT_TOUCH = 0x65
    CURRENT_PAGE_NUMBER = 0x66
    STRING_DATA = 0x70

    # Main Page Components
    PAGE_MAIN = 0x00
    B_MENU = 0x02
    B_REFRESH = 0x04

    # Menu Page Components
    PAGE_MENU = 0x01
    T_ID1 = 0x03
    T_ID2 = 0x05
    T_ID3 = 0x07
    T_ID4 = 0x09
    T_ID5 = 0x0b
    T_SSID1 = 0x02
    T_SSID2 = 0x04
    T_SSID3 = 0x06
    T_SSID4 = 0x08
    T_SSID5 = 0x0a
    B_LEFT = 0x0c
    B_RIGHT = 0x0d
    B_CONNECT = 0x0f
    B_UPDATE_LOCATION = 0x13
    B_UNIT_TEMP = 0x11
    B_BACK = 0x01


    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600):
        """
        Initialize the Nextion class for communication.

        :param port: Serial port (e.g., 'COM1' or '/dev/ttyUSB0').
        :param baudrate: Baud rate for communication (default is 9600).
        """
        self.port = port
        self.baudrate = baudrate
        self.buffer = b''
        self.ser = serial.Serial(port, baudrate, timeout = 1)
        if self.ser.is_open:
            print(f"Open {self.ser.name}, Baud: {self.ser.baudrate}.")
        else:
            raise RuntimeError(f"Failed to open {self.ser.name}, Baud: {self.ser.baudrate}.")


    def getCommands(self):
        """
        Reads commands sent from the display.
        """
        if self.ser.in_waiting <= 0:
            return []
        self.buffer += self.ser.read(self.ser.inWaiting())
        rawCommands = self.buffer.split(b'\xFF\xFF\xFF')
        if self.buffer[-3:] == b'\xFF\xFF\xFF':
            self.buffer = b''
        else:
            self.buffer = rawCommands[-1]

        commands = []
        for bytes in rawCommands[:-1]:
            match bytes[0]:
                case self.EVENT_TOUCH:
                    c = Command(event=bytes[0], page=bytes[1], component=bytes[2])
                    print("<=", c)
                    commands.append(c)
                case self.CURRENT_PAGE_NUMBER:
                    c = Command(event=bytes[0], page=bytes[1])
                    print("<=", c)
                    commands.append(c)
                case self.STRING_DATA:
                    c = Command(event=bytes[0], string_data=bytes[1:].decode("iso8859-1"))
                    print("<= string data")
                    commands.append(c)

        return commands


    def send(self, instruction_str, should_log = True):
        self.ser.write(instruction_str.encode('iso-8859-1'))
        if should_log:
            print("=>", instruction_str.replace("\xFF\xFF\xFF", ", "))


    def close(self):
        """
        Close the serial connection.
        """
        if self.ser.is_open:
            self.ser.close()
