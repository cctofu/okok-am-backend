from django.http import HttpRequest, HttpResponse
from utils.utils_require import MAX_CHAR_LENGTH, CheckRequire, require


@CheckRequire
def startup(req: HttpRequest):
    return HttpResponse(
        "Congratulations! You have successfully installed the requirements. Go ahead!"
    )
