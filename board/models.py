import json
from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from utils.utils_request import return_field
from datetime import datetime
from django.utils import timezone
from utils.utils_require import MAX_CHAR_LENGTH
from utils.utils_time import MAX_DATE
import math
from datetime import date

# from django.contrib.postgres.fields import ArrayField
# Create your models here.


class Entity(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=MAX_CHAR_LENGTH, unique=True)
    log_journal = models.TextField(blank=True, null=True, default="[]")
    operation_journal = models.TextField(blank=True, null=True, default="[]")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    def set_log_journal(self, journal):
        self.log_journal = json.dumps(journal)

    def get_log_journal(self):
        return json.loads(self.log_journal) if self.log_journal else []

    def add_log_journal(self, record):
        history = self.get_log_journal()
        history.append(record)
        self.set_log_journal(history)
        self.save()

    def set_operation_journal(self, journal):
        self.operation_journal = json.dumps(journal)

    def get_operation_journal(self):
        return json.loads(self.operation_journal) if self.operation_journal else []

    def add_operation_journal(self, record):
        history = self.get_operation_journal()
        history.append(record)
        self.set_operation_journal(history)
        self.save()

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        default=None,
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="department",
    )
    # name = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128, unique=True)
    userNumber = models.IntegerField(default=0)
    subDepartmentNumber = models.IntegerField(default=0)

    def serialize(self):
        if self.parent:  # If parent exists
            return {
                "id": self.id,
                "parentName": self.parent.name,
                "entityName": self.entity.name,
                "name": self.name,
                "userNumber": self.userNumber,
                "subDepartmentNumber": self.subDepartmentNumber,
            }
        else:
            return {  # Otherwise
                "id": self.id,
                "parentName": "",
                "entityName": self.entity.name,
                "name": self.name,
                "userNumber": self.userNumber,
                "subDepartmentNumber": self.subDepartmentNumber,
            }

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        default=None,
        related_name="entity_staff",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        default=None,
        related_name="department_staff",
    )
    character = models.IntegerField(default=1)
    lock = models.BooleanField(default=False)
    session = models.CharField(max_length=32, default="")
    email = models.EmailField(max_length=32, default="")
    feishu_name = models.CharField(max_length=50, default="")
    feishu_open_id = models.CharField(max_length=100, default="")
    feishu_phone = models.CharField(max_length=100, default="")

    def serialize(self):
        if self.department and self.entity:
            return {
                "id": self.id,
                "name": self.name,
                "password": self.password,
                "entityName": self.entity.name,
                "departmentName": self.department.name,
                "character": self.character,
                "lock": self.lock,
                "session": self.session,
                "email": self.email,
                "feishu_name": self.feishu_name,
                "feishu_phone": self.feishu_phone,
            }
        elif self.department and self.entity == None:
            return {
                "id": self.id,
                "name": self.name,
                "password": self.password,
                "entityName": "",
                "departmentName": self.department.name,
                "character": self.character,
                "lock": self.lock,
                "session": self.session,
                "email": self.email,
                "feishu_name": self.feishu_name,
                "feishu_phone": self.feishu_phone,
            }
        elif self.department == None and self.entity:
            return {
                "id": self.id,
                "name": self.name,
                "password": self.password,
                "entityName": self.entity.name,
                "departmentName": "",
                "character": self.character,
                "lock": self.lock,
                "session": self.session,
                "email": self.email,
                "feishu_name": self.feishu_name,
                "feishu_phone": self.feishu_phone,
            }
        else:
            return {
                "id": self.id,
                "name": self.name,
                "password": self.password,
                "entityName": "",
                "departmentName": "",
                "character": self.character,
                "lock": self.lock,
                "session": self.session,
                "email": self.email,
                "feishu_name": self.feishu_name,
                "feishu_phone": self.feishu_phone,
            }

    def __str__(self) -> str:
        return self.name


class AssetTree(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        default=None,
    )
    department = models.CharField(max_length=128)

    def serialize(self):
        if self.parent:  # If parent exists
            return {
                "name": self.name,
                "parentName": self.parent.name,
                "department": self.department,
            }
        else:
            return {  # Otherwise
                "name": self.name,
                "parentName": "",
                "department": self.department,
            }

    def __str__(self) -> str:
        return self.name


class Asset(models.Model):
    id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        default=None,
    )
    name = models.CharField(max_length=128)
    assetClass = models.IntegerField(default=1)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,  # 用户实际上规定不可删除
        related_name="holder",
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    description = models.CharField(max_length=128)
    position = models.CharField(max_length=128)
    expire = models.IntegerField(default=0)
    count = models.IntegerField(default=1)
    assetTree = models.ForeignKey(
        AssetTree,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="asset",
    )
    create_time = models.DateField()
    deadline = models.IntegerField()
    initial_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    warning_date = models.IntegerField(default=-1)
    warning_amount = models.IntegerField(default=-1)
    # depreciation_time = models.DateField()
    status = models.IntegerField(default=1)
    # picture_link_1 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_2 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_3 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_4 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_5 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_6 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_7 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    # picture_link_8 = models.CharField(max_length=MAX_CHAR_LENGTH, default="")
    picture_link = models.JSONField(default=list)
    history = models.TextField(blank=True, null=True)
    richtxt = models.TextField(blank=True, null=True, default="")

    def serialize(self):
        if self.parent:  # If parent exists
            return {
                "id": self.id,
                "parentName": self.parent.name,
                "name": self.name,
                "assetClass": self.assetClass,
                "userName": self.user.name,
                "price": self.price,
                "description": self.description,
                "position": self.position,
                "expire": self.expire,
                "count": self.count,
                "assetTree": self.assetTree.name if self.assetTree else "",
                "departmentName": self.department.name if self.department else "",
                "create_time": self.create_time,
                "deadline": self.deadline,
                "initial_price": self.initial_price,
                "warning_amount": self.warning_amount,
                "warning_date": self.warning_date,
                "expire_date": self.create_time
                + timezone.timedelta(days=self.deadline)
                + timezone.timedelta(hours=8),
                "status": self.status,
                "picture_link": self.picture_link,
            }
        else:
            return {  # Otherwise
                "id": self.id,
                "parentName": "",
                "name": self.name,
                "assetClass": self.assetClass,
                "userName": self.user.name,
                "price": self.price,
                "description": self.description,
                "position": self.position,
                "expire": self.expire,
                "count": self.count,
                "assetTree": self.assetTree.name if self.assetTree else "",
                "departmentName": self.department.name if self.department else "",
                "create_time": self.create_time,
                "deadline": self.deadline,
                "initial_price": self.initial_price,
                "warning_amount": self.warning_amount,
                "warning_date": self.warning_date,
                "expire_date": self.create_time
                + timezone.timedelta(days=self.deadline)
                + timezone.timedelta(hours=8),
                "status": self.status,
                "picture_link": self.picture_link,
            }

    def auto_depreciation(self):
        self.price -= self.initial_price * Decimal(str(1 / self.deadline * 6)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if self.price <= 0.00:
            self.price = 0.00
            self.expire = 1
        if timezone.now().date() >= self.create_time + timezone.timedelta(
            days=self.deadline
        ):
            self.price = 0.00
            self.expire = 1
        self.save()

    def set_history(self, history):
        self.history = json.dumps(history)

    def get_history(self):
        return json.loads(self.history) if self.history else []

    def add_history(self, record):
        history = self.get_history()
        history.append(record)
        self.set_history(history)
        self.save()

    def __str__(self) -> str:
        return self.name


class PendingRequests(models.Model):
    id = models.AutoField(primary_key=True)
    initiator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="initiated_requests",
    )
    participant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="participant_requests",
        null=True,
        blank=True,
    )
    target = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="target_requests",
        null=True,
        blank=True,
        default=None,
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="related_requests",
        null=True,
        blank=True,
    )
    type = models.IntegerField()
    result = models.IntegerField(default=0)
    request_time = models.DateTimeField()
    review_time = models.DateTimeField(default=MAX_DATE)
    count = models.IntegerField(default=1)
    maintain_asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="maintain_requests",
        null=True,
        blank=True,
        default=None,
    )
    feishu_message_id = models.CharField(max_length=100, default="")
    valid = models.IntegerField(default=1)

    def serialize(self):
        if self.target:
            return {
                "id": self.id,
                "initiatorName": self.initiator.name,
                "participantName": self.participant.name,
                "targetName": self.target.name,
                "assetName": self.asset.name,
                "assetID": self.asset.id,
                "type": self.type,
                "result": self.result,
                "request_time": self.request_time.strftime("%Y-%m-%d %H:%M:%S"),
                "review_time": self.review_time.strftime("%Y-%m-%d %H:%M:%S"),
                "count": self.count,
                "valid": self.valid,
            }
        else:
            return {
                "id": self.id,
                "initiatorName": self.initiator.name,
                "participantName": self.participant.name,
                "targetName": "",
                "assetName": self.asset.name,
                "assetID": self.asset.id,
                "type": self.type,
                "result": self.result,
                "request_time": self.request_time.strftime("%Y-%m-%d %H:%M:%S"),
                "review_time": self.review_time.strftime("%Y-%m-%d %H:%M:%S"),
                "count": self.count,
                "valid": self.valid,
            }

    def __str__(self) -> str:
        return self.initiator.name


class URL(models.Model):
    id = models.AutoField(primary_key=True)
    url = models.CharField(max_length=MAX_CHAR_LENGTH)
    name = models.CharField(max_length=50)
    authority_level = models.IntegerField(default=1)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="url",
    )

    def serialize(self):
        return {
            "id": self.id,
            "url": self.url,
            "name": self.name,
            "authority_level": self.authority_level,
            "entity": self.entity.name,
        }

    def __str__(self) -> str:
        return self.name


class Journal(models.Model):
    id = models.BigAutoField(primary_key=True)
    time = models.DateTimeField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="journal",
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="journal",
        null=True,
        blank=True,
        default=None,
    )
    operation_type = models.IntegerField()
    object_type = models.IntegerField()
    object_name = models.CharField(max_length=50)
    message = models.CharField(max_length=500)

    def serialize(self):
        return {
            "id": self.id,
            "time": self.time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user.name,
            "entity": self.entity.name if self.entity else "",
            "operation_type": self.operation_type,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "message": self.message,
        }

    def __str__(self) -> str:
        return self.user.name


class AssetStatistics(models.Model):
    id = models.BigAutoField(primary_key=True)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="asset_statistics",
        default=None,
        blank=True,
        null=True,
    )
    cur_department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="asset_statistics",
    )
    cur_user = models.ForeignKey(
        User,
        related_name="asset_sattistics",
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
    )
    cur_price = models.DecimalField(max_digits=29, decimal_places=2, default=0.00)
    cur_time = models.DateTimeField()
    cur_status = models.IntegerField(default=1)
    cur_count = models.IntegerField(default=0)

    def serialize(self):
        return {
            "id": self.id,
            "cur_name": self.asset.name if self.asset else "",
            "cur_user": self.cur_user.name if self.cur_user else "",
            "cur_department": self.cur_department.name,
            "cur_price": self.cur_price,
            "cur_time": self.cur_time.strftime("%Y-%m-%d %H:%M:%S"),
            "cur_status": self.cur_status,
            "cur_count": self.cur_count,
        }

    def __str__(self) -> str:
        return self.asset.name if self.asset else ""


class AsyncTasks(models.Model):
    id = models.BigAutoField(primary_key=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    manager = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateTimeField()
    number_need = models.IntegerField(default=0)
    number_succeed = models.IntegerField(default=0)
    finish = models.IntegerField(default=0)
    failed_message = models.TextField(blank=True, null=True)
    port_type = models.IntegerField(default=1)

    def serialize(self):
        return {
            "id": self.id,
            "entity": self.entity.name,
            "manager": self.manager.name,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "number_need": self.number_need,
            "number_succeed": self.number_succeed,
            "finish": self.finish,
            "port_type": self.port_type,
        }

    def __str__(self) -> str:
        return self.manager.name

    def set_failed_message(self, record):
        self.failed_message = json.dumps(record)

    def get_failed_message(self):
        return json.loads(self.failed_message) if self.failed_message else []

    def add_failed_message(self, record):
        history = self.get_failed_message()
        history.append(record)
        self.set_failed_message(history)
        self.save()

    def clear_failed_message(self):
        self.set_failed_message([])
        self.save()
