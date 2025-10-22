        // JavaScript to show the response div if it contains content
        // This function runs after the fade-in animation (or in parallel)
        function handleResponseDisplay() {
            const responseDiv = document.getElementById('aiResponseDiv');
            const rawContentDiv = document.getElementById('rawResponseContent');
            const renderedContentDiv = document.getElementById('renderedResponseContent');

            // Get the JSON string from the hidden div
            const rawJsonString = rawContentDiv.textContent.trim();

            let rawMarkdown = '';
            if (rawJsonString) {
                try {
                    // Parse the JSON string to get the actual markdown string
                    rawMarkdown = JSON.parse(rawJsonString);
                } catch (e) {
                    console.error("Failed to parse AI response JSON:", e);
                    // Set an error message if parsing fails
                    rawMarkdown = "Error: Could not parse the AI response format.";
                     // Display the error message directly if parsing failed
                    renderedContentDiv.innerHTML = "<p style='color: red;'>Error: Could not parse the AI response format. Please try again or contact support.</p>";
                    responseDiv.style.display = 'block'; // Make the div visible to show the error
                    return; // Exit the function as we can't parse/render Markdown
                }
            }

            // Check if we successfully got a markdown string
            if (rawMarkdown && typeof rawMarkdown === 'string' && rawMarkdown.trim() !== '') {
                 // Use Marked.js to convert Markdown to HTML
                 // marked.setOptions({ breaks: true }); // Optional: Add this line if you want single newlines in Markdown to be <br>
                 const renderedHtml = marked.parse(rawMarkdown);

                 // Insert the rendered HTML into the display div
                 renderedContentDiv.innerHTML = renderedHtml;

                 // Make the response div visible
                 responseDiv.style.display = 'block';

                 // Optional: Scroll to the response div
                 responseDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
             // If rawMarkdown is still empty or not a string, the div remains hidden by default CSS
             // Note: The response is removed from the session by the backend
             // using session.pop() when rendering the template, so it only appears once.
        }


        // JavaScript for the sequential fade-in animation
        window.onload = function() {
            // Handle response display when the window finishes loading
            // This runs in parallel with the fade-in animation
            handleResponseDisplay();


            const elementsToAnimate = [];

            // Select the hero div (contains H1 and Lottie)
            const heroElement = document.querySelector('.hero');
            if (heroElement) {
                elementsToAnimate.push(heroElement);
            }

            // Select the main "See" button
            const startButton = document.querySelector('.start');
             if (startButton) {
                elementsToAnimate.push(startButton);
            }

            // You could add other elements here if you wanted them to animate sequentially
            // e.g., const responseDiv = document.getElementById('aiResponseDiv');
            // if (responseDiv) { elementsToAnimate.push(responseDiv); } // But the response div display is handled separately


            let delay = 200; // Initial delay before the first element starts
            const delayIncrease = 300; // Delay added before each subsequent element starts

            elementsToAnimate.forEach(element => {
                // Add 'is-visible' class after the calculated delay
                setTimeout(() => {
                    element.classList.add('is-visible');
                }, delay);
                delay += delayIncrease; // Increase delay for the next element
            });

            // Note: If you wanted the response div to fade in *after* the hero/button animation,
            // you would put handleResponseDisplay() inside the setTimeout of the *last*
            // element in the elementsToAnimate array, with an additional delay.
        };