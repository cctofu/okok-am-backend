# from board.models import (
#     Entity,
#     User,
#     Department,
#     PendingRequests,
#     Asset,
#     AssetTree,
#     URL,
#     Journal,
# )

# super_manager = User.objects.filter(name="manager").first()
# if not super_manager:
#     User.objects.create(
#         name="manager",
#         password="c4d038b4bed09fdb1471ef51ec3a32cd",
#         character=4,
#     )
# else:
#     super_manager.name = "manager"
#     super_manager.password = "c4d038b4bed09fdb1471ef51ec3a32cd"
#     super_manager.character = 4
#     super_manager.save()
