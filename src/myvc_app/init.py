#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/9 10:33
import os
import json
import shutil
import pathlib
import importlib.util

from myvc_app import config


def init():
    config_path = config.USER_HOME_DIR.joinpath('.myvc')
    if not config_path.exists():
        os.makedirs(config_path)
        os.makedirs(config_path.joinpath('conf.d'))
    if not config_path.joinpath('config.json').exists():
        shutil.copy(
            config.DEFAULT_CONFIGS_PATH.joinpath('config.json'),
            config_path.joinpath('config.json')
        )
    if not list(config_path.joinpath('conf.d').iterdir()):
        shutil.copy(
            config.DEFAULT_CONFIGS_PATH.joinpath('example.cnf'),
            config_path.joinpath('conf.d/example.cnf')
        )

    with open(config.CONFIG_PATH, 'rb') as f:
        cfg = json.load(f)
        config.MYSQL_IMAGE_NAME = cfg['MYSQL_IMAGE_NAME']
        config.MYSQL_VERSION = cfg['MYSQL_VERSION']
        config.DOCKER_CLIENT_BASE_URL = cfg['DOCKER_CLIENT_BASE_URL']

    import myvc_app.signals
    from myvc_app.models.base import DB
    from myvc_app.models.models import Migration
    DB.create_tables([Migration])


def migrate():
    from myvc_app.models.base import DB
    from myvc_app.models.models import Migration
    migrations_dir = pathlib.Path(__file__).parent.joinpath('migrations')
    migrated_filenames = {m.filename for m in Migration.select()}
    migrations = list(sorted(
        filter(
            lambda path: (
                    path.is_file()
                    and path.suffix.endswith('.py')
                    and path.name != '__init__.py'
                    and path.name not in migrated_filenames
            ),
            migrations_dir.iterdir()
        ),
        key=lambda path: path.stem
    ))
    if migrations:
        print('there are {} migrations need to be applied'.format(len(migrations)))
    for migration in migrations:
        with DB.atomic():
            print('applying {} ...'.format(migration.name), end='')
            spec = importlib.util.spec_from_file_location(migration.stem, migration)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.run(DB)
            Migration.create(filename=migration.name)
            print('\rapply {} succeed'.format(migration.name))


init()
migrate()
