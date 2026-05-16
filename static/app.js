/* Fitness RPG — Frontend JS */

// ── Mobile nav hamburger ─────────────────────────────────────────────────────

const hamburger = document.getElementById("nav-hamburger");
const navLinks  = document.getElementById("nav-links");
if (hamburger && navLinks) {
  hamburger.addEventListener("click", () => {
    navLinks.classList.toggle("open");
  });
  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove("open");
    }
  });
}

// ── Auto-dismiss flash messages after 5s ────────────────────────────────────

document.querySelectorAll(".flash").forEach((el) => {
  setTimeout(() => {
    el.style.transition = "opacity 0.4s ease";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 400);
  }, 5000);
});

// ── Loading overlay ──────────────────────────────────────────────────────────

function showLoading(msg = "Generating your quest…") {
  const overlay = document.getElementById("loading-overlay");
  const text    = document.getElementById("loading-text");
  if (overlay) {
    if (text) text.textContent = msg;
    overlay.classList.add("active");
  }
}

function hideLoading() {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) overlay.classList.remove("active");
}

// ── Character counters ───────────────────────────────────────────────────────

function initCharCounter(inputId, counterId, max) {
  const input   = document.getElementById(inputId);
  const counter = document.getElementById(counterId);
  if (!input || !counter) return;

  function update() {
    const len = input.value.length;
    counter.textContent = `${len} / ${max}`;
    counter.className = "char-counter";
    if (len >= max)        counter.classList.add("over");
    else if (len >= max * 0.85) counter.classList.add("warn");
  }

  input.addEventListener("input", update);
  update();
}

initCharCounter("fitness_goal", "goal-counter",  120);
initCharCounter("equipment",    "equip-counter", 120);

// ── Workout generation form ──────────────────────────────────────────────────

const generateForm = document.getElementById("generate-form");
if (generateForm) {
  generateForm.addEventListener("submit", () => {
    showLoading("Summoning your quest from the AI oracle…");
  });
}

// ── Complete workout ─────────────────────────────────────────────────────────

function completeWorkout(workoutId) {
  const btn = document.getElementById("complete-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Completing…";
  }

  fetch(`/complete/${workoutId}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        alert("Error: " + data.error);
        if (btn) { btn.disabled = false; btn.textContent = "Complete Quest ✓"; }
        return;
      }
      updateDashboardStats(data);
      showResultModal(data);
    })
    .catch(() => {
      alert("Network error. Please try again.");
      if (btn) { btn.disabled = false; btn.textContent = "Complete Quest ✓"; }
    });
}

// ── Update dashboard stats live ──────────────────────────────────────────────

function updateDashboardStats(data) {
  const xpBar      = document.getElementById("xp-bar-fill");
  const xpText     = document.getElementById("xp-text");
  const xpStat     = document.getElementById("stat-xp");
  const levelStat  = document.getElementById("stat-level");
  const streakStat = document.getElementById("stat-streak");
  const levelLabel = document.getElementById("level-label");

  if (xpBar && data.xp_to_next > 0) {
    const pct = Math.min(100, Math.round((data.new_xp / data.xp_to_next) * 100));
    xpBar.style.width = pct + "%";
  }
  if (xpText)     xpText.textContent = `${data.new_xp} / ${data.xp_to_next} XP`;
  if (xpStat)    { xpStat.textContent = data.new_xp;     pulse(xpStat); }
  if (levelStat) { levelStat.textContent = data.new_level; if (data.leveled_up) pulse(levelStat); }
  if (streakStat){ streakStat.textContent = data.new_streak; pulse(streakStat); }
  if (levelLabel)  levelLabel.textContent = `Level ${data.new_level} → ${data.new_level + 1}`;
}

function pulse(el) {
  el.classList.remove("stat-pulse");
  void el.offsetWidth;
  el.classList.add("stat-pulse");
}

// ── Result modal ─────────────────────────────────────────────────────────────

function showResultModal(data) {
  const modal = document.getElementById("result-modal");
  if (!modal) return;

  // XP breakdown
  document.getElementById("modal-base-xp").textContent = `+${data.base_xp} XP`;

  const streakRow = document.getElementById("streak-bonus-row");
  if (data.streak_bonus_xp > 0) {
    streakRow.style.display = "flex";
    document.getElementById("streak-bonus-label").textContent =
      `🔥 Streak Bonus (${Math.round((data.streak_multiplier - 1) * 100)}%)`;
    document.getElementById("modal-streak-bonus").textContent = `+${data.streak_bonus_xp} XP`;
  } else {
    streakRow.style.display = "none";
  }

  const dailyRow = document.getElementById("daily-bonus-row");
  if (data.daily_bonus_xp > 0) {
    dailyRow.style.display = "flex";
    document.getElementById("modal-daily-bonus").textContent = `+${data.daily_bonus_xp} XP`;
  } else {
    dailyRow.style.display = "none";
  }

  document.getElementById("modal-total-xp").textContent = `+${data.total_xp_gained} XP`;
  document.getElementById("modal-streak").textContent   = `🔥 ${data.new_streak} day streak`;

  // Level up
  const levelUpSection = document.getElementById("modal-levelup");
  if (data.leveled_up) {
    levelUpSection.style.display = "block";
    document.getElementById("modal-new-level").textContent = data.new_level;
    document.getElementById("modal-new-title").textContent = `✨ New title: ${data.new_title}`;
    document.getElementById("modal-icon").textContent  = "⬆️";
    document.getElementById("modal-title").textContent = "Level Up!";
  } else {
    levelUpSection.style.display = "none";
    document.getElementById("modal-icon").textContent  = "🏆";
    document.getElementById("modal-title").textContent = "Quest Complete!";
  }

  // New achievements
  const achSection = document.getElementById("modal-achievements");
  const achList    = document.getElementById("modal-ach-list");
  if (data.new_achievements && data.new_achievements.length > 0) {
    achSection.style.display = "block";
    achList.innerHTML = data.new_achievements
      .map(a => `<div class="ach-chip unlocked">${a.emoji} ${a.name}</div>`)
      .join("");
  } else {
    achSection.style.display = "none";
  }

  modal.classList.add("active");
}

function closeModal() {
  const modal = document.getElementById("result-modal");
  if (modal) modal.classList.remove("active");
  window.location.reload();
}

document.addEventListener("click", (e) => {
  const modal = document.getElementById("result-modal");
  if (modal && e.target === modal) closeModal();
});
