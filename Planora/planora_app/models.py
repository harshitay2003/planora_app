from django.contrib.auth.models import AbstractUser
from django.db import models

# Define user roles
ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('developer', 'Developer'),
]

class Profile(AbstractUser):  
    first_name = models.CharField(max_length=50)  # First name
    last_name = models.CharField(max_length=50)   # Last name
    email = models.EmailField(unique=True)        # Email (unique)
    password = models.CharField(max_length=128)   # Password (hashed)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='developer')  

    def __str__(self):
        return f"{self.username} - {self.role}"
    
    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    manager = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="managed_projects")
    due_date=models.DateTimeField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    developers = models.ManyToManyField(Profile, related_name="assigned_projects")

# Task Model
class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    assigned_to = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="tasks")
    assigned_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="assigned_tasks")
    status = models.CharField(max_length=20, choices=[("Assigned", "Assigned"), ("In Progress", "In Progress"), ("Review","Review"),("Completed", "Completed")], default="Assigned")
    estimated_hours = models.PositiveIntegerField(default=1) 
    elapsed_time = models.PositiveIntegerField(default=0) 
    deadline = models.DateTimeField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(Profile, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    mentions = models.ManyToManyField(Profile, related_name="mentioned_comments", blank=True)
    reactions = models.ManyToManyField(Profile, related_name="comment_reactions", blank=True)

def task_file_upload_path(instance, filename):
    """Ensure files are saved under `static/task_files/task_<task_id>/filename`"""
    return f"task_files/task_{instance.task.id}/{filename}"

class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="files")
    uploaded_by = models.ForeignKey(Profile, on_delete=models.CASCADE) 
    file = models.FileField(upload_to=task_file_upload_path)  
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.task.title} by {self.uploaded_by.username}"\
            
class UserRoom(models.Model):
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent_rooms")
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="received_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room: {self.sender.username} & {self.receiver.username}"

class Message(models.Model):
    room = models.ForeignKey(UserRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    caption = models.TextField(null=True, blank=True)
    delivered = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} in Room {self.room.id}"



class Notification(models.Model):
    ROLE_CHOICES = (
        ('admin', 'admin'),
        ('manager', 'manager'),
        ('developer', 'developer'),
    )

    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.message[:30]}"

class ZoomMeeting(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="meetings")
    topic = models.CharField(max_length=255)
    join_url = models.URLField()
    meeting_id = models.CharField(max_length=100)
    start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ended = models.BooleanField(default=False)