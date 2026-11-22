const STORAGE_KEY = "studymentor-ai-state";
const THEME_KEY = "studymentor-ai-theme";

// API Base URL - auto-detect based on current origin, localStorage, or meta tag
const API_BASE = (() => {
  // Check for custom override in localStorage
  const savedApi = localStorage.getItem("studymentor_api_url");
  if (savedApi && savedApi.trim()) {
    return savedApi.trim().replace(/\/+$/, "");
  }

  // Check meta tag (only if not hardcoded to default placeholder)
  const metaApiBase = document.querySelector('meta[name="api-base-url"]');
  if (metaApiBase && metaApiBase.getAttribute('content') && !metaApiBase.getAttribute('content').includes('studymentor-api.onrender.com')) {
    return metaApiBase.getAttribute('content').replace(/\/+$/, "");
  }

  // If running in browser over HTTP/HTTPS, relative /api connects directly to the hosting server
  if (window.location.origin && window.location.origin !== "null" && !window.location.origin.startsWith("file:")) {
    return `${window.location.origin}/api`;
  }

  // Default for local development
  return 'http://localhost:8000/api';
})();

const page = document.body.dataset.page;

// Stream to subjects mapping
const streamSubjects = {
  Science: ["Math", "Physics", "Chemistry", "Biology", "English", "Computer Science"],
  Commerce: ["Accountancy", "Economics", "Business Studies", "English", "Math", "Computer Science"],
  Arts: ["History", "Geography", "Political Science", "Economics", "English", "Psychology", "Sociology"],
  General: ["Math", "Physics", "Chemistry", "Biology", "English", "Economics", "History", "Geography", "Computer Science", "Accountancy"],
  Engineering: [
    "Mathematics 1", "Engineering Physics", "Engineering Chemistry",
    "Programming in Python", "Data Structures & Algorithms",
    "Basic Electrical Engineering", "Engineering Mechanics", "Thermodynamics"
  ]
};

// Rich curriculum topics for subjects
const subjectCurriculum = {
  Math: [
    { title: "Quadratic Equations & Roots", desc: "Discriminant analysis, factoring methods, and parabolic graph roots." },
    { title: "Differential Calculus & Chain Rule", desc: "Rates of change, derivatives, tangent slopes, and optimization." },
    { title: "Vectors & Matrices", desc: "Matrix multiplication, determinants, inverses, and systems of linear equations." },
    { title: "Probability & Combinatorics", desc: "Permutations, conditional probability, and Bayes' Theorem." }
  ],
  Mathematics: [
    { title: "Calculus & Integrals", desc: "Fundamental theorem of calculus, substitution, and definite integrals." },
    { title: "Linear Algebra & Matrices", desc: "Eigenvalues, matrix rank, determinants, and linear transformations." }
  ],
  "Mathematics 1": [
    { title: "Differential Calculus", desc: "Successive differentiation, Taylor series, and partial derivatives." },
    { title: "Matrix Algebra", desc: "Rank of a matrix, Cayley-Hamilton theorem, and diagonalisation." }
  ],
  Physics: [
    { title: "Newton's Laws & Friction", desc: "Free-body diagrams, static vs kinetic friction, and inclined plane dynamics." },
    { title: "Work, Energy & Power", desc: "Conservation of mechanical energy, work-energy theorem, and collisions." },
    { title: "Thermodynamics & Heat Cycles", desc: "First and second laws, Carnot efficiency, and PV engine cycles." },
    { title: "Electromagnetism & Circuits", desc: "Kirchhoff's laws, capacitance, and magnetic Lorentz force." }
  ],
  "Engineering Physics": [
    { title: "Wave Optics & Interference", desc: "Young's double slit experiment, diffraction gratings, and lasers." },
    { title: "Quantum Physics & Wavepackets", desc: "Photoelectric effect, de Broglie hypothesis, and Schrodinger equation." }
  ],
  Chemistry: [
    { title: "Chemical Bonding & VSEPR", desc: "Lewis structures, orbital hybridization, and 3D molecular geometry." },
    { title: "Chemical Equilibrium & Kinetics", desc: "Equilibrium constant Kc, Le Chatelier's principle, and reaction orders." },
    { title: "Thermodynamics & Enthalpy", desc: "Hess's law, enthalpy change, entropy, and Gibbs free energy." },
    { title: "Organic Reaction Mechanisms", desc: "Electrophilic addition, nucleophilic substitution (SN1/SN2), and resonance." }
  ],
  "Engineering Chemistry": [
    { title: "Electrochemistry & Corrosion", desc: "Galvanic cells, Nernst equation, and corrosion prevention methods." },
    { title: "Polymer & Nano Materials", desc: "Polymerization synthesis, conducting polymers, and nanomaterials." }
  ],
  Biology: [
    { title: "Cellular Respiration & Glycolysis", desc: "Krebs cycle, electron transport chain, and ATP synthase yield." },
    { title: "Mendelian Genetics & DNA", desc: "Monohybrid/dihybrid crosses, DNA replication, and gene expression." },
    { title: "Human Physiology & Circulatory System", desc: "Cardiac cycle, oxygen transport, and neuro-endocrine regulation." }
  ],
  "Computer Science": [
    { title: "Data Structures & Big-O", desc: "Arrays, linked lists, stacks, queues, and asymptotic runtime complexity." },
    { title: "Object-Oriented Programming", desc: "Encapsulation, inheritance, polymorphism, and abstraction." },
    { title: "Relational Databases & SQL", desc: "Queries, joins, 1NF/2NF/3NF normalization, and transaction ACID." }
  ],
  "Programming in Python": [
    { title: "Python Fundamentals & Data Structures", desc: "Lists, dictionaries, list comprehensions, and functional methods." },
    { title: "Algorithmic Problem Solving", desc: "Recursion, binary search, sorting algorithms, and modular design." }
  ],
  "Data Structures & Algorithms": [
    { title: "Trees & Graph Traversals", desc: "Binary search trees, BFS, DFS, and shortest path algorithms." },
    { title: "Dynamic Programming", desc: "Memoization, tabulation, knapsack problems, and optimal substructure." }
  ],
  Economics: [
    { title: "Supply, Demand & Elasticity", desc: "Market equilibrium shifts, price elasticity of demand, and consumer surplus." },
    { title: "National Income & Macroeconomics", desc: "GDP measurement, aggregate demand, fiscal stimulus, and inflation." },
    { title: "Monetary Policy & Central Banking", desc: "Interest rates, reserve requirements, and open market operations." }
  ],
  Accountancy: [
    { title: "Double-Entry Accounting & Ledgers", desc: "Dual aspect concept, journalizing transactions, and trial balances." },
    { title: "Financial Statements & Balance Sheets", desc: "Asset categorization, liabilities, and revenue recognition." }
  ],
  "Business Studies": [
    { title: "Management Principles & Functions", desc: "Planning, organizing, staffing, directing, and controlling processes." },
    { title: "Marketing Mix (The 4 Ps)", desc: "Product lifecycle, dynamic pricing, distribution, and promotion channels." }
  ],
  History: [
    { title: "Modern World Revolutions", desc: "Industrial revolution, constitutional reforms, and societal impacts." },
    { title: "Post-War International Alliances", desc: "Decolonization, the Cold War, and international economic treaties." }
  ],
  English: [
    { title: "Critical Reading & Essay Synthesis", desc: "Argument analysis, rhetorical devices, and structured analytical essays." },
    { title: "Advanced Grammar & Cohesion", desc: "Syntax precision, transitional cohesion, and vocabulary in context." }
  ]
};

const defaultTopics = ["Math", "Physics", "Chemistry", "Biology", "English", "Economics", "History", "Accountancy"];
let appState = loadState();
let currentTopic = null;

applyTheme();

if (page === "planning") {
  initPlanningPage();
}

if (page === "dashboard") {
  initDashboardPage();
}

// -------------------------------------------------------------
// Planning Page Controller
// -------------------------------------------------------------
function initPlanningPage() {
  initAuth();
  initAiConfig();
  checkBackendHealth();

  const onboardingForm = document.getElementById("onboardingForm");
  const streamSelect = document.getElementById("streamSelect");
  const subjectsContainer = document.getElementById("subjectsSelect");
  const weakSubjectsContainer = document.getElementById("weakSubjectsSelect");
  const submitBtn = document.getElementById("planSubmitBtn") || (onboardingForm ? onboardingForm.querySelector('button[type="submit"]') : null);

  if (streamSelect) {
    streamSelect.addEventListener("change", () => {
      populateSubjects(streamSelect.value, subjectsContainer, weakSubjectsContainer);
    });
    if (streamSelect.value) {
      populateSubjects(streamSelect.value, subjectsContainer, weakSubjectsContainer);
    }
  }

  if (onboardingForm) {
    onboardingForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(onboardingForm);

      const subjectCheckboxes = [...subjectsContainer.querySelectorAll('input[name="subjects"]')];
      const weakSubjectCheckboxes = [...weakSubjectsContainer.querySelectorAll('input[name="weakSubjects"]')];

      const selectedSubjects = getCheckedValues(subjectCheckboxes);
      const selectedWeakSubjects = getCheckedValues(weakSubjectCheckboxes).filter((subject) =>
        selectedSubjects.includes(subject)
      );

      if (!selectedSubjects.length) {
        showNotification("Select at least one subject to continue.");
        return;
      }

      const profile = {
        name: formData.get("name").toString().trim() || "Student",
        class_level: formData.get("classLevel").toString(),
        stream: formData.get("stream").toString(),
        study_hours_per_day: clampNumber(Number(formData.get("studyHours")), 1, 12, 3),
        subjects: selectedSubjects,
        weak_subjects: selectedWeakSubjects
      };

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "✨ Synthesizing AI Study Plan...";
      }
      showNotification("✨ AI is analyzing syllabus & generating your schedule...");

      // Call backend AI study planner
      let generatedPlanBlocks = null;
      try {
        const planRes = await apiRequest("/plan/generate", {
          method: "POST",
          body: JSON.stringify(profile)
        });

        if (planRes && planRes.blocks && planRes.blocks.length > 0) {
          generatedPlanBlocks = planRes.blocks;
        } else if (planRes && planRes.plan_data && planRes.plan_data.blocks) {
          generatedPlanBlocks = planRes.plan_data.blocks;
        }
      } catch (err) {
        console.warn("Backend AI plan generation notice:", err);
      }

      const progress = {};
      profile.subjects.forEach((subject, index) => {
        progress[subject] = profile.weak_subjects.includes(subject) ? 25 : Math.min(75, 35 + index * 10);
      });

      // Prepare plan blocks
      const fallbackPlan = generateStudyPlan(
        { ...profile, classLevel: profile.class_level, studyHours: profile.study_hours_per_day, weakSubjects: profile.weak_subjects },
        progress
      );

      appState = {
        profile: {
          name: profile.name,
          classLevel: profile.class_level,
          stream: profile.stream,
          studyHours: profile.study_hours_per_day,
          subjects: profile.subjects,
          weakSubjects: profile.weak_subjects
        },
        progress,
        streak: 1,
        plan: (generatedPlanBlocks && generatedPlanBlocks.length > 0) ? generatedPlanBlocks : fallbackPlan,
        completedTopics: [],
        quizScores: {},
        lastActiveDate: getTodayKey()
      };

      saveState();
      showNotification("Study Plan generated! Launching your cockpit...");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 500);
    });
  }
}

function populateSubjects(stream, subjectsContainer, weakSubjectsContainer) {
  if (!subjectsContainer || !weakSubjectsContainer) return;
  const subjects = streamSubjects[stream] || streamSubjects["Science"];

  subjectsContainer.innerHTML = subjects.map(subject =>
    `<label class="checkbox-item"><input type="checkbox" name="subjects" value="${subject}" checked>${subject}</label>`
  ).join("");

  weakSubjectsContainer.innerHTML = subjects.map(subject =>
    `<label class="checkbox-item"><input type="checkbox" name="weakSubjects" value="${subject}">${subject}</label>`
  ).join("");

  const subjectCheckboxes = [...subjectsContainer.querySelectorAll('input[name="subjects"]')];
  const weakSubjectCheckboxes = [...weakSubjectsContainer.querySelectorAll('input[name="weakSubjects"]')];

  subjectCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes));
  });

  syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes);
}

// -------------------------------------------------------------
// Dashboard Page Controller
// -------------------------------------------------------------
function initDashboardPage() {
  if (!appState.profile || !appState.profile.subjects || appState.profile.subjects.length === 0) {
    window.location.href = "planning.html";
    return;
  }

  ensureStateIntegrity();

  const elements = {
    body: document.body,
    welcomeTitle: document.getElementById("welcomeTitle"),
    streakCount: document.getElementById("streakCount"),
    planList: document.getElementById("planList"),
    dashboardProgress: document.getElementById("dashboardProgress"),
    topicList: document.getElementById("topicList"),
    topicDetails: document.getElementById("topicDetails"),
    quizContainer: document.getElementById("quizContainer"),
    progressOverview: document.getElementById("progressOverview"),
    weakSubjectHighlights: document.getElementById("weakSubjectHighlights"),
    heroPlanText: document.getElementById("heroPlanText"),
    focusBlocksCount: document.getElementById("focusBlocksCount"),
    weakFocusCount: document.getElementById("weakFocusCount"),
    plannedMinutes: document.getElementById("plannedMinutes"),
    startStudyBtn: document.getElementById("startStudyBtn"),
    regeneratePlan: document.getElementById("regeneratePlan"),
    themeToggle: document.getElementById("themeToggle"),
    resetApp: document.getElementById("resetApp"),
    navLinks: [...document.querySelectorAll(".nav-link")],
    sections: {
      dashboard: document.getElementById("dashboardSection"),
      study: document.getElementById("studySection"),
      progress: document.getElementById("progressSection"),
      chat: document.getElementById("chatSection")
    }
  };

  initAuth();
  initAiConfig();
  initChatSection();
  checkBackendHealth();

  if (elements.startStudyBtn) {
    elements.startStudyBtn.addEventListener("click", () => switchSection("study", elements));
  }
  if (elements.regeneratePlan) {
    elements.regeneratePlan.addEventListener("click", () => refreshPlanFromAI(elements));
  }
  if (elements.themeToggle) {
    elements.themeToggle.addEventListener("click", () => toggleTheme(elements.themeToggle));
  }
  if (elements.resetApp) {
    elements.resetApp.addEventListener("click", resetApplication);
  }
  elements.navLinks.forEach((button) => {
    button.addEventListener("click", () => switchSection(button.dataset.section, elements));
  });

  currentTopic = appState.profile.subjects[0] || defaultTopics[0];
  updateThemeButton(elements.themeToggle);
  renderAll(elements);
}

function ensureStateIntegrity() {
  const { profile } = appState;
  appState.progress = appState.progress || {};
  (profile.subjects || []).forEach((subject, index) => {
    if (typeof appState.progress[subject] !== "number") {
      appState.progress[subject] = profile.weakSubjects && profile.weakSubjects.includes(subject) ? 25 : Math.min(75, 30 + index * 10);
    }
  });

  appState.completedTopics = Array.isArray(appState.completedTopics) ? appState.completedTopics : [];
  appState.quizScores = appState.quizScores || {};
  appState.streak = typeof appState.streak === "number" ? appState.streak : 1;

  if (!Array.isArray(appState.plan) || !appState.plan.length) {
    appState.plan = generateStudyPlan(profile, appState.progress);
  }

  updateStreak();
  saveState();
}

function renderAll(elements) {
  renderHeader(elements);
  renderDashboard(elements);
  renderStudySection(elements);
  renderProgressSection(elements);
}

function renderHeader(elements) {
  const { profile, streak } = appState;
  if (elements.welcomeTitle) {
    elements.welcomeTitle.textContent = `${profile.name}'s ${profile.classLevel || "Academic"} Hub`;
  }
  if (elements.streakCount) {
    elements.streakCount.textContent = String(streak);
  }
}

function renderDashboard(elements) {
  const { profile, plan, progress } = appState;
  const totalMinutes = plan.reduce((sum, item) => sum + (Number(item.minutes) || 0), 0);
  const weakFocus = plan.filter((item) => item.is_weak_subject || item.isWeak).length;

  if (elements.heroPlanText) {
    elements.heroPlanText.textContent = `${profile.stream || "Standard"} Track • ${profile.studyHours || 3} Hours/Day • ${profile.subjects.length} Focus Subjects`;
  }
  if (elements.focusBlocksCount) elements.focusBlocksCount.textContent = String(plan.length);
  if (elements.weakFocusCount) elements.weakFocusCount.textContent = String(weakFocus);
  if (elements.plannedMinutes) elements.plannedMinutes.textContent = `${totalMinutes} min`;

  if (elements.planList) {
    elements.planList.innerHTML = plan.map((item, index) => {
      const isWeak = item.is_weak_subject || item.isWeak;
      const isDone = item.is_completed || false;
      const taskDesc = item.task_description || item.task || `Focus on core exercises for ${item.topic}`;
      return `
        <div class="plan-card glass-card ${isDone ? "completed" : ""}" data-block-idx="${index}">
          <div class="plan-topline">
            <label class="plan-checkbox-label">
              <input type="checkbox" class="block-toggle" data-idx="${index}" ${isDone ? "checked" : ""}>
              <span>${index + 1}. ${item.subject}</span>
            </label>
            <span class="badge">${item.minutes} min</span>
          </div>
          <p style="margin: 8px 0; font-size: 0.95rem; line-height: 1.45;">${taskDesc}</p>
          <div class="plan-topline" style="font-size: 0.85rem; color: var(--text-muted, #9ca3af);">
            <span>📌 ${item.topic}</span>
            <span class="badge" style="${isWeak ? 'background: rgba(239, 68, 68, 0.15); color: #ef4444;' : ''}">
              ${isWeak ? "⚠️ Priority Weak Focus" : "Balanced Session"}
            </span>
          </div>
        </div>
      `;
    }).join("");

    // Attach checkbox toggle handlers
    elements.planList.querySelectorAll(".block-toggle").forEach((chk) => {
      chk.addEventListener("change", (e) => {
        const idx = Number(chk.dataset.idx);
        const block = appState.plan[idx];
        if (!block) return;

        block.is_completed = chk.checked;
        if (chk.checked) {
          appState.progress[block.subject] = Math.min(100, (appState.progress[block.subject] || 30) + 8);
          showNotification(`✅ Completed "${block.topic}"! +8% ${block.subject} mastery.`);
        }
        saveState();
        renderDashboard(elements);
        renderProgressSection(elements);
      });
    });
  }

  if (elements.dashboardProgress) {
    elements.dashboardProgress.innerHTML = profile.subjects.map((subject) => {
      const val = Math.round(progress[subject] || 0);
      return `
        <div class="subject-item">
          <div class="progress-topline">
            <strong>${subject}</strong>
            <span>${val}%</span>
          </div>
          <div class="progress-shell">
            <div class="progress-fill" style="width: ${val}%"></div>
          </div>
        </div>
      `;
    }).join("");
  }
}

async function refreshPlanFromAI(elements) {
  const btn = elements.regeneratePlan;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "✨ Generating...";
  }

  try {
    showNotification("✨ AI is rebalancing your daily study schedule...");
    const payload = {
      name: appState.profile.name,
      class_level: appState.profile.classLevel,
      stream: appState.profile.stream,
      study_hours_per_day: appState.profile.studyHours,
      subjects: appState.profile.subjects,
      weak_subjects: appState.profile.weakSubjects
    };

    const result = await apiRequest("/plan/generate", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    if (result && (result.blocks || (result.plan_data && result.plan_data.blocks))) {
      appState.plan = result.blocks || result.plan_data.blocks;
      saveState();
      renderDashboard(elements);
      showNotification("Study plan successfully refreshed with AI!");
    } else {
      regeneratePlan(elements);
    }
  } catch (error) {
    console.error("AI plan generation notice:", error);
    regeneratePlan(elements);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "✨ Rebalance with AI";
    }
  }
}

function renderStudySection(elements) {
  const subjects = appState.profile.subjects || defaultTopics.slice(0, 4);
  currentTopic = currentTopic && subjects.includes(currentTopic) ? currentTopic : subjects[0];

  // Render subject selector chips
  if (elements.topicList) {
    elements.topicList.innerHTML = subjects.map((subject) => {
      const chapters = subjectCurriculum[subject] || [{ title: `${subject} Core Mastery`, desc: "Fundamental definitions and practice exercises." }];
      const score = appState.quizScores[subject];
      const isWeak = (appState.profile.weakSubjects || []).includes(subject);

      return `
        <button class="topic-card ${subject === currentTopic ? "active" : ""}" type="button" data-topic="${subject}">
          <div class="topic-topline">
            <strong>${subject}</strong>
            <span class="badge">${isWeak ? "Weak Subject" : "Core"}</span>
          </div>
          <h4>${chapters[0].title}</h4>
          <p>${chapters[0].desc}</p>
          <span class="badge">${typeof score === "number" ? `Best Quiz: ${score}%` : "Quiz Available"}</span>
        </button>
      `;
    }).join("");

    elements.topicList.querySelectorAll(".topic-card").forEach((button) => {
      button.addEventListener("click", () => {
        currentTopic = button.dataset.topic;
        renderStudySection(elements);
      });
    });
  }

  renderTopicDetails(elements);
}

function renderTopicDetails(elements) {
  if (!elements.topicDetails) return;
  const subject = currentTopic;
  const chapters = subjectCurriculum[subject] || [{ title: `${subject} Core Concepts`, desc: `Learning content and exercises for ${subject}.` }];
  const currentChapter = chapters[0];
  const subjectProgress = Math.round(appState.progress[subject] || 0);
  const isWeak = (appState.profile.weakSubjects || []).includes(subject);
  const bestQuiz = appState.quizScores[subject];

  elements.topicDetails.innerHTML = `
    <div class="topic-detail-header">
      <div>
        <p class="eyebrow">${subject} Learning Module</p>
        <h3 class="topic-title">${currentChapter.title}</h3>
      </div>
      <span class="badge" style="font-size: 0.95rem;">${subject}</span>
    </div>

    <div class="topic-meta" style="margin: 12px 0;">
      <span class="badge">${subjectProgress}% Mastery</span>
      <span class="badge">${isWeak ? "⚠️ Needs Reinforcement" : "✅ On Track"}</span>
      <span class="badge">${typeof bestQuiz === "number" ? `Quiz Best: ${bestQuiz}%` : "Quiz Unattempted"}</span>
    </div>

    <p class="topic-description" style="line-height: 1.6; font-size: 1rem; color: var(--text, #fff); margin: 14px 0;">
      ${currentChapter.desc}
    </p>

    <div class="action-row" style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px;">
      <button id="generateExplanationBtn" class="primary-button" type="button">✨ Deep Dive AI Explanation</button>
      <button id="generatePracticeBtn" class="secondary-button" type="button">📝 AI Practice Sprint</button>
      <button id="takeQuizBtn" class="ghost-button" type="button">🎯 Take Chapter Quiz</button>
    </div>

    <div id="aiDynamicContent" style="margin-top: 20px;"></div>
  `;

  if (elements.quizContainer) {
    elements.quizContainer.classList.add("hidden");
    elements.quizContainer.innerHTML = "";
  }

  document.getElementById("takeQuizBtn").addEventListener("click", () => renderQuiz(subject, currentChapter.title, elements));
  document.getElementById("generateExplanationBtn").addEventListener("click", () => generateAIExplanation(subject, currentChapter.title, elements));
  document.getElementById("generatePracticeBtn").addEventListener("click", () => generateAIPractice(subject, currentChapter.title, elements));
}

// -------------------------------------------------------------
// AI Deep Dive & Practice
// -------------------------------------------------------------
async function generateAIExplanation(subject, topicTitle, elements) {
  const btn = document.getElementById("generateExplanationBtn");
  const container = document.getElementById("aiDynamicContent");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "✨ Generating Explanation...";
  }

  try {
    showNotification("✨ AI is generating an intuitive pedagogical breakdown...");
    const explanation = await fetchExplanation(subject, topicTitle);

    if (explanation && container) {
      if (typeof explanation === "object" && explanation.overview) {
        let html = `
          <div class="explanation-card glass-card">
            <h4 style="color: #6366f1; margin-bottom: 8px;">💡 Overview</h4>
            <p style="line-height: 1.6;">${explanation.overview}</p>
        `;

        if (explanation.key_concepts && explanation.key_concepts.length) {
          html += `
            <h4 style="color: #6366f1; margin-top: 14px; margin-bottom: 8px;">🔑 Core Principles</h4>
            <ul style="padding-left: 20px; line-height: 1.6;">
              ${explanation.key_concepts.map(c => `<li>${c}</li>`).join("")}
            </ul>
          `;
        }

        if (explanation.formulas_rules && explanation.formulas_rules.length) {
          html += `
            <h4 style="color: #6366f1; margin-top: 14px; margin-bottom: 8px;">📐 Governing Rules & Equations</h4>
            <ul style="padding-left: 20px; line-height: 1.6;">
              ${explanation.formulas_rules.map(r => `<li><code>${r}</code></li>`).join("")}
            </ul>
          `;
        }

        if (explanation.common_mistakes && explanation.common_mistakes.length) {
          html += `
            <h4 style="color: #ef4444; margin-top: 14px; margin-bottom: 8px;">⚠️ Classic Traps to Avoid</h4>
            <ul style="padding-left: 20px; line-height: 1.6;">
              ${explanation.common_mistakes.map(m => `<li>${m}</li>`).join("")}
            </ul>
          `;
        }

        if (explanation.practice_tip) {
          html += `
            <div class="hint-box" style="margin-top: 14px;">
              <strong>🎯 Memory Tip:</strong> ${explanation.practice_tip}
            </div>
          `;
        }

        html += `</div>`;
        container.innerHTML = html;
      } else {
        container.innerHTML = `<div class="explanation-card glass-card"><p>${String(explanation)}</p></div>`;
      }
      showNotification("AI Explanation ready!");
    }
  } catch (error) {
    showNotification("Unable to generate explanation: " + error.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "✨ Deep Dive AI Explanation";
    }
  }
}

async function generateAIPractice(subject, topicTitle, elements) {
  const btn = document.getElementById("generatePracticeBtn");
  const container = document.getElementById("aiDynamicContent");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "📝 Generating Exercises...";
  }

  try {
    showNotification("📝 AI is drafting deliberate practice exercises...");
    const practice = await fetchPracticeSprint(subject, topicTitle);

    if (practice && container) {
      if (typeof practice === "object" && practice.main_practice) {
        let html = `
          <div class="practice-card glass-card">
            <h4 style="color: #6366f1; margin-bottom: 8px;">🏋️ Active Practice Sprint</h4>
        `;

        if (practice.warmup && practice.warmup.length) {
          html += `
            <div style="margin-bottom: 14px;">
              <strong>Warm-up Checkpoints:</strong>
              <ul style="padding-left: 20px; margin-top: 6px;">
                ${practice.warmup.map(w => `<li>${w}</li>`).join("")}
              </ul>
            </div>
          `;
        }

        html += `<strong>Application Problems:</strong><div style="display: grid; gap: 12px; margin-top: 8px;">`;
        practice.main_practice.forEach((p, i) => {
          const desc = p.description || p;
          html += `
            <div style="padding: 12px; background: rgba(0,0,0,0.15); border-radius: 8px;">
              <p><strong>Problem ${i + 1}:</strong> ${desc}</p>
              ${p.hint ? `
                <details style="margin-top: 8px; cursor: pointer;">
                  <summary style="color: #eab308; font-size: 0.88rem;">💡 Reveal Hint</summary>
                  <div class="hint-box">${p.hint}</div>
                </details>
              ` : ""}
            </div>
          `;
        });
        html += `</div>`;

        if (practice.challenge) {
          const chDesc = practice.challenge.description || practice.challenge;
          html += `
            <div style="margin-top: 14px; padding: 12px; background: rgba(99, 102, 241, 0.1); border-left: 3px solid #6366f1; border-radius: 8px;">
              <strong>🔥 High-Order Challenge:</strong>
              <p style="margin-top: 6px;">${chDesc}</p>
            </div>
          `;
        }

        html += `</div>`;
        container.innerHTML = html;
      } else {
        container.innerHTML = `<div class="practice-card glass-card"><pre>${JSON.stringify(practice, null, 2)}</pre></div>`;
      }
      showNotification("Practice Sprint ready!");
    }
  } catch (error) {
    showNotification("Unable to generate practice: " + error.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "📝 AI Practice Sprint";
    }
  }
}

// -------------------------------------------------------------
// Interactive Quiz Engine
// -------------------------------------------------------------
function renderQuiz(subject, topicTitle, elements) {
  showNotification("🎯 Fetching AI Quiz questions...");
  fetchQuiz(subject, topicTitle).then(quizData => {
    if (quizData && quizData.questions && quizData.questions.length > 0) {
      renderQuizWithData(subject, quizData.questions, elements);
    } else {
      const topicFallback = getTopicData(subject);
      renderQuizWithData(subject, topicFallback.quiz, elements);
    }
  }).catch(() => {
    const topicFallback = getTopicData(subject);
    renderQuizWithData(subject, topicFallback.quiz, elements);
  });
}

function renderQuizWithData(subject, questions, elements) {
  const answers = new Array(questions.length).fill(null);

  elements.quizContainer.classList.remove("hidden");
  elements.quizContainer.innerHTML = `
    <div>
      <p class="eyebrow">Diagnostic Assessment</p>
      <h4 class="quiz-title">${subject} Mastery Check</h4>
    </div>
    ${questions.map((item, index) => `
      <div class="quiz-question" style="margin: 16px 0; padding: 14px; background: rgba(0,0,0,0.12); border-radius: 10px;">
        <p style="font-weight: 600; margin-bottom: 10px;">${index + 1}. ${item.question}</p>
        <div class="options">
          ${item.options.map((option, optionIndex) => `
            <button class="option-button" type="button" data-question="${index}" data-option="${optionIndex}">${option}</button>
          `).join("")}
        </div>
        ${item.explanation ? `<p class="explanation hidden" data-question="${index}" style="margin-top: 10px; color: #16a34a; font-size: 0.9rem;"><strong>Explanation:</strong> ${item.explanation}</p>` : ""}
      </div>
    `).join("")}
    <div style="display: flex; gap: 12px; margin-top: 16px;">
      <button id="submitQuizBtn" class="primary-button" type="button">Submit Diagnostic</button>
      <button id="closeQuizBtn" class="ghost-button" type="button">Dismiss</button>
    </div>
    <div id="quizResult" style="margin-top: 14px;"></div>
  `;

  elements.quizContainer.scrollIntoView({ behavior: "smooth" });

  elements.quizContainer.querySelectorAll(".option-button").forEach((button) => {
    button.addEventListener("click", () => {
      const questionIndex = Number(button.dataset.question);
      const optionIndex = Number(button.dataset.option);
      answers[questionIndex] = optionIndex;
      elements.quizContainer.querySelectorAll(`.option-button[data-question="${questionIndex}"]`).forEach((btn) => {
        btn.classList.toggle("selected", btn === button);
      });
    });
  });

  document.getElementById("closeQuizBtn").addEventListener("click", () => {
    elements.quizContainer.classList.add("hidden");
  });

  document.getElementById("submitQuizBtn").addEventListener("click", () => {
    if (answers.some((a) => a === null)) {
      showNotification("Please select an answer for all questions before submitting.");
      return;
    }

    const correct = questions.reduce((sum, item, index) => sum + Number(item.answer === answers[index]), 0);
    const score = Math.round((correct / questions.length) * 100);

    appState.quizScores[subject] = Math.max(score, appState.quizScores[subject] || 0);
    appState.progress[subject] = clampNumber((appState.progress[subject] || 30) + (score >= 60 ? 12 : 5), 0, 100, 0);

    if (!appState.completedTopics.includes(subject)) {
      appState.completedTopics.push(subject);
    }
    saveState();
    renderAll(elements);

    // Reveal all explanations and highlight correct/incorrect
    elements.quizContainer.querySelectorAll(".explanation").forEach((el) => el.classList.remove("hidden"));
    elements.quizContainer.querySelectorAll(".quiz-question").forEach((qBox, qIdx) => {
      const isCorrect = answers[qIdx] === questions[qIdx].answer;
      qBox.style.borderLeft = isCorrect ? "4px solid #22c55e" : "4px solid #ef4444";
    });

    const resultEl = document.getElementById("quizResult");
    if (resultEl) {
      resultEl.innerHTML = `
        <div class="quiz-result glass-card" style="padding: 16px; border-left: 4px solid ${score >= 70 ? '#22c55e' : '#eab308'};">
          <h4>Your Score: <strong>${score}%</strong> (${correct}/${questions.length} correct)</h4>
          <p style="margin-top: 6px;">${score >= 70 ? "🎉 Outstanding mastery! Your subject progress has been boosted." : "Good effort! Review the explanations above to solidify weak spots."}</p>
        </div>
      `;
    }
  });
}

function renderProgressSection(elements) {
  const subjects = appState.profile.subjects || [];
  const weakSet = new Set(appState.profile.weakSubjects || []);

  if (elements.progressOverview) {
    elements.progressOverview.innerHTML = subjects.map((subject) => {
      const val = Math.round(appState.progress[subject] || 0);
      const status = val >= 75 ? "Strong Mastery" : val >= 45 ? "Building Foundation" : "High Priority";
      return `
        <div class="progress-card glass-card">
          <div class="progress-topline">
            <h4>${subject}</h4>
            <span class="badge">${val}%</span>
          </div>
          <p style="font-size: 0.9rem; color: var(--text-muted, #9ca3af);">${status}${weakSet.has(subject) ? " • Weak Subject" : ""}</p>
          <div class="progress-shell" style="margin-top: 10px;">
            <div class="progress-fill" style="width: ${val}%"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  if (elements.weakSubjectHighlights) {
    const weakList = (appState.profile.weakSubjects || []).filter((s) => subjects.includes(s));
    elements.weakSubjectHighlights.innerHTML = weakList.length
      ? weakList.map((subject) => `
        <div class="weak-card glass-card">
          <h4>⚠️ ${subject}</h4>
          <p>${Math.round(appState.progress[subject] || 0) < 50 ? "Requires extra deliberate practice. Allocate more focus blocks today." : "Progress is trending upward! Maintain spaced repetition."}</p>
          <span class="badge">${Math.round(appState.progress[subject] || 0)}% Mastery</span>
        </div>
      `).join("")
      : `<div class="empty-state glass-card" style="padding: 18px;">No weak subjects flagged. All active topics are on a balanced schedule.</div>`;
  }
}

function switchSection(sectionName, elements) {
  elements.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.section === sectionName);
  });
  Object.entries(elements.sections).forEach(([name, section]) => {
    if (section) section.classList.toggle("active", name === sectionName);
  });
}

function regeneratePlan(elements) {
  appState.plan = generateStudyPlan(appState.profile, appState.progress);
  saveState();
  renderDashboard(elements);
  showNotification("Study plan recalibrated based on your current subject mastery.");
}

function generateStudyPlan(profile, progress) {
  const totalMinutes = (profile.studyHours || profile.study_hours_per_day || 3) * 60;
  const subjects = (profile.subjects || []).slice(0, 5);
  const weakSet = new Set(profile.weakSubjects || profile.weak_subjects || []);

  const weighted = subjects.map((s) => {
    const base = weakSet.has(s) ? 1.5 : 1.0;
    const penalty = 1 + ((100 - (progress[s] || 35)) / 150);
    return { subject: s, weight: base * penalty };
  });

  const totalWeight = weighted.reduce((sum, item) => sum + item.weight, 0);
  const plan = [];
  let allocated = 0;

  weighted.forEach((item, index) => {
    const mins = index === weighted.length - 1
      ? Math.max(25, totalMinutes - allocated)
      : Math.max(25, Math.round((item.weight / totalWeight) * totalMinutes / 5) * 5);
    allocated += mins;

    const chapters = subjectCurriculum[item.subject] || [{ title: `${item.subject} Core Mastery`, desc: "Review key topics and solve practice exercises." }];
    const ch = chapters[index % chapters.length];

    plan.push({
      subject: item.subject,
      minutes: mins,
      topic: ch.title,
      task_description: weakSet.has(item.subject)
        ? `Focus study on ${ch.title} with 5 deliberate practice exercises and active recall testing.`
        : `Review ${ch.title} concepts and complete one checkpoint quiz.`,
      is_weak_subject: weakSet.has(item.subject),
      is_completed: false
    });
  });

  return plan;
}

function getTopicData(subject) {
  const chapters = subjectCurriculum[subject] || [
    { title: `${subject} Fundamentals`, desc: `Core principles and problem solving for ${subject}.` }
  ];
  return {
    title: chapters[0].title,
    explanation: chapters[0].desc,
    practice: `Active problem solving sprint for ${chapters[0].title}.`,
    quiz: [
      {
        question: `Which approach is most effective when preparing for ${subject}?`,
        options: [
          "Active recall with spaced diagnostic quizzes",
          "Passive rereading of highlighted notes",
          "Memorizing formulas without derivation",
          "Cramming the night before tests"
        ],
        answer: 0,
        explanation: "Active recall and spaced repetition strengthen long-term neural retention."
      },
      {
        question: `What is the optimal first step when tackling a difficult problem in ${chapters[0].title}?`,
        options: [
          "Deconstruct the problem into knowns, unknowns, and governing equations",
          "Immediately jump to numerical calculation without units",
          "Look at the back-of-the-book answer first",
          "Skip the question completely"
        ],
        answer: 0,
        explanation: "Formal problem breakdown prevents calculation and conceptual traps."
      }
    ]
  };
}

function updateStreak() {
  const today = getTodayKey();
  const lastActive = appState.lastActiveDate;
  if (!lastActive) {
    appState.lastActiveDate = today;
    return;
  }
  if (lastActive === today) return;

  const diff = getDayDifference(lastActive, today);
  if (diff === 1) {
    appState.streak = (appState.streak || 1) + 1;
  } else if (diff > 1) {
    appState.streak = 1;
  }
  appState.lastActiveDate = today;
}

function syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes) {
  const selected = new Set(getCheckedValues(subjectCheckboxes));
  weakSubjectCheckboxes.forEach((chk) => {
    const isAllowed = selected.has(chk.value);
    chk.disabled = !isAllowed;
    if (!isAllowed) chk.checked = false;
  });
}

function getCheckedValues(checkboxes) {
  return checkboxes.filter((c) => c.checked).map((c) => c.value.trim()).filter(Boolean);
}

function clampNumber(val, min, max, fallback) {
  if (Number.isNaN(val)) return fallback;
  return Math.min(max, Math.max(min, val));
}

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch (_) {
    return {};
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
}

function resetApplication() {
  if (confirm("Reset current study session and create a fresh schedule?")) {
    localStorage.removeItem(STORAGE_KEY);
    window.location.href = "planning.html";
  }
}

function toggleTheme(themeToggleButton) {
  const nextTheme = document.body.classList.contains("dark") ? "light" : "dark";
  localStorage.setItem(THEME_KEY, nextTheme);
  applyTheme();
  if (themeToggleButton) updateThemeButton(themeToggleButton);
}

function applyTheme() {
  const stored = localStorage.getItem(THEME_KEY) || "light";
  document.body.classList.toggle("dark", stored === "dark");
}

function updateThemeButton(button) {
  if (!button) return;
  button.textContent = document.body.classList.contains("dark") ? "☀️ Light mode" : "🌙 Dark mode";
}

// -------------------------------------------------------------
// API Helper & Communication
// -------------------------------------------------------------
async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("access_token");
  const customGroq = localStorage.getItem("studymentor_groq_key");

  const headers = {
    "Content-Type": "application/json",
    ...options.headers
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (customGroq) {
    headers["X-Groq-Api-Key"] = customGroq;
  }

  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

async function fetchStudyPlan() {
  const payload = {
    name: appState.profile.name,
    class_level: appState.profile.classLevel,
    stream: appState.profile.stream,
    study_hours_per_day: appState.profile.studyHours,
    subjects: appState.profile.subjects,
    weak_subjects: appState.profile.weakSubjects
  };
  return await apiRequest("/plan/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

async function fetchQuiz(subject, topic) {
  const params = new URLSearchParams({
    subject,
    topic: topic || "Fundamentals",
    difficulty: "medium",
    num_questions: "5"
  });
  return await apiRequest(`/quiz/generate?${params}`, { method: "POST" });
}

async function fetchExplanation(subject, topic) {
  const res = await apiRequest("/ai/explanation", {
    method: "POST",
    body: JSON.stringify({
      generation_type: "explanation",
      subject,
      topic: topic || "Fundamentals"
    })
  });
  return res ? res.content : null;
}

async function fetchPracticeSprint(subject, topic) {
  const res = await apiRequest("/ai/practice", {
    method: "POST",
    body: JSON.stringify({
      generation_type: "practice",
      subject,
      topic: topic || "Fundamentals"
    })
  });
  return res ? res.content : null;
}

function showNotification(message) {
  const el = document.getElementById("notification");
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
  requestAnimationFrame(() => el.classList.add("show"));

  clearTimeout(showNotification.timer);
  showNotification.timer = setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.classList.add("hidden"), 250);
  }, 3000);
}

function getTodayKey() {
  return new Date().toISOString().slice(0, 10);
}

function getDayDifference(start, end) {
  const s = new Date(`${start}T00:00:00`);
  const e = new Date(`${end}T00:00:00`);
  return Math.round((e - s) / 86400000);
}

// -------------------------------------------------------------
// AI Config & Backend Health Check
// -------------------------------------------------------------
function initAiConfig() {
  const configBtn = document.getElementById("aiConfigBtn");
  const modal = document.getElementById("aiConfigModal");
  const closeBtn = document.getElementById("closeAiConfigModal");
  const saveBtn = document.getElementById("saveAiConfigBtn");
  const apiInput = document.getElementById("configApiUrl");
  const groqInput = document.getElementById("configGroqKey");

  if (configBtn && modal) {
    configBtn.addEventListener("click", () => {
      if (apiInput) apiInput.value = localStorage.getItem("studymentor_api_url") || "";
      if (groqInput) groqInput.value = localStorage.getItem("studymentor_groq_key") || "";
      modal.classList.remove("hidden");
    });
  }

  const pill = document.getElementById("aiStatusPill");
  if (pill && modal) {
    pill.addEventListener("click", () => {
      if (apiInput) apiInput.value = localStorage.getItem("studymentor_api_url") || "";
      if (groqInput) groqInput.value = localStorage.getItem("studymentor_groq_key") || "";
      modal.classList.remove("hidden");
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", () => {
      const apiUrl = apiInput ? apiInput.value.trim() : "";
      const groqKey = groqInput ? groqInput.value.trim() : "";

      if (apiUrl) {
        localStorage.setItem("studymentor_api_url", apiUrl);
      } else {
        localStorage.removeItem("studymentor_api_url");
      }

      if (groqKey) {
        localStorage.setItem("studymentor_groq_key", groqKey);
      } else {
        localStorage.removeItem("studymentor_groq_key");
      }

      if (modal) modal.classList.add("hidden");
      showNotification("Settings saved. Verifying connection...");
      checkBackendHealth();
    });
  }
}

async function checkBackendHealth() {
  const pill = document.getElementById("aiStatusPill");
  const text = document.getElementById("aiStatusText");
  const chatBadge = document.getElementById("chatBadge");

  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      if (pill) {
        pill.classList.remove("offline");
        pill.title = `Backend Connected: ${data.app || "StudyMentor"} (v${data.version || "1.0"})`;
      }
      if (text) text.textContent = "AI Online";
      if (chatBadge) {
        chatBadge.textContent = "Groq Llama 3.3 Active";
        chatBadge.style.background = "rgba(34, 197, 94, 0.15)";
        chatBadge.style.color = "#16a34a";
      }
    } else {
      throw new Error();
    }
  } catch (_) {
    if (pill) {
      pill.classList.add("offline");
      pill.title = "Offline or connecting to backend. Click to configure API URL.";
    }
    if (text) text.textContent = "Offline Mode";
    if (chatBadge) {
      chatBadge.textContent = "Pedagogical Assistant";
    }
  }
}

// -------------------------------------------------------------
// Interactive AI Mentor Chat
// -------------------------------------------------------------
function initChatSection() {
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const messagesContainer = document.getElementById("chatMessages");
  const chipsContainer = document.getElementById("chatChips");

  if (!form || !input || !messagesContainer) return;

  // Quick Action Chips
  if (chipsContainer) {
    chipsContainer.querySelectorAll(".chip-btn").forEach((chip) => {
      chip.addEventListener("click", () => {
        const promptText = chip.dataset.prompt;
        if (promptText) {
          input.value = promptText;
          form.dispatchEvent(new Event("submit"));
        }
      });
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    input.value = "";
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg user";
    userMsg.textContent = query;
    messagesContainer.appendChild(userMsg);

    const botMsg = document.createElement("div");
    botMsg.className = "chat-msg assistant";
    botMsg.innerHTML = "<em>Analyzing syllabus & formulating response...</em>";
    messagesContainer.appendChild(botMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
      const res = await apiRequest("/ai/chat", {
        method: "POST",
        body: JSON.stringify({
          generation_type: "explanation",
          subject: currentTopic || "General",
          context: {
            message: query,
            current_topic: currentTopic,
            weak_subjects: appState.profile ? appState.profile.weakSubjects : []
          }
        })
      });

      botMsg.innerHTML = formatChatMarkdown(res.content || "I have analyzed your query.");
    } catch (err) {
      botMsg.innerHTML = `<strong>StudyMentor:</strong> ${err.message || "Connection to AI service failed."}`;
    }
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  });
}

function formatChatMarkdown(text) {
  if (!text) return "";
  let formatted = text
    .replace(/^### (.*$)/gim, '<h4 style="color: #6366f1; margin: 8px 0;">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 style="color: #6366f1; margin: 10px 0;">$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
  return formatted;
}

// -------------------------------------------------------------
// Authentication Controller
// -------------------------------------------------------------
let authMode = "login";

function initAuth() {
  const authModal = document.getElementById("authModal");
  const authBtn = document.getElementById("authBtn");
  const closeAuthModal = document.getElementById("closeAuthModal");
  const authToggleBtn = document.getElementById("authToggleBtn");
  const authForm = document.getElementById("authForm");

  if (authBtn) {
    authBtn.addEventListener("click", () => {
      if (localStorage.getItem("access_token")) {
        handleLogout();
      } else {
        openAuthModal("login");
      }
    });
  }

  if (closeAuthModal && authModal) {
    closeAuthModal.addEventListener("click", () => authModal.classList.add("hidden"));
  }

  if (authToggleBtn) {
    authToggleBtn.addEventListener("click", () => {
      authMode = authMode === "login" ? "register" : "login";
      updateAuthModalUI();
    });
  }

  if (authForm) {
    authForm.addEventListener("submit", handleAuthSubmit);
  }

  checkAuthStatus();
}

function openAuthModal(mode = "login") {
  authMode = mode;
  updateAuthModalUI();
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.remove("hidden");
}

function updateAuthModalUI() {
  const title = document.getElementById("authModalTitle");
  const submitBtn = document.getElementById("authSubmitBtn");
  const toggleText = document.getElementById("authToggleText");
  const toggleBtn = document.getElementById("authToggleBtn");
  const nameGroup = document.getElementById("nameFieldGroup");

  if (authMode === "login") {
    if (title) title.textContent = "Sign In";
    if (submitBtn) submitBtn.textContent = "Sign In";
    if (toggleText) toggleText.textContent = "Don't have an account?";
    if (toggleBtn) toggleBtn.textContent = "Register";
    if (nameGroup) nameGroup.classList.add("hidden");
  } else {
    if (title) title.textContent = "Create Account";
    if (submitBtn) submitBtn.textContent = "Register";
    if (toggleText) toggleText.textContent = "Already have an account?";
    if (toggleBtn) toggleBtn.textContent = "Sign In";
    if (nameGroup) nameGroup.classList.remove("hidden");
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const nameEl = document.getElementById("authName");
  const fullName = nameEl ? nameEl.value.trim() : "";

  try {
    showNotification("Authenticating...");
    const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
    const body = authMode === "login"
      ? { email, password }
      : { email, password, full_name: fullName || "Student" };

    const res = await apiRequest(endpoint, {
      method: "POST",
      body: JSON.stringify(body)
    });

    if (authMode === "register") {
      await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
    }

    try {
      const tokenRes = await apiRequest("/auth/refresh", { method: "POST" });
      if (tokenRes && tokenRes.access_token) {
        localStorage.setItem("access_token", tokenRes.access_token);
      }
    } catch (_) {}

    const modal = document.getElementById("authModal");
    if (modal) modal.classList.add("hidden");
    showNotification(`Welcome, ${res.full_name || "Student"}!`);
    checkAuthStatus();
  } catch (err) {
    showNotification(err.message || "Authentication failed.");
  }
}

async function handleLogout() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch (_) {}
  localStorage.removeItem("access_token");
  showNotification("Signed out.");
  checkAuthStatus();
}

async function checkAuthStatus() {
  const authBtn = document.getElementById("authBtn");
  if (!authBtn) return;

  const token = localStorage.getItem("access_token");
  if (!token) {
    authBtn.textContent = "Sign in";
    return;
  }

  try {
    const user = await apiRequest("/auth/me");
    authBtn.textContent = `${user.full_name.split(" ")[0]} (Logout)`;
  } catch (_) {
    localStorage.removeItem("access_token");
    authBtn.textContent = "Sign in";
  }
}
