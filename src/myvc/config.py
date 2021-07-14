#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 09:55
import json
import os

DEFAULT_CONFIGS_PATH = os.path.join(os.path.dirname(__file__), 'configs')

DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIGS_PATH, 'config.json')
DEFAULT_CONF_D_PATH = os.path.join(DEFAULT_CONFIGS_PATH, 'conf.d')
DEFAULT_DATA_PATH = os.path.join(DEFAULT_CONFIGS_PATH, 'data')

USER_HOME_DIR = os.environ['HOME']

CONFIG_PATH = os.path.join(USER_HOME_DIR, '.myvc/config.json')
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = DEFAULT_CONFIG_PATH

CONF_D_PATH = os.path.join(USER_HOME_DIR, '.myvc/conf.d')
if not os.path.exists(CONF_D_PATH):
    CONF_D_PATH = DEFAULT_CONF_D_PATH

DATA_PATH = os.path.join(USER_HOME_DIR, '.myvc/data')
if not os.path.exists(DATA_PATH):
    DATA_PATH = DEFAULT_DATA_PATH

with open(CONFIG_PATH, 'rb') as f:
    cfg = json.load(f)
    MYSQL_IMAGE_NAME = cfg['MYSQL_IMAGE_NAME']
    MYSQL_VERSION = cfg['MYSQL_VERSION']
