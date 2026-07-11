from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Doc 3 §7.1: per-user WS group receiving application_status / notification /
    payment_due events pushed from business logic via apps.realtime.push."""

    async def connect(self):
        user = self.scope["user"]
        if user is None or user.is_anonymous:
            await self.close(code=4001)
            return
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        await self.send_json(event["payload"])
