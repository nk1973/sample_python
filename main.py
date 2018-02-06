#!/usr/bin/env python

import logging
import time
import os
import signal
import argh
import daemon
import glob
import ftplib
import sys
import json
from daemon import pidfile


class Config:
    """Read configuration & provice access via member vars"""

    def __init__(self, config):
        self.__config = json.load(open(config))
        self.pidfile = self.__config['service']['pidfile']
        self.workdir = self.__config['service']['workdir']
        self.logfile = self.__config['service']['logfile']
        self.pattern = self.__config['service']['pattern']
        self.host = self.__config['ftp']['host']
        self.port = self.__config['ftp']['port']
        self.user = self.__config['ftp']['user']
        self.passwd = self.__config['ftp']['passwd']

    def dump(self):
        print('pidfile = {}'.format(self.pidfile))
        print('workdir = {}'.format(self.workdir))
        print('logfile = {}'.format(self.logfile))
        print('pattern = {}'.format(self.pattern))
        print('host = {}'.format(self.host))
        print('port = {}'.format(self.port))
        print('user = {}'.format(self.user))
        print('passwd = {}'.format(self.passwd))


class FtpClient:
    """Simple ftp client to upload the files"""

    def __init__(self, hostname, port, user, passwd):
        self.__hostname = hostname
        self.__port = port
        self.__user = user
        self.__passwd = passwd

    def upload_file(self, local_filename, remote_filename, is_tls=True):
        try:
            session = ftplib.FTP_TLS()
            session.connect(self.__hostname, self.__port)
            session.login(self.__user, self.__passwd)
            if is_tls:
                session.prot_p()
            with open(local_filename, 'rb') as file:
                session.storbinary('STOR ' + remote_filename, file)
                logging.debug(
                    'uploaded local file {} to {}:{}/{}'.format(
                        local_filename,
                        self.__hostname,
                        self.__port,
                        remote_filename))
            session.quit()
        except Exception as e:
            logging.warning(e)


class App:
    """command listener service for remote"""

    def __init__(self, pattern, logfile, ftpclient):
        logging.basicConfig(filename=logfile, level=logging.DEBUG)
        logging.debug('created app ...')
        signal.signal(signal.SIGTERM, self.handle)
        logging.debug('installer handler for signal: ' + str(signal.SIGTERM))
        signal.signal(signal.SIGINT, self.handle)
        logging.debug('installer handler for signal: ' + str(signal.SIGINT))

        self.__quit = False
        self.__pattern = pattern
        self.__ftp_client = ftpclient
        logging.debug('using pattern \"' + self.__pattern + '\"')

    def handle(self, signum, frame):
        logging.debug('catched signal: {}'.format(signum))
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.__quit = True

    def run(self):
        logging.debug('started to run ' + str(App.__doc__))
        while not self.__quit:
            logging.debug(time.asctime() + ' app running...')
            try:
                files = glob.glob(self.__pattern)
                for filename in files:
                    basename = os.path.basename(filename)
                    logging.debug('basename = {}'.format(basename))
                    self.__ftp_client.upload_file(filename, basename)
                    logging.debug('file : {}'.format(filename))
            except Exception as e:
                print(e)
                raise
            time.sleep(1)
        logging.debug('finished to run ' + str(App.__doc__))


def start():
    """start command listener service"""
    cfg = Config('remote_config.json')
    cfg.dump()
    with daemon.DaemonContext(working_directory=cfg.workdir, pidfile=pidfile.TimeoutPIDLockFile(cfg.pidfile)):
        # replaces current context with new one running as daemon mode
        app = App(
            cfg.pattern,
            cfg.logfile,
            FtpClient(
                cfg.host,
                cfg.port,
                cfg.user,
                cfg.passwd))
        app.run()


def status():
    """get status of command listener service"""
    cfg = Config('remote_config.json')
    cfg.dump()
    pid = pidfile.TimeoutPIDLockFile(cfg.pidfile).read_pid()
    was_error = 0
    try:
        os.kill(pid, 0)
        print('{} is running with pid {}'.format(App.__doc__, pid))
    except TypeError:
        was_error = 1
        print('{} is not running'.format(App.__doc__))
    except OSError:
        was_error = 1
        print('{} is not running'.format(App.__doc__))
    sys.exit(was_error)


def stop():
    """stop command listener service"""
    cfg = Config('remote_config.json')
    pid = pidfile.TimeoutPIDLockFile(cfg.pidfile).read_pid()
    was_error = 0
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        os.kill(pid, signal.SIGKILL)
    except TypeError:
        was_error = 1
        pass
    except OSError as e:
        was_error = 1
        print(e)
        "FIXME: if it errors permission denied we have a problem"
        pass
    pidfile.TimeoutPIDLockFile(cfg.pidfile).break_lock()
    sys.exit(was_error)


if __name__ == "__main__":
    parser = argh.ArghParser()
    parser.add_commands([start, stop, status])
    parser.dispatch()
