#!/usr/bin/env python
# -*- encoding=utf8 -*-
from log import logger


class JDException(Exception):

    def __init__(self, message):
        super().__init__(message)
        logger.error(message)
