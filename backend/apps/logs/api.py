from ninja import Router
from api.dependencies import AuthBearer

router = Router()


@router.get("/", auth=AuthBearer())
def list_logs(request):
    from .models import APILog
    logs = APILog.objects.filter(user=request.auth)[:100]
    return [{"endpoint": log.endpoint, "method": log.method, "status": log.status_code} for log in logs]


@router.get("/errors", auth=AuthBearer())
def list_errors(request):
    from .models import APILog
    errors = APILog.objects.filter(user=request.auth, status_code__gte=400)[:100]
    return [{"endpoint": e.endpoint, "error": e.error_message, "created_at": e.created_at} for e in errors]
