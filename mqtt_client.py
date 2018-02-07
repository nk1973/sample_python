#!/usr/bin/env python

import syslog
import logging.handlers
import json
import signal
import time
import os
import paho.mqtt.client as mqtt

SEND_LOGS_TRIGGER = '/tmp/syslog_sendmail.now'
PANEL_ID_FILE = '/tmp/panel_id'
RETRIES_TO_WAIT_FOR_PANEL_ID_FILE = 30


class Config:
    """Read application configuration & provide access via member vars"""

    def __init__(self, config):
        self.__config = json.load(open(config))
        self.host = self.__config['mqtt_broker']['host']
        self.port = self.__config['mqtt_broker']['port']
        self.user = self.__config['mqtt_broker']['user']
        self.passwd = self.__config['mqtt_broker']['passwd']

    def dump(self):
        print('host:{} port: {} user: {} passwd: {}'.format(
            self.host, self.port, self.user, self.passwd))


class App:
    """Mqtt client class"""

    def __init__(self, panel_id, host, port, user, passwd):
        signal.signal(signal.SIGTERM, self.__sig_handle)
        signal.signal(signal.SIGINT, self.__sig_handle)

        self.panel_id = panel_id
        self.client = mqtt.Client(
            self.panel_id,
            clean_session=True,
            userdata=self)
        self.client.on_connect = App.__on_connect
        self.client.on_disconnect = App.__on_disconnect
        self.client.on_message = App.__on_message
        self.client.on_log = App.__on_log
        self.client.message_callback_add(
            'to_panel/' +
            self.panel_id +
            '/cmds/push_log',
            App.__on_push_log)
        self.client.message_callback_add(
            'to_panel/' +
            self.panel_id +
            '/cmds/open_vpn',
            App.__on_open_vpn)
        self.client.username_pw_set(user, passwd)

        # the will message will be published on disceonnect from the broker
        self.client.will_set(
            topic='from_panel/' +
            self.panel_id +
            '/status',
            payload='offline',
            retain=True)

        self.client.connect(host, port)
        self.client.subscribe('to_panel/' + self.panel_id + '/#')

        # publish we online
        self.client.publish(
            topic='from_panel/' +
            self.panel_id +
            '/status',
            payload='online',
            retain=True)
        self.__quit = False

    @staticmethod
    def __on_connect(client, app, flags, rc):
        syslog.syslog(
            syslog.LOG_DEBUG,
            'client:{} connected: {}'.format(
                app.panel_id,
                rc))

    @staticmethod
    def __on_disconnect(client, app, flags, rc):
        syslog.syslog(
            syslog.LOG_DEBUG,
            'client:{} disconnect: {}'.format(
                app.panel_id,
                rc))

    @staticmethod
    def __on_message(client, app, msg):
        syslog.syslog(syslog.LOG_DEBUG,
                      'client:{} got msg of topic{}: payload: {}'.format(
                          app.panel_id,
                          msg.topic,
                          msg.payload))

    @staticmethod
    def __on_push_log(client, app, msg):
        syslog.syslog(
            syslog.LOG_DEBUG,
            'client:{} push_log: payload {}'.format(
                app.panel_id,
                msg.payload))
        # NOTE: we can use json data to define different log server settings
        # like host, port, encrypted, user, passwd. But now all this
        # is hardcoded
        trigger = open(SEND_LOGS_TRIGGER, 'w')
        trigger.write('{}'.format(time.time()))
        syslog.syslog(syslog.LOG_DEBUG, 'written: {}'.format(time.time()))
        trigger.close()

    @staticmethod
    def __on_open_vpn(client, app, msg):
        syslog.syslog(syslog.LOG_DEBUG,
                      'client:{} open_vpn payload: {}'.format(
                          app.panel_id,
                          msg.payload))
        # FIXME: open vpn

    @staticmethod
    def __on_log(client, app, level, buf):
        syslog.syslog(
            syslog.LOG_DEBUG,
            'client: {}: {}'.format(
                app.panel_id,
                buf))

    def __sig_handle(self, signum, frame):
        syslog.syslog(syslog.LOG_DEBUG, 'catched signal: {}'.format(signum))
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.stop()

    def stop(self):
        self.__quit = True

    def run(self):
        while not self.__quit:
            ret = self.client.loop()
            if ret != mqtt.MQTT_ERR_SUCCESS and not self.__quit:
                self.client.reconnect()
                syslog.syslog(syslog.WARNING, 'reconnecting')
        syslog.syslog(syslog.LOG_DEBUG, '{} quit'.format(self.panel_id))


if __name__ == "__main__":
    for i in range(RETRIES_TO_WAIT_FOR_PANEL_ID_FILE):
        if not os.access(PANEL_ID_FILE, os.R_OK):
            syslog.syslog(
                syslog.WARNING,
                'no panel id file {} exist for reading, waiting'.format(PANEL_ID_FILE))
            time.sleep(1)
        else:
            break

    # let throw exception in case no panel id file - watchdod will restart uo
    fp = open(PANEL_ID_FILE, 'r')
    panel_id = fp.read()
    syslog.syslog(syslog.LOG_INFO, 'using panel id {}'.format(panel_id))

    cfg = Config('remote_config.json')
    cfg.dump()
    app = App(panel_id, cfg.host, cfg.port, cfg.user, cfg.passwd)
    app.run()

# vim: set ts=4 sw=4 et nu:
