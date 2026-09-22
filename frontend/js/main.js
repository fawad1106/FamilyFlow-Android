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

        const title = document.createElement("span");
        title.textContent = task.title;

        item.appendChild(title);
        taskList.appendChild(item);
    }
}

async function loadTasks() {
    clearError();

    try {
        const response = await fetch("/api/tasks");
        if (!response.ok) throw new Error("Could not load tasks.");
        const tasks = await response.json();
        renderTasks(tasks);
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