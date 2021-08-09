#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 09:55
import json
import os
import shutil

DEFAULT_CONFIGS_PATH = os.path.join(os.path.dirname(__file__), 'configs')

USER_HOME_DIR = os.environ['HOME']
CONFIG_PATH = os.path.join(USER_HOME_DIR, '.myvc')
if not os.path.exists(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)
    os.makedirs(os.path.join(CONFIG_PATH, 'conf.d'))
if not os.path.exists(os.path.join(CONFIG_PATH, 'config.json')):
    shutil.copy(
        os.path.join(DEFAULT_CONFIGS_PATH, 'config.json'),
        os.path.join(CONFIG_PATH, 'config.json')
    )
if not os.listdir(os.path.join(CONFIG_PATH, 'conf.d')):
    shutil.copy(
        os.path.join(DEFAULT_CONFIGS_PATH, 'example.cnf'),
        os.path.join(CONFIG_PATH, 'conf.d', 'example.cnf')
    )


CONFIG_PATH = os.path.join(USER_HOME_DIR, '.myvc/config.json')
CONF_D_PATH = os.path.join(USER_HOME_DIR, '.myvc/conf.d')
DATA_PATH = os.path.join(USER_HOME_DIR, '.myvc/data')

with open(CONFIG_PATH, 'rb') as f:
    cfg = json.load(f)
    MYSQL_IMAGE_NAME = cfg['MYSQL_IMAGE_NAME']
    MYSQL_VERSION = cfg['MYSQL_VERSION']
