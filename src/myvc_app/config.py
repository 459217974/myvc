#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 09:55
import json
import pathlib

DEFAULT_CONFIGS_PATH = pathlib.Path(__file__).parent.joinpath('configs')
USER_HOME_DIR = pathlib.Path.home()
CONFIG_PATH = USER_HOME_DIR.joinpath('.myvc/config.json')
CONF_D_PATH = USER_HOME_DIR.joinpath('.myvc/conf.d')
OLD_DATA_PATH = USER_HOME_DIR.joinpath('.myvc/data')
DB_PATH = USER_HOME_DIR.joinpath('.myvc/myvc.db')

with open(CONFIG_PATH, 'rb') as f:
    cfg = json.load(f)
    MYSQL_IMAGE_NAME = cfg['MYSQL_IMAGE_NAME']
    MYSQL_VERSION = cfg['MYSQL_VERSION']
    DOCKER_CLIENT_BASE_URL = cfg['DOCKER_CLIENT_BASE_URL']
