// State
let terminals = [{ id: 0, sql: "", results: null }];
let activeTabId = 0;
let nextTabId = 1;
let investigations = [];
let remainingTime = 0;

// Theme Logic
const themeBtn = document.getElementById("themeToggle");
if (themeBtn) {
  themeBtn.addEventListener("click", toggleTheme);
}

// Check preference
if (localStorage.getItem("theme") === "light") {
  document.body.classList.add("light-mode");
}

function toggleTheme() {
  document.body.classList.toggle("light-mode");
  const isLight = document.body.classList.contains("light-mode");
  localStorage.setItem("theme", isLight ? "light" : "dark");
}

// Init
document.addEventListener("DOMContentLoaded", () => {
  initGame();
  setInterval(updateTimer, 1000);
});

async function initGame() {
  // Run data fetching in parallel
  await Promise.all([syncState(), loadInvestigations(), loadSchema()]);
  renderTabs();
  restoreActiveTerminal();
  initNotepad();
}

function initNotepad() {
  const notepad = document.getElementById("caseNotes");
  if (!notepad) return;

  // Load saved notes
  const savedNotes = localStorage.getItem("case_notes");
  if (savedNotes) {
    notepad.value = savedNotes;
  }

  // Save on input
  notepad.addEventListener("input", (e) => {
    localStorage.setItem("case_notes", e.target.value);
  });
}

async function loadSchema() {
  console.log("Loading schema...");
  try {
    const res = await fetch("/api/schema");
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Failed to load schema");
    }
    const schema = await res.json();
    console.log("Schema loaded:", schema);
    renderSchema(schema);
  } catch (e) {
    console.error("Failed to load schema", e);
    document.getElementById("schemaList").innerHTML =
      `<div class="error-msg">Schema load failed: ${e.message}</div>`;
  }
}

function renderSchema(schema) {
  console.log("Rendering schema:", schema);
  const list = document.getElementById("schemaList");
  if (!list) {
    console.error("schemaList element not found!");
    return;
  }
  list.innerHTML = "";

  if (Object.keys(schema).length === 0) {
    list.innerHTML = '<div class="result-msg">No visible tables found.</div>';
    return;
  }

  for (const [table, columns] of Object.entries(schema)) {
    const div = document.createElement("div");
    div.className = "schema-table";

    const header = document.createElement("div");
    header.className = "table-name";
    header.innerText = table;
    header.onclick = () => {
      // Inject SELECT query
      const sql = `SELECT * FROM ${table}`;
      const activeTab = terminals[activeTabId];
      activeTab.sql = sql; // update state
      document.getElementById("sqlEditor").value = sql;
      document.getElementById("sqlEditor").focus();

      // Toggle columns visibility (optional improvement)
      colsDiv.classList.toggle("visible");
    };

    const colsDiv = document.createElement("div");
    colsDiv.className = "table-columns";
    columns.forEach((col) => {
      const colDiv = document.createElement("div");
      colDiv.className = "column-name";
      colDiv.innerText = col;
      colsDiv.appendChild(colDiv);
    });

    div.appendChild(header);
    div.appendChild(colsDiv);
    list.appendChild(div);
  }
}

async function syncState() {
  try {
    const res = await fetch("/api/state");
    if (res.ok) {
      const data = await res.json();
      remainingTime = data.remaining_time;
      document.getElementById("userName").textContent = data.name;

      // Show submit button if in Round 2
      if (data.round >= 2) {
        document.getElementById("finalSubmitBtn").classList.remove("hidden");
      }
    } else {
      window.location.href = "/";
    }
  } catch (e) {
    console.error("Sync failed", e);
  }
}

document.getElementById("finalSubmitBtn").addEventListener("click", async () => {
  // Get the answer from investigation 2 input field
  const inv2Input = document.getElementById("ans-2");
  const answer = inv2Input ? inv2Input.value.trim() : investigation2Answer;
  
  if (!answer) {
    alert("Please enter your answer in Investigation #2 first!");
    if (inv2Input) inv2Input.focus();
    return;
  }
  
  if (confirm(`Submit final answer: "${answer}"?\n\nThis cannot be undone.`)) {
    try {
      // First send to verify endpoint for investigation 2
      const verifyRes = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: 2, answer: answer }),
      });
      
      const verifyData = await verifyRes.json();
      
      // Also submit as final answer
      document.getElementById("finalAnswerInput").value = answer;
      document.getElementById("finalForm").submit();
    } catch (e) {
      console.error("Submission error:", e);
      alert("Submission failed. Please try again.");
    }
  }
});

async function loadInvestigations() {
  console.log("Loading investigations...");
  try {
    const res = await fetch("/api/investigations");
    if (!res.ok) throw new Error("Investigations fetch failed");
    const data = await res.json();
    console.log("Investigations loaded:", data);
    investigations = data;
    renderInvestigations();
  } catch (e) {
    console.error("Failed to load investigations", e);
    document.getElementById("investigationList").innerHTML =
      '<div class="error-msg">Failed to load directives</div>';
  }
}

// Timer
let timerExpired = false; // Prevent multiple redirects

function updateTimer() {
  if (remainingTime > 0) {
    remainingTime--;
    const totalSeconds = Math.floor(remainingTime);
    const h = Math.floor(totalSeconds / 3600)
      .toString()
      .padStart(2, "0");
    const m = Math.floor((totalSeconds % 3600) / 60)
      .toString()
      .padStart(2, "0");
    const s = Math.floor(totalSeconds % 60)
      .toString()
      .padStart(2, "0");
    document.getElementById("timerDisplay").innerText = `${h}:${m}:${s}`;
  } else {
    document.getElementById("timerDisplay").innerText = "00:00:00";
    
    // Auto-logout when time runs out
    if (!timerExpired) {
      timerExpired = true;
      alert("⏱️ TIME'S UP!\n\nYour session has expired.");
      window.location.href = '/logout';
    }
  }
}

// Global variable to store investigation 2 answer (placeholder answer)
let investigation2Answer = "";

// Investigations UI
function renderInvestigations() {
  const list = document.getElementById("investigationList");
  list.innerHTML = "";

  let allSolved = true;

  investigations.forEach((inv) => {
    const div = document.createElement("div");
    div.className = `investigation-card ${inv.solved ? "solved" : ""}`;

    let content = `
            <div class="inv-header">
                <span>ID: #${inv.id}</span>
                <span>${inv.solved ? "SOLVED" : "PENDING"}</span>
            </div>
            <div class="inv-prompt">${inv.prompt}</div>
        `;

    if (!inv.solved) {
      allSolved = false;
      
      // Check if this is investigation 2 (the placeholder investigation)
      if (inv.id === 2) {
        // Investigation 2 is a placeholder - shows input only, submit via SUBMIT FINAL REPORT button
        content += `
                <div class="inv-input-group placeholder-answer">
                    <input type="text" class="inv-input" placeholder="Enter your final answer here..." id="ans-${inv.id}" 
                           oninput="updateInvestigation2Answer(this.value)">
                    <span style="font-size: 0.7rem; color: var(--text-dim); margin-top: 6px; display: block;">
                        Use SUBMIT FINAL REPORT button below to submit
                    </span>
                </div>
            `;
      } else {
        // Regular investigation with immediate submit
        content += `
                <div class="inv-input-group">
                    <input type="text" class="inv-input" placeholder="Answer..." id="ans-${inv.id}">
                    <button class="inv-submit" onclick="submitAnswer(${inv.id})">></button>
                </div>
            `;
      }
    }

    div.innerHTML = content;
    list.appendChild(div);
  });

  // Check if ready for final submit (Round 2 logic or just specific ID logic)
  // For simplicity, if we are in Round 2 and solved the final mystery (assuming there's a distinct trigger or we just show a manual Final Submit button if desired)
  // The requirements say Round 2 determines mystery solution.
  // Let's assume if there are no more investigations to solve, we might be done OR we need to unlock next round.
  // But since `get_investigations` depends on `current_round` in backend, we should refresh after solves.
  if (allSolved) {
    // Maybe refresh to see if new round unlocked?
    setTimeout(loadInvestigations, 1000);
  }
}

async function submitAnswer(id) {
  console.log("submitAnswer called with id:", id);
  const input = document.getElementById(`ans-${id}`);
  console.log("Input element:", input);
  const answer = input ? input.value : "";
  console.log("Answer value:", answer);

  if (!answer.trim()) {
    alert("Please enter an answer!");
    return;
  }

  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, answer }),
    });

    const data = await res.json();
    console.log("Verify response:", data);
    
    if (data.correct) {
      // Reload to update state (and potentially round)
      await loadInvestigations();
      await syncState(); // Also sync state to update round and show submit button
      alert("✓ Correct! Investigation solved.");
    } else {
      input.style.borderColor = "red";
      setTimeout(() => (input.style.borderColor = "#444"), 1000);
      alert("✗ Incorrect answer. Try again.");
    }
  } catch (e) {
    console.error("Submit error:", e);
    alert("Submission failed. Please try again.");
  }
}

// Update the global investigation 2 answer when user types
function updateInvestigation2Answer(value) {
  investigation2Answer = value.trim();
}

// Terminals
function renderTabs() {
  const container = document.getElementById("tabContainer");
  container.innerHTML = "";

  terminals.forEach((t, index) => {
    const div = document.createElement("div");
    div.className = `tab ${t.id === terminals[activeTabId].id ? "active" : ""}`;

    // Tab label
    const label = document.createElement("span");
    label.className = "tab-label";
    label.innerText = `TERM_${t.id.toString().padStart(2, "0")}`;
    label.onclick = () => switchTab(index);
    div.appendChild(label);

    // Close button (only show if more than one terminal)
    if (terminals.length > 1) {
      const closeBtn = document.createElement("span");
      closeBtn.className = "tab-close";
      closeBtn.innerText = "×";
      closeBtn.onclick = (e) => {
        e.stopPropagation();
        closeTab(index);
      };
      div.appendChild(closeBtn);
    }

    container.appendChild(div);
  });

  const add = document.createElement("div");
  add.className = "tab-add";
  add.innerText = "+";
  add.onclick = addTab;
  container.appendChild(add);
}

function closeTab(index) {
  // Prevent closing the last terminal
  if (terminals.length <= 1) return;

  terminals.splice(index, 1);

  // Adjust activeTabId if necessary
  if (activeTabId >= terminals.length) {
    activeTabId = terminals.length - 1;
  } else if (activeTabId > index) {
    activeTabId--;
  }

  renderTabs();
  restoreActiveTerminal();
}

function addTab() {
  terminals.push({ id: nextTabId++, sql: "", results: null });
  switchTab(terminals.length - 1);
}

function switchTab(index) {
  // Save current
  const current = terminals[activeTabId];
  current.sql = document.getElementById("sqlEditor").value;
  current.resultsHTML = document.getElementById("resultsArea").innerHTML; // quick hack to save visual state

  activeTabId = index;
  renderTabs();
  restoreActiveTerminal();
}

function restoreActiveTerminal() {
  const t = terminals[activeTabId];
  document.getElementById("sqlEditor").value = t.sql || "";
  if (t.resultsHTML) {
    document.getElementById("resultsArea").innerHTML = t.resultsHTML;
  } else {
    document.getElementById("resultsArea").innerHTML =
      '<div class="result-msg">READY. AWAITING INPUT.</div>';
  }
  document.getElementById("sqlEditor").focus();
}

async function runQuery() {
  const sql = document.getElementById("sqlEditor").value;
  const resArea = document.getElementById("resultsArea");

  resArea.innerHTML = '<div class="result-msg">EXECUTING...</div>';

  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });

  const data = await res.json();

  if (data.error) {
    resArea.innerHTML = `<div class="error-msg">ERROR: ${data.error}</div>`;
  } else {
    renderTable(data);
  }
}

function renderTable(data) {
  if (!data.results || data.results.length === 0) {
    document.getElementById("resultsArea").innerHTML =
      '<div class="result-msg">QUERY OK. NO DATA RETURNED.</div>';
    return;
  }

  const cols = data.columns;
  let html = "<table><thead><tr>";
  cols.forEach((c) => (html += `<th>${c}</th>`));
  html += "</tr></thead><tbody>";

  data.results.forEach((row) => {
    html += "<tr>";
    cols.forEach((c) => (html += `<td>${row[c]}</td>`));
    html += "</tr>";
  });

  html += "</tbody></table>";
  document.getElementById("resultsArea").innerHTML = html;
}
