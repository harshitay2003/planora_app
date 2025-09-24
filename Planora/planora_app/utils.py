from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_task_assignment_email(user_email, task_name, due_date):
    print("inside send task email")
    subject = "New Task Assigned to You"
    message = f"Hello,\n\nYou have been assigned a new task: {task_name}.\nDeadline: {due_date}.\n\nPlease check your dashboard for more details."
    
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user_email])

def send_deadline_reminder_email(user_email, task_name, due_date):
    subject = "Task Deadline Reminder"
    message = f"Reminder: Your task '{task_name}' is due on {due_date}. Please complete it on time."

    send_mail(subject, message, settings.EMAIL_HOST_USER, [user_email])

def send_websocket_notification(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",  # Group name for the user
        {
            "type": "send_notification",
            "message": message,
        }
    )
