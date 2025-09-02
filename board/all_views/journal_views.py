from django.http import HttpRequest, HttpResponse
from datetime import datetime
import math
from board.models import (
    Entity,
    User,
    Department,
    PendingRequests,
    Asset,
    AssetTree,
    URL,
    Journal,
)
import json

PAGE_SIZE = 8
from utils.utils_request import (
    BAD_METHOD,
    request_failed,
    request_success,
    return_field,
)

from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require
from django.db.models import Q


@CheckRequire
def logjournal(req: HttpRequest, session: any, entity_name: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        entity = Entity.objects.filter(name=entity_name).first()
        if not entity:
            return request_failed(
                2,
                "该业务实体不存在。",
                status_code=400,
            )
        if user == None or (user.entity != entity and user.character != 4):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character == 1 or user.character == 2:
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

        all_page = ((len(entity.get_log_journal()) - 1) // PAGE_SIZE) + 1

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

        return_data = {"pages": all_page, "data": []}
        length = len(entity.get_log_journal())
        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        for journal in entity.get_log_journal()[start_index:end_index]:
            return_data["data"].append(
                {
                    "time": journal["time"],
                    "user": journal["user"],
                    "message": journal["message"],
                }
            )
        return_data["data"].reverse()
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def operationjournal(req: HttpRequest, session: any, entity_name: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        entity = Entity.objects.filter(name=entity_name).first()
        if not entity:
            return request_failed(
                2,
                "该业务实体不存在。",
                status_code=400,
            )
        if user == None or (user.entity != entity and user.character != 4):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character == 1 or user.character == 2:
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

        all_page = ((len(entity.get_operation_journal()) - 1) // PAGE_SIZE) + 1

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

        return_data = {"pages": all_page, "data": []}
        length = len(entity.get_operation_journal())
        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        for journal in entity.get_operation_journal()[start_index:end_index]:
            return_data["data"].append(
                {
                    "time": journal["time"],
                    "user": journal["user"],
                    "operation_type": journal["operation_type"],
                    "object_type": journal["object_type"],
                    "object_name": journal["object_name"],
                    "message": journal["message"],
                }
            )

        return_data["data"].reverse()
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def search_logjournal(req: HttpRequest, session: any, entity_name: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        entity = Entity.objects.filter(name=entity_name).first()
        if not entity:
            return request_failed(
                2,
                "该业务实体不存在。",
                status_code=400,
            )
        if user == None or (user.entity != entity and user.character != 4):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character == 1 or user.character == 2:
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
        body = json.loads(req.body.decode("utf-8"))
        date = require(body, "date", "string", err_msg="缺少信息或传入类型不正确")
        info = require(body, "info", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        try:
            page = int(page)
        except:
            return request_failed(
                3,
                "输入的页面不是数字",
                status_code=400,
            )
        journals1 = entity.get_log_journal()
        journals2 = []
        for i in journals1:
            if i["message"].__contains__(info):
                journals2.append(i)
        journals3 = []
        for i in journals2:
            if i["user"].__contains__(name):
                journals3.append(i)
        journals = []
        for i in journals3:
            if i["time"].__contains__(date):
                journals.append(i)

        all_page = ((len(journals) - 1) // PAGE_SIZE) + 1

        if all_page == 0:
            all_page = 1

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

        return_data = {"pages": all_page, "data": []}
        length = len(journals)
        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        for journal in journals[start_index:end_index]:
            return_data["data"].append(
                {
                    "time": journal["time"],
                    "user": journal["user"],
                    "message": journal["message"],
                }
            )
        return_data["data"].reverse()
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def search_operationjournal(req: HttpRequest, session: any, entity_name: any):
    if req.method == "POST":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        user = User.objects.filter(session=session).first()
        entity = Entity.objects.filter(name=entity_name).first()
        if not entity:
            return request_failed(
                2,
                "该业务实体不存在。",
                status_code=400,
            )
        if user == None or (user.entity != entity and user.character != 4):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character == 1 or user.character == 2:
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
        body = json.loads(req.body.decode("utf-8"))
        date = require(body, "date", "string", err_msg="缺少信息或传入类型不正确")
        info = require(body, "info", "string", err_msg="缺少信息或传入类型不正确")
        change = require(body, "change", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        try:
            page = int(page)
        except:
            return request_failed(
                3,
                "输入的页面不是数字",
                status_code=400,
            )
        journals1 = entity.get_operation_journal()
        journals2 = []
        for i in journals1:
            if i["message"].__contains__(info):
                journals2.append(i)
        journals3 = []
        for i in journals2:
            if i["user"].__contains__(name):
                journals3.append(i)
        journals4 = []
        for i in journals3:
            if i["object_name"].__contains__(change):
                journals4.append(i)
        journals = []
        for i in journals4:
            if i["time"].__contains__(date):
                journals.append(i)

        all_page = ((len(journals) - 1) // PAGE_SIZE) + 1

        if all_page == 0:
            all_page = 1

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

        return_data = {"pages": all_page, "data": []}
        length = len(journals)
        start_index = length - page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        if start_index < 0:
            start_index = 0

        if end_index > length:
            end_index = length

        for journal in journals[start_index:end_index]:
            return_data["data"].append(
                {
                    "time": journal["time"],
                    "user": journal["user"],
                    "message": journal["message"],
                }
            )
        return_data["data"].reverse()
        return request_success(return_data)
    else:
        return BAD_METHOD
