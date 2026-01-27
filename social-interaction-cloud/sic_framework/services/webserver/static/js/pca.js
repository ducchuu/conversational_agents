"use strict";

var socket = io();

var user_turn = false;
var recipecounter = -1;
var currentPatternId = null;
var forceShowRecipes = false; // When true, allow showing up to 100 recipes

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
window.currentUtterance = null;

socket.on("speech", (text) => {
  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
  }
  window.speechSynthesis.cancel();

  window.currentUtterance = new SpeechSynthesisUtterance(text);

  window.currentUtterance.onend = function(event) {
    socket.emit('event', 'SpeechDone');
  };

  user_turn = true;
  sessionStorage.setItem("user_turn_saved", "true");

  var micImage = $("micimg");
  if (micImage) {
    micImage.src = 'static/images/mic_out.png';
  }

  window.speechSynthesis.speak(window.currentUtterance);
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

if (micButton) {
  micButton.addEventListener('click', function() {
    if (user_turn) {
      var micImg = $("micimg");
      if(micImg) micImg.src = 'static/images/mic_on.png';
      socket.emit('buttonClick', 'mic');
    } else {
      alert("It is not your turn.");
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

socket.on("transcript", (text) => {
  if ($("transcript")) safeSetHTML("transcript", text);
});

socket.on("pattern", (pattern) => {
  currentPatternId = pattern;
  socket.emit('event', 'SpeechDone');

  if (user_turn) {
    sessionStorage.setItem("user_turn_saved", "true");
  }
  
  // Clear recipe data when starting fresh or returning to recipe selection
  if (pattern === "start" || pattern === "c10" || pattern === "a50recipeSelect") {
      sessionStorage.removeItem("currentRecipeData");
      // Reset the force flag if we go back to selection or restart
      forceShowRecipes = false;
  }

  // If the user said "No more filters" and we have <= 100 recipes, force the display
  if (pattern === "a21noMoreFilters" && recipecounter <= 100) {
      forceShowRecipes = true;
      goToRecipeOverview(); // Redirect immediately to the grid view
  }

  switch(pattern) {
    case "start":
      window.location.href = "start.html";
      break;
    case "c10":
      window.location.href = "welcome.html";
      break;
      
    // Both standard selection and the "Show List" command should trigger the overview logic
    case "a50recipeSelect":
    case "a21noMoreFilters": 
      goToRecipeOverview();
      break;
      
    case "a50recipeConfirm":
      window.location.href = "recipe_confirmation.html";
      break;
      
    // Both the closing pattern and the actual termination signal go to the closing page
    case "c43":
    case "terminated":
      window.location.href = "closing.html";
      break;
      
    default:
      // Fallback: If we don't know the pattern, assume conversation is over
      window.location.href = "closing.html";
  }
});

function goToRecipeOverview() {
  var onOverview2 = window.location.pathname.indexOf("recipe_overview2.html") !== -1;
  var onOverview1 = window.location.pathname.indexOf("recipe_overview.html") !== -1;
  var hasCount = recipecounter > -1;

  // Go to grid view (overview2) if count is small OR if forced to show
  if (hasCount && (recipecounter <= 15 || forceShowRecipes)) {
    if (!onOverview2) window.location.href = "recipe_overview2.html";
    return;
  }

  if (!onOverview1) {
    window.location.href = "recipe_overview.html";
  }
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
        updateOverviewLayout();
        goToRecipeOverview();
    }
});

socket.on("filters", function (filterString) {
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

socket.on("recipes", function (recipesString) {
  var grid = $("recipesGrid");
  var empty = $("recipesEmptyState");
  var tpl = document.querySelector("#recipeCardTemplate");
  
  if (!grid || !tpl) return;

  var recipes = normalizeRecipes(recipesString);

  grid.innerHTML = "";
  
  // Logic: Only show empty state if we actually expected recipes (count <= 15) but got none
  // The visibility of the container is handled by updateOverviewLayout()
  if (empty) {
      if (recipes.length === 0 && recipecounter <= 15 && recipecounter > -1) {
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
});

socket.on("recipe_detail", function (recipeString) {
  var recipe = normalizeSingleRecipe(recipeString);
  if (!recipe) return;

  safeSetText("recipeTitle", recipe.title);
  safeSetText("recipeTime", recipe.time || "—");
  safeSetText("recipeServings", recipe.servings || "—");
  safeSetText("recipeDescription", recipe.description || "");

  var img = $("recipeImage");
  if (img && recipe.image) {
    img.style.backgroundImage = "url('" + recipe.image.replace(/'/g, "%27") + "')";
  }

  var ing = $("ingredientsList");
  if (ing) {
    ing.innerHTML = "";
    var list = Array.isArray(recipe.ingredients) ? recipe.ingredients : parseSimpleListString(String(recipe.ingredients || ""));
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
    var st = Array.isArray(recipe.instructions) ? recipe.instructions : parseSimpleListString(String(recipe.instructions || ""));
    if (!st.length) st = ["—"];
    st.forEach(function (x) {
      var li = document.createElement("li");
      li.textContent = x;
      steps.appendChild(li);
    });
  }
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

  // Only hide the container if count is > 15 AND we are NOT forcing it to show
  if (recipecounter > 15 && !forceShowRecipes) {
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
  // Only restore recipe data on the recipe confirmation page
  var isConfirmationPage = window.location.pathname.indexOf("recipe_confirmation.html") !== -1;
  
  if (isConfirmationPage) {
    var savedRecipe = sessionStorage.getItem("currentRecipeData");
    
    if (savedRecipe) {
      var data = tryParseJSON(savedRecipe);
      if(data) {
          console.log("Restoring recipe data...", data);
          renderRecipeCard(data);
          // Load YouTube video when restoring saved recipe
          if (data.title) {
            loadYouTubeVideo(data.title);
          }
      }
    }
  }
});