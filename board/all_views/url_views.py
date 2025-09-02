import json
from django.utils import timezone
from django.http import HttpRequest, HttpResponse
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
from utils.utils_request import (
    BAD_METHOD,
    request_failed,
    request_success,
    return_field,
)
from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require
from utils.utils_time import get_timestamp
from . import feishu_utli


@CheckRequire
def url(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )

        if user.character == 1 or user.character == 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        body = json.loads(req.body.decode("utf-8"))
        if len(body) != 5:
            return request_failed(
                7,
                "url列表长度错误",
                status_code=400,
            )
        url_name_list = []
        url_list = []
        for i in range(0, 5):
            new_url = require(
                body[i],
                "url",
                "string",
                err_msg="缺少url信息或url类型不正确",
            )
            if new_url in url_list:
                return request_failed(
                    5,
                    "检测到冲突url",
                    status_code=400,
                )
            else:
                url_list.append(new_url)

            url_name = require(
                body[i],
                "name",
                "string",
                err_msg="缺少名字信息或名字类型不正确",
            )
            if url_name in url_name_list:
                return request_failed(
                    5,
                    "检测到冲突url",
                    status_code=400,
                )
            else:
                url_name_list.append(url_name)
        for i in range(0, 5):
            entity_name = require(
                body[i],
                "entity",
                "string",
                err_msg="缺少业务实体信息或业务实体类型不正确",
            )
            new_url = require(
                body[i],
                "url",
                "string",
                err_msg="缺少url信息或url类型不正确",
            )
            url_name = require(
                body[i],
                "name",
                "string",
                err_msg="缺少名字信息或名字类型不正确",
            )
            lvl = require(
                body[i],
                "character",
                "string",
                err_msg="缺少角色信息或角色类型不正确",
            )
            assert 0 < len(entity_name) <= 50, "业务实体长度不合法"
            assert 0 < len(new_url) <= MAX_CHAR_LENGTH, "url长度不合法"
            assert len(lvl) == 1, "角色长度不合法"
            lvl = int(lvl)

            given_entity = Entity.objects.filter(name=entity_name).first()
            if not given_entity:
                return request_failed(
                    2,
                    "给出的业务实体不存在",
                    status_code=400,
                )

            if user.character == 3 and user.entity != given_entity:
                return request_failed(
                    1,
                    "你无此权限",
                    status_code=400,
                )
            old_url_list = list(
                URL.objects.filter(entity=given_entity, authority_level=lvl)
                .all()
                .order_by("id")
            )
            old_url_list[i].name = url_name
            old_url_list[i].url = new_url
            old_url_list[i].save()
        # Loop ends
        prefix = ""
        if lvl == 1:
            prefix = "用户"
        elif lvl == 2:
            prefix = "资产管理员"
        elif lvl == 3:
            prefix = "系统管理员"
        if user.feishu_name != "":
            feishu_utli.send(user, f"您刚刚修改了仅{prefix}可见的第三方 URL 列表!")
        time = timezone.now()

        message = f"管理员 [{user.name}] 修改了仅{prefix}可见的第三方 URL 列表"
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=user,
            entity=given_entity,
            operation_type=2,
            object_type=5,
            object_name=given_entity.name,
            message=message,
        )
        journal.save()
        if given_entity != None:
            given_entity.add_operation_journal(journal.serialize())
        return request_success()

    elif req.method == "GET":
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

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character == 4:
            return request_failed(
                7,
                "超级管理员不能得到URL列表",
                status_code=400,
            )
        urls = []
        if user.character == 1 or user.character == 2:
            urls = list(
                URL.objects.filter(entity=user.entity, authority_level=user.character)
                .all()
                .order_by("id")
            )
        elif user.character == 3:
            urls = list(
                URL.objects.filter(entity=user.entity).all().order_by("authority_level")
            )
        return_data = {
            "data": [
                return_field(
                    valid_url.serialize(),
                    [
                        "id",
                        "url",
                        "name",
                        "authority_level",
                        "entity",
                    ],
                )
                for valid_url in urls
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD
