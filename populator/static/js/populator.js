// script.js
document.getElementById('addFactionBtn').addEventListener('click', function() {
    let factionSection = document.createElement('div');
    factionSection.className = "section";
    
    factionSection.innerHTML = `
        <h3>Faction</h3>
        <div class="input-group">
            <label for="factionType">Type:</label>
            <input type="text" id="factionType" name="factionType">
        </div>
        <div class="input-group">
            <label for="factionPrompt">Prompt:</label>
            <textarea id="factionPrompt" name="factionPrompt"></textarea>
        </div>
    `;

    document.getElementById('factionsContainer').appendChild(factionSection);
});

document.getElementById('addCharacterBtn').addEventListener('click', function() {
    let characterSection = document.createElement('div');
    characterSection.className = "section";
    
    characterSection.innerHTML = `
        <h3>Character</h3>
        <div class="input-group">
            <label for="characterFactions">Factions affiliated:</label>
            <input type="text" id="characterFactions" name="characterFactions">
        </div>
        <div class="input-group">
            <label for="characterPrompt">Prompt:</label>
            <textarea id="characterPrompt" name="characterPrompt"></textarea>
        </div>
    `;

    document.getElementById('charactersContainer').appendChild(characterSection);
});

document.getElementById('submitBtn').addEventListener('click', function(event) {
    var characterInputs = document.querySelectorAll('input[name^="character_"]'); // Select all inputs with names starting with "character_"
    
    characterInputs.forEach(function(input) {
        if (!input.value.trim()) {
            input.value = 'Default Value'; // Set to any default value you'd like
        }
    });
});