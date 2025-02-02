document.getElementById("submit-btn").addEventListener("click", function() {
    let userInputField = document.getElementById("user-input");
    let userInput = userInputField.value.trim();
    if (userInput) {
        sendChoice(userInput);
        userInputField.value = "";  // Clear input field
    }
});

function sendChoice(choiceText) {
    let gameScenario = document.getElementById("game-scenario");
    let optionsList = document.getElementById("options-list");

    // Create new user message
    let userMessage = `<p class="user-text">${choiceText}</p>`;
    gameScenario.innerHTML = userMessage + gameScenario.innerHTML;

    optionsList.innerHTML = ""; // Clear previous options

    // Send input to backend
    fetch("/play", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choice: choiceText })
    })
    .then(response => response.json())
    .then(data => {
        let formattedScenario = formatNPCDialogue(data.scenario);
        let aiMessage = `<p class="scenario-text">${formattedScenario}</p>`;
        gameScenario.innerHTML = aiMessage + gameScenario.innerHTML;

        // Ensure options always appear
        if (data.options && data.options.length > 0) {
            optionsList.innerHTML = "";
            data.options.forEach(option => {
                let li = document.createElement("li");
                let button = document.createElement("button");
                button.innerText = option;
                button.onclick = function() { sendChoice(option); };
                li.appendChild(button);
                optionsList.appendChild(li);
            });
        } else {
            optionsList.innerHTML = "<li>No options available.</li>";
        }

        // ✅ Update multiple images from backend response
        updateSceneImages(data.images);
    })
    .catch(error => console.error("Error:", error));
}

function formatNPCDialogue(text) {
    return text.replace(/"([^"]+)"/g, '<span class="npc-dialogue">"$1"</span>');
}

// **✅ Use Backend-Provided Image Paths for Environment, Items, and Characters**
function updateSceneImages(images) {
    let environmentImage = document.getElementById("environment-image");
    let itemImage = document.getElementById("item-image");
    let characterImage = document.getElementById("character-image");

    function setImage(imgElement, imagePath) {
        if (imagePath && imagePath !== "/static/images/unknown.png") {
            imgElement.src = imagePath;
            imgElement.style.display = "block";
        } else {
            imgElement.style.display = "none";
        }
    }

    setImage(environmentImage, images.environment);
    setImage(itemImage, images.item);
    setImage(characterImage, images.character);
}

// Initial API call to start the game
sendChoice("Start");
