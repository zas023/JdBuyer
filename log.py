#!/usr/bin/env python
# -*- encoding=utf8 -*-
import logging
import logging.handlers
import os
from time import strftime

LOG_FILENAME = strftime("logs\jd-buyer_%Y_%m_%d_%H.log")

logger = logging.getLogger()


def set_logger():
    path = os.path.dirname(os.getcwd()+ '\\logs\\') # 判断日志目录
    if not os.path.exists(path):
        os.makedirs(path)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=10485760, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


set_logger()
