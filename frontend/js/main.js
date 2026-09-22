const activity = document.querySelector("#activity-message");

document.querySelector("#theme-button").addEventListener("click", () => {
    document.body.classList.toggle("dark");
});

document.querySelector("#add-task").addEventListener("click", () => {
    activity.textContent = "Task creation is our next feature.";
});

document.querySelector("#add-project").addEventListener("click", () => {
    activity.textContent = "Project creation is coming after tasks.";
});

document.querySelector("#add-note").addEventListener("click", () => {
    activity.textContent = "Notes will come after the core task system.";
});
