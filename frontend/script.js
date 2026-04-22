const baseUrl = "http://127.0.0.1:5000/api";

async function fetchJson(path, options) {
  const res = await fetch(`${baseUrl}${path}`, options);
  return res.json();
}

function appendChat(role, text) {
  const chatWindow = document.getElementById("chatWindow");
  const message = document.createElement("div");
  message.className = role === "user" ? "message-user mb-3" : "message-assistant mb-3";
  message.innerText = text;
  chatWindow.appendChild(message);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function updateOverview() {
  const data = await fetchJson("/overview");
  document.getElementById("taskCount").innerText = data.taskCount;
  document.getElementById("reminderCount").innerText = data.reminderCount;
  document.getElementById("mealCount").innerText = data.mealCount;
  const statusPanels = document.getElementById("statusPanels");
  statusPanels.innerHTML = `
    <div class="rounded-3xl bg-slate-950/80 p-4">
      <h3 class="text-sm font-semibold text-cyan-200">Next action</h3>
      <p class="mt-2 text-slate-300">${data.nextAction}</p>
    </div>
    <div class="rounded-3xl bg-slate-950/80 p-4">
      <h3 class="text-sm font-semibold text-emerald-200">Safety note</h3>
      <p class="mt-2 text-slate-300">${data.safetyTip}</p>
    </div>
  `;
}

async function sendChat(message) {
  appendChat("user", message);
  const response = await fetchJson("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message}),
  });
  appendChat("assistant", response.answer || response.error || "No response.");
}

async function requestBalance() {
  const response = await fetchJson("/assist/task_balance", {method: "POST"});
  document.getElementById("balanceAdvice").innerText = response.advice || "Unable to balance tasks yet.";
}

async function requestMealPlan(ingredients) {
  const response = await fetchJson("/assist/meal_planner", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ingredients}),
  });
  document.getElementById("mealAdvice").innerText = response.plan || response.error || "No meal plan available.";
}

async function triggerSOS() {
  const response = await fetchJson("/safety/alert", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: "SOS - need safety help now"}),
  });
  document.getElementById("balanceAdvice").innerText = response.alert || "SOS sent.";
}

async function addTask(task) {
  const response = await fetchJson("/tasks", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: task}),
  });
  updateOverview();
  return response;
}

async function addReminder(note) {
  const response = await fetchJson("/reminders", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({note}),
  });
  updateOverview();
  return response;
}

window.addEventListener("DOMContentLoaded", () => {
  updateOverview();

  document.getElementById("chatForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    await sendChat(message);
  });

  document.getElementById("mealForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const ingredients = document.getElementById("ingredientsInput").value.trim();
    if (!ingredients) return;
    await requestMealPlan(ingredients);
  });

  document.getElementById("balanceButton").addEventListener("click", requestBalance);
  document.getElementById("sosButton").addEventListener("click", triggerSOS);

  document.getElementById("taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const task = document.getElementById("taskInput").value.trim();
    if (!task) return;
    document.getElementById("taskInput").value = "";
    await addTask(task);
  });

  document.getElementById("reminderForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const note = document.getElementById("reminderInput").value.trim();
    if (!note) return;
    document.getElementById("reminderInput").value = "";
    await addReminder(note);
  });
});
