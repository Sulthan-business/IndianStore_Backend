# dropship/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Fulfillment

class SupplierStatusWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]  # add HMAC later

    def post(self, request):
        # expect { "fulfillment_id": 123, "status": "SHIPPED", "carrier": "...", "tracking_no": "...", "tracking_url": "..." }
        fid = request.data.get("fulfillment_id")
        status = request.data.get("status")
        try:
            f = Fulfillment.objects.get(id=fid)
        except Fulfillment.DoesNotExist:
            return Response({"detail": "Fulfillment not found"}, status=404)

        # minimal validation:
        if status not in dict(Fulfillment.Status.choices):
            return Response({"detail": "Invalid status"}, status=400)

        f.status = status
        f.carrier = request.data.get("carrier", f.carrier)
        f.tracking_no = request.data.get("tracking_no", f.tracking_no)
        f.tracking_url = request.data.get("tracking_url", f.tracking_url)
        f.save()
        return Response({"detail": "Updated", "fulfillment": f.id})
