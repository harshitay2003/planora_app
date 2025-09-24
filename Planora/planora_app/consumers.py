import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Message, UserRoom,Profile,Notification
from django.utils.timezone import now
from collections import defaultdict


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"] 
        
        if self.user.is_authenticated:
            print(f"User Connected: {self.user.username}")
        else:
            print("User is Anonymous")

        print(f"🔵 WebSocket Connected to Room: {self.room_id}") 

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        previous_messages = await self.get_previous_messages()
        logged_in_user = next(iter(previous_messages), None)
        print("logged_in_user-:",logged_in_user)

        for message in previous_messages:
            await self.send(text_data=json.dumps({
                "message_id":message['id'],
                "sender": message["sender"],
                "message": message["message"],
                "timestamp": message["timestamp"],
                "caption":message["caption"]
            }))

    async def disconnect(self, close_code):
        print(f"🔴 WebSocket Disconnected from Room: {self.room_id}, Code: {close_code}")  
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            print(f"📩 Received Data: {data}") 

            action = data.get("action")

            if action == "update_message":
                message_id = data.get("message_id")
                updated_message = data.get("message")  # Can be text or file URL
                updated_caption = data.get("caption", "")  # Optional caption

                print(f"Message ID: {message_id}")
                print(f"Updated Message: {updated_message}")
                print(f"Updated Caption: {updated_caption}")

                # Update the message in the database
                await self.update_message_db(message_id, updated_message, updated_caption)

                # Notify the group about the updated message
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "update_message",
                        "message_id": message_id,
                        "message": updated_message,  # Send updated text or file URL
                        "caption": updated_caption  # Send caption if applicable
                    }
                )

            elif data.get("action") == "delete_message":
                message_id = data.get("message_id")
                print("deleting message-:",message_id)
                await self.delete_message_db(message_id)
              
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "delete_message",
                        "message_id": message_id                    }
                )


            else:  # Handle new messages
                message = data["message"]
                sender = data["sender"]
                file = data.get("file", None)

                saved_message = await self.save_message(sender, message, file)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message_id": saved_message.id,  # Get the message ID
                        "message": saved_message.message,
                        "sender": sender,
                        "file": file,
                        "caption":saved_message.caption
                    }
                )
        except json.JSONDecodeError:
            print("❌ JSON Decode Error:", text_data)
        except Exception as e:
            print("❌ Unexpected Error in receive:", e)

    async def chat_message(self, event):
        print(f"📤 Sending Message: {event}") 
        message_content = event["file"] if event["file"] else event["message"]
        await self.send(text_data=json.dumps({
            "message": message_content,
            "sender": event["sender"],
            "message_id": event["message_id"],
            "caption":event["caption"]
        }))
        
    async def update_message(self, event):
        """Broadcast updated message to all clients."""
        await self.send(text_data=json.dumps({
            "action": "update_message",
            "message_id": event["message_id"],
            "message": event["message"],  # Updated text or file URL
            "caption": event.get("caption", "")  # Optional caption
        }))
        
    async def delete_message(self, event):
        message_id = event["message_id"]
        print("msg)id for deleting-:",message_id)
        await self.send(text_data=json.dumps({  
            "action": "delete_message",
            "message_id": message_id        }))

    @sync_to_async
    def save_message(self, sender_id, message, file):
        print(sender_id)
        sender = Profile.objects.get(username=sender_id)
        room = UserRoom.objects.get(id=self.room_id)
        if file:
            caption=message
            file_message = file
        else:
            file_message = message
            caption=None

        return Message.objects.create(
            room=room,
            sender=sender,
            caption=caption,
            message=file_message,
            timestamp=now()
        )

    @sync_to_async
    def update_message_db(self, message_id, updated_message, updated_caption=""):
        """Update an existing message (text or file with caption) in the database."""
        try:
            print(f"🔄 Updating Message ID: {message_id}")
            
            message = Message.objects.get(id=message_id)

            message.message = updated_message 
            message.caption = updated_caption
            message.timestamp = now() 
            
            message.save()
            print(f"✅ Message {message_id} updated successfully!")

        except Message.DoesNotExist:
            print(f"❌ Message {message_id} not found!")

    @sync_to_async
    def delete_message_db(self, message_id):
        """Delete a message from the database."""
        try:
            message = Message.objects.get(id=message_id)
            message.delete()
            print(f"✅ Message {message_id} deleted successfully!")
        except Message.DoesNotExist:
            print(f"❌ Message {message_id} not found!")
            
    @sync_to_async
    def get_previous_messages(self):
        messages = Message.objects.filter(room_id=self.room_id)

        previous_messages = []
        
        for msg in messages:
            previous_messages.append({
                "id":msg.id,
                "sender": msg.sender.username,
                "message": msg.message,
                "timestamp": str(msg.timestamp),
                "caption":msg.caption
            })

        print("Previous messages:", previous_messages)
        return previous_messages 



