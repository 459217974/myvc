#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/8 22:48
from playhouse.pool import PooledSqliteDatabase
from playhouse.signals import Model
from peewee import AutoField, TimestampField
from myvc_app.config import DB_PATH

DB = PooledSqliteDatabase(DB_PATH)


class BaseModel(Model):
    id = AutoField()
    create_at = TimestampField()
    update_at = TimestampField(null=True, default=None)

    class Meta:
        database = DB
