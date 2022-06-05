#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 09:55
import pathlib

DEFAULT_CONFIGS_PATH = pathlib.Path(__file__).parent.joinpath('configs')
USER_HOME_DIR = pathlib.Path.home()
CONFIG_PATH = USER_HOME_DIR.joinpath('.myvc/config.json')
CONF_D_PATH = USER_HOME_DIR.joinpath('.myvc/conf.d')
OLD_DATA_PATH = USER_HOME_DIR.joinpath('.myvc/data')
DB_PATH = USER_HOME_DIR.joinpath('.myvc/myvc.db')

MYSQL_IMAGE_NAME = None
MYSQL_VERSION = None
DOCKER_CLIENT_BASE_URL = None
