from paker.access.sidebar import get_sidebar_access


def access_context(request):
    return {
        "sidebar_access": get_sidebar_access(request.user),
    }
