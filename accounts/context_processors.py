"""Give every template the signed-in user's menu, access flags, active menu item and notifications."""

from django.urls import reverse

from . import access


def _active_key(path, pages):
    """The menu item whose address is the longest start of the current path ("" for home)."""
    best, best_len = "", 0
    for page in pages:
        url = reverse(page.url_name)
        if path.startswith(url) and len(url) > best_len:
            best, best_len = page.key, len(url)
    return best


def user_access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"menu": [], "access": {}, "active_key": "", "notifications": [], "notification_count": 0}
    from dashboards.workspace import tasks_for  # dashboards builds on accounts, so import late

    pages = access.pages_for(user)
    waiting = [task for task in tasks_for(user) if task["count"]]
    return {
        "menu": pages,
        "access": access.access_flags(user),
        "active_key": _active_key(request.path, pages),
        "notifications": waiting,  # the to-do items with something waiting, for the bell
        "notification_count": sum(task["count"] for task in waiting),
    }
