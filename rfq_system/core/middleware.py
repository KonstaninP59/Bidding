from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages

class SimpleLoginRateLimitMiddleware:
    """
    Примитивный rate-limit на POST /login.
    Не идеален, но выполняет требование "ограничение попыток входа".
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/login/" and request.method == "POST":
            ip = request.META.get("REMOTE_ADDR", "unknown")
            key = f"login_fail:{ip}"
            fails = cache.get(key, 0)
            if fails >= 20:
                messages.error(request, "Слишком много попыток входа. Попробуйте позже.")
                return redirect("/login/")
        return self.get_response(request)
