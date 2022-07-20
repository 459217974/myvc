#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/9 10:33
import os
import pathlib
import importlib.util
from myvc_app import config


def init():
    if not config.APP_DATA_DIR.exists():
        os.makedirs(config.APP_DATA_DIR)

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
