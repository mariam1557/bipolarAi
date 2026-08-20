// ضبطي العنوان ده لو الباك إند شغال على بورت أو دومين مختلف
const API_BASE = "http://127.0.0.1:8002";

// ضبطي الـ Google OAuth Client ID هنا عشان زرار "تسجيل الدخول بجوجل" يشتغل.
// من Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client ID (Web application).
// لو سبتيه فاضي، زرار جوجل هيتخفي تلقائي والإيميل/الباسورد هيفضلوا شغالين عادي.
const GOOGLE_CLIENT_ID = "";

let conversationId = null;
let currentRole = "patient";
let currentLang = "en";
let currentUser = null; // { id, email, name, avatar_url }
let authToken = localStorage.getItem("drmood_token") || null;
let isRateLimited = false;

// ---------- Auth storage helpers ----------
function saveAuth(token, user) {
    authToken = token;
    currentUser = user;
    localStorage.setItem("drmood_token", token);
    localStorage.setItem("drmood_user", JSON.stringify(user));
}

function clearAuth() {
    authToken = null;
    currentUser = null;
    conversationId = null;
    localStorage.removeItem("drmood_token");
    localStorage.removeItem("drmood_user");
}

function loadStoredUser() {
    const stored = localStorage.getItem("drmood_user");
    if (stored) {
        try {
            currentUser = JSON.parse(stored);
        } catch {
            currentUser = null;
        }
    }
}

// ---------- Authenticated fetch wrapper ----------
async function apiFetch(path, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    const response = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));

    if (response.status === 401) {
        clearAuth();
        updateAuthUI();
        switchView("login");
    }
    return response;
}

// ---------- Navigation (Home / Chat / Info / Login / Register) ----------
const navLinkButtons = document.querySelectorAll("[data-view]");

function switchView(viewName) {
    document.querySelectorAll(".nav-link[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === viewName));
    document.querySelectorAll(".view").forEach(view => view.classList.remove("active-view"));
    const target = document.getElementById(`${viewName}View`);
    if (target) target.classList.add("active-view");
    document.getElementById("mobileMenu").classList.remove("open");
    window.scrollTo({ top: 0, behavior: "auto" });
}

navLinkButtons.forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
});

document.getElementById("homeStartChat").addEventListener("click", () => switchView("chat"));
document.getElementById("homeStartChat2").addEventListener("click", () => switchView("chat"));

// ---------- Language switch (EN / AR) ----------
const htmlRoot = document.getElementById("htmlRoot");
const langSwitch = document.getElementById("langSwitch");

function applyLanguage(lang) {
    currentLang = lang;
    htmlRoot.lang = lang;
    htmlRoot.dir = lang === "ar" ? "rtl" : "ltr";

    document.querySelectorAll("[data-en][data-ar]").forEach(el => {
        el.textContent = lang === "ar" ? el.dataset.ar : el.dataset.en;
    });

    const input = document.getElementById("questionInput");
    if (input) {
        input.placeholder = currentRole === "doctor" ?
            (lang === "ar" ? "اسألي سؤال إكلينيكي عن اضطراب ثنائي القطب..." : "Ask a clinical question about bipolar disorder...") :
            (lang === "ar" ? "اسألي سؤال عن اضطراب ثنائي القطب..." : "Ask a question about bipolar disorder...");
    }
}

if (langSwitch) {
    langSwitch.addEventListener("click", () => applyLanguage(currentLang === "en" ? "ar" : "en"));
}

// ---------- Dark mode ----------
const darkModeToggle = document.getElementById("darkModeToggle");

function setDarkMode(on) {
    document.body.classList.toggle("dark-mode", on);
    localStorage.setItem("drmood_dark", on ? "1" : "0");
    if (darkModeToggle) {
        const icon = darkModeToggle.querySelector("i");
        icon.classList.toggle("fa-moon", !on);
        icon.classList.toggle("fa-sun", on);
    }
}

if (darkModeToggle) {
    darkModeToggle.addEventListener("click", () => setDarkMode(!document.body.classList.contains("dark-mode")));
}

// ---------- Patient / Doctor mode ----------
const roleButtons = document.querySelectorAll(".role-btn");

roleButtons.forEach(button => {
    button.addEventListener("click", () => {
        roleButtons.forEach(btn => btn.classList.remove("active"));
        button.classList.add("active");
        currentRole = button.dataset.role; // "patient" | "doctor" - يطابق الـ schema بالظبط
        applyLanguage(currentLang);
    });
});

// ---------- Hamburger (mobile) ----------
const hamburgerBtn = document.getElementById("hamburgerBtn");
const mobileMenu = document.getElementById("mobileMenu");
if (hamburgerBtn) {
    hamburgerBtn.addEventListener("click", () => mobileMenu.classList.toggle("open"));
}

// ---------- Auth UI (navbar) ----------
const authActionsLoggedOut = document.getElementById("authActionsLoggedOut");
const userMenu = document.getElementById("userMenu");
const userAvatarBtn = document.getElementById("userAvatarBtn");
const userDropdown = document.getElementById("userDropdown");
const userAvatarInitial = document.getElementById("userAvatarInitial");
const userNameLabel = document.getElementById("userNameLabel");
const userDropdownEmail = document.getElementById("userDropdownEmail");
const mobileAuthActions = document.getElementById("mobileAuthActions");

function updateAuthUI() {
    const loggedIn = !!(authToken && currentUser);
    authActionsLoggedOut.hidden = loggedIn;
    userMenu.hidden = !loggedIn;
    mobileAuthActions.style.display = loggedIn ? "none" : "flex";

    if (loggedIn) {
        const label = currentUser.name || currentUser.email || "U";
        userAvatarInitial.textContent = label.trim().charAt(0).toUpperCase();
        userNameLabel.textContent = currentUser.name || currentUser.email;
        userDropdownEmail.textContent = currentUser.email;
        loadConversations();
    } else {
        document.getElementById("historyPanelBody").innerHTML =
            `<p class="history-empty" data-en="Log in to see your saved conversations." data-ar="سجّلي دخول عشان تشوفي محادثاتك المحفوظة.">Log in to see your saved conversations.</p>`;
    }

    updateChatGate();
}

if (userAvatarBtn) {
    userAvatarBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        userDropdown.classList.toggle("open");
    });
}

document.getElementById("logoutBtn").addEventListener("click", () => {
    clearAuth();
    updateAuthUI();
    resetChat();
    switchView("home");
});

document.addEventListener("click", (e) => {
    if (userDropdown && !e.target.closest(".user-menu")) userDropdown.classList.remove("open");
    if (!e.target.closest("#historyToggle")) document.getElementById("historyToggle").classList.remove("open");
});

// ---------- History dropdown ----------
const historyToggle = document.getElementById("historyToggle");
historyToggle.addEventListener("click", (e) => {
    if (e.target.closest(".history-panel")) return; // clicks inside the panel have their own handlers
    historyToggle.classList.toggle("open");
    if (currentUser) loadConversations();
});

async function loadConversations() {
    if (!authToken) return;
    try {
        const response = await apiFetch("/api/conversations");
        if (!response.ok) return;
        const conversations = await response.json();
        renderHistoryPanel(conversations);
    } catch (err) {
        console.error("Failed to load conversations:", err);
    }
}

function renderHistoryPanel(conversations) {
    const body = document.getElementById("historyPanelBody");
    if (!conversations || conversations.length === 0) {
        body.innerHTML = `<p class="history-empty" data-en="No conversations yet." data-ar="مفيش محادثات لسه.">No conversations yet.</p>`;
        return;
    }
    body.innerHTML = conversations.map(c => `
    <button class="history-entry" data-id="${c.id}">
      <i class="fa-regular fa-message"></i>
      <span>${escapeHtml(c.title || "New chat")}</span>
      <span class="delete-history" data-id="${c.id}" title="Delete"><i class="fa-regular fa-trash-can"></i></span>
    </button>
  `).join("");

    body.querySelectorAll(".history-entry").forEach(entry => {
        entry.addEventListener("click", (e) => {
            if (e.target.closest(".delete-history")) return;
            openConversation(entry.dataset.id);
            historyToggle.classList.remove("open");
            switchView("chat");
        });
    });

    body.querySelectorAll(".delete-history").forEach(btn => {
        btn.addEventListener("click", async(e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            await apiFetch(`/api/conversations/${id}`, { method: "DELETE" });
            if (conversationId === id) resetChat();
            loadConversations();
        });
    });
}

async function openConversation(id) {
    try {
        const response = await apiFetch(`/api/conversations/${id}/messages`);
        if (!response.ok) return;
        const msgs = await response.json();
        conversationId = id;
        messages.innerHTML = "";
        msgs.forEach(m => {
            if (m.role === "user") {
                addMessage(escapeHtml(m.content), "user");
            } else {
                addMessage(formatMarkdown(m.content), "assistant", m.evidence || [], m.id);
            }
        });
    } catch (err) {
        console.error("Failed to load conversation:", err);
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ---------- Evidence drawer ----------
const evidenceDrawer = document.getElementById("evidenceDrawer");
const evidenceToggle = document.getElementById("evidenceToggle");
const closeEvidence = document.getElementById("closeEvidence");
const drawerBody = document.getElementById("drawerBody");
const confidenceRow = document.getElementById("confidenceRow");
const confidenceValue = document.getElementById("confidenceValue");

function openEvidence() {
    evidenceDrawer.classList.add("open");
}

function hideEvidence() {
    evidenceDrawer.classList.remove("open");
}

evidenceToggle.addEventListener("click", openEvidence);
closeEvidence.addEventListener("click", hideEvidence);

function setConfidence(level) {
    if (!level) {
        confidenceRow.hidden = true;
        return;
    }
    confidenceRow.hidden = false;
    confidenceValue.textContent = level;
}

// بيرسم الـ evidence الحقيقية الراجعة من الـ API جوه الـ drawer
function renderEvidence(evidenceList, highlightRank = null) {
    if (!evidenceList || evidenceList.length === 0) {
        drawerBody.innerHTML = `<p class="drawer-placeholder">No supporting evidence for this answer.</p>`;
        return;
    }

    const cardsHtml = evidenceList.map((e, i) => {
        const rank = e.rank || i + 1;
        const isSelected = highlightRank ? rank === highlightRank : i === 0;
        return `
    <div class="evidence-card ${isSelected ? "selected" : ""}" id="evidence-card-${rank}">
      <div class="evidence-top">
        <span class="score">${e.score.toFixed(2)}</span>
        <span class="${e.used ? "used" : "supporting"}">
          ${e.used ? '<i class="fa-solid fa-check"></i> Used' : "Supporting"}
        </span>
      </div>
      <h4>[${rank}] ${escapeHtml(e.source_title)}</h4>
      <span class="evidence-meta">${escapeHtml(e.source_meta)}</span>
      <p>${escapeHtml(e.snippet)}</p>
    </div>
  `;
    }).join("");

    const top = highlightRank ?
        (evidenceList.find(e => (e.rank || evidenceList.indexOf(e) + 1) === highlightRank) || evidenceList[0]) :
        evidenceList[0];

    const previewHtml = `
    <div class="source-preview">
      <div class="preview-title">
        <span>Source preview</span>
        <span>${escapeHtml(top.source_meta)}</span>
      </div>
      <div class="document">
        <strong>${escapeHtml(top.source_title)}</strong>
        <p class="highlight">${escapeHtml(top.full_text)}</p>
      </div>
    </div>
  `;

    drawerBody.innerHTML = cardsHtml + previewHtml;

    if (highlightRank) {
        const el = document.getElementById(`evidence-card-${highlightRank}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

// بتحول أي [1] أو [2] جوه نص الرد لرابط قابل للضغط، بس لو فعلاً فيه evidence بنفس الرقم ده
function linkifyCitations(text, evidence) {
    if (!evidence || evidence.length === 0) return text;
    return text.replace(/\[(?:Source\s+)?(\d+)\]/gi, (match, num) => {
        const rank = parseInt(num, 10);
        const exists = evidence.some((e, i) => (e.rank || i + 1) === rank);
        return exists ?
            `<sup class="citation-link" data-rank="${rank}">[${rank}]</sup>` :
            match;
    });
}

// بتحول Markdown البسيط (bold و bullet points) اللي بيبعتها الموديل لـ HTML قبل ما نعرضها
function formatMarkdown(text) {
    if (!text) return text;
    let html = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(^|\s)\*\s+/g, "$1<br>• ");
    html = html.replace(/\n\n+/g, "<br><br>").replace(/\n/g, "<br>");
    return html;
}

// ---------- PDF download ----------
async function downloadPdf(messageId) {
    if (!messageId) return;
    try {
        const response = await apiFetch(`/api/chat/messages/${messageId}/pdf`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `drmood_summary_${messageId.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error("PDF download failed:", err);
        alert(currentLang === "ar" ?
            "تعذر تحميل الملف، تأكدي إن الباك إند شغال وحاولي تاني." :
            "Couldn't download the file. Make sure the backend is running and try again.");
    }
}

// ---------- Chat ----------
const askBtn = document.getElementById("askBtn");
const input = document.getElementById("questionInput");
const messages = document.getElementById("chatMessages");
const inputWrapper = document.getElementById("inputWrapper");
const rateLimitBanner = document.getElementById("rateLimitBanner");
const rateLimitText = document.getElementById("rateLimitText");
const loginRequiredBanner = document.getElementById("loginRequiredBanner");

function updateChatGate() {
    const loggedIn = !!(authToken && currentUser);
    // مش بنمنع الشات لو مش مسجلة دخول - بس بنوريها بانر تنبيه إن الهيستوري مش هتتحفظ
    loginRequiredBanner.hidden = loggedIn;
    if (!isRateLimited) {
        inputWrapper.classList.remove("disabled");
    }
}

function showRateLimitBanner(message) {
    isRateLimited = true;
    rateLimitText.textContent = message;
    rateLimitBanner.hidden = false;
    inputWrapper.classList.add("disabled");
}

function hideRateLimitBanner() {
    isRateLimited = false;
    rateLimitBanner.hidden = true;
    updateChatGate();
}

function resetChat() {
    conversationId = null;
    isRateLimited = false;
    rateLimitBanner.hidden = true;
    messages.querySelectorAll(".message").forEach((el, i) => { if (i > 0) el.remove(); });
    setConfidence(null);
    drawerBody.innerHTML = `<p class="drawer-placeholder" data-en="Ask a question to see supporting sources here." data-ar="اسألي سؤال عشان تشوفي المصادر الداعمة هنا.">Ask a question to see supporting sources here.</p>`;
    updateChatGate();
}

document.getElementById("newChatBtn").addEventListener("click", resetChat);

function addMessage(text, type, evidence = [], messageId = null) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${type}-message`;

    if (type === "assistant") {
        const linkedText = linkifyCitations(text, evidence);

        wrapper.innerHTML = `
      <div class="message-avatar">
        <img src="assets/logo-icon.png" alt="Dr. Mood">
      </div>
      <div class="message-content">
        <span class="message-name">Dr. Mood</span>
        <div class="bubble">
          ${linkedText}
          <div class="answer-source">
            <i class="fa-solid fa-book-medical"></i>
            Based on approved clinical resources
            <button class="dynamic-evidence">View evidence</button>
            ${messageId ? '<button class="download-pdf"><i class="fa-solid fa-file-pdf"></i> PDF</button>' : ""}
          </div>
        </div>
      </div>
    `;

        wrapper.querySelector(".dynamic-evidence").addEventListener("click", () => {
            renderEvidence(evidence);
            openEvidence();
        });

        const pdfBtn = wrapper.querySelector(".download-pdf");
        if (pdfBtn) {
            pdfBtn.addEventListener("click", () => downloadPdf(messageId));
        }

        wrapper.querySelectorAll(".citation-link").forEach(el => {
            el.addEventListener("click", () => {
                const rank = parseInt(el.dataset.rank, 10);
                renderEvidence(evidence, rank);
                openEvidence();
            });
        });
    } else {
        wrapper.innerHTML = `
      <div class="message-content">
        <span class="message-name">You</span>
        <div class="bubble">${text}</div>
      </div>
    `;
    }

    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
}

function addLoadingMessage() {
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant-message";
    wrapper.id = "loadingMessage";
    wrapper.innerHTML = `
    <div class="message-avatar">
      <img src="assets/logo-icon.png" alt="Dr. Mood">
    </div>
    <div class="message-content">
      <span class="message-name">Dr. Mood</span>
      <div class="bubble">${currentLang === "ar" ? "بيفكر..." : "Thinking..."}</div>
    </div>
  `;
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
}

function removeLoadingMessage() {
    const el = document.getElementById("loadingMessage");
    if (el) el.remove();
}

async function sendQuestion() {
    const question = input.value.trim();
    if (!question || isRateLimited) return;

    addMessage(escapeHtml(question), "user");
    input.value = "";
    addLoadingMessage();

    try {
        const response = await apiFetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: conversationId,
                role: currentRole,
                message: question,
            }),
        });

        if (response.status === 429) {
            removeLoadingMessage();
            let detail;
            try {
                const errBody = await response.json();
                detail = errBody.detail;
            } catch {
                detail = null;
            }
            const msg = (detail && detail[currentLang]) ||
                (currentLang === "ar" ?
                    "وصلنا لحد الاستخدام المسموح به دلوقتي. حاولي تاني كمان شوية." :
                    "Dr. Mood has reached its usage limit for now. Please try again soon.");
            showRateLimitBanner(msg);
            return;
        }

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const data = await response.json();
        conversationId = data.conversation_id;

        let messageText = "";
        let messageId = null;
        if (typeof data.message === "object" && data.message !== null) {
            messageText = data.message.content || "";
            messageId = data.message.id || null;
        } else {
            messageText = data.message || "";
        }

        const evidence = typeof data.message === "object" && data.message !== null ?
            (data.message.evidence || []) : [];

        removeLoadingMessage();

        const messageContent = formatMarkdown(messageText);
        addMessage(messageContent, "assistant", evidence, messageId);

        setConfidence(data.confidence || null);
        loadConversations();

    } catch (err) {
        console.error("Chat request failed:", err);
        removeLoadingMessage();
        addMessage(currentLang === "ar" ?
            "معلش، مش قادر أوصل للسيرفر دلوقتي. تأكدي إن الباك إند شغال." :
            "Sorry, I couldn't reach the server. Please make sure the backend is running.", "assistant");
    }
}

askBtn.addEventListener("click", sendQuestion);

input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
});

document.querySelectorAll(".quick-question").forEach(button => {
    button.addEventListener("click", () => {
        if (isRateLimited) return;
        input.value = button.textContent;
        sendQuestion();
    });
});

// ---------- Auth forms ----------
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginError = document.getElementById("loginError");
const registerError = document.getElementById("registerError");

function showFormError(el, message) {
    // لو الباك إند رجع validation error (list/object) بدل نص عادي، منعرضوش زي ما هو
    if (typeof message !== "string") {
        message = currentLang === "ar" ? "فيه بيانات غير صحيحة، راجعي الحقول." : "Some fields are invalid. Please check them.";
    }
    el.textContent = message;
    el.hidden = false;
}

loginForm.addEventListener("submit", async(e) => {
    e.preventDefault();
    loginError.hidden = true;
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        if (!response.ok) {
            showFormError(loginError, data.detail || (currentLang === "ar" ? "الإيميل أو كلمة المرور غلط." : "Incorrect email or password."));
            return;
        }
        saveAuth(data.access_token, data.user);
        updateAuthUI();
        loginForm.reset();
        switchView("chat");
    } catch (err) {
        showFormError(loginError, currentLang === "ar" ? "تعذر الاتصال بالسيرفر." : "Couldn't reach the server.");
    }
});

registerForm.addEventListener("submit", async(e) => {
    e.preventDefault();
    registerError.hidden = true;
    const name = document.getElementById("registerName").value.trim();
    const email = document.getElementById("registerEmail").value.trim();
    const password = document.getElementById("registerPassword").value;

    try {
        const response = await fetch(`${API_BASE}/api/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password }),
        });
        const data = await response.json();
        if (!response.ok) {
            showFormError(registerError, data.detail || (currentLang === "ar" ? "تعذر إنشاء الحساب." : "Couldn't create the account."));
            return;
        }
        saveAuth(data.access_token, data.user);
        updateAuthUI();
        registerForm.reset();
        switchView("chat");
    } catch (err) {
        showFormError(registerError, currentLang === "ar" ? "تعذر الاتصال بالسيرفر." : "Couldn't reach the server.");
    }
});

// ---------- Google Sign-In ----------
async function handleGoogleCredential(response) {
    try {
        const apiResponse = await fetch(`${API_BASE}/api/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: response.credential }),
        });
        const data = await apiResponse.json();
        if (!apiResponse.ok) {
            alert(data.detail || "Google sign-in failed.");
            return;
        }
        saveAuth(data.access_token, data.user);
        updateAuthUI();
        switchView("chat");
    } catch (err) {
        console.error("Google sign-in failed:", err);
    }
}

function initGoogleSignIn() {
    if (!GOOGLE_CLIENT_ID || typeof google === "undefined" || !google.accounts) return;
    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
    });
    ["googleLoginBtnLogin", "googleLoginBtnRegister"].forEach(id => {
        const el = document.getElementById(id);
        if (el) google.accounts.id.renderButton(el, { theme: "outline", size: "large", width: 320 });
    });
}

// ---------- Init ----------
loadStoredUser();
applyLanguage("en");
setDarkMode(localStorage.getItem("drmood_dark") === "1");
updateAuthUI();

if (!authToken) {
    switchView("home");
} else {
    switchView("chat");
}

window.addEventListener("load", () => {
    // Google's script loads async; give it a moment before wiring buttons.
    setTimeout(initGoogleSignIn, 400);
});