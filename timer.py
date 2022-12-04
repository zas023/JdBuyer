# -*- coding:utf-8 -*-
import time
from datetime import datetime


class Timer(object):

    def __init__(self, buyTime, sleepInterval=0.5):

        self.buy_time = datetime.strptime(buyTime, "%Y-%m-%d %H:%M:%S")
        self.sleepInterval = sleepInterval

    def start(self):
        now_time = datetime.now
        while True:
            if now_time() >= self.buy_time:
                break
            else:
                time.sleep(self.sleepInterval)
