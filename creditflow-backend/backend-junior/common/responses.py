from rest_framework.response import Response


def success_response(data, status_code=200):
    """Plain single-resource success response per DOC 0 §5.2 (no envelope)."""
    return Response(data, status=status_code)
