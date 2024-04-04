function updateImage() {
    console.log("updateImage called");
    var select = document.getElementById('location-select');
    var imageUrl = select.options[select.selectedIndex].getAttribute('data-img-url');
    document.getElementById('location-image').src = imageUrl;
}

document.addEventListener('DOMContentLoaded', function() {
    updateImage(); // Set initial image
    document.getElementById('location-select').onchange = updateImage; // Update on change
});