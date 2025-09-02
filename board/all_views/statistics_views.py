import json
from copy import copy
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.db import transaction
from board.models import (
    Entity,
    User,
    Department,
    PendingRequests,
    Asset,
    AssetTree,
    URL,
    Journal,
    AssetStatistics,
)
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


# Get all sub-departments in a given parent department, including lvl.1 to lvl.n
def get_all_sub_departments(parent_department: Department):
    sub_departments = Department.objects.filter(
        entity=parent_department.entity, parent=parent_department
    ).all()
    result = list(sub_departments)
    if len(result) > 0:
        for sub_department in sub_departments:
            result.extend(get_all_sub_departments(sub_department))
    return result


@CheckRequire
def count_department_asset(req: HttpRequest, session: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        manager = User.objects.filter(session=session).first()
        if not manager or manager.character != 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if manager.lock == True:
            return request_failed(
                4,
                "你已被锁定",
                status_code=400,
            )
        # all_departments = Department.objects.filter(entity=manager.entity).all()
        # all_departments = get_all_sub_departments(manager.department)
        # all_departments.append(manager.department)
        department = manager.department
        count_dict = {}
        return_lst = []
        tot_count = 0
        # for department in all_departments:
        cur_count_item = 0
        cur_count_amount = 0
        cur_assets = Asset.objects.filter(department=department, count__gt=0).all()
        for asset in cur_assets:
            if asset.assetClass == 0:
                cur_count_item += asset.count
            else:
                cur_count_amount += asset.count
        # count_dict["department"] = department.name
        tot_count = cur_count_item + cur_count_amount
        count_dict["count_item"] = cur_count_item
        count_dict["count_amount"] = cur_count_amount
        count_dict["count_total"] = tot_count
        return_lst.append(count_dict)
        return_data = {"data": return_lst}
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)


@CheckRequire
def count_status_asset(req: HttpRequest, session: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        manager = User.objects.filter(session=session).first()
        if not manager or manager.character != 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if manager.lock == True:
            return request_failed(
                4,
                "你已被锁定",
                status_code=400,
            )
        # assert len(department_name) <= 128, "输入部门长度不合法"
        # if department_name == "DEFAULT":
        #     # tar_departments = Department.objects.filter(entity=manager.entity).all()
        #     tar_departments = get_all_sub_departments(manager.department)
        #     tar_departments.append(manager.department)
        # else:
        #     tar_departments = Department.objects.filter(
        #         entity=manager.entity,
        #         name=department_name,
        #     ).all()
        #     if len(tar_departments) == 0:
        #         return request_failed(
        #             3,
        #             "无法找到该部门",
        #             status_code=400,
        #         )
        #     all_departments = get_all_sub_departments(manager.department)
        #     all_departments.append(manager.department)
        #     if tar_departments[0] not in all_departments:
        #         return request_failed(
        #             3,
        #             "无法查询非管辖范围内部门的资产信息",
        #             status_code=400,
        #         )
        # count_dict = {}
        department = manager.department
        try:
            item_latest_idle_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=11,
            ).latest('id').cur_count
        except:
            item_latest_idle_cnt = 0
        try:
            item_latest_use_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=22,
            ).latest('id').cur_count
        except:
            item_latest_use_cnt = 0
        try:
            item_latest_maintain_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=33,
            ).latest('id').cur_count
        except:
            item_latest_maintain_cnt = 0
        try:
            item_latest_expire_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=44,
            ).latest('id').cur_count
        except:
            item_latest_expire_cnt = 0

        try:
            amount_latest_idle_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=111,
            ).latest('id').cur_count
        except:
            amount_latest_idle_cnt = 0
        try:
            amount_latest_use_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=222,
            ).latest('id').cur_count
        except:
            amount_latest_use_cnt = 0
        try:
            amount_latest_maintain_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=333,
            ).latest('id').cur_count
        except:
            amount_latest_maintain_cnt = 0
        try:
            amount_latest_expire_cnt = AssetStatistics.objects.filter(
                cur_department=department,
                cur_status=444,
            ).latest('id').cur_count
        except:
            amount_latest_expire_cnt = 0

        return_lst = []
        # count_0 = 0
        # count_1 = 0
        # count_2 = 0
        # count_3 = 0
        # count_4 = 0
        # count_5 = 0
        # count_6 = 0
        # count_7 = 0

        # for department in tar_departments:
        # cur_asset_cnt = Asset.objects.filter(department=department, count__gt=0).count()
        # latest_statistics_cnt = AssetStatistics.objects.filter(
        #     cur_department=department,
        #     cur_status=501113,
        # ).first()
        # print(latest_statistics_cnt)
        # cur_assets = Asset.objects.filter(department=department, count__gt=0).all()
        # for asset in cur_assets:
        #     if asset.assetClass == 0:
        #         if asset.expire == 1:
        #             count_0 += 1
        #         else:
        #             if asset.status == 1:
        #                 count_1 += 1
        #             elif asset.status == 2:
        #                 count_2 += 1
        #             elif asset.status == 3:
        #                 count_3 += 1
        #     else:
        #         if asset.expire == 1:
        #             count_4 += asset.count
        #         else:
        #             if asset.status == 1:
        #                 count_5 += asset.count
        #             elif asset.status == 2:
        #                 count_6 += asset.count
        #             elif asset.status == 3:
        #                 count_7 += asset.count
        # count_dict["type"] = "expire"
        # count_dict["count"] = count_0
        return_lst.append(
            {
                "type": "expire",
                "count": item_latest_expire_cnt,
            }
        )
        return_lst.append(
            {
                "type": "idle",
                "count": item_latest_idle_cnt,
            }
        )
        return_lst.append(
            {
                "type": "use",
                "count": item_latest_use_cnt,
            }
        )
        return_lst.append(
            {
                "type": "maintain",
                "count": item_latest_maintain_cnt,
            }
        )
        return_lst.append(
            {
                "type": "expire",
                "count": amount_latest_expire_cnt,
            }
        )
        return_lst.append(
            {
                "type": "idle",
                "count": amount_latest_idle_cnt,
            }
        )
        return_lst.append(
            {
                "type": "use",
                "count": amount_latest_use_cnt,
            }
        )
        return_lst.append(
            {
                "type": "maintain",
                "count": amount_latest_maintain_cnt,
            }
        )
        return_data = {
            "data": return_lst
        }
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)


@CheckRequire
def info_curve(req: HttpRequest, session: any, asset_id: any, visible_type: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        manager = User.objects.filter(session=session).first()
        if not manager or manager.character != 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if manager.lock == True:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        asset_id = int(asset_id)
        # if type(asset_id) != int:
        #     return request_failed(
        #         1,
        #         "The given asset ID is invalid",
        #         status_code=400,
        #     )
        visible_type = int(visible_type)
        # if type(visible_type) != int:
        #     return request_failed(
        #         1,
        #         "The given visibe type is invalid",
        #         status_code=400,
        #     )
        if visible_type != 1 and visible_type != 2 and visible_type != 3:
            return request_failed(
                5,
                "检测到错误可见类型",
                status_code=400,
            )
        tar_asset = Asset.objects.filter(
            department=manager.department,
            id=asset_id,
        ).first()
        if not tar_asset:
            return request_failed(
                4,
                "未找到目标资产",
                status_code=400,
            )
        # tar_asset_info = (
        #     AssetStatistics.objects.filter(asset=tar_asset).all().order_by("-cur_time")
        # )
        if visible_type == 1:
            tar_asset_info = AssetStatistics.objects.filter(asset=tar_asset).order_by(
                "-id"
            )[:84]
        elif visible_type == 2:
            tar_asset_info = AssetStatistics.objects.filter(asset=tar_asset).order_by(
                "-id"
            )[:360]
        else:
            tar_asset_info = AssetStatistics.objects.filter(asset=tar_asset).order_by(
                "-id"
            )[:1250]
        # info_len = len(tar_asset_info)
        # if visible_type == 1 and info_len > 84:
        #     # 一周的情况
        #     tar_asset_info = tar_asset_info[:84]
        # elif visible_type == 2 and info_len > 360:
        #     # 一月的情况
        #     tar_asset_info = tar_asset_info[:360]
        return_data = {
            "data": [
                return_field(
                    info.serialize(),
                    [
                        "cur_price",
                        "cur_status",
                        "cur_count",
                        "cur_time",
                    ],
                )
                for info in tar_asset_info
            ],
        }
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)


@CheckRequire
def count_price_curve(req: HttpRequest, session: any, visible_type: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "用户的会话标识符信息不正确",
                status_code=400,
            )
        manager = User.objects.filter(session=session).first()
        if not manager or manager.character != 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if manager.lock == True:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        visible_type = int(visible_type)
        if visible_type != 1 and visible_type != 2 and visible_type != 3:
            return request_failed(
                5,
                "检测到错误可见类型",
                status_code=400,
            )
        if visible_type == 1:
            count_info_item = AssetStatistics.objects.filter(
                cur_status=529113,
                cur_department=manager.department,
            ).order_by("-id")[:84]
            count_info_amount = AssetStatistics.objects.filter(
                cur_status=511529,
                cur_department=manager.department,
            ).order_by("-id")[:84]
            count_info_total = AssetStatistics.objects.filter(
                cur_status=501113,
                cur_department=manager.department,
            ).order_by("-id")[:84]
        elif visible_type == 2:
            count_info_item = AssetStatistics.objects.filter(
                cur_status=529113,
                cur_department=manager.department,
            ).order_by("-id")[:360]
            count_info_amount = AssetStatistics.objects.filter(
                cur_status=511529,
                cur_department=manager.department,
            ).order_by("-id")[:360]
            count_info_total = AssetStatistics.objects.filter(
                cur_status=501113,
                cur_department=manager.department,
            ).order_by("-id")[:360]
        else:
            count_info_item = AssetStatistics.objects.filter(
                cur_status=529113,
                cur_department=manager.department,
            ).order_by("-id")[:1250]
            count_info_amount = AssetStatistics.objects.filter(
                cur_status=511529,
                cur_department=manager.department,
            ).order_by("-id")[:1250]
            count_info_total = AssetStatistics.objects.filter(
                cur_status=501113,
                cur_department=manager.department,
            ).order_by("-id")[:1250]
        return_data = {
            "data_item": [
                return_field(
                    info_item.serialize(),
                    [
                        "cur_count",
                        "cur_price",
                        "cur_time",
                    ],
                )
                for info_item in count_info_item
            ],
            "data_amount": [
                return_field(
                    info_amount.serialize(),
                    [
                        "cur_count",
                        "cur_price",
                        "cur_time",
                    ],
                )
                for info_amount in count_info_amount
            ],
            "data_total": [
                return_field(
                    info_total.serialize(),
                    [
                        "cur_count",
                        "cur_price",
                        "cur_time",
                    ],
                )
                for info_total in count_info_total
            ],
        }
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)
