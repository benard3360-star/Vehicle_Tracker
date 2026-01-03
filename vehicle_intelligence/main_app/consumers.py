import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ParkingRecord

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("dashboard", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard", self.channel_name)

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

# Signal to broadcast updates
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=ParkingRecord)
def broadcast_parking_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "dashboard",
        {
            "type": "send_update",
            "data": {
                "type": "parking_update",
                "plate_number": instance.plate_number,
                "organization": instance.organization,
                "status": instance.parking_status
            }
        }
    )