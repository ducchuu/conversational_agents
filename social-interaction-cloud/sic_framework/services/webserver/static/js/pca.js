"use strict";

// 1080p Reference Scale Engine: guarantees identical positioning & layout across all screens and resolutions
(function lock1080pResolution() {
  var TARGET_WIDTH = 1920;
  function applyScale() {
    var w = document.documentElement.clientWidth || window.innerWidth;
    if (w && w > 0) {
      var scale = w / TARGET_WIDTH;
      document.documentElement.style.zoom = scale;
    }
  }
  applyScale();
  window.addEventListener("resize", applyScale);
  window.addEventListener("orientationchange", applyScale);
})();

var socket = io();

var user_turn = false;
var recipecounter = -1;
var currentPatternId = null;
var forceShowRecipes = sessionStorage.getItem("forceShowRecipes") === "true"; // When true, allow showing up to 100 recipes

function $(id) {
  return document.getElementById(id);
}

function safeSetText(id, text) {
  var el = $(id);
  if (el) el.textContent = text;
}

function safeSetHTML(id, html) {
  var el = $(id);
  if (el) el.innerHTML = html;
}

function tryParseJSON(str) {
  if (str && typeof str === "object") return str;
  if (typeof str !== "string") return null;
  var s = str.trim();
  if (!s) return null;
  if (!(s.startsWith("{") || s.startsWith("["))) return null;
  try {
    return JSON.parse(s);
  } catch (e) {
    // Sometimes payload arrives with escaped quotes like \"...\"; try a repair pass.
    var repaired = s
      .replace(/\\"/g, "\"")
      .replace(/\\n/g, "\n")
      .replace(/\\r/g, "\r")
      .replace(/\\t/g, "\t")
      .replace(/\\\\/g, "\\");
    try {
      return JSON.parse(repaired);
    } catch (e2) {
      return null;
    }
  }
}

function parseSimpleListString(listString) {
  if (typeof listString !== "string") return [];
  var s = listString.trim();
  if (!s) return [];
  if (s.startsWith("[") && s.endsWith("]")) {
    s = s.slice(1, -1);
  }
  if (!s.trim()) return [];

  var out = [];
  var buf = "";
  var inQuote = false;
  var quoteChar = "";
  for (var i = 0; i < s.length; i++) {
    var ch = s[i];
    if ((ch === "'" || ch === '"') && (quoteChar === "" || ch === quoteChar)) {
      if (!inQuote) {
        inQuote = true;
        quoteChar = ch;
      } else {
        inQuote = false;
        quoteChar = "";
      }
      buf += ch;
      continue;
    }
    if (ch === "," && !inQuote) {
      out.push(buf.trim());
      buf = "";
      continue;
    }
    buf += ch;
  }
  if (buf.trim()) out.push(buf.trim());

  return out
    .map(function (t) {
      t = t.trim();
      if ((t.startsWith("'") && t.endsWith("'")) || (t.startsWith('"') && t.endsWith('"'))) {
        t = t.slice(1, -1);
      }
      return t.trim();
    })
    .filter(Boolean);
}

function normalizeRecipes(payloadString) {
  var parsed = tryParseJSON(payloadString);
  if (parsed) {
    if (Array.isArray(parsed)) {
      if (parsed.length === 0) return [];
      if (typeof parsed[0] === "object" && !Array.isArray(parsed[0])) {
        return parsed.map(function (r, idx) {
          return {
            id: r.id != null ? String(r.id) : String(idx),
            title: r.title || r.name || ("Recipe " + (idx + 1)),
            image: r.image || r.img || "",
            description: r.description || r.desc || "",
            time: r.time || r.cooking_time || "",
            servings: r.servings || r.yields || "",
            ingredients: r.ingredients || [],
            instructions: r.instructions || r.steps || []
          };
        });
      }
      if (Array.isArray(parsed[0])) {
        return parsed.map(function (arr, idx) {
          return {
            id: String(idx),
            title: arr[0] || ("Recipe " + (idx + 1)),
            image: arr[1] || "",
            description: arr[2] || "",
            time: arr[3] || "",
            servings: arr[4] || "",
            ingredients: arr[5] || [],
            instructions: arr[6] || []
          };
        });
      }
    }
    if (typeof parsed === "object") {
      return [{
        id: parsed.id != null ? String(parsed.id) : "0",
        title: parsed.title || parsed.name || "Recipe",
        image: parsed.image || parsed.img || "",
        description: parsed.description || parsed.desc || "",
        time: parsed.time || parsed.cooking_time || "",
        servings: parsed.servings || parsed.yields || "",
        ingredients: parsed.ingredients || [],
        instructions: parsed.instructions || parsed.steps || []
      }];
    }
  }

  var titles = parseSimpleListString(payloadString);
  return titles.map(function (t, idx) {
    return { id: String(idx), title: t, image: "", description: "", time: "", servings: "", ingredients: [], instructions: [] };
  });
}

function normalizeSingleRecipe(payloadString) {
  var recipes = normalizeRecipes(payloadString);
  return recipes.length ? recipes[0] : null;
}

if (sessionStorage.getItem("user_turn_saved") === "true") {
  user_turn = true;
  sessionStorage.removeItem("user_turn_saved");
}

socket.off("speech");
socket.off("speech_chunk");
window.currentUtterance = null;
var pendingNavigationUrl = null;
var speechWatchdog = null;
var speechTurnFinished = false;
var speechTotalChars = 0;

function handleSpeechFinished() {
  if (speechTurnFinished) return;
  speechTurnFinished = true;
  if (speechWatchdog) {
    clearTimeout(speechWatchdog);
    speechWatchdog = null;
  }
  socket.emit('event', 'SpeechDone');
  window.currentUtterance = null;

  // Check if a page transition is pending after TTS finishes
  if (pendingNavigationUrl && window.location.pathname.indexOf(pendingNavigationUrl) === -1) {
      var target = pendingNavigationUrl;
      pendingNavigationUrl = null;
      window.location.href = target;
  } else {
      // Stay on page: hand turn to user
      user_turn = true;
      sessionStorage.setItem("user_turn_saved", "true");
      var micImage = $("micimg");
      if (micImage) {
        micImage.src = 'static/images/mic_out.png';
      }
  }
}

function enqueueSpeechChunk(text, isFirst, isFinal) {
  if (isFirst) {
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
    window.speechSynthesis.cancel();
    if (speechWatchdog) {
      clearTimeout(speechWatchdog);
      speechWatchdog = null;
    }
    speechTurnFinished = false;
    speechTotalChars = 0;
  }

  var cleanedText = (text && typeof text === "string") ? text.trim() : "";
  if (!cleanedText) {
    if (isFinal) {
      if (window.currentUtterance && window.speechSynthesis.speaking) {
        window.currentUtterance.onend = handleSpeechFinished;
        window.currentUtterance.onerror = handleSpeechFinished;
      } else {
        handleSpeechFinished();
      }
    }
    return;
  }

  var utterance = new SpeechSynthesisUtterance(cleanedText);
  window.currentUtterance = utterance;
  speechTotalChars += cleanedText.length;

  // Defensive fallback watchdog: guards against Chromium SpeechSynthesis hang where neither onend nor onerror fires
  // Estimated speech duration: ~15 characters per second + 2.0s grace period (minimum 4.0s)
  if (speechWatchdog) {
    clearTimeout(speechWatchdog);
  }
  var maxSpeechTimeoutMs = Math.max(4000, (speechTotalChars / 15) * 1000 + 2000);
  speechWatchdog = setTimeout(function() {
    console.warn("TTS onend/onerror timed out; executing watchdog fallback to unblock state machine.");
    handleSpeechFinished();
  }, maxSpeechTimeoutMs);

  if (isFinal) {
    utterance.onend = handleSpeechFinished;
    utterance.onerror = handleSpeechFinished;
  } else {
    utterance.onerror = handleSpeechFinished;
  }

  window.speechSynthesis.speak(utterance);
}

socket.on("speech", (text) => {
  enqueueSpeechChunk(text, true, true);
});

socket.on("speech_chunk", (payload) => {
  if (!payload || typeof payload !== "object") return;
  enqueueSpeechChunk(payload.text || "", Boolean(payload.is_first), Boolean(payload.is_final));
});

var elements = document.getElementsByClassName("btn");

var sendButtonClick = function() {
  var name = this.getAttribute("id");
  if (name !== "mic") {
    socket.emit('buttonClick', name);
  }
};

for (var i = 0; i < elements.length; i++) {
  elements[i].addEventListener('click', sendButtonClick, false);
}

var micButton = $("mic");
let mediaRecorder;
let audioChunks = [];

// --- Model Warmup Readiness Feedback ---
// Background warmup binds the HTTP port in <1.5s, while heavier CTranslate2 & ONNX weights
// load into RAM in the background (5-10s). We poll /api/ready to update the mic status.
var isModelReady = false;

function checkModelReadiness() {
  fetch("/api/ready")
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (data && data.models_ready) {
        isModelReady = true;
        var warmNotice = $("warmupNotice");
        if (warmNotice) warmNotice.remove();
        var micBtn = $("mic");
        if (micBtn) {
          micBtn.style.filter = "none";
          micBtn.title = "Click to speak";
        }
      } else {
        isModelReady = false;
        showWarmupNotice();
        setTimeout(checkModelReadiness, 2000);
      }
    })
    .catch(function() {
      setTimeout(checkModelReadiness, 3000);
    });
}

function showWarmupNotice() {
  var micBtn = $("mic");
  if (micBtn) {
    micBtn.style.filter = "grayscale(60%) opacity(0.7)";
    micBtn.title = "Preparing speech recognition models (5-10s)...";
  }
  if ($("warmupNotice")) return;
  var notice = document.createElement("div");
  notice.id = "warmupNotice";
  notice.style.cssText = "position:fixed;bottom:20px;right:20px;background:rgba(44,62,80,0.92);color:#ecf0f1;padding:8px 16px;border-radius:20px;font-size:12px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.2);display:flex;align-items:center;gap:8px;";
  notice.innerHTML = "<span class='spinner-border spinner-border-sm' role='status' aria-hidden='true' style='width:12px;height:12px;'></span> Preparing speech recognition...";
  document.body.appendChild(notice);
}

checkModelReadiness();

// --- Inactivity Rule for Public Portfolio Demo ---
// Disconnect Socket.IO after 7 minutes of no user interaction (speech or clicks).
// Background heartbeat packets do NOT reset this timer.
// Allows Cloud Run to scale to 0 instances and prevents billing leaks when tabs are left open.
var INACTIVITY_TIMEOUT_MS = 7 * 60 * 1000; // 7 minutes
var lastUserActivityTime = Date.now();

function recordUserActivity() {
  lastUserActivityTime = Date.now();
  var banner = $("inactivityBanner");
  if (banner) banner.remove();
}

document.addEventListener("click", recordUserActivity, true);
document.addEventListener("keydown", recordUserActivity, true);

setInterval(function() {
  if (Date.now() - lastUserActivityTime > INACTIVITY_TIMEOUT_MS) {
    if (socket && socket.connected) {
      console.log("Disconnecting socket due to inactivity (7 minutes).");
      socket.disconnect();
      showInactivityBanner();
    }
  }
}, 15000);

function showInactivityBanner() {
  if ($("inactivityBanner")) return;
  var banner = document.createElement("div");
  banner.id = "inactivityBanner";
  banner.style.cssText = "position:fixed;top:0;left:0;right:0;background:#2c3e50;color:#fff;text-align:center;padding:12px 20px;z-index:999999;box-shadow:0 2px 10px rgba(0,0,0,0.3);font-size:14px;";
  banner.innerHTML = "<span>Demo session paused after 7 minutes of inactivity to save server resources.</span> " +
    "<button id='resumeInactivityBtn' style='margin-left:12px;padding:4px 14px;background:#27ae60;border:none;border-radius:4px;color:#fff;font-weight:bold;cursor:pointer;'>Resume Session</button>";
  document.body.appendChild(banner);
  var btn = document.getElementById("resumeInactivityBtn");
  if (btn) {
    btn.onclick = function() {
      banner.remove();
      recordUserActivity();
      if (!socket.connected) {
        socket.connect();
      }
    };
  }
}

if (micButton) {
  micButton.addEventListener('click', async function() {
    if (!isModelReady) {
      alert("Speech recognition models are still initializing in the background (~5-10s). Please wait a moment...");
      return;
    }
    if (!user_turn) {
      alert("It is not your turn.");
      return;
    }
    
    var micImg = $("micimg");

    // If already recording, stop it
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      if(micImg) micImg.src = 'static/images/mic_out.png';
      return;
    }
    
    // Start recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.push(event.data);
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        socket.emit('audio_stream', audioBlob);
        
        // Stop all tracks to release the microphone
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      if(micImg) micImg.src = 'static/images/mic_on.png';
      socket.emit('event', 'ListeningStarted');
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Could not access the microphone. Please check your browser permissions.");
    }
  });
}

socket.on('connect', function() {
  var micButton = $("mic");
  if (micButton) {
    micButton.disabled = false;
    micButton.style.opacity = "1.0";
  }
});

socket.on('connect_error', function(error) {
  console.log('Connection error:', error);
});

socket.on('disconnect', function() {
  console.log('Disconnected from server.');
});

socket.on("session_busy", function(data) {
  if (data && data.message && !$("sessionBusyBanner")) {
    var banner = document.createElement("div");
    banner.id = "sessionBusyBanner";
    banner.style.cssText = "position:fixed;top:0;left:0;right:0;background:#e67e22;color:#fff;text-align:center;padding:10px 20px;z-index:999998;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.25);";
    banner.innerHTML = "<span>" + data.message + "</span> <button id='dismissBusyBtn' style='margin-left:12px;padding:2px 10px;background:#34495e;border:none;border-radius:3px;color:#fff;cursor:pointer;'>Dismiss</button>";
    document.body.appendChild(banner);
    var btn = document.getElementById("dismissBusyBtn");
    if (btn) btn.onclick = function() { banner.remove(); };
  }
});

socket.on("transcript", (text) => {
  if ($("transcript")) safeSetHTML("transcript", text);
});

socket.on("pattern", (pattern) => {
  currentPatternId = pattern;

  if (pattern === "start" || pattern === "c10" || pattern === "a50recipeSelect") {
      sessionStorage.removeItem("currentRecipeData");
      sessionStorage.removeItem("forceShowRecipes");
      forceShowRecipes = false;
  }

  // If the user said "No more filters" and we have <= 100 recipes, force the display
  if (pattern === "a21noMoreFilters" && recipecounter <= 100) {
      forceShowRecipes = true;
  }

  // Determine target URL without navigating yet
  switch(pattern) {
    case "start":
      pendingNavigationUrl = "start.html";
      break;
    case "c10":
      pendingNavigationUrl = "welcome.html";
      break;
    case "a50recipeSelect":
    case "a21noMoreFilters": 
      pendingNavigationUrl = (recipecounter <= 20 || forceShowRecipes) ? "recipe_overview2.html" : "recipe_overview.html";
      break;
    case "a50recipeConfirm":
      pendingNavigationUrl = "recipe_confirmation.html";
      break;
    case "c43":
    case "terminated":
      pendingNavigationUrl = "closing.html";
      break;
    default:
      pendingNavigationUrl = "closing.html";
  }

  // If there is no speech currently playing or queued, navigate immediately
  if (!window.speechSynthesis.speaking && !window.currentUtterance) {
      if (pendingNavigationUrl && window.location.pathname.indexOf(pendingNavigationUrl) === -1) {
          var target = pendingNavigationUrl;
          pendingNavigationUrl = null;
          window.location.href = target;
      }
  }
});

function goToRecipeOverview() {
  var hasCount = recipecounter > -1;
  var targetUrl = (hasCount && (recipecounter <= 20 || forceShowRecipes)) ? "recipe_overview2.html" : "recipe_overview.html";

  // If already on the target page, nothing to do
  if (window.location.pathname.indexOf(targetUrl) !== -1) {
    return;
  }

  // If speech is playing or queued, defer navigation until TTS finishes
  if (window.speechSynthesis.speaking || window.currentUtterance) {
    pendingNavigationUrl = targetUrl;
    return;
  }

  window.location.href = targetUrl;
}

socket.on("set_turn", (whoseturn) => {
  if (whoseturn == "true") {
    user_turn = true;
    sessionStorage.setItem("user_turn_saved", "true");
  } else {
    user_turn = false;
    sessionStorage.removeItem("user_turn_saved");

    var micImage = $("micimg");
    if (micImage) {
      micImage.src = 'static/images/mic_out.png';
    }
  }
});

socket.on("recipecounter", (number) => {
  recipecounter = parseInt(number, 10);
  sessionStorage.setItem("currentRecipeCounter", String(recipecounter));
  safeSetText("recipecounter", String(recipecounter));
  
  if (currentPatternId === "a50recipeSelect") {
    goToRecipeOverview();
  }
  updateOverviewLayout();
});

// Listener for explicit 'show' flag if emitted by the backend
socket.on("forceShow", (val) => {
    // Check if the value is 'true' string or boolean true
    if (val === 'true' || val === true) {
        forceShowRecipes = true;
        sessionStorage.setItem("forceShowRecipes", "true");
        updateOverviewLayout();
        goToRecipeOverview();
    }
});

function renderFiltersList(filterString) {
  var target = $("addFiltersHere");
  var tpl = document.querySelector("#filterCardTemplate");
  
  if (!target || !tpl) {
      if(target && !tpl) {
          const filters = parseSimpleListString(filterString);
          target.innerHTML = "";
          filters.forEach(f => {
              var p = document.createElement("p");
              p.textContent = f;
              target.appendChild(p);
          });
      }
      return;
  }

  var filters = parseSimpleListString(filterString);

  target.innerHTML = "";
  filters.forEach(function (f) {
    var card = tpl.content.cloneNode(true);
    var node = card.querySelector("#filterText") || card.querySelector("[id='filterText']");
    if (node) node.textContent = f;
    target.appendChild(card);
  });
}

socket.on("filters", function (filterString) {
  if (filterString) {
    sessionStorage.setItem("currentFiltersString", String(filterString));
  }
  renderFiltersList(filterString);
});

socket.on("showRecipe", (jsonString) => {
  var data = tryParseJSON(jsonString);
  if (data) {
    sessionStorage.setItem("currentRecipeData", JSON.stringify(data));
    renderRecipeCard(data);
  } else if (typeof jsonString === "string") {
    sessionStorage.setItem("currentRecipeData", jsonString);
  }
});

socket.on("recipe_detail", function (recipeString) {
  var data = tryParseJSON(recipeString);
  if (data) {
    sessionStorage.setItem("currentRecipeData", JSON.stringify(data));
    renderRecipeCard(data);
  }
});

function renderRecipesList(recipesString) {
  var grid = $("recipesGrid");
  var empty = $("recipesEmptyState");
  var tpl = document.querySelector("#recipeCardTemplate");
  
  if (!grid || !tpl) return;

  var recipes = normalizeRecipes(recipesString);

  // Keep recipe counter in sync when we receive the recipes list
  if (recipes.length >= 0) {
    recipecounter = recipes.length;
    sessionStorage.setItem("currentRecipeCounter", String(recipecounter));
    safeSetText("recipecounter", String(recipecounter));
  }

  grid.innerHTML = "";
  
  // Logic: Only show empty state if we actually expected recipes (count <= 20) but got none
  if (empty) {
      if (recipes.length === 0 && recipecounter <= 20 && recipecounter > -1) {
          empty.style.display = "block";
      } else {
          empty.style.display = "none";
      }
  }

  recipes.forEach(function (r) {
    var node = tpl.content.cloneNode(true);

    var card = node.querySelector(".pca-recipe");
    if (card) {
      card.setAttribute("data-recipe-id", r.id);
      card.addEventListener("click", function () {
        // Use buttonClick so MARBEL treats it as a recipeRequest
        socket.emit("buttonClick", r.title);
      });
      // Accessibility
      card.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          card.click();
        }
      });
    }

    var img = node.querySelector("[data-recipe-img]");
    if (img && r.image) {
      img.style.backgroundImage = "url('" + r.image.replace(/'/g, "%27") + "')";
    }

    var title = node.querySelector("[data-recipe-title]");
    if (title) title.textContent = r.title;

    var desc = node.querySelector("[data-recipe-desc]");
    if (desc) desc.textContent = r.description || "Tap to select this recipe.";

    var time = node.querySelector("[data-recipe-time]");
    if (time) time.textContent = r.time || "—";

    var servings = node.querySelector("[data-recipe-servings]");
    if (servings) servings.textContent = r.servings || "—";

    grid.appendChild(node);
  });
}

socket.on("recipes", function (recipesString) {
  if (recipesString) {
    sessionStorage.setItem("currentRecipesList", typeof recipesString === 'string' ? recipesString : JSON.stringify(recipesString));
  }

  var recipes = normalizeRecipes(recipesString);

  // Keep recipe counter in sync when we receive the recipes list
  if (recipes.length >= 0) {
    recipecounter = recipes.length;
    sessionStorage.setItem("currentRecipeCounter", String(recipecounter));
    safeSetText("recipecounter", String(recipecounter));
  }

  // When 20 or fewer recipes are delivered and user is currently on recipe_overview.html, transition to recipe_overview2.html
  if (recipes.length > 0 && recipes.length <= 20) {
    forceShowRecipes = true;
    sessionStorage.setItem("forceShowRecipes", "true");
    var onOverview1 = window.location.pathname.indexOf("recipe_overview.html") !== -1;
    if (onOverview1) {
      if (window.speechSynthesis.speaking || window.currentUtterance) {
        pendingNavigationUrl = "recipe_overview2.html";
        return; // Do not flash cards on overview1 before transition
      } else {
        window.location.href = "recipe_overview2.html";
        return;
      }
    }
  }

  renderRecipesList(recipesString);
});

function renderRecipeCard(data) {
  var titleEl = document.getElementById("recipeTitle");
  if (!titleEl) return;

  safeSetText("recipeTitle", data.title);
  safeSetText("recipeTime", (data.time || "—"));
  safeSetText("recipeServings", (data.servings || "—"));
  safeSetText("recipeDescription", data.description || "");

  var img = document.getElementById("recipeImage");
  if (img && data.image) {
    if (img.tagName === "IMG") {
      img.src = data.image;
    } else {
      img.style.backgroundImage = "url('" + data.image.replace(/'/g, "%27") + "')";
    }
  }

  var ing = document.getElementById("ingredientsList");
  if (ing) {
    ing.innerHTML = "";
    var list = Array.isArray(data.ingredients) ? data.ingredients : parseSimpleListString(String(data.ingredients || ""));
    if (!list.length) list = ["—"];
    list.forEach(function (x) {
      var li = document.createElement("li");
      li.textContent = x;
      ing.appendChild(li);
    });
  }

  var steps = $("instructionsList");
  if (steps) {
    steps.innerHTML = "";
    var st = Array.isArray(data.instructions) ? data.instructions : parseSimpleListString(String(data.instructions || ""));
    if (!st.length) st = ["—"];
    st.forEach(function (x) {
      var li = document.createElement("li");
      li.textContent = x;
      steps.appendChild(li);
    });
  }

  // Load YouTube video for the recipe
  loadYouTubeVideo(data.title);
}

function loadYouTubeVideo(recipeTitle) {
  var videoFrame = document.getElementById("recipeVideo");
  var videoFallback = document.getElementById("videoFallback");
  
  if (!videoFrame) return;
  
  // Reset video frame
  videoFrame.src = "";
  if (videoFallback) {
    videoFallback.style.display = "none";
  }
  
  if (!recipeTitle || !recipeTitle.trim()) {
    if (videoFallback) {
      videoFallback.style.display = "block";
    }
    return;
  }
  
  // Fetch YouTube video ID from the API
  fetch("/api/youtube/search?title=" + encodeURIComponent(recipeTitle))
    .then(function(response) {
      if (!response.ok) {
        throw new Error("YouTube API request failed");
      }
      return response.json();
    })
    .then(function(data) {
      if (data.videoId) {
        // Set the iframe src to the YouTube embed URL
        videoFrame.src = "https://www.youtube.com/embed/" + data.videoId;
        if (videoFallback) {
          videoFallback.style.display = "none";
        }
      } else {
        // No video found
        if (videoFallback) {
          videoFallback.style.display = "block";
        }
      }
    })
    .catch(function(error) {
      console.error("Error loading YouTube video:", error);
      if (videoFallback) {
        videoFallback.style.display = "block";
      }
    });
}

function updateOverviewLayout() {
  var container = $("recipeResultsContainer");
  var mainTitle = $("mainTitle");
  var mainDesc = $("mainDescription");
  var subTitle = $("pageSubTitle");

  if (!container || !mainTitle) return; // Safety check if on wrong page

  // Only hide the container if count is > 20 AND we are NOT forcing it to show
  if (recipecounter > 20 && !forceShowRecipes) {
    container.style.display = "none";
    mainTitle.textContent = "Refine your preferences";
    if (mainDesc) mainDesc.textContent = "There are still too many results (" + recipecounter + "). Please add more filters like ingredients, cuisine, or time.";
    if (subTitle) subTitle.textContent = "Narrow down your search";
  } else {
    container.style.display = "block";
    if (recipecounter === 0) {
      mainTitle.textContent = "No recipes found";
      if (mainDesc) mainDesc.textContent = "Try removing a filter to see more results.";
    } else {
      mainTitle.textContent = "I found these recipes for you";
      if (mainDesc) mainDesc.textContent = "Here are the top " + recipecounter + " matches. Tap one to view details or add more filters.";
    }
    if (subTitle) subTitle.textContent = "Select a recipe";
  }
}

document.addEventListener("DOMContentLoaded", function() {
  var isStartPage = window.location.pathname.indexOf("start.html") !== -1 || window.location.pathname === "/";
  if (isStartPage) {
    sessionStorage.clear();
    socket.emit("client_start");
  }

  var isOverview1 = window.location.pathname.indexOf("recipe_overview.html") !== -1;
  var isOverview2 = window.location.pathname.indexOf("recipe_overview2.html") !== -1;

  if (isOverview1 || isOverview2) {
    var savedCounter = sessionStorage.getItem("currentRecipeCounter");
    if (savedCounter !== null) {
      recipecounter = parseInt(savedCounter, 10);
      safeSetText("recipecounter", String(recipecounter));
    }
    var savedFilters = sessionStorage.getItem("currentFiltersString");
    if (savedFilters) {
      renderFiltersList(savedFilters);
    }
    // Only restore grid cards directly on recipe_overview2.html
    if (isOverview2) {
      var savedRecipes = sessionStorage.getItem("currentRecipesList");
      if (savedRecipes) {
        renderRecipesList(savedRecipes);
      }
    }
    updateOverviewLayout();
  }

  // Only restore recipe data on the recipe confirmation page
  var isConfirmationPage = window.location.pathname.indexOf("recipe_confirmation.html") !== -1;
  
  if (isConfirmationPage) {
    var savedRecipe = sessionStorage.getItem("currentRecipeData");
    
    if (savedRecipe) {
      var data = tryParseJSON(savedRecipe);
      if(data) {
          console.log("Restoring recipe data...", data);
          renderRecipeCard(data);
      }
    }
  }
});