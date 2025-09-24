// var notificationSocket = new WebSocket("wss://74bc-150-129-146-122.https://2c62-150-129-146-122.https://be6f-150-129-146-122.ngrok-free.app-free.app-free.app/ws/notifications/");

// notificationSocket.onmessage = function(event) {
//     console.log("inside notification websocket")
//     var data = JSON.parse(event.data);
//     console.log("🔔 Notification received:", data);

//     let notificationList = document.getElementById("notification-list");
//     let notificationItem = document.createElement("li");
//     notificationItem.innerHTML = `<strong>${data.timestamp}</strong>: ${data.message}`;
    
//     notificationList.appendChild(notificationItem);
//     document.getElementById("notification-container").classList.remove("hidden");
// };
