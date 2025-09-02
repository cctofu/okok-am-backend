from django.urls import path, include
import board.views as views
import board.all_views.user_views as userViews
import board.all_views.entity_views as entityViews
import board.all_views.department_views as departmentViews
import board.all_views.asset_views as assetViews
import board.all_views.url_views as urlViews
import board.all_views.journal_views as journalViews
import board.all_views.pending_request_views as pendingRequestViews
import board.all_views.statistics_views as statisticsViews
import board.all_views.qrlogin_views as qrLogin

urlpatterns = [
    # FOR FUN
    path(
        "startup/",
        views.startup,
        name="startup",
    ),
    # user related
    path(
        "login",
        userViews.login,
    ),
    path(
        "user/<session>",
        userViews.user,
    ),
    path(
        "logout",
        userViews.logout,
    ),
    path(
        "character/<session>",
        userViews.character,
    ),
    path(
        "user_list_all/<session>/<page>",
        userViews.user_list_all,
    ),
    path(
        "user_password/<session>",
        userViews.user_password,
    ),
    path(
        "user_email/<session>",
        userViews.user_email,
    ),
    # entity related
    path(
        "entity/<session>",
        entityViews.entity,
    ),
    path(
        "user_entity/<session>/<entity_name>/<page>",
        entityViews.user_entity,
    ),
    path(
        "user_entity4user/<session>/<page>",
        entityViews.user_entity4user,
    ),
    path(
        "cur_entity/<session>",
        entityViews.cur_entity,
    ),
    path(
        "async_task/<session>",
        entityViews.async_task,
    ),
    # department related
    path(
        "user_department/<session>/<department_name>/<page>",
        departmentViews.user_department,
    ),
    path(
        "user_department_2/<session>/<department_name>",
        departmentViews.user_department_2,
    ),
    path(
        "all_departments/<session>/<entity_name>",
        departmentViews.all_departments,
    ),
    path(
        "valid_parent_departments/<session>/<department_name>",
        departmentViews.valid_parent_departments,
    ),
    path(
        "department/<session>",
        departmentViews.department,
    ),
    path(
        "sub_department/<session>/<department_name>",
        departmentViews.sub_department,
    ),
    path(
        "department/<session>/<department_name>",
        departmentViews.department_delete,
    ),
    # asset related
    path(
        "asset_tree/<session>",
        assetViews.asset_tree,
    ),
    path(
        "sub_asset_tree/<session>/<asset_tree_node_name>",
        assetViews.sub_asset_tree,
    ),
    path(
        "asset_tree_root/<session>/<department_name>",
        assetViews.asset_tree_root,
    ),
    path(
        "asset_tree_node/<session>/<asset_tree_node_name>/<page>/<expire>",
        assetViews.asset_tree_node,
    ),
    path(
        "asset/<session>",
        assetViews.asset,
    ),
    path(
        "asset_user_list/<session>/<page>",
        assetViews.asset_user_list,
    ),
    path(
        "asset_manager/<session>/<department_name>",
        assetViews.asset_manager,
    ),
    path(
        "unallocated_asset/<session>/<asset_manager_name>/<page>",
        assetViews.unallocated_asset,
    ),
    path(
        "allot_asset/<session>",
        assetViews.allot_asset,
    ),
    path(
        "transfer_asset/<session>",
        assetViews.transfer_asset,
    ),
    path(
        "maintain_asset/<session>",
        assetViews.maintain_asset,
    ),
    path(
        "expire_asset/<session>",
        assetViews.expire_asset,
    ),
    path(
        "receive_asset/<session>",
        assetViews.receive_asset,
    ),
    path(
        "return_asset/<session>",
        assetViews.return_asset,
    ),
    path(
        "asset_manager_entity/<session>/<entity_name>",
        assetViews.asset_manager_entity,
    ),
    path(
        "asset/<session>/<user_name>/<page>",
        assetViews.get_asset_user,
    ),
    path(
        "get_maintain_list/<session>",
        assetViews.get_maintain_list,
    ),
    path(
        "asset_query/<session>/<id>/<history_type>",
        assetViews.get_history_list,
    ),
    path(
        "picture/<session>/<asset_id>",
        assetViews.picture,
    ),
    path(
        "export_task/<session>",
        assetViews.export,
    ),
    path(
        "export_task/<session>/<id>",
        assetViews.export_task,
    ),
    # url related
    path(
        "url/<session>",
        urlViews.url,
    ),
    # journal related
    path(
        "logjournal/<session>/<entity_name>/<page>",
        journalViews.logjournal,
    ),
    path(
        "operationjournal/<session>/<entity_name>/<page>",
        journalViews.operationjournal,
    ),
    # pending request related
    path(
        "pending_request/<session>",
        pendingRequestViews.pending_request,
    ),
    path(
        "return_pending_request/<session>",
        pendingRequestViews.return_pending_request,
    ),
    path(
        "pending_request_list/<session>/<asset_manager_name>",
        pendingRequestViews.pending_request_list,
    ),
    path(
        "warning/<session>",
        assetViews.warning,
    ),
    path(
        "warning_get/<session>/<page>",
        assetViews.warning_get,
    ),
    path(
        "warning_list/<session>",
        assetViews.warning_list,
    ),
    # statistics related
    path(
        "count_department_asset/<session>",
        statisticsViews.count_department_asset,
    ),
    path(
        "count_status_asset/<session>",
        statisticsViews.count_status_asset,
    ),
    path(
        "info_curve/<session>/<asset_id>/<visible_type>",
        statisticsViews.info_curve,
    ),
    path(
        "count_price_curve/<session>/<visible_type>",
        statisticsViews.count_price_curve,
    ),
    path("qrLogin", qrLogin.qr_login),
    path("feishu_name/<session>", userViews.feishu_name),
    path("feishu_users/<session>", userViews.feishu_users),
    path("feishu_get_event", userViews.feishu_get_event),
    path("feishu_approval", pendingRequestViews.feishu_approval),
    path("failed_task/<session>/<id>", assetViews.failed_task),
    path("post_asset/<session>", assetViews.post_asset),
    path(
        "get_user_all/<session>",
        userViews.search_user_all,
    ),
    path(
        "get_user_department/<session>",
        userViews.search_user_department,
    ),
    path(
        "get_user_entity/<session>",
        userViews.search_user_entity,
    ),
    path(
        "get_logjournal/<session>/<entity_name>",
        journalViews.search_logjournal,
    ),
    path(
        "get_operationjournal/<session>/<entity_name>",
        journalViews.search_operationjournal,
    ),
    path(
        "search_unallocated_assets/<session>/<manager_name>",
        assetViews.search_unallocated_assets,
    ),
    path(
        "search_personal_assets/<session>",
        assetViews.search_personal_assets,
    ),
    path(
        "search_assets/<session>",
        assetViews.search_assets,
    ),
    path(
        "all_item_assets/<session>/<asset_id>",
        assetViews.all_item_assets,
    ),
]
