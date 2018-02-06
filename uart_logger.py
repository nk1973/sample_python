#!/usr/bin/env python
# Burtsev Nikolai
# The program reads data from uart & saves it to logfile


import serial
import logging

LOGFILE = '/tmp/log'
TIMEOUT_SEC = 5
UART_PATH = '/dev/ttyUSB1'
BAUDRATE = 115200

"""reads uart data & saves it to system log"""
class UartReader:
    def __is_in_debug_mode(self, data):
        return data.count('DEBUG>') > 0 or data.count('Error: No such command') > 0 or data.count('Enter \'help\'') > 0 

    def __quit_debug_mode(self):
        self.__uart.write('quit\r\n')
        self.__uart.flush()
        return

    def __enable_logging(self):
        self.__uart.write('quasar\r\n')
        self.__uart.flush()
        return

    """Constructor
        path - path of the uart to open
        baudrate - baudrate to open the uart
        the_timeout - timeout in seconds to wait for data in read methods
    """
    def __init__(self, path, baudrate, the_timeout):
        self.__uart = serial.Serial(path, baudrate, timeout = the_timeout)
        self.__uart.write('\r\n')
        self.__uart.flush()
        data = self.__uart.readline()
        print('read len: {} '.format(len(data)))
        if self.__is_in_debug_mode(data):
            self.__quit_debug_mode()
        elif len(data) > 2:
            logging.info(data[:-2])
        else:
            got_data = False
            for i in range(10):
                self.__enable_logging()
                data = self.__uart.readline()
                if (len(data) > 2): # \r\n
                    logging.info(data[:-2])
                    got_data = True
                else:
                    logging.warning('----------------------- panel doesnt respond to quasar string')
            if not got_data:
                raise RuntimeError('didn\'t succeed to read log data from {}'.format(path)) 

        return


    def run(self):
        while True:
            data = self.__uart.readline()
            if self.__is_in_debug_mode(data):
                self.__quit_debug_mode()
            elif len(data) > 2:
                logging.info(data[:-2])
            else:
                logging.warning('----------------------- timeout to read data from uart')
        return

if __name__ == "__main__" :
    logging.basicConfig(format='%(message)s',filename=LOGFILE, level=logging.INFO)
    reader = UartReader(UART_PATH, BAUDRATE, TIMEOUT_SEC)
    reader.run()

# vim: set ts=4 sw=4 et nu:
