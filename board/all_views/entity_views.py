from datetime import timedelta
from django.utils import timezone
import json
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
    AsyncTasks,
)

from utils.utils_request import (
    BAD_METHOD,
    request_failed,
    request_success,
    return_field,
)

from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require

PAGE_SIZE = 6


@CheckRequire
def entity(req: HttpRequest, session: any):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        name = require(body, "name", "string", err_msg="缺少变量或者类型错误： [name]")
        assert 0 < len(name) <= 50, "变量长度不符合要求： [entityName]"
        if name.strip() == "":
            return request_failed(
                2,
                "输入业务实体名不合法",
                status_code=400,
            )
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

        if user.character == 1 or user.character == 2 or user.character == 3:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        entity_point = Entity.objects.filter(name=name).first()
        if entity_point:
            return request_failed(
                2,
                "已经有了重名的业务实体。",
                status_code=400,
            )

        entity1 = Entity(name=name)
        entity1.save()

        for i in range(1, 4):
            for j in range(0, 5):
                new_url = URL(
                    url="",
                    name="",
                    authority_level=i,
                    entity=entity1,
                )
                new_url.save()
        return request_success()
    elif req.method == "GET":
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

        if user.character == 1 or user.character == 2 or user.character == 3:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        entitys = Entity.objects.all().order_by("id")
        return_data = {
            "data": [
                return_field(
                    entity.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for entity in entitys
                if entity.name != ""
            ],
        }
        return request_success(return_data)

    elif req.method == "PUT":
        body = json.loads(req.body.decode("utf-8"))
        name = require(body, "name", "string", err_msg="缺少变量或者类型错误： [name]")
        id = require(body, "id", "string", err_msg="缺少变量或者类型错误： [id]")
        id = int(id)

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

        if user.character == 1 or user.character == 2 or user.character == 3:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        entity = Entity.objects.filter(id=id).first()

        if not entity:
            return request_failed(
                2,
                "该ID的业务实体不存在",
                status_code=400,
            )

        if entity.name == name:
            return request_failed(
                3,
                "修改信息不合理",
                status_code=400,
            )

        entity.name = name
        entity.save()
        return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def user_entity(req: HttpRequest, session: any, entity_name: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        assert len(entity_name) <= 50, "变量长度不符合要求： [entityName]"
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character == 1:
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
        entity = Entity.objects.filter(name=entity_name).first()
        if not entity:
            return request_failed(
                2,
                "对应的业务实体不存在",
                status_code=400,
            )
        if user.entity != entity and user.character != 4:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        length = entity.entity_staff.count()
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

        start_index = max(0, start_index)
        end_index = min(end_index, length)

        users = entity.entity_staff.all()[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    user.serialize(),
                    [
                        "id",
                        "name",
                        "entityName",
                        "departmentName",
                        "character",
                        "lock",
                        "email",
                        "password",
                    ],
                )
                for user in users
            ],
        }
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def user_entity4user(req: HttpRequest, session: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or user.character != 1:
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
        entity = user.entity
        # if not entity:
        #     return request_failed(
        #         2,
        #         "对应的业务实体不存在",
        #         status_code=400,
        #     )
        # if user.entity != entity:
        #     return request_failed(
        #         1,
        #         "您无此权限",
        #         status_code=400,
        #     )
        # length = entity.entity_staff.count()
        length = User.objects.filter(entity=entity, character=1).count()
        all_pages = ((length - 1) // 8) + 1

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

        start_index = (page - 1) * 8
        end_index = start_index + 8

        start_index = max(0, start_index)
        end_index = min(end_index, length)

        users = User.objects.filter(entity=entity, character=1)[start_index:end_index]

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    user.serialize(),
                    [
                        "id",
                        "name",
                        "entityName",
                        "departmentName",
                        "email",
                    ],
                )
                for user in users
            ],
        }
        return request_success(return_data)

    else:
        return BAD_METHOD


# @CheckRequire
# def user_entity_2(req: HttpRequest, session: any):
#     if req.method == "GET":
#         if type(session) != str or len(session) != 32 or session.isalnum() == False:
#             return request_failed(
#                 1,
#                 "您给出的session ID是非法的。",
#                 status_code=400,
#             )
#         user = User.objects.filter(session=session).first()
#         if not user:
#             return request_failed(
#                 1,
#                 "您无此权限",
#                 status_code=400,
#             )
#         if user.character != 1:
#             return request_failed(
#                 1,
#                 "只有用户可以调用该API",
#                 status_code=400,
#             )
#         if user.lock:
#             return request_failed(
#                 4,
#                 "您已被锁定",
#                 status_code=400,
#             )  # The user corresponding to the session has been locked
#         users = User.objects.filter(entity=user.entity, character=1).order_by("id")
#         return_data = {
#             "data": [
#                 return_field(
#                     user.serialize(),
#                     [
#                         "id",
#                         "name",
#                         "entityName",
#                         "departmentName",
#                         "email",
#                     ],
#                 )
#                 for user in users
#             ],
#         }
#         return request_success(return_data)

#     else:
#         return BAD_METHOD


@CheckRequire
def cur_entity(req: HttpRequest, session: any):
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

        return_data = {
            "data": return_field(
                user.serialize(),
                [
                    "entityName",
                    "departmentName",
                    "name",
                    "feishu_name",
                    "feishu_phone",
                    "email",
                    "lock",
                ],
            )
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def async_task(req: HttpRequest, session: any):
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

        async_task_list = (
            AsyncTasks.objects.filter(entity=user.entity).order_by("id").all()
        )

        for async_task in async_task_list:
            if async_task.finish == 0:
                current_time = timezone.now() + timezone.timedelta(hours=8)
                create_time = async_task.create_time
                if current_time - create_time >= timedelta(minutes=5):
                    if async_task.number_need == async_task.number_succeed:
                        async_task.finish = 1
                        async_task.save()
                    else:
                        async_task.finish = 2
                        async_task.save()

        return_data = {
            "data": [
                return_field(
                    async_task.serialize(),
                    [
                        "id",
                        "manager",
                        "create_time",
                        "number_need",
                        "number_succeed",
                        "finish",
                        "port_type",
                    ],
                )
                for async_task in async_task_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD
