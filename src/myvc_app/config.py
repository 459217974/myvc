#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/14 09:55
import pathlib

DEBUG = False
USER_HOME_DIR = (
    pathlib.Path(__file__).parent.joinpath('debug_data') if DEBUG
    else pathlib.Path.home()
)
APP_DATA_DIR = USER_HOME_DIR.joinpath('.myvc')
DB_PATH = USER_HOME_DIR.joinpath('.myvc/myvc.db')
DEFAULT_CONFIGS_PATH = pathlib.Path(__file__).parent.joinpath('default_configs')
