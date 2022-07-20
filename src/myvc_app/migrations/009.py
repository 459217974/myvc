#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/8 23:04
import os.path
from datetime import datetime
import json
import pathlib
from peewee import SqliteDatabase
from myvc_app.models import models


def run(db: SqliteDatabase):
    db.create_tables([models.Config, models.MySQLConf])
    from myvc_app import config
    config_path = config.APP_DATA_DIR.joinpath('config.json')
    if not os.path.exists(config_path):
        config_path = config.DEFAULT_CONFIGS_PATH.joinpath('config.json')
    with open(config_path, 'rb') as f:
        cfg = json.load(f)
        for k, v in cfg.items():
            models.Config(
                key=k,
                value=v,
                create_at=datetime.now(),
            ).save()

    conf_d_path = config.APP_DATA_DIR.joinpath('conf.d')
    if not os.path.exists(conf_d_path):
        conf_d_path = config.DEFAULT_CONFIGS_PATH
    for path, _, file_names in os.walk(conf_d_path):
        for file_name in file_names:
            if not file_name.endswith('cnf'):
                continue
            conf_path = pathlib.Path(path).joinpath(file_name)
            with open(conf_path, 'rb') as f:
                models.MySQLConf(
                    name=conf_path.stem,
                    content=f.read(),
                    create_at=datetime.now(),
                ).save()
