#!/usr/bin/env python

import logging
import time
import os
import signal
import argh
import daemon
from daemon import pidfile

WORKDIR = '/tmp'
PIDFILE = '/tmp/myproc.pid'
LOGFILE = WORKDIR + '/mylog'

class App:
    "My simple service"
    def __init__(self, filelogname):
        logging.basicConfig(filename=filelogname, level=logging.DEBUG)
        logging.debug("created app ...")
        signal.signal(signal.SIGTERM, self.handle)
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGUSR2, self.handle)

        logging.debug("installer handler for SIGTERM ...")
        self.__quit = False 

    def handle(self, signum, frame):
        logging.debug('catched signal: %d', signum)
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.__quit = True

    def run(self):
        logging.debug("started to run app " + str(App.__doc__))
        while not self.__quit:
            logging.debug(time.asctime() + ' app running...')
            time.sleep(1)
        logging.debug("finished to run app " + str(App.__doc__))


def start():
    "starts my service"
    print('about to start app')
    with daemon.DaemonContext(working_directory = WORKDIR, pidfile = pidfile.TimeoutPIDLockFile(PIDFILE)):
        # replaces current context with new one running as daemon mode
        app = App(LOGFILE)
        app.run()

def status():
    "print status of my service"
    pid = pidfile.TimeoutPIDLockFile(PIDFILE).read_pid()
    try:
        os.kill(pid, 0)
        print('my service is running with pid %d' % pid)
    except TypeError:
        print('my service is not running')
    except OSError:
        print('my service is not running')

def stop():
    "stops my program service"
    print('stop the app')
    pid = pidfile.TimeoutPIDLockFile(PIDFILE).read_pid()
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        os.kill(pid, signal.SIGKILL)
    except TypeError:
        pass
    except OSError:
        pass
    pidfile.TimeoutPIDLockFile(PIDFILE).break_lock()

    
if __name__ == "__main__" :
    parser = argh.ArghParser()
    parser.add_commands([start, stop, status])
    parser.dispatch()

