"use strict";

/**
 * Project Conversational Agents — front-end glue
 *
 * Notes:
 * - SocketIO messages arrive as strings.
 * - This file is defensive: pages may not have all elements.
 */

var socket = io();

// Flag to keep track of whose turn it is (true --> user, false --> agent)
// Initially, it is the agent's turn; DO NOT CHANGE here, this flag is set by EISComponent in SIC framework
var user_turn = false;

// Variable to keep track of number of recipes that fulfill criteria
var recipecounter = -1;

// ---------------------------
// Utility helpers
// ---------------------------

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

function currentPageName() {
  var p = window.location.pathname.split("/").pop();
  return p || "";
}

/**
 * Try to parse JSON; returns null if it fails.
 */
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

/**
 * Parse strings like: "[a, b, c]" or "['a','b']" into ["a","b"].
 * This is NOT a full Prolog parser—just a practical fallback.
 */
function parseSimpleListString(listString) {
  if (typeof listString !== "string") return [];
  var s = listString.trim();
  if (!s) return [];
  if (s.startsWith("[") && s.endsWith("]")) {
    s = s.slice(1, -1);
  }
  if (!s.trim()) return [];

  // Split on commas that are not inside quotes (basic)
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

  // Clean tokens
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

/**
 * Normalize incoming recipe payload to:
 * [{id,title,image,description,time,servings,ingredients,instructions}, ...]
 *
 * Accepted (best) formats:
 * 1) JSON string of array of objects
 * 2) JSON string of array of arrays: [[title,img,desc,time,servings], ...]
 * 3) Fallback list of strings: "[Spaghetti, Curry]"
 */
function normalizeRecipes(payloadString) {
  // 1) JSON
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
      // Single recipe object
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

  // 2) Fallback list string
  var titles = parseSimpleListString(payloadString);
  return titles.map(function (t, idx) {
    return { id: String(idx), title: t, image: "", description: "", time: "", servings: "", ingredients: [], instructions: [] };
  });
}

function normalizeSingleRecipe(payloadString) {
  var recipes = normalizeRecipes(payloadString);
  return recipes.length ? recipes[0] : null;
}

// ---------------------------
// Buttons: send all .btn clicks (existing framework expectation)
// ---------------------------

var elements = document.getElementsByClassName("btn");

var sendButtonClick = function () {
  var name = this.getAttribute("id");
  if (name) socket.emit("buttonClick", name);
};

for (var i = 0; i < elements.length; i++) {
  elements[i].addEventListener("click", sendButtonClick, false);
}

// Dedicated mic behaviour
var micButton = $("mic");
if (micButton) {
  micButton.addEventListener("click", function () {
    if (user_turn) {
      var micImg = $("micimg");
      if (micImg) micImg.src = "static/images/mic_on.png";
    } else {
      alert("It is not your turn.");
    }
  });
}

// ---------------------------
// Socket handlers
// ---------------------------

socket.on("connect", function () {
  console.log("Connected to the server.");
});

socket.on("connect_error", function (error) {
  console.log("Connection error:", error);
});

socket.on("disconnect", function () {
  console.log("Disconnected from the server.");
});

socket.on("transcript", function (text) {
  if ($("transcript")) safeSetHTML("transcript", text);
});

// Page routing by pattern name.
// (If your MARBEL team uses different labels, just tweak these cases.)
socket.on("pattern", function (pattern) {
  switch (pattern) {
    case "start":
      window.location.href = "start.html";
      break;
    case "c10":
      window.location.href = "welcome.html";
      break;
    case "a50recipeSelect":
      // This might route to overview2 later based on recipe count; see recipecounter handler.
      window.location.href = "recipe_overview.html";
      break;
    case "a50recipeConfirm":
      window.location.href = "recipe_confirmation.html";
      break;
    case "c43":
      window.location.href = "closing.html";
      break;
    default:
      // Keep a sane fallback
      window.location.href = "closing.html";
      break;
  }
});

// Turn switching
socket.on("set_turn", function (whoseturn) {
  user_turn = (whoseturn === "true");
  if (!user_turn) {
    var micImg = $("micimg");
    if (micImg) micImg.src = "static/images/mic_out.png";
  }
});

// Recipe counter
socket.on("recipecounter", function (number) {
  recipecounter = number;
  safeSetText("recipecounter", String(recipecounter));

  // Optional: auto-switch between overview pages based on the count.
  // Only do this when you are in the selection flow.
  var page = currentPageName();
  if (page === "recipe_overview.html" && recipecounter > -1 && recipecounter <= 15) {
    window.location.href = "recipe_overview2.html";
  } else if (page === "recipe_overview2.html" && recipecounter > 15) {
    window.location.href = "recipe_overview.html";
  }
});

// Filters (template-driven)
socket.on("filters", function (filterString) {
  var target = $("addFiltersHere");
  var tpl = document.querySelector("#filterCardTemplate");
  if (!target || !tpl) return;

  var filters = parseSimpleListString(filterString);

  target.innerHTML = "";
  filters.forEach(function (f) {
    var card = tpl.content.cloneNode(true);
    var node = card.querySelector("#filterText") || card.querySelector("[id='filterText']");
    if (node) node.textContent = f;
    target.appendChild(card);
  });
});

// ---------------------------
// Recipe receivers (NEW)
// ---------------------------

/**
 * Receives a list of recipes and renders cards (used on recipe_overview2.html).
 *
 * Recommended payload (string): JSON, e.g.
 *  [
 *    {"id":"r1","title":"Pasta Primavera","image":"https://...","description":"Fresh & quick","time":"25 min","servings":"2"},
 *    ...
 *  ]
 */
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

      // Clicking a card emits a selection event for the backend/agent.
      // Your teammate can map this to MARBEL later.
      card.addEventListener("click", function () {
        socket.emit("recipeSelect", { id: r.id, title: r.title });
      });

      // Keyboard accessibility
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

/**
 * Receives a single recipe and renders the confirmation page.
 *
 * Recommended payload (string): JSON object, e.g.
 *  {"title":"Pasta Primavera","image":"https://...","time":"25 min","servings":"2",
 *   "ingredients":["..."], "instructions":["..."]}
 */
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

  // Ingredients
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

  // Instructions
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
