import json
from copy import copy
from itertools import chain
from decimal import Decimal, ROUND_HALF_UP
from time import sleep
from django.db.models import F, Q
from django.http import HttpRequest, HttpResponse
from django.db import transaction
from django.db.models import Count

# import asyncio
# from asgiref.sync import async_to_sync
from board.models import (
    Entity,
    User,
    Department,
    PendingRequests,
    Asset,
    AssetTree,
    URL,
    Journal,
    AsyncTasks,
)
from datetime import timedelta
from datetime import date, datetime, time
from utils.utils_request import (
    BAD_METHOD,
    request_failed,
    request_success,
    return_field,
)
from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require
from utils.utils_time import get_timestamp
import re
from django.utils import timezone
from . import feishu_utli

PAGE_SIZE = 6

from board.tests import verify_check


def request_update_valid(request_list: list[PendingRequests]):
    for request in request_list:
        if request.result == 0:
            if (
                request.asset.count < request.count
                or (request.type == 1 and request.asset.user != request.participant)
                or (request.type == 2 and request.asset.user != request.initiator)
                or (request.type == 3 and request.asset.user != request.initiator)
                or (request.type == 4 and request.asset.user != request.initiator)
            ):
                request.valid = 0
                request.save()


def check_for_asset_data(body, i):
    parent_id = require(
        body,
        "parent",
        "string",
        err_msg=f"缺少变量或者类型错误： [parent](错误序号：[{i}])",
    )
    asset_name = require(
        body, "name", "string", err_msg=f"缺少变量或者类型错误： [name](错误序号：[{i}])"
    )
    asset_class = require(
        body,
        "assetClass",
        "string",
        err_msg=f"缺少变量或者类型错误： [assetClass](错误序号：[{i}])",
    )
    user_name = require(
        body, "user", "string", err_msg=f"缺少变量或者类型错误： [user](错误序号：[{i}])"
    )
    asset_price = require(
        body, "price", "string", err_msg=f"缺少变量或者类型错误： [price](错误序号：[{i}])"
    )
    asset_price = Decimal(str(asset_price)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert asset_price > 0, "价格要求一定大于0"
    assert asset_price <= 999999.99, "太贵啦！"
    asset_description = require(
        body,
        "description",
        "string",
        err_msg=f"缺少变量或者类型错误： [description](错误序号：[{i}])",
    )
    asset_position = require(
        body,
        "position",
        "string",
        err_msg=f"缺少变量或者类型错误： [position](错误序号：[{i}])",
    )
    expire = require(
        body,
        "expire",
        "string",
        err_msg=f"缺少变量或者类型错误： [expire](错误序号：[{i}])",
    )
    expire = int(expire)
    count = require(body, "count", "string", err_msg=f"缺少变量或者类型错误： [count](错误序号：[{i}])")
    count = int(count)
    asset_tree_name = require(
        body,
        "assetTree",
        "string",
        err_msg=f"缺少变量或者类型错误： [assetTree](错误序号：[{i}])",
    )
    asset_department_name = require(
        body,
        "department",
        "string",
        err_msg=f"缺少变量或者类型错误： [department](错误序号：[{i}])",
    )
    # check
    parent_id = int(parent_id)
    assert 0 < len(asset_name) <= 50, f"变量长度不符合要求： [asset_name](错误序号：[{i}])"
    if asset_name.strip() == "":
        return request_failed(
            2,
            "输入资产名不合法",
            status_code=400,
        )
    assert len(asset_class) == 1, f"变量长度不符合要求： [asset_class](错误序号：[{i}])"
    asset_class = int(asset_class)
    assert 0 < len(user_name) <= 50, f"变量长度不符合要求： [user_name](错误序号：[{i}])"
    assert len(asset_description) <= 128, f"变量长度不符合要求： [asset_description](错误序号：[{i}])"
    assert len(asset_position) <= 128, f"变量长度不符合要求： [asset_position](错误序号：[{i}])"
    assert expire == 0 or expire == 1, f"变量数目不符合要求： [expire](错误序号：[{i}])"
    assert asset_class == 0 or asset_class == 1, f"变量数目不符合要求： [expire](错误序号：[{i}])"
    assert 0 < len(asset_tree_name) <= 50, f"变量长度不符合要求： [asset_tree_name](错误序号：[{i}])"
    assert (
        0 < len(asset_department_name) <= 50
    ), f"变量长度不符合要求： [asset_department_name](错误序号：[{i}])"

    pattern = r"[a-zA-Z0-9\u4e00-\u9fa5]+"
    match = re.match(pattern, user_name)
    assert match != None, f"提供的用户名不符合要求(错误序号：[{i}])"
    match = re.match(pattern, asset_name)
    assert match != None, f"提供的资产名不符合要求(错误序号：[{i}])"
    match = re.match(pattern, asset_department_name)
    assert match != None, f"提供的资产部门名不符合要求(错误序号：[{i}])"
    match = re.match(pattern, asset_tree_name)
    assert match != None, f"提供的资产分类名不符合要求(错误序号：[{i}])"
    # check if the entity and department name is valid
    if len(asset_description) != 0:
        match = re.match(pattern, asset_description)
        assert match != None, f"提供的资产描述不符合要求(错误序号：[{i}])"
    if len(asset_position) != 0:
        match = re.match(pattern, asset_position)
        assert match != None, f"提供的资产位置不符合要求(错误序号：[{i}])"
    # return value
    return (
        parent_id,
        asset_name,
        asset_class,
        user_name,
        asset_price,
        asset_description,
        asset_position,
        expire,
        count,
        asset_tree_name,
        asset_department_name,
    )


def verify(
    corr_request: PendingRequests,
    initiator_name: str,
    manager_name: str,
    target_name: str,
    count: int,
    op: int,
):
    if verify_check[0] == 1:
        return 1
    if corr_request == None:
        return 0
    if target_name == "" and corr_request.target != None:
        return 0
    if corr_request.target != None and corr_request.target.name != target_name:
        return 0
    if (
        corr_request.initiator.name == initiator_name
        and corr_request.participant.name == manager_name
        and corr_request.count == count
        and corr_request.result == 0
        and corr_request.type == op
    ):
        return 1
    else:
        return 0


def check_warning(asset: Asset):
    sum = 0
    if asset.warning_amount != -1:
        if asset.count < asset.warning_amount:
            sum += 1
    if asset.warning_date != -1:
        cur_time = timezone.now()
        ddl = asset.create_time + timezone.timedelta(days=asset.deadline)
        warning_ddl = cur_time + timezone.timedelta(days=asset.warning_date)
        warning_ddl = warning_ddl.date()
        if warning_ddl >= ddl:
            sum += 2
    return sum


def get_all_sub_assets(parent_asset: Asset):
    sub_assets = Asset.objects.filter(parent=parent_asset, count__gt=0).all()
    result = list(sub_assets)
    if len(result) > 0:
        for sub_asset in sub_assets:
            result.extend(get_all_sub_assets(sub_asset))
    return result


@CheckRequire
def asset_tree(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        name = require(body, "name", "string", err_msg="缺少变量或者类型错误： [parent]")
        parent_name = require(body, "parent", "string", err_msg="缺少变量或者类型错误： [parent]")
        department_name = require(
            body, "department", "string", err_msg="缺少变量或者类型错误： [name]"
        )
        assert 0 < len(name) <= 128, "变量长度不符合要求： [Name]"
        assert 0 < len(department_name) <= 128, "变量长度不符合要求： [departmentName]"
        assert 0 < len(parent_name) <= 128, "变量长度不符合要求： [parentName]"
        parent_node = AssetTree.objects.filter(
            name=parent_name, department=department_name
        ).first()
        if parent_node == None:
            return request_failed(
                2,
                "指定名称的父节点不存在",
                status_code=400,
            )
        if parent_node.name == "默认分类":
            return request_failed(
                2,
                "无法在此处创建一个资产分类",
                status_code=400,
            )
        department = Department.objects.filter(name=department_name).first()
        if department == None:
            return request_failed(
                2,
                "该名称的部门不存在。",
                status_code=400,
            )
        if user.character != 2 or (
            user.character == 2 and user.department.name != department_name
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        temp = AssetTree.objects.filter(name=name, department=department_name).first()
        if temp != None:
            return request_failed(
                2,
                "同名资产分类已存在",
                status_code=400,
            )
        new_node = AssetTree(name=name, parent=parent_node, department=department.name)
        new_node.save()
        time = timezone.now()
        operation_user = User.objects.filter(session=session).first()
        if operation_user.feishu_name != "":
            feishu_utli.send(operation_user, f"您刚刚创建了一个新的资产分类:{str(name)}")
        message = f"管理员 [{str(operation_user.name)}] 新建了一个资产分类 [{str(name)}] "
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=operation_user,
            operation_type=2,
            object_type=3,
            object_name=name,
            message=message,
            entity=department.entity,
        )
        journal.save()
        if department.entity != None:
            department.entity.add_operation_journal(journal.serialize())
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def sub_asset_tree(req: HttpRequest, session: any, asset_tree_node_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        parent_node = AssetTree.objects.filter(
            name=asset_tree_node_name, department=user.department.name
        ).first()
        if parent_node == None:
            return request_failed(
                2,
                "指定名称的父节点不存在",
                status_code=400,
            )
        if (
            user.character == 3
            or user.character == 4
            or (user.character == 2 and user.department.name != parent_node.department)
            or (user.character == 1 and user.department.name != parent_node.department)
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        asset_nodes = AssetTree.objects.filter(parent=parent_node).all()
        return_data = {
            "data": [
                return_field(
                    asset_node.serialize(),
                    [
                        "name",
                    ],
                )
                for asset_node in asset_nodes
            ],
        }
        return request_success(return_data)

    if req.method == "DELETE":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        if (
            asset_tree_node_name == "默认分类"
            or asset_tree_node_name == "数量型资产"
            or asset_tree_node_name == "条目型资产"
        ):
            return request_failed(
                44,
                "该资产树节点不可以删除",
                status_code=400,
            )
        current_node = AssetTree.objects.filter(
            name=asset_tree_node_name, department=user.department.name
        ).first()
        if current_node == None:
            return request_failed(
                2,
                "指定名称的资产分类不存在",
                status_code=400,
            )
        if user.character != 2 or (
            user.character == 2 and user.department.name != current_node.department
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        child_node = AssetTree.objects.filter(parent=current_node).first()
        if child_node != None:
            return request_failed(
                2,
                "你不可以删除一个非叶子的资产分类",
                status_code=400,
            )
        assets = Asset.objects.filter(
            assetTree=current_node, count__gt=0, expire=0
        ).first()
        if assets != None:
            return request_failed(
                20,
                "你不可以删除一个已经含有资产的资产分类",
                status_code=400,
            )
        time = timezone.now()
        operation_user = User.objects.filter(session=session).first()
        if operation_user.feishu_name != "":
            feishu_utli.send(
                operation_user, f"您刚刚删除了一个资产分类:{str(asset_tree_node_name)}"
            )
        message = f"管理员 [{operation_user.name}] 删除了资产分类 [{str(asset_tree_node_name)}] "
        department1 = Department.objects.filter(name=current_node.department).first()
        entity1 = department1.entity
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=operation_user,
            entity=entity1,
            operation_type=4,
            object_type=3,
            object_name=current_node.name,
            message=message,
        )
        if entity1 != None:
            entity1.add_operation_journal(journal.serialize())
        journal.save()
        current_node.delete()
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def asset_tree_root(req: HttpRequest, session: any, department_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        department = Department.objects.filter(name=department_name).first()
        if department == None:
            return request_failed(
                2,
                "该名称的部门不存在。",
                status_code=400,
            )
        asset_node = AssetTree.objects.filter(
            department=department_name, parent=None
        ).first()
        if asset_node == None:
            return request_failed(
                2,
                "资产分类不存在",
                status_code=400,
            )
        if (
            user.character == 3
            or user.character == 4
            or (user.character == 2 and user.department != department)
            or (user.character == 1 and user.department != department)
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        return_data = {
            "data": return_field(
                asset_node.serialize(),
                [
                    "name",
                ],
            )
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def asset_tree_node(
    req: HttpRequest,
    session: any,
    asset_tree_node_name: any,
    page: any,
    expire: any,
):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        expire = int(expire)
        assert expire == 0 or expire == 1, "资产清退状态选择错误"
        current_node = AssetTree.objects.filter(
            name=asset_tree_node_name, department=user.department.name
        ).first()

        if current_node == None:
            return request_failed(
                2,
                "指定名称的资产分类不存在",
                status_code=400,
            )
        if user.character != 2 or (
            user.character == 2 and user.department.name != current_node.department
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        # assets = list(
        #     Asset.objects.filter(expire=1, assetTree=current_node, count__gt=0).all()
        # )
        # asset_list = list(
        #     Asset.objects.filter(expire=0, assetTree=current_node, count__gt=0).all()
        # )
        # comb_assets = chain(assets, asset_list)
        # for asset in asset_list:
        #     assets.append(asset)
        page = int(page)
        length = Asset.objects.filter(
            expire=expire, assetTree=current_node, count__gt=0
        ).count()
        all_pages = ((length - 1) // PAGE_SIZE) + 1

        if all_pages == 0:
            all_pages = 1

        if page > all_pages:
            return request_failed(
                1,
                "请输入正确的页码",
                status_code=400,
            )

        if page <= 0:
            return request_failed(
                1,
                "输入页码应为正整数",
                status_code=400,
            )

        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        assets = Asset.objects.filter(
            expire=expire, assetTree=current_node, count__gt=0
        ).all()[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def asset(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character == 1 or user.character == 3:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        body_len = len(body)
        async_task = AsyncTasks(
            entity=user.entity,
            manager=user,
            create_time=timezone.now() + timezone.timedelta(hours=8),
            number_need=body_len,
            number_succeed=0,
            finish=0,
        )
        async_task.set_failed_message(body)
        async_task.save()
        for i in range(0, body_len):
            sleep(0.1)
            key_list = list(body[i].keys())
            if "parent" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[parent]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "name" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[name]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "assetClass" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetClass]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "user" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[user]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "price" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[price]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "description" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[description]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "position" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[position]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "expire" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[expire]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "count" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[count]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "assetTree" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetTree]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "department" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[department]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "deadline" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[deadline]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                parent_id = int(body[i]["parent"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[parent]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                asset_class = int(body[i]["assetClass"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetClass]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                expire = int(body[i]["expire"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[expire]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                count = int(body[i]["count"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[count]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                asset_price = Decimal(str(body[i]["price"])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if asset_price <= 0:
                    history = async_task.get_failed_message()
                    history[i]["message"] = "设定价格应该大于0"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[price]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                ddl = int(body[i]["deadline"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[deadline]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_name = body[i]["name"]
            user_name = body[i]["user"]
            asset_description = body[i]["description"]
            asset_position = body[i]["position"]
            asset_tree_name = body[i]["assetTree"]
            asset_department_name = body[i]["department"]

            if asset_class == 0 and count != 1:
                history = async_task.get_failed_message()
                history[i]["message"] = "仅数量型资产的数量可大于1"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if count <= 0:
                history = async_task.get_failed_message()
                history[i]["message"] = "资产数量不可小于1"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_department = Department.objects.filter(
                name=asset_department_name
            ).first()
            if not asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "对应部门不存在"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_tree = AssetTree.objects.filter(
                name=asset_tree_name, department=asset_department.name
            ).first()
            if not asset_tree:
                history = async_task.get_failed_message()
                history[i]["message"] = "未找到指定层级分类"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            temp = asset_tree
            if temp.name != "默认分类":
                f = False
                while temp != None:
                    if temp.name != "数量型资产" and temp.name != "条目型资产":
                        temp = temp.parent
                    else:
                        if (temp.name == "数量型资产" and asset_class == 0) or (
                            temp.name == "条目型资产" and asset_class == 1
                        ):
                            history = async_task.get_failed_message()
                            history[i]["message"] = "资产类别与层级分类不匹配"
                            async_task.set_failed_message(history)
                            async_task.save()
                            f = True
                            break
                        else:
                            break
                if f == True:
                    continue

            if user.character == 2 and user.department != asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "您无此权限"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if parent_id != 0:
                asset_parent = Asset.objects.filter(
                    id=parent_id,
                    department=asset_department,
                    expire=0,
                    count__gt=0,
                ).first()
                if not asset_parent or asset_parent.assetClass == 1:
                    history = async_task.get_failed_message()
                    history[i]["message"] = "父资产不符合规范"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
            else:
                asset_parent = None
            owner = User.objects.filter(name=user_name).first()
            if not owner:
                history = async_task.get_failed_message()
                history[i]["message"] = "未找到该资产挂账人"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if owner.department != asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "指定资产挂账人不处于当前部门"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            conflict_asset = Asset.objects.filter(
                name=asset_name,
                expire=0,
                count__gt=0,
            ).first()
            if conflict_asset:
                if conflict_asset.assetClass != asset_class:
                    history = async_task.get_failed_message()
                    history[i]["message"] = "资产类别错误"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
                if conflict_asset.initial_price != asset_price:
                    history = async_task.get_failed_message()
                    history[i][
                        "message"
                    ] = f"{asset_name}的初始价格应当为：{conflict_asset.initial_price}(错误序号：[{i}])"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
            if asset_class == 1:
                prev_asset = Asset.objects.filter(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=0,
                    count__gt=0,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    status=1,
                ).first()
            else:
                prev_asset = None
            if prev_asset:
                prev_asset.count += count
                prev_asset.save()
            else:
                # same_name_asset = Asset.objects.filter(name=asset_name).first()
                # if same_name_asset:
                #     wd = same_name_asset.warning_date
                #     wa = same_name_asset.warning_amount
                # else:
                #     wd = -1
                #     wa = -1
                Asset.objects.create(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    initial_price=asset_price,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=expire,
                    count=count,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    # warning_date=wd,
                    # warning_amount=wa,
                )
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if operation_user.feishu_name != "":
                feishu_utli.send(
                    operation_user, f"您刚刚新建了资产:{str(count)}个{str(asset_name)}"
                )
            message = f"管理员 [{str(operation_user.name)}] 录入了资产: {str(count)} × [{str(asset_name)}] "
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=3,
                object_type=3,
                object_name=asset_name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.character != 4:
                user.entity.add_operation_journal(journal.serialize())
            async_task.number_succeed += 1
            history = async_task.get_failed_message()
            history[i]["message"] = "成功"
            async_task.set_failed_message(history)
            async_task.save()
        if async_task.number_succeed == async_task.number_need:
            async_task.finish = 1
        else:
            async_task.finish = 2
        async_task.save()
        return request_success()

    elif req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [entity]",
        )
        id = int(id)
        parent_id = require(
            body,
            "parent",
            "string",
            err_msg="缺少变量或者类型错误： [parent]",
        )
        parent_id = int(parent_id)
        if parent_id == id:
            return request_failed(
                20,
                "资产和其父资产不可相同.",
                status_code=400,
            )
        name = require(
            body,
            "name",
            "string",
            err_msg="缺少变量或者类型错误： [name]",
        )
        assert len(name) <= 128, "变量长度不符合要求： [name]"
        if name.strip() == "":
            return request_failed(
                2,
                "输入资产名不合法",
                status_code=400,
            )
        asset_tree_name = require(
            body,
            "assetTree",
            "string",
            err_msg="缺少变量或者类型错误： [assertTree]",
        )
        assert len(asset_tree_name) <= 128, "变量长度不符合要求： [assettreeName]"
        asset_class = require(
            body,
            "assetClass",
            "string",
            err_msg="缺少变量或者类型错误： [assetClass]",
        )
        asset_class = int(asset_class)
        assert asset_class == 1 or asset_class == 0, "变量数目不符合要求： [assetClass]"
        owner_name = require(
            body,
            "user",
            "string",
            err_msg="缺少变量或者类型错误： [assetClass]",
        )
        assert len(owner_name) <= 128, "变量长度不符合要求： [user]"
        price = require(
            body,
            "price",
            "string",
            err_msg="缺少变量或者类型错误： [price]",
        )
        price = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert price <= 999999.99, "Too expensive :)"
        description = require(
            body,
            "description",
            "string",
            err_msg="缺少变量或者类型错误： [description]",
        )
        assert len(description) <= 256, "变量长度不符合要求： [description]"
        position = require(
            body,
            "position",
            "string",
            err_msg="缺少变量或者类型错误： [position]",
        )
        assert len(position) <= 256, "变量长度不符合要求： [position]"
        expire = require(
            body,
            "expire",
            "string",
            err_msg="缺少变量或者类型错误： [expire]",
        )
        expire = int(expire)
        assert expire == 1 or expire == 0, "变量数目不符合要求： [expire]"
        count = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        count = int(count)
        if count <= 0:
            return request_failed(
                700,
                "资产数目不可以小于等于0 :(",
                status_code=400,
            )
        if asset_class == 0 and count > 1:
            return request_failed(
                5,
                "只有数量型资产的数量可以大于1 :)",
                status_code=400,
            )
        department_name = require(
            body,
            "department",
            "string",
            err_msg="缺少变量或者类型错误： [department]",
        )
        assert len(department_name) <= 256, "变量长度不符合要求： [department]"
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "指定ID的资产不存在",
                status_code=400,
            )
        if asset.expire != expire:
            return request_failed(
                2,
                "你不能修改资产的清退状态",
                status_code=400,
            )
        if asset.assetClass != asset_class:
            return request_failed(
                2,
                "你不能修改资产的类型",
                status_code=400,
            )
        if asset.status == 3:
            return request_failed(
                2,
                "无法修改维保中的资产信息",
                status_code=400,
            )
        department = Department.objects.filter(name=department_name).first()
        if department == None:
            return request_failed(
                2,
                "该名称的部门不存在。",
                status_code=400,
            )
        elif department != asset.department:
            return request_failed(
                2,
                "你不能修改资产所属的部门",
                status_code=400,
            )
        owner = User.objects.filter(name=owner_name).first()
        if owner == None:
            return request_failed(
                2,
                "指定名称的用户不存在",
                status_code=400,
            )
        elif owner.department != department:
            return request_failed(
                2,
                "所提供的资产所有者不属于本部门",
                status_code=400,
            )
        elif asset.user != owner:
            return request_failed(
                2,
                "无法在维护资产信息中修改资产所有者",
                status_code=400,
            )

        if parent_id == 0:
            parent = None
        else:
            parent = Asset.objects.filter(
                id=parent_id,
                department=department,
                expire=0,
                count__gt=0,
            ).first()
            if parent == None:
                return request_failed(
                    2,
                    "指定父资产不存在",
                    status_code=400,
                )
            if parent.assetClass == 1:
                return request_failed(
                    2,
                    "父资产仅可为条目型资产",
                    status_code=400,
                )
            if parent.user != asset.user:
                return request_failed(
                    2,
                    "无法将当前资产的父资产设定为其他用户的资产",
                    status_code=400,
                )
            sub_asset = get_all_sub_assets(asset)
            if parent in sub_asset:
                return request_failed(
                    12,
                    "父资产不可以设定为该资产的子资产",
                    status_code=400,
                )
        if user.character != 2 or (
            user.character == 2 and asset.user.department != user.department
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if asset.name != name:
            exist_asset = Asset.objects.filter(
                name=name,
                expire=0,
                count__gt=0,
            ).first()
            if exist_asset:
                return request_failed(
                    8,
                    "已经有同名资产存在 :(",
                    status_code=400,
                )

        asset_node = AssetTree.objects.filter(
            name=asset_tree_name, department=asset.department.name
        ).first()
        if asset_node == None:
            return request_failed(
                2,
                "该部门下不存在该名称的资产分类",
                status_code=400,
            )
        temp = asset_node
        if temp.name != "默认分类":
            while temp != None:
                if temp.name != "数量型资产" and temp.name != "条目型资产":
                    temp = temp.parent
                else:
                    if (temp.name == "数量型资产" and asset_class == 0) or (
                        temp.name == "条目型资产" and asset_class == 1
                    ):
                        return request_failed(
                            2,
                            "资产类型(条目型/数量型)与所选层级分类不匹配",
                            status_code=400,
                        )
                    else:
                        break
        operation_user = User.objects.filter(session=session).first()
        entity1 = Department.objects.filter(name=asset_node.department).first().entity
        if asset.name == name:
            prev_asset = Asset.objects.filter(
                name=name,
                assetClass=asset_class,
                user=owner,
                parent=parent,
                price=price,
                description=description,
                position=position,
                assetTree=asset_node,
                department=department,
                deadline=asset.deadline,
                create_time=timezone.now().date(),
                expire=0,
                count=count,
                status=1,
                picture_link=asset.picture_link,
                richtxt=asset.richtxt,
            ).first()
            if prev_asset == asset:
                return request_failed(
                    20,
                    "没有作修改 :)",
                    status_code=400,
                )
            elif prev_asset != None:
                prev_asset.count += count
                asset.count = 0
                time = timezone.now()
                if operation_user.feishu_name != "":
                    feishu_utli.send(operation_user, f"您刚刚修改了名为{str(asset_name)}的资产的数量")
                message = f"管理员 [{operation_user.name}] 修改了资产 [{prev_asset.name}](id: {prev_asset.id})的数量， 由 {prev_asset.count} 修改为 {prev_asset.count + count}"
                journal = Journal(
                    time=time + timezone.timedelta(hours=8),
                    user=operation_user,
                    entity=entity1,
                    operation_type=2,
                    object_type=3,
                    object_name=asset.name,
                    message=message,
                )
                journal.save()
                if entity1 != None:
                    entity1.add_operation_journal(journal.serialize())
                prev_asset.save()
                asset.save()
                return request_success()

        time = timezone.now()
        if asset.name != name:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的名称")
            message = f"管理员 [{operation_user.name}] 将资产(id: {asset.id})的名称由 [{asset.name}] 修改为 [{name}] "
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            if entity1:
                entity1.add_operation_journal(journal.serialize())
            journal.save()

        if asset.parent != parent:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的父资产")
            message = f"管理员 [{operation_user.name}] 将资产 [{name}] (id: {asset.id}) 的父资产由 {asset.parent.name if asset.parent is not None else 'None'}(id: {asset.parent.id if asset.parent is not None else 'None'}) 修改为 {parent.name if parent is not None else 'None'}(id: {parent.id if parent is not None else 'None'})"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        if asset.assetTree != asset_node:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚对名为{asset.name}的资产所处的资产分类进行了修改")
            message = f"管理员 [{operation_user.name}] 将资产 [{name}](id: {asset.id}) 的资产分类由 [{asset.assetTree.name}] 修改为 [{asset_node.name}]"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        if asset.price != price:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的价格")
            message = f"管理员 [{operation_user.name}] 将资产 [{name}](id: {asset.id}) 的价格从 {asset.price} 修改为 {price}"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        if asset.description != description:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的描述信息")
            message = (
                f"管理员 [{operation_user.name}] 修改了资产 [{name}](id: {asset.id}) 的描述信息"
            )
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        if asset.position != position:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的位置")
            message = f"管理员 [{operation_user.name}] 修改了资产 [{name}](id:{asset.id}) 的位置"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        if asset.count != count:
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚修改了名为{asset.name}的资产的数量")
            message = f"管理员 [{operation_user.name}] 将资产 [{name}](id={asset.id}) 的数量由 {asset.count} 修改为 {count}"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                entity=entity1,
                operation_type=2,
                object_type=3,
                object_name=asset.name,
                message=message,
            )
            journal.save()
            if entity1:
                entity1.add_operation_journal(journal.serialize())

        asset.parent = parent
        asset.name = name
        asset.price = price
        asset.description = description
        asset.position = position
        asset.count = count
        asset.assetTree = asset_node
        asset.save()

        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def asset_user_list(req: HttpRequest, session: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character != 1:
            return request_failed(
                4,
                "该API只供一级用户查看自己的资产",
                status_code=400,
            )

        page = int(page)

        length = Asset.objects.filter(
            user=user,
            expire=0,
            count__gt=0,
        ).count()

        all_pages = ((length - 1) // PAGE_SIZE) + 1

        if all_pages == 0:
            all_pages = 1

        if page > all_pages:
            return request_failed(
                1,
                "请输入正确的页码",
                status_code=400,
            )

        if page <= 0:
            return request_failed(
                1,
                "输入页码应为正整数",
                status_code=400,
            )

        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        assets = Asset.objects.filter(
            user=user,
            expire=0,
            count__gt=0,
        )[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def asset_manager(req: HttpRequest, session: any, department_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        assert 0 < len(department_name) <= 50, "变量长度不符合要求： [department_name]"
        # check if the department name is valid
        pattern = r"[a-zA-Z0-9\u4e00-\u9fa5]+"
        match = re.match(pattern, department_name)
        assert match != None, "部门名称不合理"
        cur_department = Department.objects.filter(
            name=department_name,
        ).first()
        if not cur_department:
            return request_failed(
                2,
                "未找到目标部门",
                status_code=400,
            )
        if user.character != 4 and cur_department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        asset_manager_list = User.objects.filter(
            department=cur_department,
            character=2,
        ).all()
        return_data = {
            "data": [
                return_field(
                    asset_manager.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for asset_manager in asset_manager_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def unallocated_asset(
    req: HttpRequest, session: any, asset_manager_name: any, page: any
):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user or user.character == 3 or user.character == 4:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        assert 0 < len(asset_manager_name) <= 50, "变量长度不符合要求： [asset_manager_name]"

        tar_manager = User.objects.filter(name=asset_manager_name).first()
        if not tar_manager:
            return request_failed(
                2,
                "未找到目标资产管理员",
                status_code=400,
            )
        if user.character != 2 and tar_manager.department != user.department:
            return request_failed(
                6,
                "不要向非自己部门的资产管理员请求领用资产 :(",
                status_code=400,
            )
        if tar_manager.character != 2:
            return request_failed(
                7,
                "目标不是资产管理员 :(",
                status_code=400,
            )

        page = int(page)

        length = Asset.objects.filter(
            user=tar_manager,
            status=1,
            expire=0,
            count__gt=0,
        ).count()

        all_pages = ((length - 1) // PAGE_SIZE) + 1

        if all_pages == 0:
            all_pages = 1

        if page > all_pages:
            return request_failed(
                1,
                "请输入正确的页码",
                status_code=400,
            )

        if page <= 0:
            return request_failed(
                1,
                "输入页码应为正整数",
                status_code=400,
            )

        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        asset_list = Asset.objects.filter(
            user=tar_manager,
            status=1,
            expire=0,
            count__gt=0,
        )[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    valid_asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for valid_asset in asset_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def allot_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [id]",
        )
        id = int(id)
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        cnt = int(cnt)
        if cnt <= 0:
            return request_failed(
                250,
                "如果不要调拨资产，请勿浪费时间 :)",
                status_code=400,
            )
        manager_name = require(
            body,
            "name",
            "string",
            err_msg="缺少变量或者类型错误： [name]",
        )
        assert len(manager_name) <= 128, "变量长度不符合要求： [name]"
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "指定ID的资产不存在",
                status_code=400,
            )
        if asset.department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        asset_manager = User.objects.filter(name=manager_name).first()
        if asset_manager == None:
            return request_failed(
                2,
                "指定姓名的资产管理员不存在",
                status_code=400,
            )
        if asset_manager == user:
            return request_failed(
                529,
                "请不要浪费时间?",
                status_code=400,
            )
        elif asset_manager.character != 2:
            return request_failed(
                2,
                "你只能调拨资产给资产管理员",
                status_code=400,
            )
        if asset.assetClass == 0 and cnt != 1:
            return request_failed(
                3,
                f"资产 {asset.name} 不是数量型资产, 请自行检查",
                status_code=400,
            )
        if asset.department != asset_manager.department:
            department = asset_manager.department
            asset_node = AssetTree.objects.filter(
                name="默认分类",
                department=department.name,
            ).first()
            if asset_node == None:
                return request_failed(
                    2,
                    "指定名称的资产分类不存在",
                    status_code=400,
                )
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产 {asset.name} 数量不足",
                        status_code=400,
                    )
                elif asset.count >= cnt:
                    manager_asset = Asset.objects.filter(
                        parent=None,
                        name=asset.name,
                        user=asset_manager,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=0,
                        count__gt=0,
                        # assetTree=asset_node,
                        department=department,
                        deadline=asset.deadline,
                        create_time=asset.create_time,
                        status=1,
                        picture_link=asset.picture_link,
                        richtxt=asset.richtxt,
                    ).first()
                    if manager_asset:
                        manager_asset.count += cnt
                        manager_asset.save()
                    else:
                        # same_name_asset = Asset.objects.filter(name=asset.name).first()
                        # if same_name_asset:
                        #     wd = same_name_asset.warning_date
                        #     wa = same_name_asset.warning_amount
                        # else:
                        #     wd = -1
                        #     wa = -1
                        Asset.objects.create(
                            parent=None,
                            name=asset.name,
                            assetClass=asset.assetClass,
                            user=asset_manager,  #
                            initial_price=asset.initial_price,
                            price=asset.price,
                            description=asset.description,
                            position=asset.position,
                            expire=asset.expire,
                            count=cnt,  #
                            assetTree=asset_node,  #
                            department=department,  #
                            create_time=asset.create_time,
                            deadline=asset.deadline,
                            # warning_date=wd,
                            # warning_amount=wa,
                            richtxt=asset.richtxt,
                            picture_link=asset.picture_link,
                        )
                    asset.count -= cnt
                    asset.save()
                return request_success()
            else:  # 条目型资产，需要更新整颗子树
                asset.parent = None  # 断开该子树与该父结点的连接
                asset.user = asset_manager
                asset.department = department
                asset.assetTree = asset_node
                asset.save()
                all_sub_assets = get_all_sub_assets(asset)
                # 子树转移
                for sub_asset in all_sub_assets:
                    sub_asset.user = asset_manager
                    sub_asset.department = department
                    sub_asset.assetTree = asset_node
                    sub_asset.save()
                return request_success()
        else:  # 接受调拨方在同一个部门
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产 {asset.name} 数量不足",
                        status_code=400,
                    )
                elif asset.count >= cnt:
                    manager_asset = Asset.objects.filter(
                        parent=None,
                        name=asset.name,
                        user=asset_manager,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=0,
                        count__gt=0,
                        assetTree=asset.assetTree,
                        department=asset.department,
                        deadline=asset.deadline,
                        create_time=asset.create_time,
                        status=1,
                        picture_link=asset.picture_link,
                        richtxt=asset.richtxt,
                    ).first()
                    if manager_asset:
                        if manager_asset == asset:
                            return request_failed(
                                529,
                                "没有作资产的调拨",
                                status_code=400,
                            )
                        manager_asset.count += cnt
                        manager_asset.save()
                    else:
                        # same_name_asset = Asset.objects.filter(name=asset.name).first()
                        # if same_name_asset:
                        #     wd = same_name_asset.warning_date
                        #     wa = same_name_asset.warning_amount
                        # else:
                        #     wd = -1
                        #     wa = -1
                        Asset.objects.create(
                            parent=None,
                            name=asset.name,
                            assetClass=asset.assetClass,
                            user=asset_manager,  #
                            initial_price=asset.initial_price,
                            price=asset.price,
                            description=asset.description,
                            position=asset.position,
                            expire=asset.expire,
                            count=cnt,  #
                            assetTree=asset.assetTree,  #
                            department=asset.department,  #
                            create_time=asset.create_time,
                            deadline=asset.deadline,
                            # warning_date=wd,
                            # warning_amount=wa,
                            richtxt=asset.richtxt,
                            picture_link=asset.picture_link,
                        )
                    asset.count -= cnt
                    asset.save()
                return request_success()
            else:
                asset.parent = None  # 断开该子树与父结点的连接
                asset.user = asset_manager
                asset.save()
                all_sub_assets = get_all_sub_assets(asset)
                # 子树转移
                for sub_asset in all_sub_assets:
                    sub_asset.user = asset_manager
                    sub_asset.save()
                return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def transfer_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        id = require(body, "id", "string", err_msg="缺少变量或者类型错误： [entity]")
        id = int(id)
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        cnt = int(cnt)
        if cnt <= 0:
            return request_failed(
                250,
                "如果不要转移资产，请勿浪费时间 :)",
                status_code=400,
            )
        sender_name = require(
            body,
            "sender",
            "string",
            err_msg="缺少变量或者类型错误： [sender]",
        )
        assert 0 < len(sender_name) <= 128, "变量长度不符合要求： [sender]"
        target_name = require(
            body,
            "target",
            "string",
            err_msg="缺少变量或者类型错误： [target]",
        )
        assert 0 < len(target_name) <= 128, "变量长度不符合要求： [target]"
        sender_user = User.objects.filter(name=sender_name).first()
        if sender_user == None:
            return request_failed(
                2,
                "指定名称的发送者不存在",
                status_code=400,
            )
        elif sender_user.character != 1:
            return request_failed(
                2,
                "只有用户可以进行资产转移",
                status_code=400,
            )

        target_user = User.objects.filter(name=target_name).first()
        if target_user == None:
            return request_failed(
                2,
                "指定名称的目标用户不存在",
                status_code=400,
            )
        elif target_user.character != 1:
            return request_failed(
                2,
                "目标用户角色必须为用户",
                status_code=400,
            )
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
            user=sender_user,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "该ID的资产不存在",
                status_code=400,
            )
        if asset.department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if asset.assetClass == 0 and cnt != 1:
            return request_failed(
                3,
                f"资产 {asset.name} 不是数量型资产，请自行检查",
                status_code=400,
            )
        request_id = require(
            body,
            "request_id",
            "string",
            err_msg="缺少变量或者类型错误： [request_id]",
        )
        request_id = int(request_id)
        corr_request = PendingRequests.objects.filter(id=request_id).first()
        verilog = verify(corr_request, sender_name, user.name, target_name, cnt, 4)
        if verilog == 0:
            return request_failed(
                501,
                "该操作非法",
                status_code=400,
            )
        if asset.department != target_user.department:
            department = target_user.department
            asset_node = AssetTree.objects.filter(
                name="默认分类",
                department=department.name,
            ).first()
            if asset_node == None:
                return request_failed(
                    2,
                    "指定名称的资产分类不存在",
                    status_code=400,
                )
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产 {asset.name} 数量不足",
                        status_code=400,
                    )
                elif asset.count >= cnt:
                    prev_asset = Asset.objects.filter(
                        parent=None,  # 如果要合并，一定是一项单独资产
                        name=asset.name,
                        user=target_user,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=0,
                        count__gt=0,
                        create_time=asset.create_time,
                        deadline=asset.deadline,
                        picture_link=asset.picture_link,
                        richtxt=asset.richtxt,
                        status=2,
                    ).first()
                    if prev_asset:
                        if prev_asset == asset:
                            return request_failed(
                                529,
                                "没有作资产的调拨",
                                status_code=400,
                            )
                        prev_asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f" 由于{asset.department.name} 的 {sender_name}作了资产的转移，资产数量增长了 {cnt}  ",
                            }
                        )
                        prev_asset.count += cnt
                    else:
                        # same_name_asset = Asset.objects.filter(name=asset.name).first()
                        # if same_name_asset:
                        #     wd = same_name_asset.warning_date
                        #     wa = same_name_asset.warning_amount
                        # else:
                        #     wd = -1
                        #     wa = -1
                        prev_asset = Asset(
                            parent=None,
                            name=asset.name,
                            assetClass=asset.assetClass,
                            user=target_user,  #
                            initial_price=asset.initial_price,
                            price=asset.price,
                            description=asset.description,
                            position=asset.position,
                            expire=asset.expire,
                            count=cnt,  #
                            assetTree=asset_node,  #
                            department=department,  #
                            create_time=asset.create_time,
                            deadline=asset.deadline,
                            # warning_date=wd,
                            # warning_amount=wa,
                            richtxt=asset.richtxt,
                            picture_link=asset.picture_link,
                            status=2,
                        )
                        prev_asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f" 资产由{asset.department.name}的{sender_name}作了转移  ",
                            }
                        )
                    prev_asset.save()
                    asset.count -= cnt
                    if asset.count != 0:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f" 由于资产转移到了 {target_user.department.name} 的 {target_name},资产减少了 {cnt}",
                            }
                        )
                    else:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f"资产转移到了 {target_user.department.name} 的 {target_name}",
                            }
                        )
                    asset.save()
                return request_success()
            else:
                asset.user = target_user
                asset.department = department
                asset.assetTree = asset_node
                asset.parent = None
                asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "转移",
                        "message": f"资产转移到了 {target_user.department.name} 的 {target_name}",
                    }
                )
                asset.save()
                all_sub_assets = get_all_sub_assets(asset)
                for sub_asset in all_sub_assets:
                    sub_asset.user = target_user
                    sub_asset.department = department
                    sub_asset.assetTree = asset_node
                    sub_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "转移",
                            "message": f"资产转移到了 {target_user.department.name} 的 {target_name}",
                        }
                    )
                    sub_asset.save()
                return request_success()
        else:  # in the same department
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产 {asset.name} 数量不足",
                        status_code=400,
                    )
                elif asset.count >= cnt:
                    prev_asset = Asset.objects.filter(
                        parent=None,
                        name=asset.name,
                        user=target_user,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=0,
                        count__gt=0,
                        create_time=asset.create_time,
                        deadline=asset.deadline,
                        assetTree=asset.assetTree,
                        picture_link=asset.picture_link,
                        richtxt=asset.richtxt,
                        status=2,
                    ).first()
                    if prev_asset:
                        if prev_asset == asset:
                            return request_failed(
                                529,
                                "没有作资产的转移",
                                status_code=400,
                            )
                        prev_asset.count += cnt
                        prev_asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f"由于{sender_name}的转移,资产增加了 {cnt}",
                            }
                        )
                    else:
                        # same_name_asset = Asset.objects.filter(name=asset.name).first()
                        # if same_name_asset:
                        #     wd = same_name_asset.warning_date
                        #     wa = same_name_asset.warning_amount
                        # else:
                        #     wd = -1
                        #     wa = -1
                        prev_asset = Asset(
                            parent=None,
                            name=asset.name,
                            assetClass=asset.assetClass,
                            user=target_user,  #
                            initial_price=asset.initial_price,
                            price=asset.price,
                            description=asset.description,
                            position=asset.position,
                            expire=asset.expire,
                            count=cnt,  #
                            assetTree=asset.assetTree,  #
                            department=asset.department,  #
                            create_time=asset.create_time,
                            deadline=asset.deadline,
                            # warning_date=wd,
                            # warning_amount=wa,
                            richtxt=asset.richtxt,
                            picture_link=asset.picture_link,
                            status=2,
                        )
                        prev_asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f" {sender_name}进行了资产转移",
                            }
                        )
                    prev_asset.save()
                    asset.count -= cnt
                    if asset.count != 0:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f"由于转移给 {target_name},资产减少了{cnt} ",
                            }
                        )
                    else:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "转移",
                                "message": f"资产转移给了{target_name}",
                            }
                        )
                    asset.save()
                return request_success()
            else:  # item asset, may have many subasset
                asset.user = target_user
                asset.parent = None
                asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "转移",
                        "message": f"资产被转移给了{target_name}",
                    }
                )
                asset.save()
                all_sub_assets = get_all_sub_assets(asset)
                for sub_asset in all_sub_assets:
                    sub_asset.user = target_user
                    sub_asset.save()
                    sub_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "转移",
                            "message": f"资产被转移给了{target_name}",
                        }
                    )
                return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def get_maintain_list(req: HttpRequest, session: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        maintain_request_list = PendingRequests.objects.filter(
            type=3, result=1, participant=user
        ).all()
        maintain_asset_list = []
        for maintain_request in maintain_request_list:
            if (
                maintain_request.maintain_asset.user == user
                and maintain_request.maintain_asset.count > 0
                and maintain_request.maintain_asset.expire == 0
            ):
                cur_asset = maintain_request.maintain_asset
                min_ddl = (
                    cur_asset.create_time
                    + timezone.timedelta(days=cur_asset.deadline)
                    - timezone.now().date()
                )
                min_ddl = str(min_ddl).split()[0]
                # print(min_ddl)
                maintain_asset_list.append(
                    {
                        "assetID": cur_asset.id,
                        # "requestID": maintain_request.id,
                        "assetName": cur_asset.name,
                        "assetPrice": cur_asset.price,
                        "assetInitialPrice": cur_asset.initial_price,
                        "assetAmount": cur_asset.count,
                        "assetDeadline": cur_asset.create_time
                        + timezone.timedelta(days=cur_asset.deadline),
                        "assetOwner": maintain_request.initiator.name,
                        "min_ddl_days": min_ddl,
                    }
                )
        return_data = {
            "data": maintain_asset_list,
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def maintain_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [entity]",
        )
        id = int(id)
        # r_id = require(
        #     body,
        #     "request_id",
        #     "string",
        #     err_msg="缺少变量或者类型错误： [request_id]",
        # )
        # r_id = int(r_id)
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        cnt = int(cnt)
        name = require(
            body,
            "name",
            "string",
            err_msg="缺少变量或者类型错误： [name]",
        )
        assert 0 < len(name) <= 128, "变量长度不符合要求： [name]"

        new_deadline = require(
            body,
            "new_deadline",
            "string",
            err_msg="缺少变量或者类型错误： [new_deadline]",
        )
        new_deadline = int(new_deadline)
        new_price = require(
            body,
            "new_price",
            "string",
            err_msg="缺少变量或者类型错误： [new_price]",
        )
        new_price = Decimal(str(new_price)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        target_user = User.objects.filter(name=name).first()
        if target_user == None:
            return request_failed(
                2,
                "该资产转移的申请用户不存在",
                status_code=400,
            )
        elif target_user.character != 1:
            return request_failed(
                2,
                "只有用户可以进行资产转移",
                status_code=400,
            )
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
            user=user,
            status=3,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "指定信息的资产不存在",
                status_code=400,
            )
        if asset.department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if asset.assetClass == 0 and cnt != 1:
            return request_failed(
                3,
                f"资产{asset.name}数量错误",
                status_code=400,
            )
        if new_price > asset.initial_price:
            return request_failed(
                5,
                f"新价格不可以比初始价格高 :{asset.initial_price} ",
                status_code=400,
            )
        if timezone.now().date() + timezone.timedelta(
            days=new_deadline
        ) < asset.create_time + timezone.timedelta(days=asset.deadline):
            return request_failed(
                6,
                f"新的截止日期不可以早于原先的截止日期 :{asset.create_time + timezone.timedelta(days=asset.deadline)}",
                status_code=400,
            )
        # tar_req = PendingRequests.objects.filter(id=r_id).first()
        # if tar_req.initiator != target_user:
        #     return request_failed(
        #         5,
        #         "Can not return back current asset to another user who is not the request initiator",
        #         status_code=400,
        #     )
        # request_id = require(
        #     body,
        #     "id",
        #     "string",
        #     err_msg="缺少变量或者类型错误： [request_id]",
        # )
        # request_id = int(request_id)
        # corr_request = PendingRequests.objects.filter(id=request_id).first()
        # verilog = verify(corr_request, name, user.name, "", cnt, 3)
        # if verilog == 0:
        #     return request_failed(
        #         501,
        #         "该操作非法",
        #         status_code=400,
        #     )
        if asset.assetClass == 1:
            if asset.count != cnt:
                return request_failed(
                    4,
                    f"维保资产数目错误",
                    status_code=400,
                )
            else:
                prev_asset = Asset.objects.filter(
                    parent=None,
                    name=asset.name,
                    user=target_user,
                    price=new_price,
                    description=asset.description,
                    position=asset.position,
                    expire=0,
                    count__gt=0,
                    create_time=(timezone.now() + timezone.timedelta(hours=8)).date(),
                    deadline=new_deadline,
                    status=2,
                    picture_link=asset.picture_link,
                    richtxt=asset.richtxt,
                ).first()
                if prev_asset:
                    prev_asset.count += cnt
                    asset.count -= cnt
                    prev_asset.save()
                    prev_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "维保",
                            "message": f"维保接受， {cnt} 个资产返还给了 {target_user.name}",
                        }
                    )
                    asset.save()
                else:
                    asset.user = target_user
                    asset.price = new_price
                    asset.deadline = new_deadline
                    asset.create_time = (
                        timezone.now() + timezone.timedelta(hours=8)
                    ).date()
                    asset.status = 2
                    asset.save()
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "维保",
                            "message": f"维保结束后, {cnt} 个资产返还给了 {target_user.name}",
                        }
                    )
                    # new_asset = Asset.objects.create(
                    #     parent=None,
                    #     name=asset.name,
                    #     user=target_user,
                    #     price=new_price,
                    #     initial_price=new_price,
                    #     description=asset.description,
                    #     position=asset.position,
                    #     expire=0,
                    #     count=cnt,
                    #     create_time=timezone.now().date(),
                    #     depreciation_time=timezone.now().date(),
                    #     deadline=new_deadline,
                    #     assetTree=asset.assetTree,
                    #     picture_link=asset.picture_link,
                    #     warning_date=asset.warning_date,
                    #     warning_amount=asset.warning_amount,
                    #     department=asset.department,
                    #     status=2,
                    # )
        else:  # item asset, may have many subasset but no need to consider
            asset.user = target_user
            asset.price = new_price
            asset.deadline = new_deadline
            asset.create_time = (timezone.now() + timezone.timedelta(hours=8)).date()
            asset.status = 2
            asset.save()
            asset.add_history(
                {
                    "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "type": "维保",
                    "message": f"维保结束后, 资产转移给了 {target_user.name}",
                }
            )
        cur_time = timezone.now() + timezone.timedelta(hours=8)
        message = f"管理员 [{user.name}] 完成了用户 [{target_user.name}] 的资产维保: {asset.count} × [{asset.name}] "
        journal = Journal.objects.create(
            time=cur_time,
            user=user,
            operation_type=2,
            object_type=3,
            object_name=asset.name,
            message=message,
            entity=user.entity,
        )
        if user.entity:
            user.entity.add_operation_journal(journal.serialize())
        requests = PendingRequests.objects.filter(asset=asset).all()
        request_update_valid(requests)
        requests = PendingRequests.objects.filter(valid=0).all()
        if requests != None:
            for i in requests:
                if i.feishu_message_id != "":
                    feishu_utli.update_pending_approval(i.feishu_message_id, 2)
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def get_asset_user(req: HttpRequest, session: any, user_name: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong
        if type(user_name) != str or len(user_name) > 128:
            return request_failed(
                2,
                "用户名非法",
                status_code=400,
            )  # The session is wrong
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        owner = User.objects.filter(name=user_name).first()
        if owner == None:
            return request_failed(
                2,
                "指定名称的用户不存在",
                status_code=400,
            )
        if user.character != 2 or user.entity != owner.entity:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        page = int(page)
        length = Asset.objects.filter(user=owner, count__gt=0).count()
        all_pages = ((length - 1) // PAGE_SIZE) + 1

        if all_pages == 0:
            all_pages = 1

        if page > all_pages:
            return request_failed(
                1,
                "请输入正确的页码",
                status_code=400,
            )

        if page <= 0:
            return request_failed(
                1,
                "输入页码应为正整数",
                status_code=400,
            )

        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        assets = Asset.objects.filter(user=owner, count__gt=0)[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def expire_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        id = int(
            require(
                body,
                "id",
                "string",
                err_msg="缺少变量或者类型错误： [id]",
            ),
        )
        cnt = int(
            require(
                body,
                "count",
                "string",
                err_msg="缺少变量或者类型错误： [count]",
            ),
        )
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
        ).first()
        if not asset:
            return request_failed(
                1,
                "该ID的资产不存在",
                status_code=400,
            )
        if user.department != asset.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if cnt <= 0:
            return request_failed(
                250,
                "请不要浪费时间",
                status_code=400,
            )
        if asset.assetClass == 1:
            if cnt > asset.count:
                return request_failed(
                    5,
                    f"资产 {asset.name} 数量不足",
                    status_code=400,
                )
            elif cnt <= asset.count:
                prev_expire_asset = Asset.objects.filter(
                    parent=asset.parent,
                    name=asset.name,
                    user=asset.user,
                    description=asset.description,
                    position=asset.position,
                    expire=1,
                    count__gt=0,
                    assetTree=asset.assetTree,
                    department=asset.department,
                    picture_link=asset.picture_link,
                    richtxt=asset.richtxt,
                    # deadline=asset.deadline, # 暂定可将ddl不同的过期资产合并
                ).first()
                if prev_expire_asset:
                    prev_expire_asset.count += cnt
                    prev_expire_asset.save()
                else:
                    new_expire_asset = Asset(
                        parent=asset.parent,
                        name=asset.name,
                        assetClass=asset.assetClass,
                        user=asset.user,
                        initial_price=asset.initial_price,
                        price=float(0.00),
                        description=asset.description,
                        position=asset.position,
                        expire=1,
                        count=cnt,
                        assetTree=asset.assetTree,
                        department=asset.department,
                        create_time=asset.create_time,
                        deadline=asset.deadline,
                        richtxt=asset.richtxt,
                        picture_link=asset.picture_link,
                    )
                    new_expire_asset.save()
                asset.count -= cnt
        else:
            asset.expire = 1
            lvl1_sub_assets = Asset.objects.filter(parent=asset).all()
            for ast in lvl1_sub_assets:
                ast.parent = None  # 断开子一级资产的子树与该结点的连接
                ast.save()
            asset.price = float(0.00)
        asset.save()
        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def receive_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [id]",
        )
        id = int(id)
        user_name = require(
            body,
            "name",
            "string",
            err_msg="缺少变量或者类型错误： [name]",
        )
        assert len(user_name) <= 128, "变量长度不符合要求： [name]"
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        cnt = int(cnt)
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "指定ID的资产不存在",
                status_code=400,
            )
        if asset.department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        asset_receiver = User.objects.filter(name=user_name).first()
        if asset_receiver == None:
            return request_failed(
                2,
                "领用资产的用户不存在",
                status_code=400,
            )
        if asset_receiver.character != 1:
            return request_failed(
                2,
                "只有用户可以领用资产",
                status_code=400,
            )
        if asset_receiver.department != user.department:
            return request_failed(
                2,
                "领用者和资产管理员不在一个部门下.",
                status_code=400,
            )
        if cnt <= 0:
            return request_failed(
                250,
                "请不要浪费时间 :)",
                status_code=400,
            )
        if cnt > 1 and asset.assetClass == 0:
            return request_failed(
                3,
                f"资产 {asset.name} 不是数量型资产，请自行检查",
                status_code=400,
            )
        request_id = require(
            body,
            "request_id",
            "string",
            err_msg="缺少变量或者类型错误： [request_id]",
        )
        request_id = int(request_id)
        corr_request = PendingRequests.objects.filter(id=request_id).first()
        verilog = verify(corr_request, user_name, user.name, "", cnt, 1)
        if verilog == 0:
            return request_failed(
                501,
                "该操作非法",
                status_code=400,
            )
        if asset.assetClass == 1:
            if asset.count < cnt:
                return request_failed(
                    4,
                    f"资产 {asset.name} 数量不足",
                    status_code=400,
                )
            elif asset.count >= cnt:
                prev_asset = Asset.objects.filter(
                    parent=None,
                    name=asset.name,
                    user=asset_receiver,
                    price=asset.price,
                    description=asset.description,
                    position=asset.position,
                    expire=0,
                    count__gt=0,
                    assetTree=asset.assetTree,
                    department=asset.department,
                    deadline=asset.deadline,
                    create_time=asset.create_time,
                    status=2,
                    picture_link=asset.picture_link,
                    richtxt=asset.richtxt,
                ).first()
                if prev_asset:
                    prev_asset.count += cnt
                    prev_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "领用",
                            "message": f" {asset_receiver.name}领用资产后,资产数目增加了{cnt}",
                        }
                    )
                    prev_asset.save()
                else:
                    # same_name_asset = Asset.objects.filter(name=asset.name).first()
                    # if same_name_asset:
                    #     wd = same_name_asset.warning_date
                    #     wa = same_name_asset.warning_amount
                    # else:
                    #     wd = -1
                    #     wa = -1
                    asset1 = Asset.objects.create(
                        parent=None,
                        name=asset.name,
                        assetClass=asset.assetClass,
                        user=asset_receiver,
                        initial_price=asset.initial_price,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=asset.expire,
                        count=cnt,
                        assetTree=asset.assetTree,
                        department=asset.department,
                        create_time=asset.create_time,
                        deadline=asset.deadline,
                        # warning_date=wd,
                        # warning_amount=wa,
                        status=2,
                        richtxt=asset.richtxt,
                        picture_link=asset.picture_link,
                    )
                    asset1.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "领用",
                            "message": f"{cnt} 个资产被 {asset_receiver.name} 领用",
                        }
                    )
                asset.count -= cnt
                if asset.count > 0:
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "领用",
                            "message": f"{asset_receiver.name}领用资产后,资产数目减少了{cnt}",
                        }
                    )
                else:
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "领用",
                            "message": f"默认分类被{asset_receiver.name}领用",
                        }
                    )
                asset.save()
                # print(f"now :{asset.name} = {asset.count}")
                return request_success()
        else:
            asset.user = asset_receiver
            asset.parent = None
            asset.status = 2
            asset.save()
            # print(f"now user:{asset.user}")
            asset.add_history(
                {
                    "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "type": "领用",
                    "message": f"资产被{asset_receiver.name}领用",
                }
            )
            all_sub_assets = get_all_sub_assets(asset)
            for sub_asset in all_sub_assets:
                sub_asset.user = asset_receiver
                sub_asset.status = 2
                sub_asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "领用",
                        "message": f"资产被 {asset_receiver.name} 领用",
                    }
                )
                sub_asset.save()
            return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def return_asset(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [entity]",
        )
        id = int(id)
        user_name = require(
            body,
            "name",
            "string",
            err_msg="缺少变量或者类型错误： [name]",
        )
        assert len(user_name) <= 128, "变量长度不符合要求： [name]"
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少变量或者类型错误： [count]",
        )
        cnt = int(cnt)
        asset = Asset.objects.filter(
            id=id,
            expire=0,
            count__gt=0,
        ).first()
        if asset == None:
            return request_failed(
                2,
                "指定ID的资产不存在",
                status_code=400,
            )
        if asset.department != user.department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        asset_owner = User.objects.filter(name=user_name).first()
        if asset_owner == None:
            return request_failed(
                2,
                "领用资产的用户不存在",
                status_code=400,
            )
        if asset_owner.character != 1:
            return request_failed(
                2,
                "只有用户可以退库资产",
                status_code=400,
            )
        if asset_owner.department != user.department:
            return request_failed(
                2,
                "退库者和资产管理员不在一个部门下.",
                status_code=400,
            )
        if asset.user != asset_owner:
            return request_failed(
                1,
                "给出的资产拥有者不合理",
                status_code=400,
            )
        if cnt <= 0:
            return request_failed(
                250,
                "请不要浪费时间 :)",
                status_code=400,
            )
        if cnt > 1 and asset.assetClass == 0:
            return request_failed(
                3,
                f"资产 {asset.name} 不是数量型资产，请自行检查",
                status_code=400,
            )
        request_id = require(
            body,
            "request_id",
            "string",
            err_msg="缺少变量或者类型错误： [request_id]",
        )
        request_id = int(request_id)
        corr_request = PendingRequests.objects.filter(id=request_id).first()
        verilog = verify(corr_request, user_name, user.name, "", cnt, 2)
        if verilog == 0:
            return request_failed(
                501,
                "该操作非法",
                status_code=400,
            )
        if asset.assetClass == 1:
            if asset.count < cnt:
                return request_failed(
                    4,
                    f"资产 {asset.name} 数量不足",
                    status_code=400,
                )
            elif asset.count >= cnt:
                manager_asset = Asset.objects.filter(
                    parent=None,
                    name=asset.name,
                    user=user,
                    price=asset.price,
                    description=asset.description,
                    position=asset.position,
                    expire=0,
                    count__gt=0,
                    assetTree=asset.assetTree,
                    department=asset.department,
                    deadline=asset.deadline,
                    create_time=asset.create_time,
                    status=1,
                    picture_link=asset.picture_link,
                    richtxt=asset.richtxt,
                ).first()
                if manager_asset:
                    manager_asset.count += cnt
                    manager_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "退库",
                            "message": f" 由于 {user.name} 的退库,资产数目增加了 {cnt}",
                        }
                    )
                    manager_asset.save()
                else:
                    # same_name_asset = Asset.objects.filter(name=asset.name).first()
                    # if same_name_asset:
                    #     wd = same_name_asset.warning_date
                    #     wa = same_name_asset.warning_amount
                    # else:
                    #     wd = -1
                    #     wa = -1
                    asset1 = Asset.objects.create(
                        parent=None,
                        name=asset.name,
                        assetClass=asset.assetClass,
                        user=user,
                        initial_price=asset.initial_price,
                        price=asset.price,
                        description=asset.description,
                        position=asset.position,
                        expire=asset.expire,
                        count=cnt,
                        assetTree=asset.assetTree,
                        department=asset.department,
                        create_time=asset.create_time,
                        deadline=asset.deadline,
                        # warning_date=wd,
                        # warning_amount=wa,
                        richtxt=asset.richtxt,
                        picture_link=asset.picture_link,
                    )
                    asset1.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "退库",
                            "message": f"资产被{user.name} 退库",
                        }
                    )
                asset.count -= cnt
                if asset.count > 0:
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "退库",
                            "message": f"由于 {user.name} 的退库,资产数目减少了 {cnt}",
                        }
                    )
                else:
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "退库",
                            "message": f"默认分类被{user.name}退库",
                        }
                    )
                asset.save()
            return request_success()
        else:  # 条目型资产，子树转移
            asset.user = user
            asset.status = 1
            asset.add_history(
                {
                    "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "type": "退库",
                    "message": f"资产被{user.name}退库",
                }
            )
            asset.parent = None
            asset.save()
            all_sub_assets = get_all_sub_assets(asset)
            for sub_asset in all_sub_assets:
                sub_asset.user = user
                sub_asset.status = 1
                sub_asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "退库",
                        "message": f"资产被{user.name}退库",
                    }
                )
                sub_asset.save()
            return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def asset_manager_entity(req: HttpRequest, session: any, entity_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        assert 0 < len(entity_name) <= 50, "变量长度不符合要求： [department_name]"
        # check if the department name is valid
        pattern = r"[a-zA-Z0-9\u4e00-\u9fa5]+"
        match = re.match(pattern, entity_name)
        assert match != None, "The provided entity name is invalid"
        cur_entity = Entity.objects.filter(name=entity_name).first()
        if not cur_entity:
            return request_failed(
                2,
                "未发现目标业务实体",
                status_code=400,
            )
        asset_manager_list = User.objects.filter(entity=cur_entity, character=2).all()
        return_data = {
            "data": [
                return_field(
                    asset_manager.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for asset_manager in asset_manager_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def warning(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        department = user.department

        body = json.loads(req.body.decode("utf-8"))
        date = int(
            require(
                body,
                "date",
                "string",
                err_msg="缺少变量或者类型错误： [type]",
            )
        )
        amount = int(
            require(
                body,
                "amount",
                "string",
                err_msg="缺少变量或者类型错误： [number]",
            )
        )
        id = require(
            body,
            "id",
            "string",
            err_msg="缺少变量或者类型错误： [id]",
        )

        warning_asset = Asset.objects.filter(
            id=id,
            expire=0,
            department=department,
            count__gt=0,
        ).first()

        if not warning_asset:
            return request_failed(
                1,
                "该资产不存在",
                status_code=400,
            )
        assetClass = warning_asset.assetClass
        if assetClass == 0 and amount != -1:
            return request_failed(
                3,
                "条目型资产不可以设置数目",
                status_code=400,
            )

        warning_asset.warning_date = date
        warning_asset.warning_amount = amount
        warning_asset.save()

        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def warning_get(req: HttpRequest, session: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        if user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        department = user.department

        # asset_dict = {}
        # asset_dict1 = {}
        # for asset in asset_list1:
        #     asset_dict1[asset.name] = asset
        #     if asset.name in asset_dict:
        #         asset_dict[asset.name] += asset.count
        #     else:
        #         asset_dict[asset.name] = asset.count
        # return_data = {"data": []}

        # for name, count in asset_dict.items():
        #     asset = asset_dict1[name]
        #     return_data["data"].append(
        #         {
        #             "date": asset.warning_date,
        #             "amount": asset.warning_amount,
        #             "name": asset.name,
        #             "assetClass": asset.assetClass,
        #             "count": count,
        #         }
        #     )
        length = Asset.objects.filter(
            expire=0,
            department=department,
            count__gt=0,
        ).count()

        all_page = ((length - 1) // PAGE_SIZE) + 1

        if all_page == 0:
            all_page = 1

        page = int(page)

        if page > all_page:
            return request_failed(
                4,
                "请求的页面数超过了总页面数。",
                status_code=400,
            )

        if page <= 0:
            return request_failed(
                4,
                "输入的页面数必须为正整数。",
                status_code=400,
            )

        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        assets = Asset.objects.filter(
            expire=0,
            department=department,
            count__gt=0,
        )[start_index:end_index]

        return_data = {
            "pages": all_page,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "name",
                        "assetClass",
                        "count",
                        "price",
                        "description",
                        "warning_date",
                        "warning_amount",
                    ],
                )
                for asset in assets
            ],
        }

        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def warning_list(req: HttpRequest, session: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user or (user.character != 1 and user.character != 2):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        # if user.character != 2:
        #     return request_failed(5, "您无此权限", status_code=400)
        if user.character == 2:
            all_assets = Asset.objects.exclude(
                warning_date=-1, warning_amount=-1
            ).filter(department=user.department, expire=0, count__gt=0,)[:300]
        else:
            all_assets = Asset.objects.exclude(
                warning_date=-1, warning_amount=-1
            ).filter(
                department=user.department,
                expire=0,
                count__gt=0,
                user=user,
            )[
                :300
            ]
        return_data = {"data": []}
        for asset in all_assets:
            if check_warning(asset) == 1:
                return_data["data"].append(
                    {
                        "name": asset.name,
                        "id": asset.id,
                        "description": asset.description,
                        "postion": asset.position,
                        "parent": asset.parent.name if asset.parent else "",
                        "price": asset.price,
                        "assetTree": asset.assetTree.name,
                        "date": -1,
                        "amount": asset.warning_amount - asset.count,
                        "user": asset.user.name,
                    }
                )
            elif check_warning(asset) == 2:
                return_data["data"].append(
                    {
                        "name": asset.name,
                        "date": (
                            asset.create_time
                            + timezone.timedelta(days=asset.deadline)
                            - timezone.now().date()
                        ).days,
                        "id": asset.id,
                        "description": asset.description,
                        "parent": asset.parent.name if asset.parent else "",
                        "price": asset.price,
                        "assetTree": asset.assetTree.name,
                        "amount": -1,
                        "user": asset.user.name,
                    }
                )
            elif check_warning(asset) == 3:
                return_data["data"].append(
                    {
                        "name": asset.name,
                        "date": (
                            asset.create_time
                            + timezone.timedelta(days=asset.deadline)
                            - timezone.now().date()
                        ).days,
                        "id": asset.id,
                        "description": asset.description,
                        "parent": asset.parent.name if asset.parent else "",
                        "price": asset.price,
                        "assetTree": asset.assetTree.name,
                        "amount": asset.warning_amount - asset.count,
                        "user": asset.user.name,
                    }
                )
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def get_history_list(req: HttpRequest, session: any, id: any, history_type: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character != 4 and user.character != 2:
            return request_failed(5, "您无此权限", status_code=400)
        id = int(id)
        history_type = int(history_type)

        asset = Asset.objects.filter(id=id).first()

        if not asset:
            return request_failed(
                5,
                "The corresponding asset cannot be found based on ID",
                status_code=400,
            )

        if (
            history_type != 1
            and history_type != 2
            and history_type != 3
            and history_type != 4
            and history_type != 5
        ):
            return request_failed(6, "The view type is not valid", status_code=400)
        return_data = {"data": []}
        if history_type == 1:
            for record in asset.get_history():
                if record["type"] == "转移":
                    return_data["data"].append(record)

        elif history_type == 2:
            for record in asset.get_history():
                if record["type"] == "维保":
                    return_data["data"].append(record)

        elif history_type == 3:
            for record in asset.get_history():
                if record["type"] == "领用":
                    return_data["data"].append(record)

        elif history_type == 4:
            for record in asset.get_history():
                if record["type"] == "退库":
                    return_data["data"].append(record)

        elif history_type == 5:
            for record in asset.get_history():
                return_data["data"].append(record)

        return_data["data"].reverse()
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def picture(req: HttpRequest, session: any, asset_id: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        links = require(
            body,
            "links",
            "list",
            err_msg="缺少变量或者类型错误： [links]",
        )
        richtxt = require(
            body,
            "richtxt",
            "string",
            err_msg="缺少变量或者类型错误： [richtxt]",
        )
        assetID = int(asset_id)
        tar_asset = Asset.objects.filter(id=assetID).first()
        if not tar_asset:
            return request_failed(
                3,
                "未找到指定资产",
                status_code=400,
            )
        if tar_asset.department != user.department:
            return request_failed(
                5,
                "您无此权限",
                status_code=400,
            )
        tar_asset.picture_link = links
        tar_asset.richtxt = richtxt
        # var_prefix = "picture_link_"
        # for i in range(1, 9):
        #     var_name = var_prefix + str(i)
        #     locals()[var_name] = links[i - 1]
        tar_asset.save()

        return request_success()
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or (user.character != 2 and user.character != 1):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        assetID = int(asset_id)
        tar_asset = Asset.objects.filter(id=assetID).first()
        if not tar_asset:
            return request_failed(
                3,
                "未找到指定资产",
                status_code=400,
            )
        if tar_asset.department != user.department:
            return request_failed(
                5,
                "您无此权限",
                status_code=400,
            )

        return_data = {
            "links": tar_asset.picture_link,
            "richtxt": tar_asset.richtxt,
        }

        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)


@CheckRequire
def failed_task(req: HttpRequest, session: any, id: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                2,
                "用户未找到",
                status_code=400,
            )

        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        if user.character != 3:
            return request_failed(
                5,
                "只有系统管理员有查看异步任务权限",
                status_code=400,
            )
        async_task = AsyncTasks.objects.filter(id=id).first()
        if not async_task:
            return request_failed(
                6,
                "对应id的异步任务不存在",
                status_code=400,
            )
        if async_task.port_type != 1:
            return request_failed(
                8,
                "不能通过此API获取导出的异步任务",
                status_code=400,
            )
        if async_task.entity != user.entity:
            return request_failed(
                7,
                "你无此权限",
                status_code=400,
            )
        return_data = {"data": []}
        for failed_task in async_task.get_failed_message():
            if "message" in failed_task.keys():
                if failed_task["message"] != "成功":
                    return_data["data"].append(failed_task)
            else:
                return_data["data"].append(failed_task)

        return request_success(return_data)

    elif req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                2,
                "用户未找到",
                status_code=400,
            )

        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )
        if user.character != 3:
            return request_failed(
                5,
                "只有系统管理员有查看异步任务权限",
                status_code=400,
            )
        async_task = AsyncTasks.objects.filter(id=id).first()
        if not async_task:
            return request_failed(
                6,
                "对应id的异步任务不存在",
                status_code=400,
            )
        if async_task.entity != user.entity:
            return request_failed(
                7,
                "你无此权限",
                status_code=400,
            )
        if async_task.port_type != 1:
            return request_failed(
                8,
                "不能通过此API重新评测某导出任务",
                status_code=400,
            )
        length = 0
        for task in async_task.get_failed_message():
            if "message" in task.keys():
                if task["message"] != "成功":
                    length += 1
            else:
                length += 1
        async_task.clear_failed_message()
        async_task.create_time = timezone.now() + timezone.timedelta(hours=8)
        async_task.finish = 0
        async_task.save()
        body = json.loads(req.body.decode("utf-8"))
        body_len = len(body)
        if body_len != length:
            return request_failed(
                8,
                "新传入的POST资产信息一定要与之前的失败信息长度相同",
                status_code=400,
            )
        async_task.set_failed_message(body)
        async_task.save()
        for i in range(0, body_len):
            sleep(0.1)
            key_list = list(body[i].keys())
            if "parent" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[parent]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "name" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[name]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "assetClass" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetClass]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "user" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[user]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "price" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[price]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "description" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[description]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "position" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[position]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "expire" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[expire]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "count" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[count]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "assetTree" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetTree]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "department" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[department]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if "deadline" not in key_list:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[deadline]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                parent_id = int(body[i]["parent"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[parent]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                asset_class = int(body[i]["assetClass"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[assetClass]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                expire = int(body[i]["expire"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[expire]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                count = int(body[i]["count"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[count]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                asset_price = Decimal(str(body[i]["price"])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[price]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            try:
                ddl = int(body[i]["deadline"])
            except:
                history = async_task.get_failed_message()
                history[i]["message"] = "缺少变量或类型错误:[deadline]"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_name = body[i]["name"]
            user_name = body[i]["user"]
            asset_description = body[i]["description"]
            asset_position = body[i]["position"]
            asset_tree_name = body[i]["assetTree"]
            asset_department_name = body[i]["department"]

            if asset_class == 0 and count != 1:
                history = async_task.get_failed_message()
                history[i]["message"] = "仅数量型资产的数量可大于1"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if count <= 0:
                history = async_task.get_failed_message()
                history[i]["message"] = "资产数量不可小于1"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_department = Department.objects.filter(
                name=asset_department_name
            ).first()
            if not asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "对应部门不存在"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            asset_tree = AssetTree.objects.filter(
                name=asset_tree_name, department=asset_department.name
            ).first()
            if not asset_tree:
                history = async_task.get_failed_message()
                history[i]["message"] = "未找到指定层级分类"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            temp = asset_tree
            if temp.name != "默认分类":
                f = False
                while temp != None:
                    if temp.name != "数量型资产" and temp.name != "条目型资产":
                        temp = temp.parent
                    else:
                        if (temp.name == "数量型资产" and asset_class == 0) or (
                            temp.name == "条目型资产" and asset_class == 1
                        ):
                            history = async_task.get_failed_message()
                            history[i]["message"] = "资产类别与层级分类不匹配"
                            async_task.set_failed_message(history)
                            async_task.save()
                            f = True
                            break
                        else:
                            break
                if f == True:
                    continue

            if user.character == 2 and user.department != asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "您无此权限"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if parent_id != 0:
                asset_parent = Asset.objects.filter(
                    id=parent_id,
                    department=asset_department,
                    expire=0,
                    count__gt=0,
                ).first()
                if not asset_parent or asset_parent.assetClass == 1:
                    history = async_task.get_failed_message()
                    history[i]["message"] = "父资产不符合规范"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
            else:
                asset_parent = None
            owner = User.objects.filter(name=user_name).first()
            if not owner:
                history = async_task.get_failed_message()
                history[i]["message"] = "未找到该资产挂账人"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            if owner.department != asset_department:
                history = async_task.get_failed_message()
                history[i]["message"] = "指定资产挂账人不处于当前部门"
                async_task.set_failed_message(history)
                async_task.save()
                continue
            conflict_asset = Asset.objects.filter(
                name=asset_name,
                expire=0,
                count__gt=0,
            ).first()
            if conflict_asset:
                if conflict_asset.assetClass != asset_class:
                    history = async_task.get_failed_message()
                    history[i]["message"] = "资产类别错误"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
                if conflict_asset.initial_price != asset_price:
                    history = async_task.get_failed_message()
                    history[i][
                        "message"
                    ] = f"{asset_name}的初始价格应当为：{conflict_asset.initial_price}(错误序号：[{i}])"
                    async_task.set_failed_message(history)
                    async_task.save()
                    continue
            if asset_class == 1:
                prev_asset = Asset.objects.filter(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=0,
                    count__gt=0,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    status=1,
                ).first()
            else:
                prev_asset = None
            if prev_asset:
                prev_asset.count += count
                prev_asset.save()
            else:
                # same_name_asset = Asset.objects.filter(name=asset_name).first()
                # if same_name_asset:
                #     wd = same_name_asset.warning_date
                #     wa = same_name_asset.warning_amount
                # else:
                #     wd = -1
                #     wa = -1
                Asset.objects.create(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    initial_price=asset_price,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=expire,
                    count=count,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    # warning_date=wd,
                    # warning_amount=wa,
                )
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if operation_user.feishu_name != "":
                feishu_utli.send(
                    operation_user, f"您刚刚新建了资产:{str(count)}个{str(asset_name)}"
                )
            message = f"管理员 [{str(operation_user.name)}] 录入了资产: {str(count)} × [{str(asset_name)}] "
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=3,
                object_type=3,
                object_name=asset_name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.entity:
                user.entity.add_operation_journal(journal.serialize())
            async_task.number_succeed += 1
            history = async_task.get_failed_message()
            history[i]["message"] = "成功"
            async_task.set_failed_message(history)
            async_task.save()
        if async_task.number_succeed == async_task.number_need:
            async_task.finish = 1
        else:
            async_task.finish = 2
        async_task.save()
        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def post_asset(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character == 1 or user.character == 3:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        # print(body[0])
        body_len = len(body)
        # print(body_len)
        for i in range(0, body_len):
            (
                parent_id,
                asset_name,
                asset_class,
                user_name,
                asset_price,
                asset_description,
                asset_position,
                expire,
                count,
                asset_tree_name,
                asset_department_name,
            ) = check_for_asset_data(body[i], i)
            if asset_class == 0 and count != 1:
                return request_failed(
                    5,
                    f"仅数量型资产的数量可大于 1 (错误序号：[{i}])",
                    status_code=400,
                )
            if count <= 0:
                return request_failed(
                    250,
                    f"资产数量不可小于 1 (错误序号：[{i}])",
                    status_code=400,
                )
            # search the entity ,if not exsit ,create a new entity
            asset_department = Department.objects.filter(
                name=asset_department_name
            ).first()
            if not asset_department:
                return request_failed(
                    1,
                    "对应部门不存在(错误序号：[0])",
                    status_code=400,
                )
            asset_tree = AssetTree.objects.filter(
                name=asset_tree_name, department=asset_department.name
            ).first()
            if not asset_tree:
                return request_failed(
                    1,
                    f"未找到指定层级分类(错误序号：[{i}])",
                    status_code=400,
                )
            temp = asset_tree
            if temp.name != "默认分类":
                while temp != None:
                    if temp.name != "数量型资产" and temp.name != "条目型资产":
                        temp = temp.parent
                    else:
                        if (temp.name == "数量型资产" and asset_class == 0) or (
                            temp.name == "条目型资产" and asset_class == 1
                        ):
                            return request_failed(
                                2,
                                f"资产类别与层级分类不匹配(错误序号：[{i}])",
                                status_code=400,
                            )
                        else:
                            break

            if user.character == 2 and user.department != asset_department:
                return request_failed(
                    1,
                    "您无此权限",
                    status_code=400,
                )
            if parent_id != 0:
                asset_parent = Asset.objects.filter(
                    id=parent_id,
                    department=asset_department,
                    expire=0,
                    count__gt=0,
                ).first()
                if not asset_parent or asset_parent.assetClass == 1:
                    return request_failed(
                        1,
                        f"父资产不符合规范(错误序号：[{i}])",
                        status_code=400,
                    )
            else:
                asset_parent = None
            owner = User.objects.filter(name=user_name).first()
            if not owner:
                return request_failed(
                    1,
                    f"未找到该资产挂账人(错误序号：[{i}])",
                    status_code=400,
                )
            if owner.department != asset_department:
                return request_failed(
                    2,
                    f"指定资产挂账人不处于当前部门(错误序号：[{i}])",
                    status_code=400,
                )
            ddl = int(
                require(
                    body[i],
                    "deadline",
                    "string",
                    err_msg="缺少变量或者类型错误： [deadline]",
                )
            )
            conflict_asset = Asset.objects.filter(
                name=asset_name,
                expire=0,
                count__gt=0,
            ).first()
            if conflict_asset:
                if conflict_asset.assetClass != asset_class:
                    return request_failed(
                        10,
                        f"资产类别错误(错误序号：[{i}])",
                        status_code=400,
                    )
                if conflict_asset.initial_price != asset_price:
                    return request_failed(
                        11,
                        f"{asset_name}的初始价格应当为：{conflict_asset.initial_price}(错误序号：[{i}])",
                        status_code=400,
                    )

            if asset_class == 1:
                prev_asset = Asset.objects.filter(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=0,
                    count__gt=0,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    status=1,
                ).first()
            else:
                prev_asset = None
            if prev_asset:
                prev_asset.count += count
                prev_asset.save()
            else:
                # same_name_asset = Asset.objects.filter(name=asset_name).first()
                # if same_name_asset:
                #     wd = same_name_asset.warning_date
                #     wa = same_name_asset.warning_amount
                # else:
                #     wd = -1
                #     wa = -1
                Asset.objects.create(
                    parent=asset_parent,
                    name=asset_name,
                    assetClass=asset_class,
                    user=owner,
                    initial_price=asset_price,
                    price=asset_price,
                    description=asset_description,
                    position=asset_position,
                    expire=expire,
                    count=count,
                    assetTree=asset_tree,
                    department=asset_department,
                    create_time=timezone.now().date(),
                    deadline=ddl,
                    # warning_date=wd,
                    # warning_amount=wa,
                )
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if operation_user.feishu_name != "":
                feishu_utli.send(
                    operation_user, f"您刚刚新建了资产:{str(count)}个{str(asset_name)}"
                )
            message = f"管理员 [{str(operation_user.name)}] 录入了资产: {str(count)} × [{str(asset_name)}] "
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=3,
                object_type=3,
                object_name=asset_name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.entity:
                user.entity.add_operation_journal(journal.serialize())
        return request_success()


@CheckRequire
def all_item_assets(req: HttpRequest, session: any, asset_id: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or user.character != 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked
        asset_id = int(asset_id)

        if asset_id == 0:
            valid_assets = Asset.objects.filter(
                assetClass=0, user=user, count=1, expire=0
            )
        else:
            tar_asset = Asset.objects.filter(
                id=asset_id, department=user.department, count__gt=0, expire=0
            ).first()
            if not tar_asset:
                return request_failed(
                    2,
                    "指定资产无效或不存在",
                    status_code=400,
                )
            tar_asset_invalid_parent = get_all_sub_assets(tar_asset)
            tar_asset_invalid_parent.append(tar_asset)
            invalid_assets_id = [ast.pk for ast in tar_asset_invalid_parent]
            valid_assets = Asset.objects.filter(
                assetClass=0, user=tar_asset.user, count=1, expire=0
            ).exclude(Q(pk__in=invalid_assets_id))

        return_data = {
            "data": [
                return_field(
                    valid_asset.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for valid_asset in valid_assets
            ],
        }
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)


@CheckRequire
def search_assets(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong
        # check if the user exists
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.character != 2:
            return request_failed(
                2,
                "你无此权限",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        tree_node = require(body, "asset_tree_node", "string", err_msg="缺少信息或传入类型不正确")
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        price_inf = require(body, "price_inf", "string", err_msg="缺少信息或传入类型不正确")
        default_price_inf = 0
        if price_inf != "":
            price_inf = int(price_inf)
            default_price_inf = price_inf
        price_sup = require(body, "price_sup", "string", err_msg="缺少信息或传入类型不正确")
        default_price_sup = 100000000
        if price_sup != "":
            price_sup = int(price_sup)
            default_price_sup = price_sup
        description = require(body, "description", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        if id != "":
            id = int(id)
            assets = Asset.objects.filter(
                id=id, department=user.department, count__gt=0, expire=0
            ).all()
            all_pages = 1
        else:
            if tree_node != "":
                asset_tree_node = AssetTree.objects.filter(
                    name=tree_node,
                    department=user.department.name,
                ).first()
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]
            elif tree_node == "":
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    department=user.department,
                    name__contains=name,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    department=user.department,
                    name__contains=name,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def search_unallocated_assets(req: HttpRequest, session: any, manager_name: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong
        # check if the user exists
        assert len(manager_name) <= 128, "字段长度非法：[manager_name]"
        user = User.objects.filter(session=session).first()
        if not user or user.character != 1:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        manager = User.objects.filter(name=manager_name).first()
        if (
            not manager
            or manager.character != 2
            or manager.department != user.department
        ):
            return request_failed(
                2,
                "所选资产管理员非法",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        tree_node = require(body, "asset_tree_node", "string", err_msg="缺少信息或传入类型不正确")
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        price_inf = require(body, "price_inf", "string", err_msg="缺少信息或传入类型不正确")
        default_price_inf = 0
        if price_inf != "":
            price_inf = int(price_inf)
            default_price_inf = price_inf
        price_sup = require(body, "price_sup", "string", err_msg="缺少信息或传入类型不正确")
        default_price_sup = 100000000
        if price_sup != "":
            price_sup = int(price_sup)
            default_price_sup = price_sup
        description = require(body, "description", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        if id != "":
            id = int(id)
            assets = Asset.objects.filter(
                id=id,
                department=user.department,
                user=manager,
                status=1,
                count__gt=0,
                expire=0,
            ).all()
            all_pages = 1
        else:
            if tree_node != "":
                asset_tree_node = AssetTree.objects.filter(
                    name=tree_node,
                    department=user.department.name,
                ).first()
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    user=manager,
                    status=1,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    user=manager,
                    status=1,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]
            elif tree_node == "":
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    user=manager,
                    status=1,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    user=manager,
                    status=1,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def search_personal_assets(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong
        # check if the user exists
        user = User.objects.filter(session=session).first()
        if not user or user.character != 1:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        tree_node = require(body, "asset_tree_node", "string", err_msg="缺少信息或传入类型不正确")
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        price_inf = require(body, "price_inf", "string", err_msg="缺少信息或传入类型不正确")
        default_price_inf = 0
        if price_inf != "":
            price_inf = int(price_inf)
            default_price_inf = price_inf
        price_sup = require(body, "price_sup", "string", err_msg="缺少信息或传入类型不正确")
        default_price_sup = 100000000
        if price_sup != "":
            price_sup = int(price_sup)
            default_price_sup = price_sup
        description = require(body, "description", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        if id != "":
            id = int(id)
            assets = Asset.objects.filter(
                id=id,
                user=user,
                count__gt=0,
                expire=0,
            ).all()
            all_pages = 1
        else:
            if tree_node != "":
                asset_tree_node = AssetTree.objects.filter(
                    name=tree_node,
                    department=user.department.name,
                ).first()
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    user=user,
                    status=2,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    assetTree=asset_tree_node,
                    user=user,
                    status=2,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]
            elif tree_node == "":
                length = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    user=user,
                    status=2,
                    count__gt=0,
                    expire=0,
                ).count()
                all_pages = ((length - 1) // PAGE_SIZE) + 1
                if all_pages == 0:
                    all_pages = 1
                page = int(page)
                if page > all_pages:
                    return request_failed(
                        4,
                        "请求的页面数超过了总页面数。",
                        status_code=400,
                    )
                if page <= 0:
                    return request_failed(
                        4,
                        "输入的页面数必须为正整数。",
                        status_code=400,
                    )
                start_index = (page - 1) * PAGE_SIZE
                end_index = start_index + PAGE_SIZE
                if start_index < 0:
                    start_index = 0
                if end_index > length:
                    end_index = length
                assets = Asset.objects.filter(
                    price__gte=default_price_inf,
                    price__lte=default_price_sup,
                    description__contains=description,
                    name__contains=name,
                    user=user,
                    status=2,
                    count__gt=0,
                    expire=0,
                )[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    asset.serialize(),
                    [
                        "id",
                        "parentName",
                        "name",
                        "assetClass",
                        "userName",
                        "price",
                        "description",
                        "position",
                        "expire",
                        "count",
                        "assetTree",
                        "departmentName",
                        "create_time",
                        "deadline",
                        "initial_price",
                        "status",
                    ],
                )
                for asset in assets
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def export(req: HttpRequest, session: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if user.character != 2:
            return request_failed(
                2,
                "只有资产管理员能进行资产导出异步任务",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        body_len = len(body)
        async_task = AsyncTasks(
            entity=user.entity,
            manager=user,
            create_time=timezone.now() + timezone.timedelta(hours=8),
            number_need=body_len,
            number_succeed=0,
            finish=0,
            port_type=2,
        )
        async_task.save()
        for i in range(0, body_len):
            try:
                id = int(body[i])
            except:
                continue
            asset = Asset.objects.filter(id=id).first()
            if not asset:
                continue
            async_task.add_failed_message(
                {
                    "id": asset.id,
                    "parentName": asset.parent.name if asset.parent else "",
                    "name": asset.name,
                    "assetClass": asset.assetClass,
                    "userName": asset.user.name,
                    "price": str(asset.price),
                    "description": asset.description,
                    "position": asset.position,
                    "expire": asset.expire,
                    "count": asset.count,
                    "assetTree": asset.assetTree.name,
                    "departmentName": asset.department.name,
                    "create_time": str(asset.create_time),
                    "deadline": asset.deadline,
                    "initial_price": str(asset.initial_price),
                    "warning_amount": asset.warning_amount,
                    "warning_date": asset.warning_date,
                    "expire_date": str(
                        asset.create_time
                        + timezone.timedelta(days=asset.deadline)
                        + timezone.timedelta(hours=8)
                    ),
                    "status": asset.status,
                }
            )
            async_task.number_succeed += 1
            async_task.save()

        if async_task.number_succeed == async_task.number_need:
            async_task.finish = 1
        else:
            async_task.finish = 2
        async_task.save()
        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def export_task(req: HttpRequest, session: any, id: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if user.character != 3:
            return request_failed(
                2,
                "只有系统管理员能查看导出异步任务",
                status_code=400,
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        id = int(id)
        async_task = AsyncTasks.objects.filter(id=id).first()
        if async_task.port_type != 2:
            return request_failed(
                4,
                "该API只可用于查看导出异步任务的成功记录",
                status_code=400,
            )
        return_data = {"data": []}
        return_data["data"] = async_task.get_failed_message()

        return request_success(return_data)

    else:
        return BAD_METHOD
