"""Give every template the signed-in user's menu and access flags from the access policy."""

from . import access


def user_access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"menu": [], "access": {}}
    return {"menu": access.pages_for(user), "access": access.access_flags(user)}
