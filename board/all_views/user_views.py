import json
import random
from django.db import transaction
from django.http import HttpRequest, HttpResponse
import uuid
from django.db.models import F, Q
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
import re
from django.utils import timezone
from datetime import datetime
from django.db.models import Q
from utils.utils_time import MAX_DATE
from . import feishu_utli
from django.core.paginator import Paginator

PAGE_SIZE = 6


def check_for_user_data(body):
    user_name = require(body, "name", "string", err_msg="缺少用户名信息或传入用户名类型不正确")
    new_password = require(body, "password", "string", err_msg="缺少密码信息或传入密码类型不正确")
    user_entity = require(body, "entity", "string", err_msg="缺少业务实体信息或传入业务实体类型不正确")
    department = require(body, "department", "string", err_msg="缺少部门信息或传入部门类型不正确")
    character_str = require(body, "character", "string", err_msg="缺少角色信息或传入角色类型不正确")
    character = int(character_str)
    lock_str = require(body, "lock", "string", err_msg="缺少锁定信息或传入锁定类型不正确")
    lock = False
    if lock_str == "True":
        lock = True
    session = require(body, "session", "string", err_msg="缺少会话标识符信息或会话标识符类型不正确")
    email = require(body, "email", "string", err_msg="缺少邮箱信息或邮箱类型不正确")
    # check the length of name and password and session and entity and department
    assert 0 < len(user_name) <= 50, "输入名字长度不合法"
    if user_name.strip() == "":
        return request_failed(
            2,
            "输入用户名不合法",
            status_code=400,
        )
    assert 0 < len(new_password) <= 50, "输入密码长度不合法"
    assert len(user_entity) <= 50, "输入业务实体长度不合法"
    assert len(department) <= 128, "输入部门长度不合法"
    assert len(session) == 0 or len(session) == 32, "输入会话标识符长度不合法"
    # check if the username and password is valid
    pattern = r"[a-zA-Z0-9\u4e00-\u9fa5]+"
    match = re.match(pattern, user_name)
    assert match != None, "提供的名字无效"
    match = re.match(pattern, new_password)
    assert match != None, "提供的密码无效"
    # check if the entity and department name is valid
    if len(user_entity) != 0:
        match = re.match(pattern, user_entity)
    assert match != None, "提供的业务实体无效"
    if len(department) != 0:
        match = re.match(pattern, department)
    assert match != None, "提供的部门无效"
    # check if the character is valid
    assert (
        character == 1 or character == 2 or character == 3 or character == 4
    ), "提供的用户权限等级不合法"
    # check if the session is valid
    if len(session) != 0:
        assert session.isalnum() == True, "提供的会话标识符无效"
    # check if the email is valid
    if len(email) != 0:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        match = re.match(pattern, email)
        assert match != None, "提供的邮箱格式不合法"
    # return value
    return (
        user_name,
        new_password,
        user_entity,
        department,
        character,
        lock,
        session,
        email,
    )


@CheckRequire
def login(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        identity = require(body, "identity", "string", err_msg="缺少用户名或邮箱信息或用户名或邮箱类型不正确")
        password = require(body, "password", "string", err_msg="缺少密码信息或密码类型不正确")

        user = User.objects.filter(name=identity).first()

        if not user:
            user = User.objects.filter(email=identity).first()
        # check if the user exists
        if not user:
            return request_failed(
                2,
                "用户名或密码错误",
                status_code=400,
            )

        if user.password != password:
            return request_failed(
                2,
                "用户名或密码错误",
                status_code=400,
            )
        if user.lock == True:
            return request_failed(
                3,
                "您已被锁定",
                status_code=400,
            )

        while True:
            session_index = str(uuid.uuid4())
            conflictUser = User.objects.filter(
                session=session_index.replace("-", "")
            ).first()
            if not conflictUser:
                break
        user.session = session_index.replace("-", "")
        user.save()
        return_data = {"data": return_field(user.serialize(), ["session", "character"])}
        if user.feishu_name != "":
            feishu_utli.send(user, "您刚刚登录了启源资产管理系统!")
        time = timezone.now()
        prefix = ""
        if user.character == 1:
            prefix = "用户"
        elif user.character == 2:
            prefix = "资产管理员"
        elif user.character == 3:
            prefix = "系统管理员"
        elif user.character == 4:
            prefix = "尊贵的超级管理员"
        message = f"{prefix} [{str(user.name)}] 登录了启源资产管理系统 "
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=user,
            operation_type=1,
            object_type=1,
            object_name=user.name,
            message=message,
            entity=user.entity,
        )
        journal.save()
        if user.entity:
            user.entity.add_log_journal(journal.serialize())
        return request_success(return_data)

    else:
        return BAD_METHOD


@CheckRequire
def logout(req: HttpRequest):
    if req.method == "PUT":
        body = json.loads(req.body.decode("utf-8"))
        session = require(body, "session", "string", err_msg="缺少会话标识符信息或会话标识符类型不正确")

        if len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "用户还未登录",
                status_code=400,
            )  # The user corresponding to the session was not found

        user.session = ""
        user.save()
        if user.feishu_name != "":
            feishu_utli.send(user, "您刚刚登出了启源资产管理系统!")
        time = timezone.now()
        prefix = ""
        if user.character == 1:
            prefix = "用户"
        elif user.character == 2:
            prefix = "资产管理员"
        elif user.character == 3:
            prefix = "系统管理员"
        elif user.character == 4:
            prefix = "尊贵的超级管理员"
        message = f"{prefix} [{str(user.name)}] 登出了启源资产管理系统 "
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=user,
            operation_type=1,
            object_type=1,
            object_name=user.name,
            message=message,
            entity=user.entity,
        )
        journal.save()
        if user.entity:
            user.entity.add_log_journal(journal.serialize())
        return request_success()

    else:
        return BAD_METHOD


@transaction.atomic
@CheckRequire
def user(req: HttpRequest, session: any):
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
        body = json.loads(req.body.decode("utf-8"))
        (
            user_name,
            new_password,
            user_entity_name,
            user_department_name,
            character,
            lock,
            session_id,
            email,
        ) = check_for_user_data(body)
        if user.character == 1 or user.character == 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        elif user.character == 3 and user.entity.name != user_entity_name:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if user.character == 3 and character == 3:
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
        if character == 4:
            return request_failed(
                10,
                "不能创建一个超级管理员",
                status_code=400,
            )
        # search the entity ,if not exsit ,create a new entity
        if user_entity_name == "" and character != 4:
            return request_failed(
                2,
                "你应该为该用户提供业务实体",
                status_code=400,
            )
        user_entity = Entity.objects.filter(name=user_entity_name).first()
        if not user_entity:
            return request_failed(
                2,
                "提供的业务实体不存在",
                status_code=400,
            )
        if character == 3:
            manager_cnt = User.objects.filter(entity=user_entity, character=3).count()
            if manager_cnt >= 5:
                return request_failed(
                    20,
                    "一个业务实体最多有5个系统管理员",
                    status_code=400,
                )
        # search the department ,if not exsit ,create a new department
        if user_department_name == "" and character != 4 and character != 3:
            return request_failed(
                2,
                "你应该为该用户提供部门",
                status_code=400,
            )
        user_department = Department.objects.filter(
            name=user_department_name, entity=user_entity
        ).first()
        if not user_department:
            if character == 3 and user_department_name == "":
                user_department = None
            else:
                return request_failed(
                    2,
                    "提供的部门不存在",
                    status_code=400,
                )
        if user_department != None:
            exist_users_cnt = User.objects.filter(
                department=user_department, character=1
            ).count()
            if exist_users_cnt >= 550:
                return request_failed(
                    2,
                    "一个部门下最多只能有550个用户",
                    status_code=400,
                )
        if character == 2:
            manager_cnt = User.objects.filter(
                entity=user_entity, department=user_department, character=2
            ).count()
            if manager_cnt >= 5:
                return request_failed(
                    20,
                    "一个部门最多有5个资产管理员",
                    status_code=400,
                )
        # check if the entity of the user and the corresponding department is the same
        if character == 1 or character == 2:
            if user_entity.id != user_department.entity.id:
                return request_failed(
                    2,
                    "提供的部门并不属于用户所属的业务实体，按规定用户所属的部门也必须属于用户所属的业务实体",
                    status_code=400,
                )
        # Find the corresponding user
        seek_user = User.objects.filter(
            name=user_name
        ).first()  # If not exists, return None
        seek_email = User.objects.filter(email=email).first()
        if seek_user:
            return request_failed(
                2,
                "该用户名或邮箱对应的用户已经存在",
                status_code=400,
            )
        if seek_email and email != "":
            return request_failed(
                2,
                "该用户名或邮箱对应的用户已经存在",
                status_code=400,
            )
        else:
            # User not exists, create user
            if user_department != None:
                user_department.userNumber += 1
                user_department.save()
            user = User(
                name=user_name,
                password=new_password,
                entity=user_entity,
                department=user_department,
                character=character,
                lock=lock,
                session=session_id,
                email=email,
            )
            user.save()
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚创建了一个名为{str(user.name)}的用户")
            message = f"管理员 [{str(operation_user.name)}] 创建了用户: 用户名--[{str(user.name)}], 用户id--[{user.id}]"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=3,
                object_type=1,
                object_name=user.name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.character != 4:
                user.entity.add_operation_journal(journal.serialize())
            return request_success()
    elif req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong

        operator = User.objects.filter(session=session).first()
        if not operator:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if operator.character == 1 or operator.character == 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if operator.lock and operator.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        new_password = require(body, "password", "string", err_msg="缺少密码信息或密码类型不正确")
        lock_str = require(body, "lock", "string", err_msg="缺少锁定信息或传入锁定类型不正确")
        lock = False
        if lock_str == "True":
            lock = True
        id = require(body, "id", "string", err_msg="缺少ID信息或ID类型不正确")
        id = int(id)
        user = User.objects.filter(id=id).first()
        if not user:
            return request_failed(
                2,
                "目标用户不存在",
                status_code=400,
            )
        if operator.character == 3 and operator.entity.name != user.entity.name:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if operator != user and (operator.character <= user.character):
            return request_failed(
                5,
                "你无权限修改同级或级别高于你的用户的信息",
                status_code=400,
            )
        if lock == True and operator == user:
            return request_failed(
                250,
                "不要尝试锁定自己 !!!!!",
                status_code=400,
            )
        time = timezone.now()
        operation_user = User.objects.filter(session=session).first()
        message = "DEFAULT"
        if user.lock == 0 and lock == 1:
            message = f"管理员 [{str(operation_user.name)}] 锁定了用户 [{str(user.name)}]"
        if user.lock == 1 and lock == 0:
            message = f"管理员 [{str(operation_user.name)}] 解锁了用户 [{str(user.name)}]"
        if user.password != new_password:
            message = f"管理员 [{str(operation_user.name)}] 修改了用户 [{str(user.name)}] 的密码"
        user.password = new_password
        user.lock = lock
        if message != "DEFAULT":
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=2,
                object_type=1,
                object_name=user.name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.character != 4:
                user.entity.add_operation_journal(journal.serialize())
        user.save()
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def character(req: HttpRequest, session: any):
    if req.method == "GET":
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
                "用户还未登录",
                status_code=400,
            )  # The user corresponding to the session was not found
        else:
            if user.lock and user.character != 4:
                return request_failed(
                    4,
                    "你已被锁定，无法进行该操作",
                    status_code=400,
                )  # The user corresponding to the session has been locked
            return_data = {"data": return_field(user.serialize(), ["character"])}
            return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def feishu_name(req: HttpRequest, session: any):
    if req.method == "PUT":
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
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        feishu_name = require(
            body,
            "feishu_name",
            "string",
            err_msg="缺少飞书用户名信息或飞书用户名类型不正确",
        )
        feishu_phone = require(
            body,
            "feishu_phone",
            "string",
            err_msg="缺少飞书电话号码信息或飞书电话号码类型不正确",
        )
        if feishu_name != "":
            conf_user = User.objects.filter(feishu_name=feishu_name).first()
            if conf_user != None:
                return request_failed(
                    9,
                    "该飞书用户名对应的用户已经存在",
                    status_code=400,
                )
        if feishu_phone != "":
            conf_user = User.objects.filter(feishu_phone=feishu_phone).first()
            if conf_user != None:
                return request_failed(
                    10,
                    "该飞书电话号码对应的用户已经存在",
                    status_code=400,
                )
            feishu_user_name = feishu_utli.get_user(feishu_phone)
            if feishu_user_name != feishu_name:
                return request_failed(
                    11,
                    "飞书用户名与飞书电话号码不匹配",
                    status_code=400,
                )
        user.feishu_name = feishu_name
        user.feishu_phone = feishu_phone
        user.save()
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def feishu_users(req: HttpRequest, session: any):
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
        if (user.lock == True) and (user.character != 4):
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        if user.character != 3:
            return request_failed(
                5,
                "你无此权限",
                status_code=400,
            )
        cur_entity = Entity.objects.filter(name=user.entity).first()
        if cur_entity == None:
            return request_failed(
                6,
                "找不到管理员的实体",
                status_code=400,
            )
        if user.feishu_name == "":
            return request_failed(
                7,
                "管理员尚未绑定飞书用户",
                status_code=400,
            )
        feishu_users = feishu_utli.get_entity_users()
        new_department = Department.objects.filter(entity=cur_entity).first()
        if new_department == None:
            new_department = Department(
                entity=cur_entity, name=cur_entity.name + "_feishu"
            )
            new_department.save()
        for i in feishu_users:
            conf_user = User.objects.filter(feishu_name=i[0]).first()
            if conf_user == None:
                new_name = i[0]
                conf_user = User.objects.filter(name=new_name).first()
                while conf_user != None:
                    new_name = new_name + "1"
                    conf_user = User.objects.filter(name=new_name).first()
                new_department.userNumber += 1
                new_department.save()
                user = User(
                    name=new_name,
                    password="c4d038b4bed09fdb1471ef51ec3a32cd",
                    entity=cur_entity,
                    department=new_department,
                    character=1,
                    lock=False,
                    session="",
                    email="",
                )
                user.feishu_name = i[0]
                user.feishu_phone = i[1]
                user.save()
                time = timezone.now()
                operation_user = User.objects.filter(session=session).first()
                message = f"管理员 [{str(operation_user.name)}] 创建了用户: 用户名--[{str(user.name)}], 用户id--[{user.id}]"
                journal = Journal(
                    time=time + timezone.timedelta(hours=8),
                    user=operation_user,
                    operation_type=3,
                    object_type=1,
                    object_name=user.name,
                    message=message,
                    entity=user.entity,
                )
                journal.save()
                if user.character != 4:
                    user.entity.add_operation_journal(journal.serialize())
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def feishu_get_event(req: HttpRequest):
    if req.method == "POST":
        try:
            body = json.loads(req.body.decode("utf-8"))
            challenge = body["challenge"]
            return_data = {"challenge": challenge}
            return request_success(return_data)
        except:
            body = json.loads(req.body.decode("utf-8"))
            feishu_name = body["event"]["object"]["name"]
            feishu_phone = body["event"]["object"]["mobile"]
            user = User.objects.filter(feishu_name=feishu_name).first()
            if user == None:
                feishu_users = feishu_utli.get_entity_users()
                for i in feishu_users:
                    manager = User.objects.filter(feishu_name=i[0]).first()
                    if manager != None:
                        new_entity = manager.entity
                        new_department = Department.objects.filter(
                            entity=new_entity
                        ).first()
                new_name = feishu_name
                conf_user = User.objects.filter(name=new_name).first()
                while conf_user != None:
                    new_name = new_name + "1"
                    conf_user = User.objects.filter(name=new_name).first()
                new_department.userNumber += 1
                new_department.save()
                user = User(
                    name=new_name,
                    password="c4d038b4bed09fdb1471ef51ec3a32cd",
                    entity=new_entity,
                    department=new_department,
                    character=1,
                    lock=False,
                    session="",
                    email="",
                )
                user.feishu_name = feishu_name
                user.feishu_phone = feishu_phone
                user.save()
            return request_success()

    else:
        return BAD_METHOD


@CheckRequire
def user_list_all(req: HttpRequest, session: any, page: any):
    if req.method == "GET":
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
        if user.character == 1 or user.character == 2 or user.character == 3:
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
        length = User.objects.count()
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
        # paginator = Paginator(users, PAGE_SIZE)
        # users_list = list(paginator.page(page))
        users_list = User.objects.all()[start_index:end_index]
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
                # for user in users[start_index:end_index]
                for user in users_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def user_password(req: HttpRequest, session: any):
    if req.method == "PUT":
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
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        old_password = require(
            body, "oldpassword", "string", err_msg="缺少变量或者类型错误： [oldpassword]"
        )
        new_password = require(
            body, "newpassword", "string", err_msg="缺少变量或者类型错误： [newpassword]"
        )
        if user.password != old_password:
            return request_failed(
                2,
                "您输入的初始密码不正确",
                status_code=400,
            )
        user.password = new_password
        user.save()
        if user.character != 4:
            time = timezone.now()
            message = f"用户 [{str(user.name)}] 修改了自己的密码"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=user,
                operation_type=2,
                object_type=1,
                object_name=user.name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            user.entity.add_operation_journal(journal.serialize())
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def user_email(req: HttpRequest, session: any):
    if req.method == "PUT":
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
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        body = json.loads(req.body.decode("utf-8"))
        old_password = require(
            body, "oldpassword", "string", err_msg="缺少变量或者类型错误： [oldpassword]"
        )
        email = require(body, "email", "string", err_msg="缺少变量或者类型错误： [email]")
        if len(email) > 0:
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            match = re.match(pattern, email)
            assert match != None, "提供的邮箱格式不合法"
        if user.password != old_password:
            return request_failed(
                2,
                "您输入的初始密码不正确",
                status_code=400,
            )
        if user.email != email:
            user1 = User.objects.filter(email=email).first()
            if user1:
                return request_failed(
                    5,
                    "指定邮箱的用户已经存在，无法修改",
                    status_code=400,
                )
        user.email = email
        user.save()
        if user.character != 4:
            time = timezone.now()
            message = f"用户 [{str(user.name)}] 修改了自己的邮箱"
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=user,
                operation_type=2,
                object_type=1,
                object_name=user.name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            user.entity.add_operation_journal(journal.serialize())
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def search_user_all(req: HttpRequest, session: any):
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
        if user.character == 1 or user.character == 2 or user.character == 3:
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
        body = json.loads(req.body.decode("utf-8"))
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        entity = require(body, "entity", "string", err_msg="缺少信息或传入类型不正确")
        department = require(body, "department", "string", err_msg="缺少信息或传入类型不正确")
        character = require(body, "character", "string", err_msg="缺少信息或传入类型不正确")
        lock = require(body, "lock", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        if entity == "" and department != "":
            return request_failed(
                2,
                "传入的业务实体和部门非法",
                status_code=400,
            )
        users = User.objects.filter(name__contains=name).all()
        if id != "":
            id = int(id)
            users = users.filter(id=id).all()
        if entity != "":
            cur_entity = Entity.objects.filter(name=entity).first()
            users = users.filter(entity=cur_entity).all()
        if department != "":
            cur_department = Department.objects.filter(
                name=department, entity=cur_entity
            ).first()
            users = users.filter(department=cur_department).all()
        if character != "":
            cur_character = int(character)
            users = users.filter(character=cur_character).all()
        if lock != "":
            if lock == "1":
                cur_lock = True
            elif lock == "0":
                cur_lock = False
            users = users.filter(lock=cur_lock).all()
        length = len(users)
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
                    ],
                )
                for user in users[start_index:end_index]
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def search_user_department(req: HttpRequest, session: any):
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
        cur_entity = user.entity
        cur_department = user.department
        body = json.loads(req.body.decode("utf-8"))
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        character = require(body, "character", "string", err_msg="缺少信息或传入类型不正确")
        lock = require(body, "lock", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        users = User.objects.filter(
            name__contains=name, entity=cur_entity, department=cur_department
        ).all()
        if id != "":
            id = int(id)
            users = users.filter(id=id).all()
        if character != "":
            cur_character = int(character)
            users = users.filter(character=cur_character).all()
        if lock != "":
            if lock == "1":
                cur_lock = True
            elif lock == "0":
                cur_lock = False
            users = users.filter(lock=cur_lock).all()
        length = len(users)
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
                    ],
                )
                for user in users[start_index:end_index]
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def search_user_entity(req: HttpRequest, session: any):
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
        if user.character != 3:
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
        cur_entity = user.entity
        body = json.loads(req.body.decode("utf-8"))
        id = require(body, "id", "string", err_msg="缺少信息或传入类型不正确")
        name = require(body, "name", "string", err_msg="缺少信息或传入类型不正确")
        department = require(body, "department", "string", err_msg="缺少信息或传入类型不正确")
        character = require(body, "character", "string", err_msg="缺少信息或传入类型不正确")
        lock = require(body, "lock", "string", err_msg="缺少信息或传入类型不正确")
        page = require(body, "page", "string", err_msg="缺少信息或传入类型不正确")
        users = User.objects.filter(name__contains=name, entity=cur_entity).all()
        if id != "":
            id = int(id)
            users = users.filter(id=id).all()
        if department != "":
            cur_department = Department.objects.filter(name=department).first()
            users = users.filter(department=cur_department).all()
        if character != "":
            cur_character = int(character)
            users = users.filter(character=cur_character).all()
        if lock != "":
            if lock == "1":
                cur_lock = True
            elif lock == "0":
                cur_lock = False
            users = users.filter(lock=cur_lock).all()
        length = len(users)
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

        return_data = {
            "pages": all_pages,
            "data": [
                return_field(
                    user.serialize(),
                    [
                        "id",
                        "entityName",
                        "departmentName",
                        "character",
                        "lock",
                        "email",
                    ],
                )
                for user in users[start_index:end_index]
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD
