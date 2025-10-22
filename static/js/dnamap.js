document.getElementById('startAssessmentButton').addEventListener('click', function() {
    const assessmentForm = document.getElementById('assessmentForm');
    assessmentForm.classList.add('visible');
    setTimeout(() => {
        assessmentForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
});

// Set default values for range inputs
document.getElementById('creativityRange').value = 5;
document.getElementById('logicRange').value = 5;
document.getElementById('communicationRange').value = 5;
document.getElementById('leadershipRange').value = 5;
document.getElementById('curiosityRange').value = 5;

// Get the suggested career passed from the backend (if any)
const suggestedCareerFromBackend = "{{ suggested_career if suggested_career is not none else '' }}";
console.log("Suggested career from backend:", suggestedCareerFromBackend);


// JavaScript to show the modal if there's an AI response on page load
window.onload = function() {
    const aiResponseContentDiv = document.getElementById('aiResponseContent');
    // Show modal if there's significant text response OR if a career was explicitly suggested by backend
     // This check ensures the modal opens automatically if the analysis was successful
    if ((aiResponseContentDiv && aiResponseContentDiv.textContent.trim().length > 50) || suggestedCareerFromBackend) {
         var aiModal = new bootstrap.Modal(document.getElementById('aiResponseModal'));
         aiModal.show();
    }
     // The suggested_career variable is now used by the shown.bs.modal handler
     // ai_response is consumed by session.pop() in app.py when the page is rendered
};

// Add event listener for when the modal is fully shown
// This is where we enable/disable the Future You button based on the career
var aiResponseModal = document.getElementById('aiResponseModal');
aiResponseModal.addEventListener('shown.bs.modal', function () {
    const futureYouButton = document.getElementById('futureYouButton');

    if (futureYouButton) { // Ensure button exists
        // Check if a career was successfully extracted and passed from the backend
        if (suggestedCareerFromBackend) {
            console.log("Setting Future You button with backend career:", suggestedCareerFromBackend);
            futureYouButton.dataset.career = suggestedCareerFromBackend; // Store the reliable career
            futureYouButton.disabled = false; // Enable the button
            futureYouButton.innerText = 'Future You'; // Reset button text
        } else {
            console.warn("No reliable career found from backend. Future You button disabled.");
            futureYouButton.dataset.career = ''; // Clear any old data
            futureYouButton.disabled = true; // Keep button disabled
            futureYouButton.innerText = 'Future You (Career Not Found)'; // Update button text
        }
    } else {
         console.error("Future You button not found in the modal.");
    }
    // Client-side text parsing is no longer needed or attempted here
});

// Add event listener to the Future You button for form submission
document.getElementById('futureYouButton').addEventListener('click', function() {
    const career = this.dataset.career; // Get the career from the data attribute (set by shown.bs.modal)

    if (career && career !== 'Career Not Found') { // Ensure career is present and not the fallback text
        // Create a hidden form element dynamically
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/envision-career'; // Target the existing endpoint for envisioning
        form.style.display = 'none'; // Hide the form

        // Create an input field for the career and set its value
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'career'; // Match the expected form field name in app.py
        input.value = career;

        // Append the input to the form
        form.appendChild(input);

        // Append the form to the document body and submit it
        document.body.appendChild(form);
        form.submit();

    } else {
        console.error("No valid career data found on the Future You button. Submission prevented.");
        alert("Could not determine the career to envision. Please close the modal and try the DNA Mapping analysis again.");
    }
});

// Particle effect script (keep existing)
const canvas = document.getElementById('particle-canvas');
const ctx = canvas.getContext('2d');

let particles = [];
const particleCount = 250;
const maxRadius = 1.2;
const maxOrbit = 15;
const animationSpeed = 0.005;

function Particle(x, y) {
    this.x = x;
    this.y = y;
    this.initialX = x;
    this.initialY = y;
    this.radius = Math.random() * maxRadius;
    this.angle = Math.random() * Math.PI * 2;
    this.orbitRadius = Math.random() * maxOrbit;
    this.color = 'rgba(255, 255, 255, ' + (0.3 + Math.random() * 0.5) + ')';
}

Particle.prototype.draw = function() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
    ctx.fillStyle = this.color;
    ctx.fill();
};

Particle.prototype.update = function() {
    this.angle += animationSpeed;
    this.x = this.initialX + Math.cos(this.angle) * this.orbitRadius;
    this.y = this.initialY + Math.sin(this.angle) * this.orbitRadius;
};

function init() {
    particles = [];
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    for (let i = 0; i < particleCount; i++) {
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height;
        particles.push(new Particle(x, y));
    }
}

function animate() {
    requestAnimationFrame(animate);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(particle => {
        particle.update();
        particle.draw();
    });
}

window.addEventListener('resize', init);
init();
animate();