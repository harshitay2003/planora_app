from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task, Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Task)
def task_status_update(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    group_name = f"user_{instance.assigned_to.id}"  # Notify the assigned user

    message = f"Task '{instance.name}' status updated to {instance.status}."

    # Save notification in the database
    notification = Notification.objects.create(user=instance.assigned_to, message=message)

    # Send real-time notification via WebSocket
    async_to_sync(channel_layer.group_send)(
        group_name, {
            "type": "send_notification",
            "id": notification.id,
            "message": notification.message,
            "timestamp": str(notification.timestamp),
            "is_read": notification.is_read
        }
    )
