const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatTextarea = document.getElementById("chat-textarea");
const modeTabs = document.getElementById("mode-tabs");

let sessionId = null;
let history = [];
let mode = "chat";

const PLACEHOLDERS = {
  chat: "Type a request...",
  audio: "Enter text to convert to speech...",
  video: "Describe the video you want to generate...",
};

function setMode(nextMode) {
  mode = nextMode;
  chatTextarea.placeholder = PLACEHOLDERS[mode] || PLACEHOLDERS.chat;
  modeTabs.querySelectorAll(".mode-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  chatTextarea.focus();
}

modeTabs.addEventListener("click", (event) => {
  const tab = event.target.closest(".mode-tab");
  if (tab) {
    setMode(tab.dataset.mode);
  }
});

function appendMessage(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role === "user" ? "user" : "assistant"}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function appendMedia(kind, src, caption) {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble media";

  if (caption) {
    const label = document.createElement("div");
    label.className = "media-caption";
    label.textContent = caption;
    bubble.appendChild(label);
  }

  let media;
  if (kind === "audio") {
    media = document.createElement("audio");
    media.controls = true;
    media.src = src;
  } else {
    media = document.createElement("video");
    media.controls = true;
    media.src = src;
    media.className = "media-video";

    const link = document.createElement("a");
    link.href = src;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Open / download video";
    link.className = "media-link";
    bubble.appendChild(media);
    bubble.appendChild(link);
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    chatLog.appendChild(wrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
    return;
  }

  bubble.appendChild(media);
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showThinking(label) {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant thinking";
  wrapper.id = "thinking-indicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble typing";
  bubble.innerHTML =
    '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

  if (label) {
    const note = document.createElement("span");
    note.className = "typing-note";
    note.textContent = label;
    bubble.appendChild(note);
  }

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeThinking() {
  const indicator = document.getElementById("thinking-indicator");
  if (indicator) {
    indicator.remove();
  }
}

function setLoading(isLoading) {
  chatTextarea.disabled = isLoading;
  chatForm.querySelector("button").disabled = isLoading;
}

async function parseError(response) {
  try {
    const data = await response.json();
    return data.detail || JSON.stringify(data);
  } catch (_) {
    return await response.text();
  }
}

async function handleChat(message) {
  showThinking();
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, history }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const data = await response.json();
  sessionId = data.session_id;
  history = data.messages;
  removeThinking();
  appendMessage("assistant", data.reply);
}

async function handleAudio(message) {
  showThinking("Generating speech...");
  const response = await fetch("/api/audio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: message }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const data = await response.json();
  removeThinking();
  appendMedia("audio", `data:${data.mime_type};base64,${data.audio_base64}`, "Generated speech");
}

async function handleVideo(message) {
  showThinking("Generating video... this can take a few minutes");
  const response = await fetch("/api/video", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: message }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const data = await response.json();
  removeThinking();
  appendMedia("video", data.download_url, "Generated video");
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatTextarea.value.trim();
  if (!message) {
    return;
  }

  appendMessage("user", message);
  if (mode === "chat") {
    history.push({ role: "user", content: message });
  }
  chatTextarea.value = "";
  chatTextarea.style.height = "auto";
  setLoading(true);

  try {
    if (mode === "audio") {
      await handleAudio(message);
    } else if (mode === "video") {
      await handleVideo(message);
    } else {
      await handleChat(message);
    }
  } catch (error) {
    removeThinking();
    appendMessage(
      "assistant",
      `⚠️ Request failed: ${error instanceof Error ? error.message : String(error)}`
    );
  } finally {
    setLoading(false);
    chatTextarea.focus();
  }
});

chatTextarea.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.dispatchEvent(new Event("submit"));
  }
});
