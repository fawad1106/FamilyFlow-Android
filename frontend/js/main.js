const taskForm = document.querySelector("#task-form");
const taskTitle = document.querySelector("#task-title");
const taskList = document.querySelector("#task-list");
const taskCount = document.querySelector("#task-count");
const emptyTasks = document.querySelector("#empty-tasks");
const taskError = document.querySelector("#task-error");
const activity = document.querySelector("#activity-message");

function showError(message) {
    taskError.textContent = message;
    taskError.hidden = false;
}

function clearError() {
    taskError.hidden = true;
    taskError.textContent = "";
}

function renderTasks(tasks) {
    taskList.replaceChildren();
    taskCount.textContent = tasks.length;
    emptyTasks.hidden = tasks.length !== 0;

    for (const task of tasks) {
        const item = document.createElement("li");
        item.className = "task-item";
        if (task.completed) item.classList.add("completed");

        const checkbox = document.createElement("button");
        checkbox.type = "button";
        checkbox.className = "task-check";
        checkbox.textContent = task.completed ? "✓" : "○";
        checkbox.setAttribute("aria-label", task.completed ? "Task completed" : "Complete task");
        checkbox.disabled = task.completed;
        checkbox.addEventListener("click", () => completeTask(task.id));

        const title = document.createElement("span");
        title.textContent = task.title;

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-task";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", () => deleteTask(task.id));

        item.append(checkbox, title, deleteButton);
        taskList.appendChild(item);
    }
}

async function loadTasks() {
    clearError();

    try {
        const response = await fetch("/api/tasks");
        if (!response.ok) throw new Error("Could not load tasks.");
        renderTasks(await response.json());
    } catch (error) {
        showError(error.message);
    }
}

async function completeTask(taskId) {
    clearError();

    try {
        const response = await fetch(`/api/tasks/${taskId}/complete`, { method: "PATCH" });
        if (!response.ok) throw new Error("Could not complete task.");
        activity.textContent = "Task completed.";
        await loadTasks();
    } catch (error) {
        showError(error.message);
    }
}

async function deleteTask(taskId) {
    clearError();

    try {
        const response = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
        if (!response.ok) throw new Error("Could not delete task.");
        activity.textContent = "Task deleted.";
        await loadTasks();
    } catch (error) {
        showError(error.message);
    }
}

taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();

    const title = taskTitle.value.trim();
    if (!title) return;

    try {
        const response = await fetch("/api/tasks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title })
        });

        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Could not create task.");
        }

        taskTitle.value = "";
        activity.textContent = "Task added.";
        await loadTasks();
        taskTitle.focus();
    } catch (error) {
        showError(error.message);
    }
});

document.querySelector("#theme-button").addEventListener("click", () => {
    document.body.classList.toggle("dark");
});

loadTasks();