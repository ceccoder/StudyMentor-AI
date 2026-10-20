const STORAGE_KEY = "studymentor-ai-state";
const THEME_KEY = "studymentor-ai-theme";
// API base URL - auto-detect based on environment
const API_BASE = (() => {
  // Check if we're on Render (production)
  if (window.location.hostname.includes('onrender.com') || window.location.hostname.includes('render.com')) {
    return 'https://studymentor-api.onrender.com/api';
  }
  // Check for custom API_BASE_URL meta tag (for deployment flexibility)
  const metaApiBase = document.querySelector('meta[name="api-base-url"]');
  if (metaApiBase) {
    return metaApiBase.getAttribute('content');
  }
  // Default to localhost for development
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
    "Mathematics 1", "Mathematics 2", "Engineering Physics", "Engineering Chemistry",
    "Basic Electrical Engineering", "Basic Electronics Engineering",
    "Programming in C", "Programming in Python", "Data Structures & Algorithms",
    "Engineering Drawing", "Engineering Mechanics", "Thermodynamics",
    "Fluid Mechanics", "Strength of Materials", "Control Systems",
    "Signals & Systems", "Microprocessors & Microcontrollers",
    "Digital Electronics", "Communication Systems", "Power Systems",
    "Machine Design", "Manufacturing Processes"
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

function initPlanningPage() {
  const onboardingForm = document.getElementById("onboardingForm");
  const streamSelect = document.getElementById("streamSelect");
  const subjectsContainer = document.getElementById("subjectsSelect");
  const weakSubjectsContainer = document.getElementById("weakSubjectsSelect");

  // Populate subjects when stream changes
  streamSelect.addEventListener("change", () => {
    populateSubjects(streamSelect.value, subjectsContainer, weakSubjectsContainer);
  });

  // Initial population if stream is already selected
  if (streamSelect.value) {
    populateSubjects(streamSelect.value, subjectsContainer, weakSubjectsContainer);
  }

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
      classLevel: formData.get("classLevel").toString(),
      stream: formData.get("stream").toString(),
      studyHours: clampNumber(Number(formData.get("studyHours")), 1, 12, 3),
      subjects: selectedSubjects,
      weakSubjects: selectedWeakSubjects
    };

    // Try to save to backend first, fallback to localStorage
    try {
      const token = localStorage.getItem("access_token");
      if (token) {
        const response = await fetch(`${API_BASE}/profile`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(profile)
        });
        if (response.ok) {
          window.location.href = "dashboard.html";
          return;
        }
      }
    } catch (error) {
      console.log("Backend not available, using localStorage fallback");
    }

    // Fallback to localStorage
    const progress = {};
    profile.subjects.forEach((subject, index) => {
      progress[subject] = Math.min(72, 18 + index * 11);
    });

    appState = {
      profile,
      progress,
      streak: 3,
      plan: generateStudyPlan(profile, progress),
      completedTopics: [],
      quizScores: {},
      lastActiveDate: getTodayKey()
    };

    saveState();
    window.location.href = "dashboard.html";
  });
}

function populateSubjects(stream, subjectsContainer, weakSubjectsContainer) {
  const subjects = streamSubjects[stream] || [];
  
  subjectsContainer.innerHTML = subjects.map(subject => 
    `<label class="checkbox-item"><input type="checkbox" name="subjects" value="${subject}">${subject}</label>`
  ).join("");
  
  weakSubjectsContainer.innerHTML = subjects.map(subject => 
    `<label class="checkbox-item"><input type="checkbox" name="weakSubjects" value="${subject}">${subject}</label>`
  ).join("");

  // Re-attach event listeners
  const subjectCheckboxes = [...subjectsContainer.querySelectorAll('input[name="subjects"]')];
  const weakSubjectCheckboxes = [...weakSubjectsContainer.querySelectorAll('input[name="weakSubjects"]')];
  
  subjectCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes));
  });
  
  syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes);
}

function initDashboardPage() {
  if (!appState.profile) {
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
      progress: document.getElementById("progressSection")
    }
  };

  elements.startStudyBtn.addEventListener("click", () => switchSection("study", elements));
  elements.regeneratePlan.addEventListener("click", () => refreshPlanFromAI(elements));
  elements.themeToggle.addEventListener("click", () => {
    toggleTheme(elements.themeToggle);
  });
  elements.resetApp.addEventListener("click", resetApplication);
  elements.navLinks.forEach((button) => {
    button.addEventListener("click", () => switchSection(button.dataset.section, elements));
  });

  currentTopic = appState.profile.subjects[0] || defaultTopics[0];
  updateThemeButton(elements.themeToggle);
  renderAll(elements);
  
  // Try to fetch AI-generated plan on load if backend is available
  const token = localStorage.getItem("access_token");
  if (token && (!appState.plan || appState.plan.length === 0)) {
    refreshPlanFromAI(elements);
  }
}

function ensureStateIntegrity() {
  const { profile } = appState;
  appState.progress = appState.progress || {};
  profile.subjects.forEach((subject, index) => {
    if (typeof appState.progress[subject] !== "number") {
      appState.progress[subject] = Math.min(70, 20 + index * 10);
    }
  });

  appState.completedTopics = Array.isArray(appState.completedTopics) ? appState.completedTopics : [];
  appState.quizScores = appState.quizScores || {};
  appState.streak = typeof appState.streak === "number" ? appState.streak : 3;
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
  elements.welcomeTitle.textContent = `${profile.name}'s ${profile.classLevel} study hub`;
  elements.streakCount.textContent = String(streak);
}

function renderDashboard(elements) {
  const { profile, plan, progress } = appState;
  const totalMinutes = plan.reduce((sum, item) => sum + item.minutes, 0);
  const weakFocus = plan.filter((item) => item.isWeak).length;

  elements.heroPlanText.textContent = `${profile.stream} track | ${profile.studyHours} hours/day | ${profile.subjects.length} active subjects`;
  elements.focusBlocksCount.textContent = String(plan.length);
  elements.weakFocusCount.textContent = String(weakFocus);
  elements.plannedMinutes.textContent = `${totalMinutes} min`;

  elements.planList.innerHTML = plan.map((item, index) => `
    <div class="plan-card">
      <div class="plan-topline">
        <strong>${index + 1}. ${item.subject}</strong>
        <span class="badge">${item.minutes} min</span>
      </div>
      <p>${item.task}</p>
      <div class="plan-topline">
        <span>${item.topic}</span>
        <span>${item.isWeak ? "Priority focus" : "Balanced block"}</span>
      </div>
    </div>
  `).join("");

  elements.dashboardProgress.innerHTML = profile.subjects.map((subject) => `
    <div class="subject-item">
      <div class="progress-topline">
        <strong>${subject}</strong>
        <span>${Math.round(progress[subject] || 0)}%</span>
      </div>
      <div class="progress-shell">
        <div class="progress-fill" style="width: ${Math.round(progress[subject] || 0)}%"></div>
      </div>
    </div>
  `).join("");
}

// Fetch and render AI-generated plan
async function refreshPlanFromAI(elements) {
  try {
    showNotification("Generating AI study plan...");
    const result = await fetchStudyPlan();
    if (result && result.plan_data && result.plan_data.blocks) {
      appState.plan = result.plan_data.blocks;
      saveState();
      renderDashboard(elements);
      showNotification("AI study plan generated successfully!");
    }
  } catch (error) {
    showNotification("Failed to generate AI plan, using local fallback.");
  }
}

function renderStudySection(elements) {
  const subjects = appState.profile.subjects;
  const topicSubjects = subjects.length ? subjects : defaultTopics.slice(0, 4);
  currentTopic = currentTopic && topicSubjects.includes(currentTopic) ? currentTopic : topicSubjects[0];

  elements.topicList.innerHTML = topicSubjects.map((subject) => {
    const topic = getTopicData(subject);
    const score = appState.quizScores[subject];
    const completed = appState.completedTopics.includes(subject);
    return `
      <button class="topic-card ${subject === currentTopic ? "active" : ""}" type="button" data-topic="${subject}">
        <div class="topic-topline">
          <strong>${subject}</strong>
          <span>${completed ? "Done" : "Up next"}</span>
        </div>
        <h4>${topic.title}</h4>
        <p>${topic.explanation}</p>
        <span class="badge">${typeof score === "number" ? `Best quiz ${score}%` : "Quiz available"}</span>
      </button>
    `;
  }).join("");

  [...elements.topicList.querySelectorAll(".topic-card")].forEach((button) => {
    button.addEventListener("click", () => {
      currentTopic = button.dataset.topic;
      renderStudySection(elements);
    });
  });

  renderTopicDetails(elements);
}

function renderTopicDetails(elements) {
  const subject = currentTopic;
  const topic = getTopicData(subject);
  const subjectProgress = Math.round(appState.progress[subject] || 0);
  const isWeak = appState.profile.weakSubjects.includes(subject);
  const bestQuiz = appState.quizScores[subject];

  elements.topicDetails.innerHTML = `
    <div class="topic-detail-header">
      <div>
        <p class="eyebrow">Study module</p>
        <h3 class="topic-title">${topic.title}</h3>
      </div>
      <span class="badge">${subject}</span>
    </div>
    <div class="topic-meta">
      <span class="badge">${subjectProgress}% mastery</span>
      <span class="badge">${isWeak ? "Weak subject boost" : "On track"}</span>
      <span class="badge">${typeof bestQuiz === "number" ? `Best quiz ${bestQuiz}%` : "Quiz pending"}</span>
    </div>
    <p class="topic-description">${topic.explanation}</p>
    <div class="plan-card">
      <strong>Practice sprint</strong>
      <p>${topic.practice}</p>
    </div>
    <div class="action-row">
      <button id="takeQuizBtn" class="primary-button" type="button">Take Quiz</button>
      <button id="practiceBtn" class="secondary-button" type="button">Practice</button>
      <button id="generateExplanationBtn" class="ghost-button" type="button">Generate Explanation</button>
      <button id="generatePracticeBtn" class="ghost-button" type="button">Generate Practice</button>
    </div>
  `;

  elements.quizContainer.classList.add("hidden");
  elements.quizContainer.innerHTML = "";
  document.getElementById("takeQuizBtn").addEventListener("click", () => renderQuiz(subject, elements));
  document.getElementById("practiceBtn").addEventListener("click", () => completePractice(subject, elements));
  document.getElementById("generateExplanationBtn").addEventListener("click", () => generateAIExplanation(subject, elements));
  document.getElementById("generatePracticeBtn").addEventListener("click", () => generateAIPractice(subject, elements));
}

// Generate AI explanation for a topic
async function generateAIExplanation(subject, elements) {
  const btn = document.getElementById("generateExplanationBtn");
  btn.disabled = true;
  btn.textContent = "Generating...";
  
  try {
    showNotification("Generating AI explanation...");
    // This would call a backend endpoint - for now use WebSocket or a new REST endpoint
    // We'll simulate with a placeholder since the backend doesn't have a dedicated explanation endpoint yet
    const explanation = await fetchExplanation(subject, topic.title);
    if (explanation) {
      // Update the UI with AI-generated explanation
      const descEl = elements.topicDetails.querySelector(".topic-description");
      if (descEl) descEl.textContent = explanation.overview || "Explanation generated";
      showNotification("AI explanation generated!");
    } else {
      showNotification("AI explanation feature coming soon. Using fallback content.");
    }
  } catch (error) {
    console.error("Failed to generate explanation:", error);
    showNotification("Failed to generate explanation.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Explanation";
  }
}

// Generate AI practice sprint for a topic
async function generateAIPractice(subject, elements) {
  const btn = document.getElementById("generatePracticeBtn");
  btn.disabled = true;
  btn.textContent = "Generating...";
  
  try {
    showNotification("Generating AI practice sprint...");
    const practice = await fetchPracticeSprint(subject, topic.title);
    if (practice) {
      const practiceEl = elements.topicDetails.querySelector(".plan-card p");
      if (practiceEl) practiceEl.textContent = JSON.stringify(practice, null, 2);
      showNotification("AI practice sprint generated!");
    } else {
      showNotification("AI practice feature coming soon. Using fallback content.");
    }
  } catch (error) {
    console.error("Failed to generate practice:", error);
    showNotification("Failed to generate practice sprint.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Practice";
  }
}

function renderQuiz(subject, elements) {
  // Try to fetch AI-generated quiz first
  fetchQuiz(subject, "Fundamentals").then(quizData => {
    if (quizData && quizData.questions && quizData.questions.length > 0) {
      renderQuizWithData(subject, quizData.questions, elements);
    } else {
      // Fallback to local quiz
      const topic = getTopicData(subject);
      renderQuizWithData(subject, topic.quiz, elements);
    }
  }).catch(() => {
    // Fallback to local quiz
    const topic = getTopicData(subject);
    renderQuizWithData(subject, topic.quiz, elements);
  });
}

function renderQuizWithData(subject, questions, elements) {
  const answers = new Array(questions.length).fill(null);

  elements.quizContainer.classList.remove("hidden");
  elements.quizContainer.innerHTML = `
    <div>
      <p class="eyebrow">Quiz mode</p>
      <h4 class="quiz-title">${subject} quick check</h4>
    </div>
    ${questions.map((item, index) => `
      <div class="quiz-question">
        <p>${index + 1}. ${item.question}</p>
        <div class="options">
          ${item.options.map((option, optionIndex) => `
            <button class="option-button" type="button" data-question="${index}" data-option="${optionIndex}">${option}</button>
          `).join("")}
        </div>
        ${item.explanation ? `<p class="explanation hidden" data-question="${index}">${item.explanation}</p>` : ""}
      </div>
    `).join("")}
    <button id="submitQuizBtn" class="primary-button" type="button">Submit quiz</button>
    <button id="generateQuizBtn" class="ghost-button" type="button" style="margin-left: 12px;">Generate New Quiz</button>
    <div id="quizResult"></div>
  `;

  [...elements.quizContainer.querySelectorAll(".option-button")].forEach((button) => {
    button.addEventListener("click", () => {
      const questionIndex = Number(button.dataset.question);
      const optionIndex = Number(button.dataset.option);
      answers[questionIndex] = optionIndex;
      [...elements.quizContainer.querySelectorAll(`.option-button[data-question="${questionIndex}"]`)].forEach((optionButton) => {
        optionButton.classList.toggle("selected", optionButton === button);
      });
    });
  });

  document.getElementById("submitQuizBtn").addEventListener("click", () => {
    if (answers.some((answer) => answer === null)) {
      showNotification("Answer all questions before submitting.");
      return;
    }

    const correct = questions.reduce((sum, item, index) => sum + Number(item.answer === answers[index]), 0);
    const score = Math.round((correct / questions.length) * 100);
    appState.quizScores[subject] = Math.max(score, appState.quizScores[subject] || 0);
    appState.progress[subject] = clampNumber((appState.progress[subject] || 0) + 12, 0, 100, 0);
    if (!appState.completedTopics.includes(subject)) {
      appState.completedTopics.push(subject);
    }
    appState.plan = generateStudyPlan(appState.profile, appState.progress);
    saveState();
    renderAll(elements);

    // Show explanations for wrong answers
    [...elements.quizContainer.querySelectorAll(".explanation")].forEach((el) => {
      el.classList.remove("hidden");
    });

    const result = document.getElementById("quizResult");
    if (result) {
      result.innerHTML = `<div class="quiz-result">Score: <strong>${score}%</strong>. Progress for ${subject} increased.</div>`;
    }
    showNotification(score >= 70 ? "You completed today's goal. Momentum updated." : "Quiz submitted. Review the topic once more.");
  });

  document.getElementById("generateQuizBtn").addEventListener("click", () => {
    renderQuiz(subject, elements);
  });
}

function completePractice(subject, elements) {
  appState.progress[subject] = clampNumber((appState.progress[subject] || 0) + 8, 0, 100, 0);
  if (!appState.completedTopics.includes(subject)) {
    appState.completedTopics.push(subject);
  }
  appState.plan = generateStudyPlan(appState.profile, appState.progress);
  saveState();
  renderAll(elements);
  showNotification(`${subject} practice completed. Progress synced locally.`);
}

function renderProgressSection(elements) {
  const subjects = appState.profile.subjects;
  const weakSet = new Set(appState.profile.weakSubjects);

  elements.progressOverview.innerHTML = subjects.map((subject) => {
    const value = Math.round(appState.progress[subject] || 0);
    const status = value >= 75 ? "Strong" : value >= 45 ? "Building" : "Needs attention";
    return `
      <div class="progress-card">
        <div class="progress-topline">
          <h4>${subject}</h4>
          <span>${value}%</span>
        </div>
        <p>${status}${weakSet.has(subject) ? " | weak subject" : ""}</p>
        <div class="progress-shell">
          <div class="progress-fill" style="width: ${value}%"></div>
        </div>
      </div>
    `;
  }).join("");

  const weakSubjects = appState.profile.weakSubjects.filter((subject) => subjects.includes(subject));
  elements.weakSubjectHighlights.innerHTML = weakSubjects.length
    ? weakSubjects.map((subject) => `
      <div class="weak-card">
        <h4>${subject}</h4>
        <p>${Math.round(appState.progress[subject] || 0) < 50 ? "Extra revision recommended today." : "Improving, keep the repetition going."}</p>
        <span class="badge">${Math.round(appState.progress[subject] || 0)}% complete</span>
      </div>
    `).join("")
    : `<div class="empty-state">No weak subjects marked. The dashboard will flag low-progress topics automatically.</div>`;
}

function switchSection(sectionName, elements) {
  elements.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.section === sectionName);
  });
  Object.entries(elements.sections).forEach(([name, section]) => {
    section.classList.toggle("active", name === sectionName);
  });
}

function regeneratePlan(elements) {
  appState.plan = generateStudyPlan(appState.profile, appState.progress);
  saveState();
  renderDashboard(elements);
  showNotification("Study plan regenerated from your current strengths and weak areas.");
}

function generateStudyPlan(profile, progress) {
  const totalMinutes = profile.studyHours * 60;
  const subjects = profile.subjects.slice(0, 5);
  const weakSet = new Set(profile.weakSubjects);
  const weightedSubjects = subjects.map((subject) => {
    const baseWeight = weakSet.has(subject) ? 1.45 : 1;
    const progressPenalty = 1 + ((100 - (progress[subject] || 40)) / 180);
    return { subject, weight: baseWeight * progressPenalty };
  });

  const weightTotal = weightedSubjects.reduce((sum, item) => sum + item.weight, 0);
  const plan = [];
  let assigned = 0;

  weightedSubjects.forEach((item, index) => {
    const minutes = index === weightedSubjects.length - 1
      ? Math.max(20, totalMinutes - assigned)
      : allocateMinutes(item.weight, weightTotal, totalMinutes);
    assigned += minutes;
    const topic = getTopicData(item.subject);

    plan.push({
      subject: item.subject,
      minutes,
      topic: topic.title,
      task: weakSet.has(item.subject)
        ? `Revise ${topic.title} with examples, then finish a short checkpoint quiz.`
        : `Study ${topic.title} and complete one practice sprint.`,
      isWeak: weakSet.has(item.subject)
    });
  });

  return plan;
}

function allocateMinutes(weight, totalWeight, totalMinutes) {
  return Math.max(20, Math.round((weight / totalWeight) * totalMinutes / 5) * 5);
}

function getTopicData(subject) {
  // Return minimal fallback - actual content comes from backend API
  return {
    title: `${subject} Fundamentals`,
    explanation: `Learning content for ${subject} will be generated by AI.`,
    practice: `Practice exercises for ${subject} will be generated by AI.`,
    quiz: [
      { question: `Which statement best matches ${subject} fundamentals?`, options: ["It requires regular revision", "It can only be learned in one day", "Practice does not matter", "Concepts never connect"], answer: 0 },
      { question: `A strong ${subject} routine usually includes:`, options: ["Short review blocks", "Skipping weak areas", "Only memorizing titles", "No testing"], answer: 0 },
      { question: "Progress improves fastest when you:", options: ["Avoid feedback", "Revise and test yourself", "Study once a month", "Ignore mistakes"], answer: 1 }
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
  if (lastActive === today) {
    return;
  }
  const dayDifference = getDayDifference(lastActive, today);
  if (dayDifference === 1) {
    appState.streak += 1;
  } else if (dayDifference > 1) {
    appState.streak = 1;
  }
  appState.lastActiveDate = today;
}

function syncWeakSubjectOptions(subjectCheckboxes, weakSubjectCheckboxes) {
  const selectedSubjects = new Set(getCheckedValues(subjectCheckboxes));
  weakSubjectCheckboxes.forEach((checkbox) => {
    const isAllowed = selectedSubjects.has(checkbox.value);
    checkbox.disabled = !isAllowed;
    if (!isAllowed) {
      checkbox.checked = false;
    }
  });
}

function getCheckedValues(checkboxes) {
  return checkboxes
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => checkbox.value.trim())
    .filter(Boolean);
}

function clampNumber(value, min, max, fallback) {
  if (Number.isNaN(value)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, value));
}

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch (error) {
    return {};
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
}

function resetApplication() {
  localStorage.removeItem(STORAGE_KEY);
  window.location.href = "planning.html";
}

function toggleTheme(themeToggleButton) {
  const nextTheme = document.body.classList.contains("dark") ? "light" : "dark";
  localStorage.setItem(THEME_KEY, nextTheme);
  applyTheme();
  if (themeToggleButton) {
    updateThemeButton(themeToggleButton);
  }
}

function applyTheme() {
  const storedTheme = localStorage.getItem(THEME_KEY) || "light";
  document.body.classList.toggle("dark", storedTheme === "dark");
}

function updateThemeButton(button) {
  if (!button) {
    return;
  }
  button.textContent = document.body.classList.contains("dark") ? "Light mode" : "Dark mode";
}

// API Helper Functions
async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = {
    "Content-Type": "application/json",
    ...options.headers
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// Fetch AI-generated study plan
async function fetchStudyPlan() {
  try {
    return await apiRequest("/plan/generate", { method: "POST" });
  } catch (error) {
    console.error("Failed to fetch study plan:", error);
    // Fallback to local generation
    return { plan_data: { blocks: generateStudyPlan(appState.profile, appState.progress) } };
  }
}

// Fetch AI-generated quiz
async function fetchQuiz(subject, topic, difficulty = "medium", numQuestions = 5) {
  try {
    const params = new URLSearchParams({
      subject,
      topic,
      difficulty,
      num_questions: numQuestions.toString()
    });
    return await apiRequest(`/quiz/generate?${params}`, { method: "POST" });
  } catch (error) {
    console.error("Failed to fetch quiz:", error);
    return null;
  }
}

// Fetch AI-generated explanation
async function fetchExplanation(subject, topic) {
  try {
    // This would call a dedicated explanation endpoint
    // For now, return a placeholder that triggers AI generation
    return null;
  } catch (error) {
    console.error("Failed to fetch explanation:", error);
    return null;
  }
}

// Fetch AI-generated practice sprint
async function fetchPracticeSprint(subject, topic) {
  try {
    // This would call a dedicated practice endpoint
    return null;
  } catch (error) {
    console.error("Failed to fetch practice:", error);
    return null;
  }
}

function showNotification(message) {
  const notification = document.getElementById("notification");
  if (!notification) {
    return;
  }
  notification.textContent = message;
  notification.classList.remove("hidden");
  requestAnimationFrame(() => {
    notification.classList.add("show");
  });

  clearTimeout(showNotification.timer);
  showNotification.timer = setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => notification.classList.add("hidden"), 250);
  }, 2600);
}

function getTodayKey() {
  return new Date().toISOString().slice(0, 10);
}

function getDayDifference(start, end) {
  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);
  return Math.round((endDate - startDate) / 86400000);
}
