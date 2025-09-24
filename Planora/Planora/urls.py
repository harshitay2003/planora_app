"""
URL configuration for Planora project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from planora_app import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.home_view,name="home_view"),
    path('login',views.login_view,name="login_view"),
    path('signup',views.signup_view,name="signup_view"),
    path('forgot_password',views.forgot_pass_view,name="forgot_pass_view"),
    path('dashboard',views.dashboard_view, name='dashboard_view'),
    path("projects", views.projects_view, name="projects_view"),  
    path("admin_dashboard/<int:project_id>", views.admin_dashboard, name="admin_dashboard"),
    path("manager_dashboard",views.manager_dashboard,name="manager_dashboard"),
    path("developer_dashboard",views.developer_dashboard,name="developer_dashboard"),
    path("create_project",views.create_project,name="create_project"),
    path('users', views.users_view, name='users'),
    path('logout',views.logout_view,name="logout_view"),
    path("create_task",views.create_task,name="create_task"),
    path("manager_tasks_view",views.manager_tasks_view,name="manager_tasks_view"),
    path("update_task_status",views.update_task_status,name="update_task_status"),
    path("update_password",views.update_password,name="update_password"),
    path("view_task/<int:task_id>",views.view_task,name="view_task"),
    path("start_task/<int:task_id>",views.start_task,name="start_task"),
    path("update_task_time",views.update_task_time,name="update_task_time"),
    path("upload_file",views.upload_file,name="upload_file"),
    path("add_comment",views.add_comment,name="add_comment"),
    path("chat",views.chat,name="chat"),
    path("send_message",views.send_message,name="send_message"),
    path("get_or_create_room",views.get_or_create_room,name="get_or_create_room"),
    path("upload_chat_file",views.upload_chat_file,name="upload_chat_file"),
    path('delete_project/<int:project_id>', views.delete_project, name='delete_project'),
    path("delete_task/<int:task_id>",views.delete_task,name="delete_task"),
    path("notifications/mark-read/", views.mark_notifications_read, name="mark_notifications_read"),
    path('get_project_tasks/<int:project_id>', views.get_project_tasks, name='get_project_tasks'),
    path('get_admin_dashboard',views.get_admin_dashboard,name="get_admin_dashboard"),
    path("get_tasks",views.get_tasks,name="get_tasks"),
    path('calender_page', views.calender_page, name='calender_page'),
    path('get-calendar-events', views.get_calendar_events, name='get_calendar_events'),
    path('notifications_view',views.notifications_view,name='notifications_view'),
    path('mark_as_read',views.mark_as_read,name="mark_as_read"),
    path('get_unread_notification_count',views.get_unread_notification_count,name="get_unread_notification_count"),
    path("ai_assistant", views.ai_assistant, name="ai_assistant"),
    path('suggest_tasks',views.suggest_tasks,name='suggest_tasks'),
    path('toggle_reaction',views.toggle_reaction,name='toggle_reaction'),
    path('get-mention-users/', views.get_mention_users, name='get_mention_users'),
    path('create_zoom_meeting', views.create_zoom_meeting, name='create_zoom_meeting'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh')
    # path('tasks/<int:pk>/', views.task_detail, name='task_detail'),



]

if settings.DEBUG: 
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)