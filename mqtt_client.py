#!/usr/bin/env python

import logging
import json
import signal
import time
import paho.mqtt.client as mqtt

LOGFILE = '/tmp/log'
SEND_LOGS_TRIGGER = '/tmp/syslog_sendmail.now'


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
        signal.signal(signal.SIGTERM, self.handle)
        signal.signal(signal.SIGINT, self.handle)

        self.panel_id = panel_id
        self.client = mqtt.Client(
            self.panel_id,
            clean_session=True,
            userdata=self)
        self.client.on_connect = App.on_connect
        self.client.on_disconnect = App.on_disconnect
        self.client.on_message = App.on_message
        self.client.on_log = App.on_log
        self.client.message_callback_add(
            'to_panel/' +
            self.panel_id +
            '/cmds/push_log',
            App.on_push_log)
        self.client.message_callback_add(
            'to_panel/' +
            self.panel_id +
            '/cmds/open_vpn',
            App.on_open_vpn)
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
        return

    @staticmethod
    def on_connect(client, app, flags, rc):
        logging.debug('client:{} connected: {}'.format(app.panel_id, rc))
        return

    @staticmethod
    def on_disconnect(client, app, flags, rc):
        logging.debug('client:{} disconnect: {}'.format(app.panel_id, rc))
        return

    @staticmethod
    def on_message(client, app, msg):
        logging.debug(
            'client:{} got msg of topic{}: payload: {}'.format(
                app.panel_id,
                msg.topic,
                msg.payload))
        return

    @staticmethod
    def on_push_log(client, app, msg):
        logging.debug('client:{} push_log: payload {}'.format(
            app.panel_id,
            msg.payload))
        # NOTE: we can use json data to define different log server settings
        # like host, port, encrypted, user, passwd. But now all this
        # is hardcoded
        trigger = open(SEND_LOGS_TRIGGER, 'w')
        trigger.write('{}'.format(time.time()))
        logging.debug('written: {}'.format(time.time()))
        trigger.close()
        return

    @staticmethod
    def on_open_vpn(client, app, msg):
        logging.debug(
            'client:{} open_vpn payload: {}'.format(
                app.panel_id,
                msg.payload))
        # FIXME: open vpn
        return

    @staticmethod
    def on_log(client, app, level, buf):
        logging.debug('client: {}: {}'.format(app.panel_id, buf))
        return

    def handle(self, signum, frame):
        logging.debug('catched signal: {}'.format(signum))
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.__quit = True

    def stop(self):
        self.__quit = True
        return

    def run(self):
        while not self.__quit:
            ret = self.client.loop()
            if ret != mqtt.MQTT_ERR_SUCCESS and not self.__quit:
                self.client.reconnect()
                logging.warning('reconnecting')
        logging.debug('{} quit'.format(self.panel_id))
        return


if __name__ == "__main__":
    # FIXME: read panel id from filesystem
    panel_id = '12345'
    logging.basicConfig(
        format='%(asctime)s:%(message)s',
        filename=LOGFILE,
        level=logging.DEBUG)
    cfg = Config('remote_config.json')
    cfg.dump()
    app = App(panel_id, cfg.host, cfg.port, cfg.user, cfg.passwd)
    app.run()

# vim: set ts=4 sw=4 et nu:
