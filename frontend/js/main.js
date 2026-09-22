const taskForm=document.querySelector("#task-form");
const taskTitle=document.querySelector("#task-title");
const taskDue=document.querySelector("#task-due");
const taskList=document.querySelector("#task-list");
const taskCount=document.querySelector("#task-count");
const emptyTasks=document.querySelector("#empty-tasks");
const taskError=document.querySelector("#task-error");
const activity=document.querySelector("#activity-message");

function showError(message){taskError.textContent=message;taskError.hidden=false}
function clearError(){taskError.hidden=true;taskError.textContent=""}
function formatDue(date){if(!date)return ""; const d=new Date(date+"T00:00:00"); return d.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"})}

function renderTasks(tasks){
 taskList.replaceChildren(); taskCount.textContent=tasks.length; emptyTasks.hidden=tasks.length!==0;
 for(const task of tasks){
  const item=document.createElement("li"); item.className="task-item"; if(task.completed)item.classList.add("completed");
  const check=document.createElement("button"); check.type="button"; check.className="task-check"; check.textContent=task.completed?"✓":"○"; check.disabled=task.completed; check.onclick=()=>completeTask(task.id);
  const content=document.createElement("div"); content.className="task-content";
  const title=document.createElement("span"); title.className="task-title"; title.textContent=task.title;
  content.appendChild(title);
  if(task.due_date){const due=document.createElement("small"); due.className="task-due"; due.textContent="Due "+formatDue(task.due_date); content.appendChild(due)}
  const edit=document.createElement("button"); edit.type="button"; edit.textContent="Edit"; edit.className="edit-task"; edit.onclick=()=>editTask(task);
  const del=document.createElement("button"); del.type="button"; del.textContent="Delete"; del.className="delete-task"; del.onclick=()=>deleteTask(task.id);
  item.append(check,content,edit,del); taskList.appendChild(item);
 }
}
async function loadTasks(){clearError();try{const r=await fetch("/api/tasks");if(!r.ok)throw Error("Could not load tasks.");renderTasks(await r.json())}catch(e){showError(e.message)}}
async function completeTask(id){clearError();try{const r=await fetch("/api/tasks/"+id+"/complete",{method:"PATCH"});if(!r.ok)throw Error("Could not complete task.");activity.textContent="Task completed.";await loadTasks()}catch(e){showError(e.message)}}
async function deleteTask(id){clearError();try{const r=await fetch("/api/tasks/"+id,{method:"DELETE"});if(!r.ok)throw Error("Could not delete task.");activity.textContent="Task deleted.";await loadTasks()}catch(e){showError(e.message)}}
async function editTask(task){
 const title=prompt("Edit task title:",task.title); if(title===null)return;
 const clean=title.trim(); if(!clean){showError("Task title cannot be empty.");return}
 const due=prompt("Due date (YYYY-MM-DD), or leave blank:",task.due_date||""); if(due===null)return;
 try{const r=await fetch("/api/tasks/"+task.id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:clean,due_date:due.trim()||null})});if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.detail||"Could not update task.")}activity.textContent="Task updated.";await loadTasks()}catch(e){showError(e.message)}
}
taskForm.addEventListener("submit",async e=>{e.preventDefault();clearError();const title=taskTitle.value.trim();if(!title)return;try{const r=await fetch("/api/tasks",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title,due_date:taskDue.value||null})});if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.detail||"Could not create task.")}taskForm.reset();activity.textContent="Task added.";await loadTasks();taskTitle.focus()}catch(e){showError(e.message)}});
document.querySelector("#theme-button").onclick=()=>document.body.classList.toggle("dark");
loadTasks();