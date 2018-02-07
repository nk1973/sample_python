#!/usr/bin/env python
# Burtsev Nikolai
# The program reads data from uart & saves it to logfile

import serial
import signal
import syslog
import os

TIMEOUT_SEC = 4
UART_PATH = '/dev/ttyUSB1'
BAUDRATE = 115200
PANEL_ID_FILE = '/tmp/panel_id'


class UartReader:
    """reads uart data & saves it to system log"""

    def __init__(self, path, baudrate, the_timeout):
        self.__quit = False
        signal.signal(signal.SIGTERM, self.__sig_handler)
        signal.signal(signal.SIGINT, self.__sig_handler)

        self.__uart = serial.Serial(path, baudrate, timeout=the_timeout)
        self.__uart.write('\r\n')
        self.__uart.flush()
        data = self.__uart.readline()

        # if no logging was enabled
        if not data:
            self.__enable_logging()
            self.__uart.write('\r\n')
            self.__uart.flush()
            data = self.__uart.readline()
        panel_id = self.__read_panel_id(self.__is_in_debug_mode(data))

        # create panel id file
        fp = open(PANEL_ID_FILE + '.tmp', 'w')
        fp.write(panel_id)
        fp.close()
        os.rename(PANEL_ID_FILE + '.tmp', PANEL_ID_FILE)

        print('panel id: {}'.format(panel_id))

    def __sig_handler(self, signum, stack_frame):
        if signum == signal.SIGINT or signum == signal.SIGTERM:
            self.__quit = True

    def __is_in_debug_mode(self, data):
        return data.count('DEBUG>') > 0 or data.count(
            'Error: No such command') > 0 or data.count('Enter \'help\'') > 0

    def __enter_debug_mode(self):
        self.__uart.write('`\r\n')
        self.__uart.flush()
        print('entered debug mode')

    def __quit_debug_mode(self):
        self.__uart.write('quit\r\n')
        self.__uart.flush()

    def __enable_logging(self):
        self.__uart.write('quasar\r\n')
        self.__uart.flush()

    def __read_panel_id(self, is_in_debug):
        if not is_in_debug:
            self.__enter_debug_mode()
        self.__uart.write('ip\r\n')
        self.__uart.flush()
        read_panel_id = False
        panel_id = ''
        while not read_panel_id and not self.__quit:
            data = self.__uart.readline()
            if len(data) > 2 and data.count('IP: ') > 0:
                idx = data.find('IP: ')
                space_idx = data.find(' ', idx + 4)
                panel_id = data[idx + 4:space_idx - 1]
                read_panel_id = True
        self.__quit_debug_mode()
        return panel_id

    def run(self):
        while not self.__quit:
            data = self.__uart.readline()
            if self.__is_in_debug_mode(data):
                self.__quit_debug_mode()
            elif len(data) > 2:
                syslog.syslog(syslog.LOG_INFO, data[:-2])
            else:
                syslog.syslog(syslog.LOG_WARNING, '---timeout to read data')
        syslog.syslog(syslog.LOG_INFO, 'uart reader quit.')


if __name__ == "__main__":
    #    logging.basicConfig(
    #        format='%(message)s',
    #        filename=LOGFILE,
    #        level=logging.INFO)
    reader = UartReader(UART_PATH, BAUDRATE, TIMEOUT_SEC)
    reader.run()

# vim: set ts=4 sw=4 et nu:
