from django.http import HttpResponse
from django.db import connection

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return HttpResponse("OK", status=200)
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=503)
