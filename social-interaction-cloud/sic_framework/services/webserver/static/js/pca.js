/** * Javascript code for the Project Conversational Agents course.
 * * This code makes some basic assumptions about the interaction protocol:
 * - User always is the first to say something (by turning on the microphone)
 * - The microphone automatically is closed again when a transcript has been received (the user has said something)
 * - After receiving a transcript, the turn is given to the agent and the user cannot turn on the microphone.
 * - When the agent has said something, the turn is handed back to the user.
 * * This code also makes assumptions about the names of two buttons: the 'start' and 'mic'(rophone) button.
 * Button clicks are passed on to the webserver, which passes them on to the MARBEL agent using an EIS connector.
 * * Finally, on pages where there is a microphone, a footer should be present with a <p> element with id="transcript".
 * This element will be used to display the transcript received from the ASR component.
 * * SocketIO is used to communicate with the server.
*/

"use strict";

// Establish a WebSocket connection
var socket = io();

var user_turn = false;

// a fix for user-agent turn, as it was not storing when the website was changing, for instance from welcome.html to recipe_overview.html
if (sessionStorage.getItem("user_turn_saved") === "true") {
    console.log("Restoring user turn from previous page.");
    user_turn = true;
    sessionStorage.removeItem("user_turn_saved");
}

// Variable to keep track of number of recipes that fullfill criteria
var recipecounter = -1;

socket.off("speech");
window.currentUtterance = null;

socket.on("speech", (text) => {
    console.log("Agent speaking:", text);

    if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
    }
    window.speechSynthesis.cancel(); 

    window.currentUtterance = new SpeechSynthesisUtterance(text);

    window.currentUtterance.onend = function(event) {
        console.log("Speech finished naturally. Unlocking mic...");
        socket.emit('event', 'SpeechDone'); 
    };

    console.log("Setting up speech...");
    

    user_turn = true; 
    sessionStorage.setItem("user_turn_saved", "true");
    
    var micImage = document.getElementById('micimg');
    if (micImage) {
        micImage.src = 'static/images/mic_out.png'; 
    }

    window.speechSynthesis.speak(window.currentUtterance);
});

// Code for handling button elements on page
var elements = document.getElementsByClassName("btn");
// Send button clicks to server
var sendButtonClick = function() {
    var name = this.getAttribute("id");
    if (name !== "mic") {
        socket.emit('buttonClick', name); // send button name to web server
    }
};

for (var i = 0; i < elements.length; i++) {
    elements[i].addEventListener('click', sendButtonClick, false);
}

var micButton = document.getElementById('mic');

if (micButton) {
    micButton.addEventListener('click', function() {
        if (user_turn) {
            document.getElementById('micimg').src = 'static/images/mic_on.png';
            socket.emit('buttonClick', 'mic');
        } else {
            console.log("Blocked: It is not your turn.");
            alert("It is not your turn.");
        }
    });
}

// Event handler for successful connection
socket.on('connect', function() { 
    console.log('Connected to server.');

    var micButton = document.getElementById('mic');
    if (micButton) {
        micButton.disabled = false;
        micButton.style.opacity = "1.0";
        console.log("Microphone unlocked.");
    }
});

// Event handler for connection errors
socket.on('connect_error', function(error) { 
    console.log('Connection error:', error);
});

// Event handler for disconnection
socket.on('disconnect', function() { 
    console.log('Disconnected from server.');
});

// Event handler for transcript event
socket.on("transcript", (text) => {
    var transcriptEl = document.getElementById("transcript");
    if (transcriptEl) {
        transcriptEl.innerHTML = text;
    }
});

socket.on("pattern", (pattern) => {
    console.log("Received Pattern Switch:", pattern);

    socket.emit('event', 'SpeechDone'); 

    if (user_turn) {
        sessionStorage.setItem("user_turn_saved", "true");
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
        default:
            window.location.href = "closing.html";
      }
})

// Event handler for switching turns
socket.on("set_turn", (whoseturn) => {
    if (whoseturn == "true") {
        user_turn = true;
        sessionStorage.setItem("user_turn_saved", "true");
    } else {
        user_turn = false;
        sessionStorage.removeItem("user_turn_saved");
        
        var micImage = document.getElementById('micimg');
        if (micImage) {
            micImage.src = 'static/images/mic_out.png';
        }
    }
})

socket.on("recipecounter", (number) => {
    recipecounter = number;
    var counterEl = document.getElementById("recipecounter");
    if (counterEl) {
        counterEl.innerHTML = recipecounter;
    }
})

// Adding filters to a card deck on an HTML page
socket.on("filters", (filterString) => {
    const filtersString = filterString.substring(1, filterString.length-1);
    if (filterString.length != 0) {
        const filters = filtersString.split(',');
        
        var container = document.getElementById("addFiltersHere");
        if (container) {
            container.innerHTML = "";
            filters.forEach((element) => {
                filterCard(element);
            });
        } else {
            console.log("Received filters, but 'addFiltersHere' element not found on this page. Ignoring.");
        }
    }
})

function renderRecipeCard(data) {
    const container = document.querySelector("#content");
    const template = document.querySelector("#recipeDetailsTemplate");

    // Safety check: ensure elements exist on this specific page
    if (container && template) {
        container.innerHTML = ""; 
        const card = template.content.cloneNode(true);

        card.querySelector(".recipe-title").textContent = data.title;
        card.querySelector(".recipe-image").src = data.image;
        card.querySelector(".recipe-time").textContent = data.time + " mins";
        card.querySelector(".recipe-servings").textContent = data.servings + " people";

        container.appendChild(card);
    }
}

// Socket Listener: Saves data and tries to render immediately
socket.on("showRecipe", (jsonString) => {
    console.log("Received recipe data:", jsonString);
    
    // 1. Save to Session Storage (Persist data across page loads)
    sessionStorage.setItem("currentRecipeData", jsonString);

    // 2. Parse and Render
    const data = JSON.parse(jsonString);
    renderRecipeCard(data);
});

// Create and add a single card for a filter based on the template in the HTML file
function filterCard(filter) {
    let filterTemplate = document.querySelector('#filterCardTemplate');
    if (filterTemplate) {
        const card = filterTemplate.content.cloneNode(true);
        card.querySelector('#filterText').innerHTML = filter;
        document.getElementById("addFiltersHere").appendChild(card);
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const savedRecipe = sessionStorage.getItem("currentRecipeData");
    
    // Only render if we have data AND we are on a page that supports it (has the #content div)
    if (savedRecipe && document.querySelector("#content")) {
        console.log("Restoring recipe card from storage...");
        const data = JSON.parse(savedRecipe);
        renderRecipeCard(data);
    }
});