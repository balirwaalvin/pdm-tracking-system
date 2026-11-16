from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .scoping import scope_queryset


class RoleRequiredMixin(LoginRequiredMixin):
    """Allow only users who hold one of `allowed_roles`.

    An empty `allowed_roles` lets any signed-in user through.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.allowed_roles and not (
            request.user.is_superuser or request.user.has_role(*self.allowed_roles)
        ):
            raise PermissionDenied("Your role cannot open this page.")
        return super().dispatch(request, *args, **kwargs)


class ScopedQuerysetMixin:
    """Limit a list or detail view to records inside the user's area."""

    unit_field = "admin_unit"

    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request.user, self.unit_field)


def role_required(*role_names):
    """Decorator for function views: only these roles (or a superuser) may call it."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if not (user.is_superuser or user.has_role(*role_names)):
                raise PermissionDenied("Your role cannot do this.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
