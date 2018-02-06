#!/usr/bin/env python

import logging
import json
import signal
import time
import paho.mqtt.client as mqtt

LOGFILE = '/tmp/log'
SEND_LOGS_TRIGGER = '/tmp/syslog_sendmail.now'

"""Read configuration & provice access via member vars"""


class Config:
    def __init__(self, config):
        self.__config = json.load(open(config))
        self.host = self.__config['mqtt_broker']['host']
        self.port = self.__config['mqtt_broker']['port']
        self.user = self.__config['mqtt_broker']['user']
        self.passwd = self.__config['mqtt_broker']['passwd']

    def dump(self):
        print('host:{} port: {} user: {} passwd: {}'.format(
            self.host, self.port, self.user, self.passwd))


"""Mqtt client class"""


class App:
    @staticmethod
    def on_connect(client, userdata, flags, rc):
        instance = userdata
        print(
            'Connection for client {} returned: {}'.format(
                instance.panel_id, rc))
        logging.debug(
            'Connection for client {} returned: {}'.format(
                instance.panel_id, rc))
        return

    def on_disconnect(client, userdata, flags, rc):
        instance = userdata
        print(
            'Connection for client {} returned: {}'.format(
                instance.panel_id, rc))
        logging.debug(
            'Connection for client {} returned: {}'.format(
                instance.panel_id, rc))
        return

    @staticmethod
    def on_message(client, userdata, message):
        instance = userdata
        print('client {} got message of topic{}: payload: {}'.format(
            instance.panel_id, message.topic, message.payload))
        logging.debug(
            'client {} got message of topic{}: payload: {}'.format(
                instance.panel_id,
                message.topic,
                message.payload))
        return

    @staticmethod
    def on_push_log(client, userdata, message):
        instance = userdata
        logging.debug(
            'client {} push_log: payload {}'.format(
                instance.panel_id,
                message.payload))
        trigger = open(SEND_LOGS_TRIGGER, 'w')
        trigger.write('{}'.format(time.time()))
        logging.debug('written: {}'.format(time.time()))
        trigger.close()
        return

    @staticmethod
    def on_open_vpn(client, userdata, message):
        instance = userdata
        logging.debug(
            'client {} open_vpn payload: {}'.format(
                instance.panel_id,
                message.payload))
        # FIXME: open vpn
        return

    @staticmethod
    def on_log(client, userdata, level, buf):
        instance = userdata
        print('client: {}: {}'.format(instance.panel_id, buf))
        logging.debug('client: {}: {}'.format(instance.panel_id, buf))
        return

    def handle(self, signum, frame):
        logging.debug('catched signal: {}'.format(signum))
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.__quit = True

    def __init__(self, panel_id, host, port, user, passwd):
        signal.signal(signal.SIGTERM, self.handle)
        signal.signal(signal.SIGINT, self.handle)

        self.panel_id = panel_id
        self.client = mqtt.Client(
            self.panel_id,
            clean_session=True,
            userdata=self)
        self.client.on_connect = App.on_connect
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
