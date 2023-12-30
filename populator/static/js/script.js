document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    var username = document.getElementById('username').value;
    var password = document.getElementById('password').value;

    console.log("Username:", username);
    console.log("Password:", password);

    // Add login logic here
});
