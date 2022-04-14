#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/8 23:04
from datetime import datetime

from peewee import SqliteDatabase
from myvc_app.models.models import *


def run(db: SqliteDatabase):
    db.create_tables([DataVersion, DBInfo])
    from myvc_app.old_data_manager.dbs import DBs
    dbs = DBs.load()
    for db in dbs.dbs:
        db_info = DBInfo(
            name=db.name,
            password=db.password,
            conf_volume=db.conf_volume,
            port=db.port,
            container_id=db.container_id,
            create_at=datetime.strptime(db.create_at, '%Y-%m-%d %H:%M:%S'),
        )
        db_info.save()
        for version in db.version.get_self_and_all_children_objects():
            data_version = DataVersion(
                name=version.name,
                volume=version.volume,
                db=db_info,
                create_at=datetime.strptime(version.create_at, '%Y-%m-%d %H:%M:%S'),
            )
            if version.parent:
                data_version.parent = DataVersion.get(DataVersion.volume == version.parent.volume)
            data_version.save()
            if db.current_version == version.volume:
                db_info.current_version = data_version
                db_info.save()
