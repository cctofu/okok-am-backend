import json
from copy import deepcopy
from django.http import HttpRequest
from django.db.models import F
from board.models import (
    User,
    Department,
    PendingRequests,
    Asset,
    AssetTree,
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


def get_all_sub_assets(parent_asset: Asset):
    sub_assets = Asset.objects.filter(parent=parent_asset, count__gt=0).all()
    result = list(sub_assets)
    if len(result) > 0:
        for sub_asset in sub_assets:
            result.extend(get_all_sub_assets(sub_asset))
    return result


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


@CheckRequire
def pending_request(req: HttpRequest, session: any):
    if req.method == "POST":
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
            )  # The user corresponding to the session was not found
        if user.lock:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        initial_name = require(
            body,
            "initiator",
            "string",
            err_msg="缺少 [initiator] 或 [initiator] 类型不正确",
        )
        participant_name = require(
            body,
            "participant",
            "string",
            err_msg="缺少 [participant] 或 [participant] 类型不正确",
        )
        target_name = require(
            body,
            "target",
            "string",
            err_msg="缺少 [target] 或 [target] 类型不正确",
        )
        asset_id = require(
            body,
            "asset_id",
            "string",
            err_msg="缺少 [asset_id] 或 [asset_id] 类型不正确",
        )
        type1 = require(
            body,
            "type",
            "string",
            err_msg="缺少 [type] 或 [type] 类型不正确",
        )
        cnt = require(
            body,
            "count",
            "string",
            err_msg="缺少 [count] 或 [count] 类型不正确",
        )
        asset_id = int(asset_id)
        type1 = int(type1)
        cnt = int(cnt)
        initial_user = User.objects.filter(name=initial_name).first()
        if not initial_user:
            return request_failed(
                2,
                "提交请求的用户不存在",
                status_code=400,
            )
        if initial_user.character != 1:
            return request_failed(
                2,
                "提交请求的用户的角色不合法",
                status_code=400,
            )
        if user.name != initial_name:
            return request_failed(
                9,
                "Hacker detected!",
                status_code=400,
            )
        participant_user = User.objects.filter(name=participant_name).first()
        if not participant_user:
            return request_failed(
                3,
                "通过请求的 用户不存在",
                status_code=400,
            )
        if participant_user.character != 2 or participant_user.entity != user.entity:
            return request_failed(
                8,
                "通过请求的 用户的角色不合法",
                status_code=400,
            )
        if target_name != "":
            target_user = User.objects.filter(name=target_name).first()
            if not target_user:
                return request_failed(
                    9,
                    "未找到目标用户",
                    status_code=400,
                )
            elif target_user.character != 1 or target_user.entity != user.entity:
                return request_failed(
                    8,
                    "通过资产的 用户的角色不合法",
                    status_code=400,
                )
        else:
            target_user = None

        if type1 != 1 and type1 != 2 and type1 != 3 and type1 != 4:
            return request_failed(
                5,
                "申请类型不合法",
                status_code=400,
            )
        if type1 == 1:
            tar_asset = Asset.objects.filter(
                id=asset_id,
                user=participant_user,
                expire=0,
                count__gt=0,
            ).first()
        elif type1 == 2 or type1 == 3 or type1 == 4:
            tar_asset = Asset.objects.filter(
                id=asset_id,
                user=initial_user,
                expire=0,
                count__gt=0,
            ).first()
        else:
            tar_asset = None
        if tar_asset == None:
            return request_failed(
                4,
                "所涉及的资产不存在",
                status_code=400,
            )
        if tar_asset.assetClass == 0 and cnt > 1:
            return request_failed(
                3,
                f"资产{tar_asset.name}不是数量型资产，请重新检查",
                status_code=400,
            )
        if tar_asset.assetClass == 1:
            if cnt > tar_asset.count:
                return request_failed(
                    4,
                    f"资产{tar_asset.name}数量不足",
                    status_code=400,
                )
        if cnt <= 0:
            return request_failed(
                250,
                "如果您不想获得此资产，请什么都不做，而不是浪费时间",
                status_code=400,
            )
        conflict_request = PendingRequests.objects.filter(
            initiator=initial_user,
            participant=participant_user,
            target=target_user,
            asset=tar_asset,
            type=type1,
            result=0,
        ).first()
        if conflict_request:
            return request_failed(
                6,
                "不要那么操之过急，操之过急也没用",
                status_code=400,
            )
        pending_request = PendingRequests(
            initiator=initial_user,
            participant=participant_user,
            target=target_user,
            asset=tar_asset,
            type=type1,
            request_time=timezone.now() + timezone.timedelta(hours=8),
            count=cnt,
        )
        pending_request.save()
        time = timezone.now()
        if type1 == 1:
            message = f"用户 [{str(initial_name)}] 向管理员 [{str(participant_name)}] 申请资产领用: {cnt} × [{tar_asset.name}]"
            if initial_user.feishu_name != "":
                feishu_utli.send_approval_success(
                    initial_user,
                    "资产领用",
                    f"您向资产管理员{str(participant_name)}请求领用{cnt} × {tar_asset.name},请确认.",
                )
            if participant_user.feishu_name != "" and initial_user.feishu_name != "":
                message_id = feishu_utli.recieve_pending_approval(
                    participant_user,
                    "资产领用",
                    initial_user,
                    f"您收到{str(initial_user.name)}请求领用{cnt} × {tar_asset.name}的申请,请尽快审批.",
                )
                pending_request.feishu_message_id = message_id
                pending_request.save()
        if type1 == 2:
            message = f"用户 [{str(initial_name)}] 向管理员 [{str(participant_name)}] 申请资产退库: {cnt} × [{tar_asset.name}]"
            if initial_user.feishu_name != "":
                feishu_utli.send_approval_success(
                    initial_user,
                    "资产退库",
                    f"您向资产管理员{str(participant_name)}请求退库{cnt} × {tar_asset.name},请确认.",
                )
            if participant_user.feishu_name != "" and initial_user.feishu_name != "":
                message_id = feishu_utli.recieve_pending_approval(
                    participant_user,
                    "资产退库",
                    initial_user,
                    f"您收到{str(initial_user.name)}请求退库{cnt} × {tar_asset.name}的申请,请尽快审批.",
                )
                pending_request.feishu_message_id = message_id
                pending_request.save()
        if type1 == 3:
            message = f"用户 [{str(initial_name)}] 向管理员 [{str(participant_name)}] 申请资产维保: {cnt} × [{tar_asset.name}]"
            if initial_user.feishu_name != "":
                feishu_utli.send_approval_success(
                    initial_user,
                    "资产维保",
                    f"您向资产管理员{str(participant_name)}请求维保{cnt} × {tar_asset.name},请确认.",
                )
            if participant_user.feishu_name != "" and initial_user.feishu_name != "":
                message_id = feishu_utli.recieve_pending_approval(
                    participant_user,
                    "资产维保",
                    initial_user,
                    f"您收到{str(initial_user.name)}请求维保{cnt} × {tar_asset.name}的申请,请尽快审批.",
                )
                pending_request.feishu_message_id = message_id
                pending_request.save()
        if type1 == 4:
            message = f"用户 [{str(initial_name)}] 向管理员 [{str(participant_name)}] 申请资产转移: 转移 {cnt} × [{tar_asset.name}] 至用户 [{str(target_user.name)}]"
            if initial_user.feishu_name != "":
                feishu_utli.send_approval_success(
                    initial_user,
                    "资产转移",
                    f"您向资产管理员{str(participant_user.name)}请求转移{cnt} × {tar_asset.name}给用户{str(target_user.name)},请确认.",
                )
            if participant_user.feishu_name != "" and initial_user.feishu_name != "":
                message_id = feishu_utli.recieve_pending_approval(
                    participant_user,
                    "资产转移",
                    initial_user,
                    f"您收到{str(initial_user.name)}请求转移{cnt} × {tar_asset.name}给用户{str(target_user.name)}的申请,请尽快审批.",
                )
                pending_request.feishu_message_id = message_id
                pending_request.save()
        if initial_user.feishu_name != "":
            feishu_utli.send(initial_user, "您的申请已经成功提交,请耐心等待管理员审批.")
        if participant_user.feishu_name != "":
            feishu_utli.send(participant_user, "您收到了新的申请,请尽快前去审批.")
        journal = Journal(
            time=time + timezone.timedelta(hours=8),
            user=initial_user,
            operation_type=3,
            object_type=4,
            object_name=participant_name,
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
def pending_request_list(req: HttpRequest, session: any, asset_manager_name: any):
    if req.method == "GET":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user or user.character == 3 or user.character == 4:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        if user.lock:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        asset_manager = User.objects.filter(name=asset_manager_name).first()
        if not asset_manager and user.character == 2:
            return request_failed(
                2,
                "对应名字的资产管理员不存在",
                status_code=400,
            )
        if user.character == 2 and user.entity != asset_manager.entity:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )
        request_list = []
        if user.character == 2 or user.character == 4:
            request_list = PendingRequests.objects.filter(
                participant=asset_manager,
                # result=0,
            ).order_by("result", "-request_time")
        elif user.character == 1:
            request_list = PendingRequests.objects.filter(
                initiator=user,
            ).order_by("result", "-request_time")
            # elif user.character == 4:
            # request_list = (
            #     PendingRequests.objects.filter(
            #         participant=asset_manager,
            #     )
            #     .all()
            #     .order_by("request_time")
            # )
        # for request in request_list:
        #     if request.asset.count < request.count:
        #         request.valid = 0
        #         request.save()
        request_update_valid(request_list)
        return_data = {
            "data": [
                return_field(
                    request.serialize(),
                    [
                        "id",
                        "initiatorName",
                        "participantName",
                        "targetName",
                        "assetName",
                        "assetID",
                        "type",
                        "result",
                        "request_time",
                        "review_time",
                        "count",
                        "valid",
                    ],
                )
                for request in request_list
            ],
        }
        return request_success(return_data)
    else:
        return BAD_METHOD


@CheckRequire
def return_pending_request(req: HttpRequest, session: any):
    if req.method == "PUT":
        if type(session) != str or len(session) != 32 or session.isalnum() == False:
            return request_failed(
                2,
                "用户的会话标识符信息不正确",
                status_code=400,
            )  # The session is wrong

        user = User.objects.filter(session=session).first()
        if not user or user.character != 2:
            return request_failed(
                1,
                "你无此权限",
                status_code=400,
            )  # The user corresponding to the session was not found
        if user.lock:
            return request_failed(
                4,
                "你已被锁定，无法进行该操作",
                status_code=400,
            )
        body = json.loads(req.body.decode("utf-8"))
        id = int(
            require(
                body,
                "id",
                "string",
                err_msg="缺少 [id] 或 [id] 类型不正确",
            ),
        )
        request = PendingRequests.objects.filter(id=id, participant=user).first()
        if not request:
            return request_failed(
                1,
                "资产管理员下的该请求不存在",
                status_code=400,
            )
        result = int(
            require(
                body,
                "result",
                "string",
                err_msg="缺少 [result] 或 [result] 类型不正确",
            )
        )
        request.result = result
        request.review_time = timezone.now() + timezone.timedelta(hours=8)
        request.save()
        time = timezone.now()
        cur_asset = request.asset
        if result == 1:
            # print(f"{request.asset.name}审批有效性：{request.valid}")
            if request.valid == 0:
                # print("ERROOOOOO")
                return request_failed(
                    7,
                    "该审批单已失效，无法通过此申请",
                    status_code=400,
                )
            if request.type == 1:
                message = f"管理员 [{str(user.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产领用申请: {str(request.count)} × [{str(cur_asset.name)}]"
                if request.initiator.feishu_name != "":
                    feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
                if user.feishu_name != "":
                    feishu_utli.send(user, f"您刚才成功通过了{str(request.initiator.name)}的申请.")
            elif request.type == 2:
                message = f"管理员 [{str(user.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产退库申请: {str(request.count)} × [{str(cur_asset.name)}]"
                if request.initiator.feishu_name != "":
                    feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
                if user.feishu_name != "":
                    feishu_utli.send(user, f"您刚才成功通过了{str(request.initiator.name)}的申请.")
            elif request.type == 3:
                if cur_asset.assetClass == 0:
                    cur_asset.status = 3
                    cur_asset.user = request.participant
                    request.maintain_asset = cur_asset
                    cur_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "维保",
                            "message": f"资产交付给资产管理者 {request.participant.name} 进行维护",
                        }
                    )
                else:
                    # prev_maintain_asset = Asset.objects.filter(
                    #     user=request.participant,
                    #     name=cur_asset.name,
                    #     parent=cur_asset.parent,
                    #     price=cur_asset.price,
                    #     description=cur_asset.description,
                    #     position=cur_asset.position,
                    #     assetTree=cur_asset.assetTree,
                    #     count__gt=0,
                    #     expire=0,
                    #     status=3,
                    #     create_time=cur_asset.create_time,
                    #     deadline=cur_asset.deadline,
                    # ).first()
                    # if prev_maintain_asset:
                    #     prev_maintain_asset.count += request.count
                    #     prev_maintain_asset.save()
                    # else:
                    new_maintain_asset = Asset.objects.create(
                        user=request.participant,
                        name=cur_asset.name,
                        parent=cur_asset.parent,
                        price=cur_asset.price,
                        initial_price=cur_asset.initial_price,
                        description=cur_asset.description,
                        position=cur_asset.position,
                        assetTree=cur_asset.assetTree,
                        department=cur_asset.department,
                        picture_link=cur_asset.picture_link,
                        warning_date=cur_asset.warning_date,
                        warning_amount=cur_asset.warning_amount,
                        count=request.count,
                        expire=0,
                        status=3,
                        create_time=timezone.now().date(),
                        deadline=cur_asset.deadline,
                    )
                    cur_asset.count -= request.count
                    request.maintain_asset = new_maintain_asset
                    cur_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "维保",
                            "message": f"{request.count}个资产交付给资产管理员{request.participant.name}进行维保",
                        }
                    )
                cur_asset.save()
                request.save()
                message = f"管理员 [{str(user.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产维保申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 4:
                message = f"管理员 [{str(user.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产转移申请: 转移 {str(request.count)} × [{str(cur_asset.name)}] 至用户 [{str(request.target.name)}]"
            if request.initiator.feishu_name != "":
                feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
            if user.feishu_name != "":
                feishu_utli.send(user, f"您刚才成功通过了{str(request.initiator.name)}的申请.")
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=user,
                operation_type=2,
                object_type=4,
                object_name=request.initiator.name,
                message=message,
                entity=user.entity,
            )
            if user.character != 4:
                user.entity.add_operation_journal(journal.serialize())
            journal.save()
            if request.feishu_message_id != "":
                feishu_utli.update_pending_approval(request.feishu_message_id, 1)
        elif result == 2:
            if request.type == 1:
                message = f"管理员 [{str(user.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产领用申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 2:
                message = f"管理员 [{str(user.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产退库申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 3:
                message = f"管理员 [{str(user.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产维保申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 4:
                message = f"管理员 [{str(user.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产转移申请: 转移 {str(request.count)} × [{str(cur_asset.name)}] 至用户 [{str(request.target.name)}]"
            if request.initiator.feishu_name != "":
                feishu_utli.send(request.initiator, "很抱歉,您提交的申请没有通过.")
            if user.feishu_name != "":
                feishu_utli.send(user, f"您刚才拒绝了{str(request.initiator.name)}的申请.")
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=user,
                operation_type=2,
                object_type=4,
                object_name=request.initiator.name,
                message=message,
                entity=user.entity,
            )
            journal.save()
            if user.character != 4:
                user.entity.add_operation_journal(journal.serialize())
            if request.feishu_message_id != "":
                feishu_utli.update_pending_approval(request.feishu_message_id, 2)
        requests = PendingRequests.objects.filter(asset=request.asset).all()
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
def feishu_approval(req: HttpRequest):
    if req.method == "POST":
        body = json.loads(req.body.decode("utf-8"))
        action_type = body["action_type"]
        message_id = body["message_id"]
        request = PendingRequests.objects.filter(feishu_message_id=message_id).first()
        if not request:
            return request_failed(
                1,
                "对应id不存在",
                status_code=400,
            )
        if action_type == "APPROVE":
            request.result = 1
        elif action_type == "REJECT":
            request.result = 2
        else:
            return request_failed(
                11,
                "操作类型无效!",
                status_code=400,
            )
        request.review_time = timezone.now() + timezone.timedelta(hours=8)
        request.save()
        time = timezone.now()
        cur_asset = request.asset
        if request.result == 1:
            if request.type == 1:
                message = f"管理员 [{str(request.participant.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产领用申请: {str(request.count)} × [{str(cur_asset.name)}]"
                if request.initiator.feishu_name != "":
                    feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
                if request.participant.name != "":
                    feishu_utli.send(
                        request.participant,
                        f"您刚才成功通过了{str(request.initiator.name)}的申请.",
                    )
            elif request.type == 2:
                message = f"管理员 [{str(request.participant.name)}] 通过了用户 {str(request.initiator.name)} 的资产退库申请: {str(request.count)} × [{str(cur_asset.name)}]"
                if request.initiator.feishu_name != "":
                    feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
                if request.participant.feishu_name != "":
                    feishu_utli.send(
                        request.participant,
                        f"您刚才成功通过了{str(request.initiator.name)}的申请.",
                    )
            elif request.type == 3:
                if cur_asset.assetClass == 0:
                    cur_asset.status = 3
                    cur_asset.user = request.participant
                    request.maintain_asset = cur_asset
                else:
                    # prev_maintain_asset = Asset.objects.filter(
                    #     user=request.participant,
                    #     name=cur_asset.name,
                    #     parent=cur_asset.parent,
                    #     price=cur_asset.price,
                    #     description=cur_asset.description,
                    #     position=cur_asset.position,
                    #     assetTree=cur_asset.assetTree,
                    #     count__gt=0,
                    #     expire=0,
                    #     status=3,
                    #     create_time=cur_asset.create_time,
                    #     deadline=cur_asset.deadline,
                    # ).first()
                    # if prev_maintain_asset:
                    #     prev_maintain_asset.count += request.count
                    #     prev_maintain_asset.save()
                    # else:
                    new_maintain_asset = Asset.objects.create(
                        user=request.participant,
                        name=cur_asset.name,
                        parent=cur_asset.parent,
                        price=cur_asset.price,
                        initial_price=cur_asset.initial_price,
                        description=cur_asset.description,
                        position=cur_asset.position,
                        assetTree=cur_asset.assetTree,
                        department=cur_asset.department,
                        picture_link=cur_asset.picture_link,
                        warning_date=cur_asset.warning_date,
                        warning_amount=cur_asset.warning_amount,
                        count=request.count,
                        expire=0,
                        status=3,
                        create_time=timezone.now().date(),
                        deadline=cur_asset.deadline,
                    )
                    cur_asset.count -= request.count
                    request.maintain_asset = new_maintain_asset
                cur_asset.save()
                request.save()
                message = f"管理员 [{str(request.participant.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产维保申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 4:
                message = f"管理员 [{str(request.participant.name)}] 通过了用户 [{str(request.initiator.name)}] 的资产转移申请: 转移 {str(request.count)} × [{str(cur_asset.name)}] 至用户 [{str(request.target.name)}]"

            if request.initiator.feishu_name != "":
                feishu_utli.send(request.initiator, "您提交的申请已经成功通过.")
            if request.participant.feishu_name != "":
                feishu_utli.send(
                    request.participant, f"您刚才成功通过了{str(request.initiator.name)}的申请."
                )
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=request.participant,
                operation_type=2,
                object_type=4,
                object_name=request.initiator.name,
                message=message,
                entity=request.participant.entity,
            )
            journal.save()
        elif request.result == 2:
            if request.type == 1:
                message = f"管理员 [{str(request.participant.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产领用申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 2:
                message = f"管理员 [{str(request.participant.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产退库申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 3:
                message = f"管理员 [{str(request.participant.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产维保申请: {str(request.count)} × [{str(cur_asset.name)}]"
            elif request.type == 4:
                message = f"管理员 [{str(request.participant.name)}] 拒绝了用户 [{str(request.initiator.name)}] 的资产转移申请: 转移 {str(request.count)} × [{str(cur_asset.name)}] 至用户 [{str(request.target.name)}]"
            if request.initiator.feishu_name != "":
                feishu_utli.send(request.initiator, "很抱歉,您提交的申请没有通过.")
            if request.participant.feishu_name != "":
                feishu_utli.send(
                    request.participant, f"您刚才拒绝了{str(request.initiator.name)}的申请."
                )
            journal = Journal(
                time=time + timezone.timedelta(hours=8),
                user=request.participant,
                operation_type=2,
                object_type=4,
                object_name=request.initiator.name,
                message=message,
                entity=request.participant.entity,
            )
            journal.save()
            requests = PendingRequests.objects.filter(asset=request.asset).all()
            request_update_valid(requests)
            requests = PendingRequests.objects.filter(valid=0).all()
            if requests != None:
                for i in requests:
                    if i.feishu_message_id != "":
                        feishu_utli.update_pending_approval(i.feishu_message_id, 2)
        if request.type == 1 and request.result == 1:
            asset = request.asset
            if asset == None:
                return request_failed(
                    2,
                    "资产不存在",
                    status_code=400,
                )
            user = request.participant
            asset_receiver = request.initiator
            cnt = request.count
            if asset_receiver == None:
                return request_failed(
                    2,
                    "指定名称的资产管理员不存在",
                    status_code=400,
                )
            if asset_receiver.character != 1:
                return request_failed(
                    2,
                    "只有用户才能接收资产",
                    status_code=400,
                )
            if asset_receiver.department != user.department:
                return request_failed(
                    2,
                    "资产接收者与资产管理人不在同一部门下。",
                    status_code=400,
                )
            if cnt <= 0:
                return request_failed(
                    250,
                    "如果您不想要此资产，请什么都不做，而不是浪费时间",
                    status_code=400,
                )
            if cnt > 1 and asset.assetClass == 0:
                return request_failed(
                    3,
                    f"资产{asset.name}不是数量类型资产，请再次检查",
                    status_code=400,
                )
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产{asset.name}数量不足",
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
                                "message": f"由于用户{asset_receiver.name}的领用，资产数量增加了{cnt}",
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
                            # # warning_date=wd,
                            # # warning_amount=wa,
                            status=2,
                        )
                        asset1.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "领用",
                                "message": f"{cnt}个资产由用户{asset_receiver.name}领用",
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
                                "message": f"由于用户{asset_receiver.name}的领用，资产数量减少了{cnt}",
                            }
                        )
                    else:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "领用",
                                "message": f"默认分类均由用户{asset_receiver.name}领用",
                            }
                        )
                    asset.save()
                    requests = PendingRequests.objects.filter(asset=request.asset).all()
                    request_update_valid(requests)
                    requests = PendingRequests.objects.filter(valid=0).all()
                    if requests != None:
                        for i in requests:
                            if i.feishu_message_id != "":
                                feishu_utli.update_pending_approval(
                                    i.feishu_message_id, 2
                                )
                    return request_success()
            else:
                asset.user = asset_receiver
                asset.status = 2
                asset.parent = None
                asset.save()
                asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "领用",
                        "message": f"默认分类均由用户{asset_receiver.name}领用",
                    }
                )
                all_sub_assets = get_all_sub_assets(asset)
                for sub_asset in all_sub_assets:
                    sub_asset.user = asset_receiver
                    sub_asset.status = 2
                    sub_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "领用",
                            "message": f"默认分类均由用户{asset_receiver.name}领用",
                        }
                    )
                    sub_asset.save()
                requests = PendingRequests.objects.filter(asset=request.asset).all()
                request_update_valid(requests)
                requests = PendingRequests.objects.filter(valid=0).all()
                if requests != None:
                    for i in requests:
                        if i.feishu_message_id != "":
                            feishu_utli.update_pending_approval(i.feishu_message_id, 2)
                return request_success()
        if request.type == 2 and request.result == 1:
            asset = request.asset
            user = request.participant
            asset_owner = request.initiator
            cnt = request.count
            if asset == None:
                return request_failed(
                    2,
                    "指定 ID 的资产不存在",
                    status_code=400,
                )
            if asset.department != user.department:
                return request_failed(
                    1,
                    "你无此权限",
                    status_code=400,
                )
            if asset_owner == None:
                return request_failed(
                    2,
                    "指定名称的资产获取者不存在",
                    status_code=400,
                )
            if asset_owner.character != 1:
                return request_failed(
                    2,
                    "只有用户能退库资产",
                    status_code=400,
                )
            if asset_owner.department != user.department:
                return request_failed(
                    2,
                    "资产接收者与资产管理员不在同一部门下",
                    status_code=400,
                )
            if asset.user != asset_owner:
                return request_failed(
                    1,
                    "提供的资产所有者无效",
                    status_code=400,
                )
            if cnt <= 0:
                return request_failed(
                    250,
                    "如果您不想归还此资产，则什么都不做，而不是浪费时间",
                    status_code=400,
                )
            if cnt > 1 and asset.assetClass == 0:
                return request_failed(
                    3,
                    f"资产{asset.name}不是数量类型资产，请再次检查",
                    status_code=400,
                )
            if asset.assetClass == 1:
                if asset.count < cnt:
                    return request_failed(
                        4,
                        f"资产{asset.name}的数量不足",
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
                                "message": f"由于用户{user.name}的退库，资产数量增加了{cnt}",
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
                        )
                        asset1.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "退库",
                                "message": f"资产由用户{user.name}退库",
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
                                "message": f"由于用户{user.name}的退库，资产数量减少了{cnt}",
                            }
                        )
                    else:
                        asset.add_history(
                            {
                                "time": (
                                    timezone.now() + timezone.timedelta(hours=8)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "退库",
                                "message": f"默认分类均由用户{user.name}退库",
                            }
                        )
                    asset.save()
                requests = PendingRequests.objects.filter(asset=request.asset).all()
                request_update_valid(requests)
                requests = PendingRequests.objects.filter(valid=0).all()
                if requests != None:
                    for i in requests:
                        if i.feishu_message_id != "":
                            feishu_utli.update_pending_approval(i.feishu_message_id, 2)
                return request_success()
            else:  # 条目型资产，子树转移
                asset.user = user
                asset.status = 1
                asset.parent = None
                asset.add_history(
                    {
                        "time": (timezone.now() + timezone.timedelta(hours=8)).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "type": "退库",
                        "message": f"资产由用户{user.name}退库",
                    }
                )
                asset.save()
                all_sub_assets = get_all_sub_assets(asset)
                for sub_asset in all_sub_assets:
                    sub_asset.user = user
                    sub_asset.status = 1
                    sub_asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "退库",
                            "message": f"资产由用户{user.name}退库",
                        }
                    )
                    sub_asset.save()
                requests = PendingRequests.objects.filter(asset=request.asset).all()
                request_update_valid(requests)
                requests = PendingRequests.objects.filter(valid=0).all()
                if requests != None:
                    for i in requests:
                        if i.feishu_message_id != "":
                            feishu_utli.update_pending_approval(i.feishu_message_id, 2)
                return request_success()
        if request.type == 3 and request.result == 1:
            requests = PendingRequests.objects.filter(asset=request.asset).all()
            request_update_valid(requests)
            requests = PendingRequests.objects.filter(valid=0).all()
            if requests != None:
                for i in requests:
                    if i.feishu_message_id != "":
                        feishu_utli.update_pending_approval(i.feishu_message_id, 2)
            return request_success()
        if request.type == 4 and request.result == 1:
            cnt = request.count
            sender_user = request.initiator
            if sender_user == None:
                return request_failed(
                    2,
                    "对应名字的转移发起人不存在",
                    status_code=400,
                )
            elif sender_user.character != 1:
                return request_failed(
                    2,
                    "转移发起人必须是用户",
                    status_code=400,
                )
            target_user = request.target
            if target_user == None:
                return request_failed(
                    2,
                    "对应名字的转移接收人不存在",
                    status_code=400,
                )
            elif target_user.character != 1:
                return request_failed(
                    2,
                    "转移接收人必须是用户",
                    status_code=400,
                )
            asset = request.asset
            if asset == None:
                return request_failed(
                    2,
                    "指定 ID 的有效资产不存在",
                    status_code=400,
                )
            if asset.department != target_user.department:
                return request_failed(
                    1,
                    "你无此权限",
                    status_code=400,
                )

            if asset.assetClass == 0 and cnt != 1:
                return request_failed(
                    3,
                    f"资产{asset.name}不是数量类型资产，请再次检查",
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
                        "指定名字的资产树结点不存在",
                        status_code=400,
                    )
                if asset.assetClass == 1:
                    if asset.count < cnt:
                        return request_failed(
                            4,
                            f"资产{asset.name}的数量不足",
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
                        ).first()
                        if prev_asset:
                            if prev_asset == asset:
                                return request_failed(
                                    529,
                                    "未进行任何转移",
                                    status_code=400,
                                )
                            prev_asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"由于来自部门{asset.department.name}的用户{sender_user.name}的资产转移，资产数量增加了{cnt}",
                                }
                            )
                            prev_asset.count += cnt
                        else:
                            # same_name_asset = Asset.objects.filter(
                            #     name=asset.name
                            # ).first()
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
                                picture_link=asset.picture_link,
                                richtxt=asset.richtxt,
                            )
                            prev_asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"资产由来自部门{asset.department.name}的用户{sender_user.name}转移",
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
                                    "message": f"由于来自部门{target_user.department.name}的用户{target_user.name}的资产转移，资产数量减少了{cnt}",
                                }
                            )
                        else:
                            asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"资产转移到来自部门{target_user.department.name}的用户{target_user.name}",
                                }
                            )
                        asset.save()
                        requests = PendingRequests.objects.filter(
                            asset=request.asset
                        ).all()
                        request_update_valid(requests)
                        requests = PendingRequests.objects.filter(valid=0).all()
                        if requests != None:
                            for i in requests:
                                if i.feishu_message_id != "":
                                    feishu_utli.update_pending_approval(
                                        i.feishu_message_id, 2
                                    )
                    return request_success()
                else:
                    asset.user = target_user
                    asset.department = department
                    asset.assetTree = asset_node
                    asset.parent = None
                    asset.add_history(
                        {
                            "time": (
                                timezone.now() + timezone.timedelta(hours=8)
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "转移",
                            "message": f"资产转移到来自部门{target_user.department.name}的用户{target_user.name}",
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
                                "message": f"资产转移到来自部门{target_user.department.name}的用户{target_user.name}",
                            }
                        )
                        sub_asset.save()
                    requests = PendingRequests.objects.filter(asset=request.asset).all()
                    request_update_valid(requests)
                    requests = PendingRequests.objects.filter(valid=0).all()
                    if requests != None:
                        for i in requests:
                            if i.feishu_message_id != "":
                                feishu_utli.update_pending_approval(
                                    i.feishu_message_id, 2
                                )
                    return request_success()
            else:  # in the same department
                if asset.assetClass == 1:
                    if asset.count < cnt:
                        return request_failed(
                            4,
                            f"资产{asset.name}数量不足",
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
                        ).first()
                        if prev_asset:
                            if prev_asset == asset:
                                return request_failed(
                                    529,
                                    "未发生转移",
                                    status_code=400,
                                )
                            prev_asset.count += cnt
                            prev_asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"由于来自部门{asset.department.name}的用户{sender_user.name}的资产转移，资产数量增加了{cnt}",
                                }
                            )
                        else:
                            # same_name_asset = Asset.objects.filter(
                            #     name=asset.name
                            # ).first()
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
                            )
                            prev_asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"资产由用户为{sender_user.name}的资产转移",
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
                                    "message": f"由于转移到用户{target_user.name}的资产，资产减少了{cnt}",
                                }
                            )
                        else:
                            asset.add_history(
                                {
                                    "time": (
                                        timezone.now() + timezone.timedelta(hours=8)
                                    ).strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": "转移",
                                    "message": f"资产转移到用户{target_user.name}",
                                }
                            )
                        asset.save()
                    requests = PendingRequests.objects.filter(asset=request.asset).all()
                    request_update_valid(requests)
                    requests = PendingRequests.objects.filter(valid=0).all()
                    if requests != None:
                        for i in requests:
                            if i.feishu_message_id != "":
                                feishu_utli.update_pending_approval(
                                    i.feishu_message_id, 2
                                )
                    return request_success()
                else:  # item asset, may have many subasset
                    asset.user = target_user
                    asset.parent = None
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
                                "message": f"资产转移到用户{target_user.name}",
                            }
                        )
                    requests = PendingRequests.objects.filter(asset=request.asset).all()
                    request_update_valid(requests)
                    requests = PendingRequests.objects.filter(valid=0).all()
                    if requests != None:
                        for i in requests:
                            if i.feishu_message_id != "":
                                feishu_utli.update_pending_approval(
                                    i.feishu_message_id, 2
                                )
                    return request_success()
        return request_success()
    else:
        return BAD_METHOD
