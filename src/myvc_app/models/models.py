#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/9 10:42
from typing import List
from peewee import CharField, ForeignKeyField, DeferredForeignKey, IntegerField, TextField
from myvc_app.models.base import BaseModel


class Migration(BaseModel):
    filename = CharField()


class DataVersion(BaseModel):
    name = CharField()
    volume = CharField()
    parent = ForeignKeyField('self', null=True, backref='children')
    path = CharField(null=True)
    db = DeferredForeignKey('DBInfo', backref='versions')

    @property
    def self_and_child_versions(self):
        return DataVersion.select().where(DataVersion.path.contains(str(self.id)))

    @property
    def child_versions(self):
        return DataVersion.select().where(DataVersion.id != self.id, DataVersion.path.contains(str(self.id)))

    @property
    def children_tree_objects(self) -> List["DataVersion"]:
        objects = []

        def _get_children(current: DataVersion, depth: int):
            setattr(current, 'depth', depth)
            objects.append(current)
            if current.children:
                _ = depth + 1
                for v in current.children:
                    _get_children(v, _)

        _get_children(self, 0)
        return objects

    @property
    def children_tree(self) -> str:
        lines = []
        indent = '   '
        for v in self.children_tree_objects:
            version_info = f'{indent * v.depth}[{v.volume}({v.name})]'
            lines.append(
                '{0}{1}'.format(version_info, str(v.create_at).rjust(80 - len(version_info), '┈'))
            )
        return '\n'.join(lines)


class DBInfo(BaseModel):
    name = CharField()
    password = CharField()
    current_version = ForeignKeyField(DataVersion, null=True)
    conf_volume = CharField()
    port = IntegerField()
    container_id = CharField(null=True)

    @property
    def root_version(self) -> DataVersion:
        return DataVersion.get(parent=None, db=self)


class Config(BaseModel):
    key = CharField()
    value = CharField()


class MySQLConf(BaseModel):
    name = CharField()
    content = TextField()
