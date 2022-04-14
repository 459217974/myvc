#!/usr/bin/env python
# -*- encoding: UTF-8 -*-
# Created by CaoDa on 2022/4/13 14:52
import time

from playhouse.signals import pre_save, post_save

from myvc_app.models.models import DataVersion


@pre_save()
def set_update_at(model_class, instance, created):
    if hasattr(model_class, 'update_at') and not created:
        instance.update_at = time.time()


@post_save(sender=DataVersion)
def update_path(model_class, instance, created):
    if instance.parent:
        path = f'{instance.parent.path}{instance.id}/'
    else:
        path = f'/{instance.id}/'
    model_class.update(path=path).where(model_class.id == instance.id).execute()
