#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2021/7/11 13:05
import json
from typing import List


class DataVersion:

    def __init__(self, volume, children=None):
        # type: (str, List[DataVersion]) -> None
        self.volume = volume
        self.parent = None  # type: DataVersion
        self.children = children or []  # type: List[DataVersion]
        for c in self.children:
            c.parent = self
        self.name = None
        self.create_at = None

    def add_child(self, child):
        # type: (DataVersion) -> None
        self.children.append(child)
        child.parent = self

    def remove_child(self, child_volume):
        for i, c in enumerate(self.children):
            if c.volume == child_volume:
                self.children.pop(i)
                break

    def get_self_and_all_children_objects(self):
        volumes = []

        def _get_all(current: DataVersion, depth):
            setattr(current, 'depth', depth)
            volumes.append(current)
            if current.children:
                for v in current.children:
                    _get_all(v, depth + 1)

        _get_all(self, 0)

        return volumes

    def get_self_and_all_children(self):
        return [v.volume for v in self.get_self_and_all_children_objects()]

    def get_version_by_volume(self, volume):

        def _find(current: DataVersion):
            if current.volume == volume:
                return current
            if current.children:
                for v in current.children:
                    _ = _find(v)
                    if _:
                        return _

        return _find(self)

    def __repr__(self):
        lines = []
        indent = '   '

        def _print_tree(current: DataVersion, depth):
            version_info = '{0}[{1}({2})]'.format(
                indent * depth, current.volume, current.name,
            )
            lines.append(
                '{0}{1}'.format(version_info, str(current.create_at).rjust(80 - len(version_info), '┈'))
            )
            if current.children:
                _ = depth + 1
                for v in current.children:
                    _print_tree(v, _)

        _print_tree(self, 0)

        return '\n'.join(lines)

    def to_json(self):
        version_tree = {}
        extra_data = {}

        def _get_all(_dict, current: DataVersion):
            d = _dict.setdefault(current.volume, {})
            extra_data[current.volume] = {
                'name': current.name,
                'create_at': current.create_at
            }
            if current.children:
                for v in current.children:
                    _get_all(d, v)

        _get_all(version_tree, self)

        return json.dumps(
            {'version_tree': version_tree, 'extra_data': extra_data},
            ensure_ascii=False, indent=2
        )

    @classmethod
    def load_from_json(cls, json_string):
        # type: (str) -> DataVersion
        data_dict = json.loads(json_string)  # type: dict
        assert 'version_tree' in data_dict, 'invalid json string'
        assert 'extra_data' in data_dict, 'invalid json string'
        version_tree = data_dict['version_tree']
        extra_data = data_dict['extra_data']
        assert isinstance(version_tree, dict) and len(version_tree.keys()) == 1, 'invalid json string'
        assert isinstance(extra_data, dict), 'invalid json string'

        def _set_extra_data(ver: DataVersion):
            data = extra_data.get(ver.volume)
            for k, v in data.items():
                if hasattr(ver, k):
                    setattr(ver, k, v)

        root_key, root_dict = list(version_tree.items())[0]
        root = DataVersion(root_key)
        _set_extra_data(root)

        def _load(version: DataVersion, _dict):
            for k, v in _dict.items():
                ver = DataVersion(k)
                _set_extra_data(ver)
                version.add_child(ver)
                if v:
                    _load(ver, v)

        _load(root, root_dict)

        return root
