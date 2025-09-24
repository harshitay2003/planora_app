
const statuses = ["Assigned", "In Progress", "Review", "Completed"];
const timers = {}; 
const taskTimes = {}; 

function renderBoard() {
    const board = document.getElementById("kanban-board");
    board.innerHTML = "";
    const isDeveloper = developers_data.some(dev => dev.username === users_data.username);

    statuses.forEach(status => {
        const column = document.createElement("div");
        column.className = "dark:bg-gray-800 rounded-lg shadow-lg kanban-column";
        column.setAttribute("data-status", status);
        column.innerHTML = `<h2>${status}</h2>`;
        column.ondragover = allowDrop;
        column.ondrop = drop;

        const filteredTasks = tasks_data.filter(task => task.status === status);
        filteredTasks.forEach(task => {
            const taskElement = document.createElement("div");
            taskElement.className = " dark:bg-gray-800 rounded-lg shadow-lg task";
            taskElement.draggable = true;
            taskElement.setAttribute("data-id", task.id);
            taskElement.ondragstart = drag;
            
            const optionElement=document.createElement("div")
            console.log("Created optionElement:", optionElement);

            optionElement.className="text-gray-700 dark:text-white options"
            optionElement.textContent=`three dot`
            optionElement.innerHTML = "&#x22EE;"; // Vertical ellipsis (⋮)
            optionElement.style.marginLeft="11.5rem";
            optionElement.style.position = "absolute";
            // optionElement.style.top = "6rem";
            optionElement.style.fontWeight = "bold";
            optionElement.style.cursor = "pointer";

            // Create dropdown menu
            const dropdownMenu = document.createElement("div");
            dropdownMenu.className = "dark:bg-gray-800 rounded-lg shadow-lg  dropdown-menu";
            dropdownMenu.style.position = "absolute";
            dropdownMenu.style.top = "8rem";
            dropdownMenu.style.left = "10rem";
            // dropdownMenu.style.background = "#fff";
            dropdownMenu.style.border = "1px solid #ccc";
            dropdownMenu.style.padding = "5px";
            dropdownMenu.style.boxShadow = "0px 2px 5px rgba(0, 0, 0, 0.2)";
            dropdownMenu.style.display = "none"; // Initially hidden

            // Create Edit Option
            const editOption = document.createElement("div");
            editOption.textContent = "Edit";
            editOption.style.padding = "5px";
            editOption.className = "text-gray-700 dark:text-white dropdown-item";
            editOption.style.cursor = "pointer";
            editOption.onclick = function (event) {
                document.getElementById("assignTaskModal").classList.remove("hidden");
                // document.getElementById('projectModal').classList.remove('hidden');

                // Populate form fields with existing project data
                document.getElementById('id').value = task.id;
                document.getElementById('task-title').value = task.title;
                document.getElementById('task-description').value = task.description;
                document.getElementById('task-hours').value = task.estimated_time;
                document.getElementById('project').value = task.project_id;
                const developerSelect = document.getElementById('developer');
                const assignedDeveloper = task.assigned_to;
                console.log(assignedDeveloper)
                if ([...developerSelect.options].some(option => option.value == assignedDeveloper)) {
                    developerSelect.value = assignedDeveloper;
                } else {

                    developerSelect.value = ""; 
                }

            };
            document.getElementById("closeModal").addEventListener("click", function () {
                document.getElementById("assignTaskModal").classList.add("hidden");
            });

            // Create Delete Option
            const deleteOption = document.createElement("div");
            deleteOption.textContent = "Delete";
            deleteOption.style.padding = "5px";
            deleteOption.className = "text-gray-700 dark:text-white  dropdown-item";
            deleteOption.style.cursor = "pointer";
            deleteOption.onclick = function () {
                DeleteTask(task.id);
               
            };

            // Append options to dropdown
            dropdownMenu.appendChild(editOption);
            dropdownMenu.appendChild(deleteOption);

            // Toggle dropdown visibility when clicking optionElement
            optionElement.onclick = function (event) {
                event.stopPropagation();
                dropdownMenu.style.display = dropdownMenu.style.display === "none" ? "block" : "none";
            };

            // Hide dropdown when clicking outside
            document.addEventListener("click", function () {
                dropdownMenu.style.display = "none";
            });

            
            const titleElement = document.createElement("div");
            titleElement.textContent = task.title;
            titleElement.className = "task-title";
            titleElement.style.cursor = "pointer";
            titleElement.style.display = "flex";
            titleElement.style.justifyContent = "space-between";
            titleElement.onclick = function() {
                viewTask(task.id);
            };
            if(users_data.role === 'manager'){
                titleElement.appendChild(optionElement);
            }
            const assignedToElement = document.createElement("div");
            assignedToElement.textContent = `Assigned to: ${task.assigned_to}`;
            assignedToElement.className = "text-gray-700 dark:text-white task-assigned";
            if (!(task.id in taskTimes)) {
                taskTimes[task.id] = task.elapsed_time || 0;
            }


            const timeDisplay = document.createElement("div");
            timeDisplay.className = "timer-display";
            timeDisplay.textContent = formatTime(taskTimes[task.id]);
            timeDisplay.style.display = isDeveloper ? "block" : "none";

            const startButton = document.createElement("button");
            startButton.textContent = "▶ Start";
            startButton.className = "start-btn";
            startButton.style.display = timers[task.id] ? "none" : "inline-block";
            startButton.onclick = function (event) {
                event.stopPropagation();
                startTimer(task.id, timeDisplay, startButton, stopButton);
            };
            const stopButton = document.createElement("button");
            stopButton.textContent = "⏹ Stop";
            stopButton.className = "stop-btn";
            stopButton.style.display = timers[task.id] ? "inline-block" : "none";
            stopButton.onclick = function (event) {
                event.stopPropagation();
                stopTimer(task.id, startButton, stopButton);
            };
            const buttonGroup = document.createElement("div");
            buttonGroup.className = "button-group";
            buttonGroup.appendChild(startButton);
            buttonGroup.appendChild(stopButton);
            buttonGroup.style.display = isDeveloper ? "block" : "none";
            taskElement.appendChild(titleElement);
            taskElement.appendChild(assignedToElement);
            taskElement.appendChild(timeDisplay);
            console.log(users_data.role)

           


            taskElement.appendChild(dropdownMenu);
            console.log("Appended optionElement to taskElement:", taskElement);

            taskElement.appendChild(buttonGroup);
            column.appendChild(taskElement);
        });

        board.appendChild(column);
    });
}

function allowDrop(event) {
    event.preventDefault();
}

function drag(event) {
    event.dataTransfer.setData("text", event.target.getAttribute("data-id"));
}

function drop(event) {
    event.preventDefault();
    const taskId = parseInt(event.dataTransfer.getData("text"));  
    const newStatus = event.currentTarget.getAttribute("data-status");

    const task = tasks_data.find(task => task.id === taskId);
    if (task) {
        task.status = newStatus;
        fetch('/update_task_status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: taskId, status: newStatus})
        }).catch(error => console.error('Error:', error));
    }

    renderBoard();
}

function viewTask(task_id) {
    window.location.href = `/view_task/${task_id}`;
}

function startTimer(taskId, display, startButton, stopButton) {
    if (timers[taskId]) return;

    timers[taskId] = setInterval(() => {
        taskTimes[taskId]++;
        display.textContent = formatTime(taskTimes[taskId]);

        fetch('/update_task_time', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: taskId, elapsed_time: taskTimes[taskId]})
        }).catch(error => console.error('Error:', error));

    }, 1000);

    // Toggle button visibility
    startButton.style.display = "none";
    stopButton.style.display = "inline-block";
}

function stopTimer(taskId, startButton, stopButton) {
    if (timers[taskId]) {
        clearInterval(timers[taskId]);
        delete timers[taskId];
    }

    // Toggle button visibility
    startButton.style.display = "inline-block";
    stopButton.style.display = "none";
}

// Helper function to format time
function formatTime(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs}h ${mins}m ${secs}s`;
}

function DeleteTask(task_id) {

    if (confirm("Are you sure you want to delete this project?")) {
        fetch(`/delete_task/${task_id}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            location.reload();
        })
        .catch(error => console.error('Error:', error));
    }
}


renderBoard();

