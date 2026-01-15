"use strict";

var socket = io();

var user_turn = false;
var recipecounter = -1;

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
  if (typeof str !== "string") return null;
  var s = str.trim();
  if (!s) return null;
  if (!(s.startsWith("{") || s.startsWith("["))) return null;
  try {
    return JSON.parse(s);
  } catch (e) {
    return null;
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
  socket.emit('event', 'SpeechDone');

  if (user_turn) {
    sessionStorage.setItem("user_turn_saved", "true");
  }
  
  if (pattern === "start" || pattern === "c10") {
      sessionStorage.removeItem("currentRecipeData");
      console.log("Session cleared: New conversation started.");
  }

  switch(pattern) {
    case "start":
      window.location.href = "start.html";
      break;
    case "c10":
      window.location.href = "welcome.html";
      break;
    case "a50recipeSelect":
      window.location.href = "recipe_overview.html";
      break;
    case "a50recipeConfirm":
      window.location.href = "recipe_confirmation.html";
      break;
    case "c43":
      window.location.href = "closing.html";
      break;
    default:
      window.location.href = "closing.html";
  }
});

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
  recipecounter = number;
  safeSetText("recipecounter", String(recipecounter));
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
  sessionStorage.setItem("currentRecipeData", jsonString);
  var data = tryParseJSON(jsonString);
  if(data) renderRecipeCard(data);
});

socket.on("recipes", function (recipesString) {
  var grid = $("recipesGrid");
  var empty = $("recipesEmptyState");
  var tpl = document.querySelector("#recipeCardTemplate");
  if (!grid || !tpl) return;

  var recipes = normalizeRecipes(recipesString);

  grid.innerHTML = "";
  if (empty) empty.style.display = recipes.length ? "none" : "block";

  recipes.forEach(function (r) {
    var node = tpl.content.cloneNode(true);

    var card = node.querySelector(".pca-recipe");
    if (card) {
      card.setAttribute("data-recipe-id", r.id);
      card.addEventListener("click", function () {
        socket.emit("recipeSelect", { id: r.id, title: r.title });
      });
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
  if (titleEl) {
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
    if (ing && data.ingredients) {
        ing.innerHTML = "";
        var list = Array.isArray(data.ingredients) ? data.ingredients : parseSimpleListString(String(data.ingredients));
        if (!list.length) list = ["—"];
        list.forEach(function (x) {
            var li = document.createElement("li");
            li.textContent = x;
            ing.appendChild(li);
        });
    }
    return;
  }

  var container = document.querySelector("#content");
  var template = document.querySelector("#recipeDetailsTemplate");

  if (container && template) {
    container.innerHTML = "";
    var card = template.content.cloneNode(true);

    var t = card.querySelector(".recipe-title");
    if(t) t.textContent = data.title;
    
    var i = card.querySelector(".recipe-image");
    if(i) i.src = data.image;

    var tm = card.querySelector(".recipe-time");
    if(tm) tm.textContent = (data.time || "") + " mins";

    var sv = card.querySelector(".recipe-servings");
    if(sv) sv.textContent = (data.servings || "") + " people";

    container.appendChild(card);
  }
}

document.addEventListener("DOMContentLoaded", function() {
  var savedRecipe = sessionStorage.getItem("currentRecipeData");
  
  if (savedRecipe) {
    var data = tryParseJSON(savedRecipe);
    if(data) {
        console.log("Restoring recipe data...", data);
        renderRecipeCard(data);
    }
  }
});