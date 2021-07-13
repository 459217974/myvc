#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 13:04
import datetime
import socket
import time


def get_id():
    return hex(int(time.time() * 1000000))[6:]


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def get_current_datetime_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
