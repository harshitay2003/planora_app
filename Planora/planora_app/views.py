import json,smtplib,re,genai,jwt,os,requests
from django.contrib.auth import login, authenticate,logout
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.shortcuts import render,redirect
from datetime import datetime, timedelta
from django.core.mail import send_mass_mail
from base64 import b64encode
from rest_framework_simplejwt.tokens import RefreshToken
from email.mime.multipart import MIMEMultipart
from .models import Profile,Project,Task,TaskComment,TaskFile,UserRoom,Message,ZoomMeeting
from django.http import JsonResponse
from django.utils.timezone import localtime
from email.mime.text import MIMEText
from django.contrib import messages
from django.db.models import Q
from django.db import models
from django.conf import settings
import google.generativeai as genai
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Count, Q


genai.configure(api_key="AIzaSyDqeJFw51iaX8Wht89HUO-ELq5Kcu9y8mQ")
SECRET_KEY = settings.SECRET_KEY

@csrf_exempt
def home_view(request):
    return render(request,'admin_dashboard.html')
SECRET_KEY = settings.SECRET_KEY

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        ##print(username)
        password = request.POST.get("password")
        #print(password)

        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            request.session['username'] = username
            refresh = RefreshToken.for_user(user)

            return JsonResponse({   
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'username': user.username,
                    'role': user.role
                }
            })

        else:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
    return render(request, 'login.html')


@csrf_exempt
def signup_view(request):
    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        role = request.POST.get("role")
        user = Profile.objects.create_user(username=username, email=email, password=password1, role=role)
        if user:
            send_user_creation_email(email,username,password1)
            return JsonResponse({"message": "User created successfully"}, status=201)


    return render(request, "signup.html")

def forgot_pass_view(request):
    return render(request,'forgot_password.html')

def dashboard_view(request):
    if "username" not in request.session:
        return redirect("login_view") 
    
    user = request.user
    username = request.session.get('username') 
    body_unicode = request.body.decode('utf-8')  
    data = json.loads(body_unicode)  
    #print(data)
    role=data.get("role")
    projectId=data.get("project_id")
    #print(projectId)
    
    if role == "admin":
        return JsonResponse({"project_id":projectId})

    elif role == "manager":
        return JsonResponse({"project_id":projectId})

    elif role == "developer":
        return JsonResponse({"project_id":projectId})
    return redirect("login_view")


def projects_view(request):
    if "username" not in request.session:
        return redirect("login_view") 
    username = request.session.get('username')
    
    manager_profile = Profile.objects.get(username=username)

    if manager_profile.role == "admin":
        projects = Project.objects.all()  
    elif manager_profile.role == "manager":
        projects = Project.objects.filter(manager=manager_profile) 
    else: 
        assigned_tasks = Task.objects.filter(assigned_to=manager_profile)
        project_ids = assigned_tasks.values_list('project', flat=True).distinct()
        projects = Project.objects.filter(id__in=project_ids)
    for project in projects:
        active_meeting = ZoomMeeting.objects.filter(project=project, ended=False).order_by('-created_at').first()
        #print(active_meeting)
        project.active_zoom = active_meeting.join_url if active_meeting else None

    managers = Profile.objects.filter(role="manager")
    developers=Profile.objects.filter(role="developer")
    return render(request, "projects.html", {"active_zoom_meet":active_meeting,"projects": projects, "managers": managers,"manager_role":manager_profile.role,"developers":developers})


def admin_dashboard(request, project_id):
    if "username" not in request.session:
        return redirect("login_view")  

    username = request.session.get("username")
    current_user = Profile.objects.get(username=username)  

    #print(project_id)  
    projects = [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "manager_id": project.manager_id,
            "due_date": project.due_date.strftime("%Y-%m-%d %H:%M:%S") if project.due_date else None,
            "created_at": project.created_at.strftime("%Y-%m-%d %H:%M:%S") if project.created_at else None
        }
        for project in Project.objects.filter(id=project_id)
    ]

    if current_user.role == "developer":
        tasks = Task.objects.filter(project_id=project_id, assigned_to=current_user)
    else: 
        tasks = Task.objects.filter(project_id=project_id)

    tasks = [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "assigned_to": task.assigned_to.username if task.assigned_to else "Unassigned",
            "project_id": task.project_id,
            "estimated_time": task.estimated_hours,
            "elapsed_time": task.elapsed_time,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
            "status": task.status
        }
        for task in tasks
    ]

    developers = [
        {
            "id": dev.id,
            "username": dev.username,
            "role": dev.role
        }
        for dev in Project.objects.get(id=project_id).developers.all()
    ]
    current_user_data = {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }

    context = {
        "projects": json.dumps(projects),  
        "tasks": json.dumps(tasks),  
        "developers": json.dumps(developers),
        "current_user": json.dumps(current_user_data)  
    }
    return render(request, "dashboard.html", context)


@csrf_exempt
def create_project(request):
    if request.method == "POST":
        #print(request.POST)

        project_id = request.POST.get("project_id")
        name = request.POST.get("title")
        description = request.POST.get("description")
        due_date = request.POST.get("due_date")
        manager = request.POST.get("manager")
        developer_usernames = request.POST.getlist("developers") 

        manager_profile = get_object_or_404(Profile, username=manager)

        if not name or not description or not due_date:
            return JsonResponse({"error": "All fields are required"}, status=400)

        if project_id:
            project = get_object_or_404(Project, id=project_id)
            project.name = name
            project.description = description
            project.due_date = due_date
            project.manager = manager_profile
            project.save()

            developers = Profile.objects.filter(username__in=developer_usernames)
            project.developers.set(developers)

            return JsonResponse({"message": "Project updated successfully!"})
        else:
            project = Project.objects.create(
                name=name,
                description=description,
                due_date=due_date,
                manager=manager_profile
            )
    
            developers = Profile.objects.filter(username__in=developer_usernames)
            project.developers.set(developers)

            return JsonResponse({"message": "Project created successfully!", "project_id": project.id})

    return JsonResponse({"error": "Invalid request"}, status=400)


# @csrf_exempt
# def create_project(request):
#     if request.method == "POST":
#         #print(request.POST)
#         project_id = request.POST.get("project_id")  # Check if project_id is provided
#         name = request.POST.get("title")
#         description = request.POST.get("description")
#         due_date = request.POST.get("due_date")
#         manager=request.POST.get("manager")
#         developer=request.POST.get("developers")
#         manager_id=get_object_or_404(Profile,username=manager)

#         if not name or not description or not due_date:
#             return JsonResponse({"error": "All fields are required"}, status=400)

#         if project_id:  # If project_id exists, update the existing project
#             project = get_object_or_404(Project, id=project_id)
#             project.name = name
#             project.description = description
#             project.due_date = due_date
#             project.manager= manager_id
#             project.save()
#             return JsonResponse({"message": "Project updated successfully!"})

#         else:  # If no project_id, create a new project
#             project = Project.objects.create(
#                 name=name,
#                 description=description,
#                 due_date=due_date,
#                 manager= manager_id
#             )
#             return JsonResponse({"message": "Project created successfully!", "project_id": project.id})

#     return JsonResponse({"error": "Invalid request"}, status=400)

def users_view(request):
    if "username" not in request.session:
        return redirect("login_view") 
    users = Profile.objects.all() 
    return render(request, 'users.html', {'users': users})

@csrf_exempt
def logout_view(request):
    """
    Logs out the user by clearing the session and redirects to the login page.
    """
    logout(request)  
    return redirect("login_view")  

def manager_dashboard(request):
    if "username" not in request.session:
        return redirect("login_view") 
    username = request.session.get('username')
    manager_profile = Profile.objects.get(username=username)
    projects = Project.objects.filter(manager=manager_profile)
    developers = Profile.objects.filter(role="developer")  
    return render(request, "manager_dashboard.html", {"projects": projects, "developers": developers})

@csrf_exempt
def create_task(request):
    if request.method == "POST":
        try:
            task_id = request.POST.get("task_id")  # Get task_id from form (if exists)
            task_name = request.POST.get("task-title")
            task_description = request.POST.get("task-description")
            project_id = request.POST.get("project")
            developer_id = request.POST.get("developer")
            estimated_hours = request.POST.get("task-hours")
            deadline=request.POST.get('task_due_date')
            #print(deadline)

            project = get_object_or_404(Project, id=project_id)
            assigned_by = get_object_or_404(Profile, username=request.session.get('username'))
            assigned_to = get_object_or_404(Profile, id=developer_id)
            #print("assigned_to-:",assigned_to)

            if not assigned_to:
                return JsonResponse({"error": "Developer is required"}, status=400)

            if task_id:  # If task_id exists, update the existing task
                task = get_object_or_404(Task, id=task_id)
                #print(task)
                task.title = task_name
                task.description = task_description
                task.estimated_hours = estimated_hours
                task.assigned_by = assigned_by
                task.assigned_to = assigned_to
                task.project = project
                task.deadline=deadline
                task.save()  
                
                # #print("📧 Sending email...")
                # send_task_assignment_email(assigned_to.email, task.title, task.estimated_hours)
                # #print("success")
                send_notification(
                    role='Developer',
                    receiver=assigned_to.user,  # Assuming Profile has OneToOneField to User
                    message=f"You have been assigned a new task: {task.title}",
                    task=task
                )

                # Send notification to the manager
                send_notification(
                    role='Manager',
                    receiver=assigned_by.user,
                    message=f"You assigned task '{task.title}' to {assigned_to.username}",
                    task=task
                )

                # Optional: Notify Admins globally
                send_notification(
                    role='Admin',
                    message=f"Manager {assigned_by.username} assigned task '{task.title}' to {assigned_to.username}",
                    task=task
                )

                
                # #print("🔔 Sending websocket notification...")
                # send_websocket_notification(assigned_to.id, f"Task Updated: {task.title}",task_id)

                return JsonResponse({"message": "Task updated successfully"}, status=200)

            else:  # If no task_id, create a new task
                task = Task.objects.create(
                    title=task_name,
                    description=task_description,
                    estimated_hours=estimated_hours,
                    assigned_by=assigned_by,
                    assigned_to=assigned_to,
                    deadline=deadline,
                    project=project
                )
                task_id=task.id
                # #print(task)
                # #print("📧 Sending email...")
                # # send_task_assignment_email(assigned_to.email, task.title, task.estimated_hours)
                # #print("success")
                send_notification(
                    role='Developer',
                    receiver=assigned_to,  # Assuming Profile has OneToOneField to User
                    message=f"You have been assigned a new task: {task.title}",
                    task=task
                )

                # Send notification to the manager
                send_notification(
                    role='Manager',
                    receiver=assigned_by,
                    message=f"You assigned task '{task.title}' to {assigned_to.username}",
                    task=task
                )

                # Optional: Notify Admins globally
                send_notification(
                    role='Admin',
                    message=f"Manager {assigned_by.username} assigned task '{task.title}' to {assigned_to.username}",
                    task=task
                )

                # #print("🔔 Sending websocket notification...")
                # send_websocket_notification(assigned_to.id, f"New Task Assigned: {task.title}",task_id)

                return JsonResponse({"message": "Task created successfully"}, status=201)

        except Exception as e:
            #print("❌ Error in create_task:", str(e))
            return JsonResponse({"error": "Something went wrong"}, status=500)

    return render(request, "tasks.html")

def manager_tasks_view(request):
    if "username" not in request.session:
        return redirect("login_view") 
    if request.user.role != 'manager':   
        return redirect('dashboard') 


    username = request.session.get('username')  
    manager_profile = get_object_or_404(Profile, username=username, role="manager") 

    projects = Project.objects.filter(manager=manager_profile) 
    tasks = Task.objects.filter(project__in=projects)  

    return render(request, "manager_tasks.html", {"projects": projects, "tasks": tasks})

@csrf_exempt
def update_task_status(request):
    #print("inside update status")
    if "username" not in request.session:
        return redirect("login_view") 
    if request.method == "POST":
        body_unicode = request.body.decode('utf-8')  
        data = json.loads(body_unicode)  
        #print(data)

        task_id = data.get("id")
        #print(task_id)
        task = get_object_or_404(Task, id=task_id)
        status = data.get("status")
        #print(status)
        if status:
            task.status = status
            task.save()  
            return JsonResponse({"message": "Task status updated successfully", "status": task.status})
    return JsonResponse({"error": "Invalid request method"}, status=405)

def developer_dashboard(request):
    if "username" not in request.session:
        return redirect("login_view") 
    user = request.user
    tasks = Task.objects.filter(assigned_to=user)  
    projects = Project.objects.filter(tasks__in=tasks).distinct()  

    return render(request, "developer_dashboard.html", {"tasks": tasks, "projects": projects})
    

def send_user_creation_email(receiver_mail,username,password):
    smtp_host = "smtp.zoho.com"  
    smtp_port = 587
    smtp_user = 'harshita.yadav@techinfini.in'  
    smtp_password = 'Harshita@987'
    subject = "New Account created"
    app_url="https://6b43-150-129-146-122.https://2c62-150-129-146-122.https://be6f-150-129-146-122.ngrok-free.app-free.app-free.app/update_password"
    body = f"""
    Hello {username},

    Your account has been created successfully.

    Here are your login details:
    --------------------------------
    🌐 **Login URL:** {app_url}
    👤 **Username:** {username}
    🔑 **Password:** {password}
    --------------------------------

    Please log in and update your password after the first login.

    Best Regards,  
    Your Company
    """
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] =receiver_mail
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, receiver_mail, msg.as_string())
    
    except Exception as e:
        print(f"Error sending email: {e}")
        
@csrf_exempt
def update_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        old_password = request.POST.get("old_password")
        #print(old_password)
        new_password = request.POST.get("new_password")

        user = authenticate(username=username, password=old_password)
        #print(user)

        if user is None:
            messages.error(request, "Old password is incorrect!")
            #print("none")
            return redirect("/update-password")

        user.set_password(new_password)
        user.save()

        messages.success(request, "Password updated successfully!")
        return JsonResponse({"success":"password_updated_successfully"})  

    return render(request, "update_password.html")

# def view_task(request,task_id):
#     task = Task.objects.get(id=task_id)
#     return render(request,"view_task.html",{"task":task})


def start_task(request, task_id):
    task = Task.objects.get(id=task_id)
    start_time = now() 
    end_time = start_time + timedelta(hours=task.estimated_hours)
    #print(end_time)
    task.status = "In Progress"
    task.start_time = start_time
    task.end_time = end_time  
    task.save()
    return JsonResponse({"success": True})
        
@csrf_exempt
def update_task_time(request):
    
    if request.method == "POST":
        data = json.loads(request.body)
        task_id = data.get('id')
        elapsed_time = data.get('elapsed_time')

        task = Task.objects.filter(id=task_id).first()
        if task:
            task.elapsed_time = elapsed_time
            task.save()
            return JsonResponse({"message": "Time updated", "elapsed_time": elapsed_time})
        
        return JsonResponse({"error": "Task not found"}, status=404)

def view_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    comments = task.comments.all()
    files = task.files.all()
    
    if request.method == "POST":
        # Handle Comment Submission
        if "comment_text" in request.POST:
            comment_text = request.POST.get("comment_text")
            comment = TaskComment.objects.create(task=task, author=request.user, text=comment_text)

            # Handle Mentions (@username)
            mentioned_users = re.findall(r'@(\w+)', comment_text)
            users = Profile.objects.filter(username__in=mentioned_users)
            comment.mentions.set(users)  # Save mentioned users

            return redirect('view_task', task_id=task.id)

        # Handle File Upload
        elif "task_file" in request.FILES:
            uploaded_file = request.FILES["task_file"]
            TaskFile.objects.create(task=task, uploaded_by=request.user, file=uploaded_file)

            return redirect('view_task', task_id=task.id)

    return render(request, "view_task.html", {
        "task": task,
        "comments": comments,
        "files": files,
    })

from django.http import JsonResponse
from .models import TaskFile
from django.core.files.storage import default_storage

@csrf_exempt
def upload_file(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        #print(uploaded_file)
        task_id = request.POST.get("task_id")
        
        if not uploaded_file:
            return JsonResponse({"success": False, "error": "No file provided"})
        
        task = Task.objects.get(id=task_id)

        file_instance = TaskFile.objects.create(
            task=task,
            uploaded_by=request.user,
            file=uploaded_file
        )

        return JsonResponse({
            "success": True,
            "file_url": file_instance.file.url,
            "file_name": file_instance.file.name,
            "uploaded_by": file_instance.uploaded_by.username,
            "uploaded_at": file_instance.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
        })


    return JsonResponse({"success": False, "error": "No file provided"})

@csrf_exempt
def add_comment(request):
    #print("inside")
    if request.method == "POST":
        #print(request.POST)
        text = request.POST.get("comment_text", "").strip()
        #print(text)
        task_id = request.POST.get("task_id")
        #print(task_id)
        task = Task.objects.get(id=task_id)
        mentions = [Profile.objects.get(username=u[1:]) for u in text.split() if u.startswith("@")]

        comment = TaskComment.objects.create(
            task=task,
            author=request.user,
            text=text
        )
        comment.mentions.set(mentions) 

        return JsonResponse({
            "success": True,
            "message": "Comment added successfully!",
            "comment": {
                "author": request.user.username,
                "text": comment.text,
                "mentions": [u.username for u in mentions],
                "created_at": localtime(comment.created_at).strftime("%Y-%m-%d %H:%M")
            }
        })

    return JsonResponse({"success": False, "error": "Invalid request"})


def chat(request):
    if "username" not in request.session:
        return redirect("login_view") 
    users = Profile.objects.exclude(id=request.user.id)  
    return render(request, 'chat.html', {'users': users})

@csrf_exempt
def send_message(request): 
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            sender = request.user
            receiver_id = data.get("receiver_id")
            message_text = data.get("message")

            if not receiver_id or not message_text:
                return JsonResponse({"success": False, "error": "Missing data"}, status=400)

            receiver = Profile.objects.get(id=receiver_id)

            room, created = UserRoom.objects.get_or_create(
                sender_id=min(sender.id, receiver.id),
                receiver_id=max(sender.id, receiver.id)
            )
            #print(room)
            message = Message.objects.create(
                room=room,
                sender=sender,
                message=message_text
            )

            return JsonResponse({
                "success": True, 
                "message_id": message.id, 
                "room_id": room.id  
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

@csrf_exempt
def get_or_create_room(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "error": "User not authenticated"}, status=401)

        data = json.loads(request.body)
        sender = request.user  
        receiver_id = data.get("receiver_id")

        try:
            receiver = Profile.objects.get(id=receiver_id)
            room = UserRoom.objects.filter(
                (Q(sender=sender, receiver=receiver) | Q(sender=receiver, receiver=sender))
            ).first()

            if room:
                return JsonResponse({
                    "success": True,
                    "room_id": room.id,
                    "message": "Room already exists",
                    "current_user": sender.username 
                })
            room = UserRoom.objects.create(sender=sender, receiver=receiver)
            return JsonResponse({
                "success": True,
                "room_id": room.id,
                "message": "New room created",
                "current_user": sender.username  
            })

        except Profile.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"}, status=404)

@csrf_exempt
def upload_chat_file(request):
    if request.method == "POST" and request.FILES.get("file"):
        #print(request.POST)
        file = request.FILES["file"]
        upload_dir = os.path.join(settings.STATIC_ROOT, "uploads")
        #print(upload_dir)
        if not os.path.exists(upload_dir):
            #print("doesnot exists")
            os.makedirs(upload_dir)

        file_name = file.name
        file_relative_path = f"uploads/{file_name}" 
        file_full_path = os.path.join(upload_dir, file_name)
        
        with open(file_full_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        file_url = os.path.join(settings.STATIC_URL, file_full_path)
        #print(file_url)
        

        return JsonResponse({"success": True, "file_url": file_relative_path})

    return JsonResponse({"success": False, "error": "No file uploaded."})

def delete_project(request, project_id):
    if request.method == "DELETE":
        project = get_object_or_404(Project, id=project_id)
        project.delete()
        return JsonResponse({"message": "Project deleted successfully!"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def delete_task(request,task_id):
    if request.method == "DELETE":
        project = get_object_or_404(Task, id=task_id)
        project.delete()
        return JsonResponse({"message": "Project deleted successfully!"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

from django.shortcuts import render
from .models import Notification

def notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    return render(request, 'notifications.html', {'notifications': notifications})

@csrf_exempt
def mark_notifications_read(request):
    if request.method == "POST":
        user = request.user
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return JsonResponse({"message": "Notifications marked as read"})

@csrf_exempt
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all()
    
    return render(request, "project_detail.html", {
        "project": project,
        "tasks": tasks
    })

@csrf_exempt
def get_project_tasks(request, project_id):
    #print("project_id-:",project_id)
    tasks = Task.objects.filter(project_id=project_id)
    #print("tasks-:",tasks)
    data = [
        {
            "id": task.id,
            "title": task.title,
            "start": task.created_at.strftime('%Y-%m-%d'),
            "end": task.deadline.strftime('%Y-%m-%d') if task.deadline else None,
            "status": task.status
        }
        for task in tasks
    ]
    return JsonResponse(data, safe=False)




def get_admin_dashboard(request):
    user = request.user
    #print("user-:",user)
    user_id=user.id
    username=user.username
    #print(username)
    now = timezone.now()
    last_7_days = now - timezone.timedelta(days=7)
    upcoming_7_days = now + timezone.timedelta(days=7)
    profile = Profile.objects.get(username=username)
    #print("profile-:",profile)
    #print(profile.role)

    if profile.role == "admin":
        project_queryset = Project.objects.all()
        task_queryset = Task.objects.all()
    elif profile.role == "manager":
        project_queryset = Project.objects.filter(manager_id=user_id)
        task_queryset = Task.objects.filter(project__in=project_queryset)
    elif profile.role == "developer":
        #print("inside develper")
        task_queryset = Task.objects.filter(assigned_to=user_id)
        project_queryset = Project.objects.filter(tasks__in=task_queryset).distinct()
    else:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    total_projects = project_queryset.count()
    created_projects = project_queryset.filter(created_at__gte=last_7_days).count()
    updated_projects = task_queryset.filter(created_at__gte=last_7_days).values('project').distinct().count()
    completed_projects = task_queryset.filter(status="Completed", created_at__gte=last_7_days).values('project').distinct().count()

    task_status_summary = task_queryset.values('status').annotate(count=Count('id'))

    project_progress = []
    for project in project_queryset:
        total = project.tasks.count()
        done = project.tasks.filter(status="Completed").count()
        in_progress = project.tasks.filter(status="In Progress").count()
        to_do = total - done - in_progress
        progress = {
            "project": project.name,
            "done": round((done / total) * 100, 1) if total else 0,
            "in_progress": round((in_progress / total) * 100, 1) if total else 0,
            "to_do": round((to_do / total) * 100, 1) if total else 0,
        }
        project_progress.append(progress)

    if profile.role in ["admin", "manager"]:
        team_workload = Profile.objects.filter(role="developer").annotate(
            task_count=Count('tasks')
        ).values('username', 'task_count')
    else:
        team_workload = []

    recent_comments = TaskComment.objects.filter(task__in=task_queryset).select_related('author', 'task').order_by('-created_at')[:5]
    recent_activities = [
        {
            "author": comment.author.username,
            "task": comment.task.title,
            "comment": comment.text,
            "created_at": comment.created_at
        } for comment in recent_comments
    ]

    due_soon = task_queryset.filter(deadline__lte=upcoming_7_days, deadline__gte=now).count()

    return JsonResponse({
        "role":profile.role,
        "projects": {
            "total": total_projects,
            "created": created_projects,
            "updated": updated_projects,
            "completed": completed_projects,
        },
        "task_status": list(task_status_summary),
        "project_progress": project_progress,
        "team_workload": list(team_workload),
        "recent_activity": recent_activities,
        "due_soon": due_soon,
    })

def get_tasks(request):
    return render(request,"get_tasks.html")

@csrf_exempt
def calender_page(request):
    return render(request,'calender.html')

@csrf_exempt
def get_calendar_events(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    user = request.user
    #print("user-:", user.role)

    status_colors = {
        "Assigned": "#facc15",      
        "In Progress": "#3b82f6",  
        "Review": "#fb923c",       
        "Completed": "#10b981",
    }


    if user.role == "developer":
        #print("inside developer")
        queryset = Task.objects.filter(assigned_to=user).exclude(deadline__isnull=True)
        #print("inside if")
    elif user.role == "manager":
        #print("inside elif")
        queryset = Task.objects.filter(assigned_by=user).exclude(deadline__isnull=True)
        if queryset.count() == 0:
            #print("No tasks found, using project data")
            project_queryset = Project.objects.filter(manager=user).exclude(due_date__isnull=True)
        else:
            project_queryset = None

        
    if user.role == 'admin':
        #print("Inside admin role fallback")
        queryset = Task.objects.exclude(deadline__isnull=True)
        project_queryset = None 

    #print("Queryset: ", queryset)

    events = []
    for task in queryset:
        events.append({
            "title": task.title,
            "start": task.deadline.isoformat(),
            "color": status_colors.get(task.status, "#9ca3af"),
            "url": f"/view_task/{task.id}"
        })

    if project_queryset:
        for project in project_queryset:
            events.append({
                "title": f"[Project] {project.name}",
                "start": project.due_date.isoformat(),
                "color": "#3b82f6",  # Blue or custom color for project
                "url": f"/admin_dashboard/{project.id}"
            })

    return JsonResponse(events, safe=False)

def notifications_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user=request.user
 
    profile = Profile.objects.filter(username=user)
    role=user.role
    #print(role)

    # Get both personal and role-based notifications (unread only)
    notifications = Notification.objects.filter(
        is_read=False
    ).filter(
        models.Q(receiver=request.user) | models.Q(role=role)
    ).order_by('-created_at')
    #print(notifications)

    return render(request, 'notifications.html', {'notifications': notifications})

@csrf_exempt
def mark_as_read(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        #print(data)
        note_id = data.get('note_id')
        #print(note_id)

        try:
            note = Notification.objects.get(id=note_id, receiver=request.user)
            note.is_read = True
            note.save()
            return JsonResponse({'status': 'success'})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def send_notification(role, message, task=None, receiver=None):
    """
    Create a notification for a user with a specific role.
    - role: 'Admin', 'Manager', or 'Developer'
    - message: Notification message
    - task: Optional Task object
    - receiver: User object (optional; can broadcast to all users with that role)
    """
    if receiver:
        Notification.objects.create(
            receiver=receiver,
            role=role,
            message=message,
            related_task=task
        )
    else:
        # Send to all users with that role
        users = Profile.objects.filter(role=role)  # Assuming you have a Profile model with role
        for user in users:
            Notification.objects.create(
                receiver=user,
                role=role,
                message=message,
                related_task=task
            )

def get_unread_notification_count(request):
    count = Notification.objects.filter(receiver=request.user, is_read=False).count()
    #print(count)
    return JsonResponse({'unread_count': count})

@csrf_exempt
def ai_assistant(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("message", "")
        #print("User Question:", user_input)

        tasks = Task.objects.all()
        projects = Project.objects.all()

        task_info = "\n".join([
            f"Task: {t.title}, Status: {t.status}, Deadline: {t.deadline}, Assigned To: {t.assigned_to.username}"
            for t in tasks
        ])

        project_info = "\n".join([
            f"Project: {p.name}, Deadline: {p.due_date}, Description: {p.description},Assigned To:{p.manager.username}"
            for p in projects
        ])

        db_context = f"""
        Here is the current state of the project management system:

        Projects:
        {project_info}

        Tasks:
        {task_info}
        """
        #print("project_info-:",project_info)
        input_prompt = (
        f"Here's the database content with common information of projects and tasks:\n\n{db_context}\n\n"
        f"please give the answer for the following question:\n\n{user_input}"
        "Provide a direct, concise response to the customer. The response should address their query or concern fully, "
        "based on the database, and maintain a professional tone using 'we' and 'our'. Do not include a summary or explanation of the call."
    )

    try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(input_prompt)
            #print(response.text)
            
            reply = response.text

            return JsonResponse({"reply": reply})

    except Exception as e:
        return ["Sorry, there was an error processing the request. Please try again later."]



@csrf_exempt
def suggest_tasks(request):

    data = json.loads(request.body)
    #print(data)
    new_project_name = data.get('project_name', '')
    #print(new_project_name)
    input_prompt = (
        f"You are an expert software project planner. I am building a project called:\n\n'{new_project_name}'\n\n"
        "Please suggest 5-6 coding-related tasks only — such as modules to develop, integrations, or core logic work.\n"
        "Return your answer in a valid Python list format like this:\n"
        '["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]\n'
        "Do not include any explanation or summary, only the Python list."
    )
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(input_prompt)
    #print(response.text)
    
    reply = response.text

    return JsonResponse({"reply": reply})

@csrf_exempt
def toggle_reaction(request):
    if request.method == "POST":
        comment_id = request.POST.get("comment_id")
        comment = TaskComment.objects.get(id=comment_id)
        user = request.user

        if user in comment.reactions.all():
            comment.reactions.remove(user)
            reacted = False
        else:
            comment.reactions.add(user)
            reacted = True

        return JsonResponse({
            "success": True,
            "reacted": reacted,
            "reaction_count": comment.reactions.count()
        })

    return JsonResponse({"success": False, "error": "Invalid request"})

@csrf_exempt
def get_mention_users(request):
    q = request.GET.get("q", "")
    #print(q)
    users = Profile.objects.filter(username__icontains=q)[:5]
    data = [{"username": u.username} for u in users]
    return JsonResponse(data, safe=False)

import jwt
from django.views import View
from django.http import JsonResponse
from django.conf import settings

class ProtectedView(View):
    def get(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization header missing"}, status=401)

        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            request_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')

            if decoded['ip'] != request_ip:
                return JsonResponse({"error": "IP address mismatch"}, status=403)

            return JsonResponse({"message": f"Welcome {decoded['username']} from {request_ip}"})
        
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"error": "Invalid token"}, status=401)


@csrf_exempt
def create_zoom_meeting(request):
    data = json.loads(request.body)
    project_id = data.get("project_id")
    topic = data.get("topic")
    duration = data.get("duration")
    start_time_raw = data.get("start_time")
    #print("create_zoom_meeting")
    client_id = "_Cz_CEbWQJu8HG1KVGlT_Q"
    client_secret = "K3YPDdpArB4I3gMtE84AXleB6uPFNeh5"
    account_id = "PVtLwbY4QdWQvUwSUZcLuA"
    start_time = f"{start_time_raw}:00Z" 
    #print(start_time)
    auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()
    #print(auth_header)
    token_response = requests.post(
        "https://zoom.us/oauth/token",
        headers={
            "Authorization": f"Basic {auth_header}"
        },
        data={
            "grant_type": "account_credentials",
            "account_id": account_id
        }
    )
    #print(token_response.status_code)

    if token_response.status_code != 200:
        #print(token_response.text)
        return JsonResponse({
            "error": "Failed to get Zoom token",
            "details": token_response.text
        }, status=500)


    access_token = token_response.json()['access_token']

    meeting_payload = {
        "topic": topic or "Django Meeting",
        "type": 2,  
        "duration": duration,
        "start_time": start_time,
        "timezone": "UTC",
        "settings": {
            "join_before_host": True,
            "host_video": True,
            "participant_video": True
        }
    }

    meeting_response = requests.post(
        "https://api.zoom.us/v2/users/me/meetings",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=meeting_payload
    )

    if meeting_response.status_code != 201:
        return JsonResponse({
            "error": "Failed to create Zoom meeting",
            "details": meeting_response.text
        }, status=400)
    zoom_data = meeting_response.json()

    project = get_object_or_404(Project,id=project_id)

    ZoomMeeting.objects.create(
        project=project,
        topic=zoom_data["topic"],
        join_url=zoom_data["join_url"],
        meeting_id=zoom_data["id"],
        start_time=parse_datetime(zoom_data.get("start_time")) if zoom_data.get("start_time") else None
    )
    notify_project_users(project, zoom_data["join_url"])
    return JsonResponse(meeting_response.json())


def notify_project_users(project, zoom_url):
    users = list(project.developers.all())
    if project.manager:
        users.append(project.manager)

    # Avoid duplicates by user ID
    users = list({user.id: user for user in users}.values())

    from_email = settings.DEFAULT_FROM_EMAIL

    messages = [
        (
            f"Zoom Meeting Scheduled: {project.name}",
            f"A new Zoom meeting has been scheduled.\n\nJoin here: {zoom_url}",
            from_email,
            [user.email]
        )
        for user in users
    ]
    send_mass_mail(messages, fail_silently=False)

