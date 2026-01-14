"use strict";

// Establish a WebSocket connection
var socket = io();


var user_turn = false;
if (sessionStorage.getItem("user_turn_saved") === "true") {
    console.log("Restoring user turn from previous page.");
    user_turn = true;

    sessionStorage.removeItem("user_turn_saved");
}

var recipecounter = -1;

socket.off("speech");
window.currentUtterance = null;

socket.on("speech", (text) => {
    console.log("Agent speaking:", text);
    window.speechSynthesis.cancel(); 

    window.currentUtterance = new SpeechSynthesisUtterance(text);

    console.log("Unlocking microphone (Speech Start).");
    user_turn = true; 

    sessionStorage.setItem("user_turn_saved", "true");

    var micImage = document.getElementById('micimg');
    if (micImage) {
        micImage.src = 'static/images/mic_out.png'; 
    }

    setTimeout(() => {
        socket.emit('event', 'SpeechDone');
    }, 500);

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

socket.on('connect', function() { console.log('Connected to server.'); });
socket.on('connect_error', function(error) { console.log('Connection error:', error); });
socket.on('disconnect', function() { console.log('Disconnected from server.'); });

socket.on("transcript", (text) => {
    document.getElementById("transcript").innerHTML = text;
});

socket.on("pattern", (pattern) => {
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
        default:
            window.location.href = "closing.html";
      }
})

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
    document.getElementById("recipecounter").innerHTML = recipecounter;
})

socket.on("filters", (filterString) => {
    const filtersString = filterString.substring(1, filterString.length-1);
    if (filterString.length != 0) {
        const filters = filtersString.split(',');
        document.getElementById("addFiltersHere").innerHTML = "";
        filters.forEach((element) => {
            filterCard(element);
        });
    }
})

function filterCard(filter) {
    let filterTemplate = document.querySelector('#filterCardTemplate');
    const card = filterTemplate.content.cloneNode(true);
    card.querySelector('#filterText').innerHTML = filter;
    document.getElementById("addFiltersHere").appendChild(card);
}