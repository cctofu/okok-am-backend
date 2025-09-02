import json
from django.http import HttpRequest, HttpResponse
from django.db import transaction
from django.db.models import Q
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
from django.utils import timezone
from . import feishu_utli

PAGE_SIZE = 6


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
def user_department(req: HttpRequest, session: any, department_name: any, page: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        assert len(department_name) <= 128, "变量长度不符合要求： [departmentName]"
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
        department = Department.objects.filter(name=department_name).first()
        if not department:
            return request_failed(
                2,
                "对应的部门未找到",
                status_code=400,
            )
        if (
            user.department != department
            and user.character != 4
            and user.character != 3
        ):
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        length = department.department_staff.count()
        # users = User.objects.filter(department=department).all().order_by("id")
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
        users = department.department_staff.all()[start_index:end_index]

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
def user_department_2(req: HttpRequest, session: any, department_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        assert len(department_name) <= 128, "变量长度不符合要求： [departmentName]"
        user = User.objects.filter(session=session).first()
        if not user:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        if user.character != 1:
            return request_failed(
                1,
                "只有用户可以调用该API",
                status_code=400,
            )
        department = Department.objects.filter(name=department_name).first()
        if not department:
            return request_failed(
                2,
                "对应的部门未找到",
                status_code=400,
            )
        if user.department != department:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        users = User.objects.filter(character=1, department=department)
        return_data = {
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
                # if user.department != None and user.department.name == department_name and user.character == 1
            ],
        }
        return request_success(return_data)

    else:
        return BAD_METHOD


@transaction.atomic
@CheckRequire
def department(req: HttpRequest, session: any):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        entity_name = require(body, "entity", "string", err_msg="缺少变量或者类型错误： [entity]")
        parent_name = require(body, "parent", "string", err_msg="缺少变量或者类型错误： [parent]")
        department_name = require(body, "name", "string", err_msg="缺少变量或者类型错误： [name]")
        assert 0 < len(entity_name) <= 50, "变量长度不符合要求： [entityName]"
        if entity_name.strip() == "":
            return request_failed(
                2,
                "输入业务实体名不合法",
                status_code=400,
            )
        assert 0 < len(department_name) <= 128, "变量长度不符合要求： [departmentName]"
        if department_name.strip() == "":
            return request_failed(
                2,
                "输入部门名不合法",
                status_code=400,
            )
        assert len(parent_name) <= 128, "变量长度不符合要求： [departmentName]"
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
            )

        if user.character == 1 or user.character == 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        given_entity = Entity.objects.filter(name=entity_name).first()
        if not given_entity:
            return request_failed(
                2,
                "给出的业务实体未找到。",
                status_code=400,
            )
        exist_departments = Department.objects.filter(entity=given_entity).all()
        if len(exist_departments) >= 200:
            return request_failed(
                2,
                "一个业务实体下最多有两百个部门。",
                status_code=400,
            )
        if user.character == 3 and user.entity != given_entity:
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

        old_department = Department.objects.filter(
            entity=given_entity, name=department_name
        ).first()
        if old_department:
            return request_failed(
                2,
                "已存在同名的业务实体",
                status_code=400,
            )
        if parent_name == "":
            new_department = Department(
                name=department_name,
                entity=given_entity,
                parent=None,
                userNumber=0,
                subDepartmentNumber=0,
            )
            new_department.save()
            new_node = AssetTree(
                name="默认分类",
                parent=None,
                department=new_department.name,
            )
            new_node.save()
            child_node1 = AssetTree(
                name="数量型资产",
                parent=new_node,
                department=new_department.name,
            )
            child_node1.save()
            child_node2 = AssetTree(
                name="条目型资产",
                parent=new_node,
                department=new_department.name,
            )
            child_node2.save()
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if operation_user.feishu_name != "":
                feishu_utli.send(operation_user, f"您刚刚创建了一个名为{str(department_name)}的部门")
            message = (
                f"管理员 [{str(operation_user.name)}] 创建了部门 [{str(department_name)}] "
            )
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=operation_user,
                operation_type=3,
                object_type=2,
                object_name=department_name,
                message=message,
                entity=given_entity,
            )
            journal.save()
            if given_entity:
                given_entity.add_operation_journal(journal.serialize())
            return request_success()
        else:
            given_parent = Department.objects.filter(name=parent_name).first()
            if not given_parent:
                return request_failed(
                    2,
                    "给定的父部门不存在",
                    status_code=400,
                )
            elif given_parent.entity != given_entity:
                return request_failed(
                    2,
                    "不可以将当前部门的父部门设定为另一个业务实体下的部门",
                    status_code=400,
                )
            else:
                new_department = Department(
                    name=department_name,
                    entity=given_entity,
                    parent=given_parent,
                    userNumber=0,
                    subDepartmentNumber=0,
                )
                new_department.save()
                given_parent.subDepartmentNumber += 1
                given_parent.save()
                temp = given_parent.parent
                while temp != None:
                    temp.subDepartmentNumber += 1
                    temp.save()
                    temp = temp.parent
                new_node = AssetTree(
                    name="默认分类",
                    parent=None,
                    department=new_department.name,
                )
                new_node.save()
                child_node1 = AssetTree(
                    name="数量型资产",
                    parent=new_node,
                    department=new_department.name,
                )
                child_node1.save()
                child_node2 = AssetTree(
                    name="条目型资产",
                    parent=new_node,
                    department=new_department.name,
                )
                child_node2.save()
                time = timezone.now()
                operation_user = User.objects.filter(session=session).first()
                if operation_user.feishu_name != "":
                    feishu_utli.send(
                        operation_user, f"您刚刚创建了一个名为{str(department_name)}的部门"
                    )
                message = (
                    f"管理员 [{str(operation_user.name)}] 创建了部门 [{str(department_name)}] "
                )
                journal = Journal(
                    time=time + timezone.timedelta(hours=8),
                    user=operation_user,
                    operation_type=3,
                    object_type=2,
                    object_name=department_name,
                    message=message,
                    entity=given_entity,
                )
                journal.save()
                if given_entity:
                    given_entity.add_operation_journal(journal.serialize())
                return request_success()
    elif req.method == "PUT":
        body = json.loads(req.body.decode("utf-8"))
        new_parent_name = require(
            body, "parent", "string", err_msg="缺少变量或者类型错误： [parent]"
        )
        new_department_name = require(
            body, "name", "string", err_msg="缺少变量或者类型错误： [name]"
        )
        if new_department_name.strip() == "":
            return request_failed(
                2,
                "输入部门名不合法",
                status_code=400,
            )
        assert 0 < len(new_department_name) <= 128, "变量长度不符合要求： [departmentName]"
        assert len(new_parent_name) <= 128, "变量长度不符合要求： [departmentName]"
        id = require(body, "id", "string", err_msg="缺少变量或者类型错误： [id]")
        id = int(id)

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
            )
        if user.lock and user.character != 4:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked
        if user.character == 1 or user.character == 2:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )

        department = Department.objects.filter(id=id).first()
        if not department:
            return request_failed(
                2,
                "该ID的部门不存在",
                status_code=400,
            )
        if user.character == 3 and user.entity != department.entity:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        old_department = Department.objects.filter(
            entity=user.entity, name=new_department_name
        )
        if old_department:
            old_department_list = list(old_department)
            for i in old_department_list:
                if i.id != department.id:
                    return request_failed(
                        2,
                        "已存在同名的业务实体",
                        status_code=400,
                    )
        if department.name != new_department_name:
            asset_tree_nodes = AssetTree.objects.filter(
                department=department.name
            ).all()
            for i in asset_tree_nodes:
                i.department = new_department_name
                i.save()
        if new_parent_name == "":
            time = timezone.now()
            operation_user = User.objects.filter(session=session).first()
            if department.name != new_department_name:
                message = f"管理员 [{str(operation_user.name)}] 修改了部门名称(id: {str(department.id)})，由 [{str(department.name)}] 修改为 [{str(new_department_name)}] "
            if operation_user.feishu_name != "":
                feishu_utli.send(
                    operation_user, f"您刚刚修改了一个名为{str(department.name)}的部门的名称"
                )
            if department.parent:
                message = f"管理员 [{str(operation_user.name)}] 移除了部门 [{str(department.name)}] 的父部门"
            if operation_user.feishu_name != "":
                feishu_utli.send(
                    operation_user, f"您刚刚修改了一个名为{str(department.name)}的部门的父部门"
                )
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                operation_type=2,
                user=operation_user,
                object_type=2,
                object_name=new_department_name,
                message=message,
                entity=department.entity,
            )
            if department.entity:
                department.entity.add_operation_journal(journal.serialize())
            journal.save()
            old_parent = department.parent
            department.parent = None
            department.name = new_department_name
            department.save()
            while old_parent != None:
                old_parent.subDepartmentNumber -= department.subDepartmentNumber + 1
                old_parent.save()
                old_parent = old_parent.parent
            return request_success()
        else:
            new_parent = Department.objects.filter(name=new_parent_name).first()
            child_list = get_all_sub_departments(department)
            if new_parent == department:
                return request_failed(
                    2,
                    "给出的父部门名不合法",
                    status_code=400,
                )
            if not new_parent:
                return request_failed(
                    2,
                    "给定的父部门不存在",
                    status_code=400,
                )
            elif new_parent.entity != department.entity:
                return request_failed(
                    2,
                    "不可以将部门移至另一个业务实体下。",
                    status_code=400,
                )
            elif new_parent in child_list:
                return request_failed(
                    2,
                    "不可以将该部门的子部门设定为父部门。",
                    status_code=400,
                )
            else:
                time = timezone.now()
                operation_user = User.objects.filter(session=session).first()
                old_parent = department.parent
                if old_parent != new_parent:
                    department.parent = None
                    while old_parent != None:
                        old_parent.subDepartmentNumber -= (
                            department.subDepartmentNumber + 1
                        )
                        old_parent.save()
                        old_parent = old_parent.parent
                    department.parent = new_parent
                    department.name = new_department_name
                    department.save()
                    while new_parent != None:
                        new_parent.subDepartmentNumber += (
                            department.subDepartmentNumber + 1
                        )
                        new_parent.save()
                        new_parent = new_parent.parent
                    message = f"管理员 [{str(operation_user.name)}] 将部门 [{str(department.name)}] 的父部门修改为 [{str(new_parent_name)}]"
                    if operation_user.feishu_name != "":
                        feishu_utli.send(
                            operation_user, f"您刚刚修改了一个名为{str(department.name)}的部门的父部门"
                        )
                else:
                    message = f"管理员 [{str(operation_user.name)}] 修改了部门名称(id: {str(department.id)}), 由 [{str(department.name)}] 修改为 [{str(new_department_name)}] "
                    if operation_user.feishu_name != "":
                        feishu_utli.send(
                            operation_user, f"您刚刚修改了一个原名为{str(department.name)}的部门的名称"
                        )
                    department.name = new_department_name
                    department.save()
                journal = Journal(
                    time=time + timezone.timedelta(hours=8),
                    user=operation_user,
                    operation_type=2,
                    object_type=2,
                    object_name=department.name,
                    message=message,
                    entity=department.entity,
                )
                if department.entity:
                    department.entity.add_operation_journal(journal.serialize())
                journal.save()
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

        if user.lock and user.character != 4:
            return request_failed(
                4,
                "您已被锁定",
                status_code=400,
            )  # The user corresponding to the session has been locked

        if user.character == 1 or user.character == 2 or user.character == 3:
            departments = (
                Department.objects.filter(entity=user.entity, parent=None)
                .all()
                .order_by("id")
            )
            return_data = {
                "data": [
                    return_field(
                        department.serialize(),
                        [
                            "id",
                            "name",
                            "entityName",
                            "userNumber",
                            "subDepartmentNumber",
                        ],
                    )
                    for department in departments
                    if department.name != ""
                ],
            }
            return request_success(return_data)
        elif user.character == 4:
            departments = (
                Department.objects.filter(parent=None).all().order_by("entity_id")
            )
            return_data = {
                "data": [
                    return_field(
                        department.serialize(),
                        [
                            "id",
                            "name",
                            "entityName",
                            "userNumber",
                            "subDepartmentNumber",
                        ],
                    )
                    for department in departments
                    if department.name != ""
                ],
            }
            return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def sub_department(req: HttpRequest, session: any, department_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                1,
                "您给出的session ID是非法的。",
                status_code=400,
            )

        assert len(department_name) <= 128, "变量长度不符合要求： [departmentName]"
        # check if the user exists
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
                "你已被锁定，无法进行该操作",
                status_code=400,
            )  # The user corresponding to the session has been locked

        parent_department = Department.objects.filter(name=department_name).first()
        if not parent_department:
            return request_failed(
                1,
                "给定的父部门不存在",
                status_code=400,
            )

        if user.character == 1 or user.character == 2 or user.character == 3:
            if user.entity != parent_department.entity:
                return request_failed(
                    1,
                    "您无此权限",
                    status_code=400,
                )
            else:
                sub_departments = (
                    Department.objects.filter(parent=parent_department)
                    .all()
                    .order_by("id")
                )
                return_data = {
                    "data": [
                        return_field(
                            sub_department.serialize(),
                            [
                                "id",
                                "name",
                                "userNumber",
                                "subDepartmentNumber",
                            ],
                        )
                        for sub_department in sub_departments
                    ],
                }
                return request_success(return_data)

        elif user.character == 4:
            sub_departments = (
                Department.objects.filter(parent=parent_department).all().order_by("id")
            )
            return_data = {
                "data": [
                    return_field(
                        sub_department.serialize(),
                        [
                            "id",
                            "name",
                            "userNumber",
                            "subDepartmentNumber",
                        ],
                    )
                    for sub_department in sub_departments
                ],
            }
            return request_success(return_data)
    else:
        return BAD_METHOD


@transaction.atomic
@CheckRequire
def department_delete(req: HttpRequest, session: any, department_name: any):
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
        if user.character == 2 or user.character == 1:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        current_department = Department.objects.filter(name=department_name).first()
        if current_department == None:
            return request_failed(
                2,
                "该名称的部门不存在。",
                status_code=400,
            )
        if user.character == 3 and current_department.entity != user.entity:
            return request_failed(
                1,
                "您无此权限",
                status_code=400,
            )
        child_department = Department.objects.filter(parent=current_department).first()
        if child_department != None:
            return request_failed(
                2,
                "不可以删除非叶节点的部门",
                status_code=400,
            )
        users = User.objects.filter(department=current_department).first()
        if users != None:
            return request_failed(
                2,
                "不可以删除有用户的部门",
                status_code=400,
            )
        cur_parent = current_department.parent
        while cur_parent != None:
            cur_parent.subDepartmentNumber -= current_department.subDepartmentNumber + 1
            cur_parent.save()
            cur_parent = cur_parent.parent
        asset_root = AssetTree.objects.filter(
            name="默认分类",
            department=current_department.name,
        ).first()
        if asset_root != None:
            asset_root.delete()
        asset_child = AssetTree.objects.filter(
            name="数量型资产",
            department=current_department.name,
        ).first()
        if asset_child != None:
            asset_child.delete()
        asset_child = AssetTree.objects.filter(
            name="条目型资产",
            department=current_department.name,
        ).first()
        if asset_child != None:
            asset_child.delete()
        time = timezone.now()
        operation_user = User.objects.filter(session=session).first()
        if operation_user.feishu_name != "":
            feishu_utli.send(operation_user, f"您刚刚删除了一个名为{current_department.name}的部门")
        message = f"管理员 [{operation_user.name}] 删除了部门 [{current_department.name}] "
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=operation_user,
            entity=current_department.entity,
            operation_type=4,
            object_type=2,
            object_name=current_department.name,
            message=message,
        )
        journal.save()
        if current_department.entity:
            current_department.entity.add_operation_journal(journal.serialize())
        current_department.delete()
        return request_success()
    else:
        return BAD_METHOD


@CheckRequire
def all_departments(req: HttpRequest, session: any, entity_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or user.character == 1 or user.character == 2:
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
            )
        assert len(entity_name) <= 128, "业务实体名称长度不合法"
        if user.character == 4:
            cur_entity = Entity.objects.filter(name=entity_name).first()
        elif user.character == 3:
            cur_entity = user.entity
        if not cur_entity:
            return request_failed(
                1,
                "指定业务实体不存在",
                status_code=400,
            )
        all_dps = Department.objects.filter(entity=cur_entity).all()
        return_data = {
            "data": [
                return_field(
                    dp.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for dp in all_dps
            ],
        }
        return request_success(return_data)
    else:
        return return_field(BAD_METHOD)


def valid_parent_departments(req: HttpRequest, session: any, department_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "您给出的session ID是非法的。",
                status_code=400,
            )
        user = User.objects.filter(session=session).first()
        if not user or user.character != 3:
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
            )
        assert len(department_name) <= 128, "业务实体名称长度不合法"
        tar_department = Department.objects.filter(
            entity=user.entity, name=department_name
        ).first()
        if not tar_department:
            return request_failed(
                3,
                "当前部门不存在",
                status_code=400,
            )
        invalid_departments = get_all_sub_departments(tar_department)
        invalid_departments.append(tar_department)
        if tar_department.parent != None:
            invalid_departments.append(tar_department.parent)
        invalid_departments_id = [department.pk for department in invalid_departments]
        valid_departments = Department.objects.filter(entity=user.entity).exclude(
            Q(pk__in=invalid_departments_id)
        )
        return_data = {
            "data": [
                return_field(
                    valid_department.serialize(),
                    [
                        "id",
                        "name",
                    ],
                )
                for valid_department in valid_departments
            ],
        }
        return request_success(return_data)
    else:
        return request_failed(BAD_METHOD)
