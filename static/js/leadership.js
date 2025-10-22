const skillSelect = document.getElementById('skill-select');
const scenarioModal = new bootstrap.Modal(document.getElementById('scenarioModal'));
const scenarioModalLabel = document.getElementById('scenarioModalLabel');
const scenarioDetails = document.getElementById('scenario-details');
const chatBox = document.getElementById('chat-box');
const chatForm = document.getElementById('chat-form');
const textarea = document.getElementById('user-prompt');
const sendButton = document.getElementById('send-button');
const endButton = document.getElementById('end-conversation-button'); // Get the end button
const practiceTextElement = document.getElementById('practice-text'); // Get the paragraph element
const feedbackModal = new bootstrap.Modal(document.getElementById('feedbackModal')); // Get the feedback modal
const feedbackDetails = document.getElementById('feedback-details'); // Get feedback details area

// Store the currently active skill/scenario context
let activeSkill = null;
let chatHistory = []; // To store messages for context

// Define scenarios
const scenarios = {
    "Effective Communication": {
        title: "Difficult Conversation: Employee Performance",
        description: "You are a team lead. You need to have a conversation with John, a junior employee, about his recent poor performance and consistent delays on tasks. Your goal is to address the issue constructively, understand his challenges, and set clear expectations for improvement.",
        persona: "John, a junior employee who is struggling with performance and deadlines.",
        instructions: "Start the conversation as the team lead. Think about how you would initiate this difficult discussion professionally and effectively. The AI will respond as John."
    },
    "Leadership": {
         title: "Team Conflict Resolution",
         description: "Two key members of your team, Sarah and David, are in constant conflict, impacting team morale and productivity. As their leader, you need to mediate the situation, understand both sides, and find a resolution that allows the team to function effectively again.",
         persona: "Sarah and David, two team members in conflict.",
         instructions: "Initiate a meeting or conversation to address the conflict. How would you approach mediating this situation? The AI will respond as both Sarah and David, or switch between their perspectives."
    }
    // Add more scenarios here
};

// Function to create the typing effect
function typeWriter(element, text, delay = 50) {
    let i = 0;
    element.textContent = ''; // Clear existing text
     // Only add typing class if it's the element itself, not a child message
    if (element.id === 'practice-text' || element.classList.contains('chat-message')) {
        element.classList.add('typing'); // Add typing cursor class
    }


    function type() {
        if (i < text.length) {
             // Handle HTML tags if necessary (basic version)
            if (text[i] === '<' && text.substring(i).startsWith('<strong')) {
                 const strongEnd = text.indexOf('>', i);
                 const strongTextStart = strongEnd + 1;
                 const strongTextEnd = text.indexOf('</strong>', strongTextStart);
                 if (strongEnd !== -1 && strongTextEnd !== -1) {
                      const strongTag = text.substring(i, strongEnd + 1);
                      const strongContent = text.substring(strongTextStart, strongTextEnd);
                      const strongEndTag = '</strong>';

                      // Append the <strong> tag structure
                      const tempDiv = document.createElement('div');
                      tempDiv.innerHTML = element.innerHTML + strongTag + strongContent + strongEndTag;
                      element.innerHTML = tempDiv.innerHTML;

                      // Update index to after the closing tag
                      i = strongTextEnd + strongEndTag.length;

                      // Find the latest strong tag in the actual DOM element to potentially type into it
                      // This part gets complicated quickly for complex HTML.
                      // A simpler approach for ratings is to append the rating part, then type the rest.
                      // Let's stick to typing plain text or very simple HTML for now.
                      // If AI response includes HTML, set innerHTML directly.
                      console.warn("Complex HTML detected in typing. Using simple text append.");
                      element.textContent += text.charAt(i); // Fallback to simple append
                      i++;


                 } else {
                     element.textContent += text.charAt(i);
                     i++;
                 }
            } else {
                element.textContent += text.charAt(i);
                i++;
            }

            setTimeout(type, delay);
        } else {
            if (element.id === 'practice-text' || element.classList.contains('chat-message')) {
               element.classList.remove('typing'); // Remove cursor when done
            }
        }
    }

     // If the text contains HTML (like strong tags from AI rating), don't type it
    if (/<[a-z][\s\S]*>/i.test(text)) {
         element.innerHTML = text; // Set innerHTML directly
         if (element.id === 'practice-text' || element.classList.contains('chat-message')) {
            element.classList.remove('typing'); // Ensure no typing class is left
         }
         // Scroll after instant display
         if (element.classList.contains('chat-message')) {
             setTimeout(() => {
                 chatBox.scrollTop = chatBox.scrollHeight;
             }, 50);
         }

    } else {
        // Type plain text
        type();
    }
}

 // Function to display a message in the chat box (modified for initial typing effect)
function displayMessage(message, sender, typeEffect = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', `${sender}-message`);

    if (typeEffect) {
        // Apply typing effect
        chatBox.appendChild(messageElement); // Append first to type into it
        typeWriter(messageElement, message, 30); // Adjust typing speed here (ms per character)
    } else {
        // Display message instantly
         // If message contains HTML (like the AI rating), use innerHTML
         if (/<[a-z][\s\S]*>/i.test(message)) {
              messageElement.innerHTML = message;
         } else {
              messageElement.textContent = message;
         }

        chatBox.appendChild(messageElement);
    }

    // Scroll to the bottom after a small delay to allow typing to start or display
    setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    }, typeEffect ? (message.length * 30 + 100) : 50); // Adjust delay based on message length if typing
}


// Handle skill selection
skillSelect.addEventListener('change', function() {
    activeSkill = this.value;
    chatHistory = []; // Clear chat history when a new skill is selected
    chatBox.innerHTML = ''; // Clear the chat box display

     // Hide End button until a scenario is started
    endButton.style.display = 'none';


    if (activeSkill && scenarios[activeSkill]) {
        const scenario = scenarios[activeSkill];
        scenarioModalLabel.textContent = activeSkill;
        scenarioDetails.innerHTML = `
            <p><strong>Scenario:</strong> ${scenario.description}</p>
            <p><strong>Your Role:</strong> You are the team lead/leader in this scenario.</p>
            <p><strong>AI's Role:</strong> The AI will play the role of "${scenario.persona}".</p>
            <p><strong>How to Start:</strong> ${scenario.instructions}</p>
            <p>The AI will rate your responses before replying.</p>
        `;
        scenarioModal.show();
         // Initial AI message for the scenario - use typing effect
         displayMessage("Okay, let's begin the scenario. You can start whenever you're ready.", "ai", true);

         // Show End button after scenario starts
         endButton.style.display = 'inline-flex'; // or 'block', depending on layout


    } else {
         // Handle case where "Choose a Skill" is selected or skill not found
         activeSkill = null;
         chatBox.innerHTML = ''; // Ensure chat box is clear
         displayMessage("Hello! Select a skill from the dropdown above to begin a leadership scenario.", "ai", true); // Type the initial message
    }
});

// Handle form submission (sending message)
chatForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submit

    const userMessage = textarea.value.trim();

    if (!userMessage) {
        return; // Don't send empty messages
    }

    if (!activeSkill) {
         displayMessage("Please select a skill from the dropdown first.", "ai", false); // Instant display
         textarea.value = '';
         return;
    }

    // Display user message (instantly)
    displayMessage(userMessage, 'user', false); // No typing effect for user messages
    chatHistory.push({ role: 'user', content: userMessage }); // Add to history

    // Clear input and disable
    textarea.value = '';
    textarea.style.height = 'auto'; // Reset height
    sendButton.disabled = true;
    endButton.disabled = true; // Disable end button too
    textarea.disabled = true;

    // Add a temporary AI message element for loading indication
    const loadingMessageElement = document.createElement('div');
    loadingMessageElement.classList.add('chat-message', 'ai-message', 'typing'); // Use typing class for simple loading effect
    loadingMessageElement.textContent = '...';
    chatBox.appendChild(loadingMessageElement);
    chatBox.scrollTop = chatBox.scrollHeight; // Scroll to show loading


    try {
        // Send message to backend
        const response = await fetch('/send-leadership-prompt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_message: userMessage,
                skill: activeSkill,
                history: chatHistory // Send current history
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const aiResponse = data.ai_response; // This is the full AI response including rating and role-play

        // Remove the loading message
         if (chatBox.lastChild === loadingMessageElement) { // Check if it's still the last element
              chatBox.removeChild(loadingMessageElement);
         }


        // Display AI message (instantly for subsequent messages)
        displayMessage(aiResponse, 'ai', false); // No typing effect for subsequent AI messages


        // Update chat history with the AI's response
         if (data.updated_history) {
              chatHistory = data.updated_history;
         } else {
             // Fallback if backend doesn't return full history
             chatHistory.push({ role: 'assistant', content: aiResponse });
         }


    } catch (error) {
        console.error('Error sending message:', error);
        // Remove loading indicator if still there
         if (chatBox.lastChild === loadingMessageElement) {
              chatBox.removeChild(loadingMessageElement);
         }
        displayMessage(`Error: Could not get response from AI. ${error.message}`, 'ai', false); // No typing effect for errors
        chatHistory.push({ role: 'assistant', content: `[Error] ${error.message}` }); // Add error to history
    } finally {
        // Re-enable input
        sendButton.disabled = false;
        endButton.disabled = false; // Re-enable end button
        textarea.disabled = false;
         textarea.focus(); // Put focus back on textarea
    }
});

// Handle End Conversation Button Click
endButton.addEventListener('click', async function() {
     if (!activeSkill || chatHistory.length === 0) {
         displayMessage("No active scenario or conversation to end.", "ai", false);
         return;
     }

     // Disable buttons while processing
     sendButton.disabled = true;
     endButton.disabled = true;
     textarea.disabled = true;

     // Show loading in feedback modal
     feedbackDetails.innerHTML = '<p>Generating feedback...</p>';
     feedbackModal.show();

     try {
         const response = await fetch('/end-leadership-scenario', {
             method: 'POST',
             headers: {
                 'Content-Type': 'application/json'
             },
             body: JSON.stringify({
                 skill: activeSkill,
                 history: chatHistory // Send full history for feedback
             })
         });

         if (!response.ok) {
             throw new Error(`HTTP error! status: ${response.status}`);
         }

         const data = await response.json();
         const feedback = data.feedback;

         // Display feedback in the modal
         feedbackDetails.innerHTML = feedback; // AI should return formatted HTML/Markdown

         // Reset the chat after feedback is shown
         activeSkill = null;
         chatHistory = [];
         chatBox.innerHTML = '';
         skillSelect.value = ''; // Reset dropdown
         endButton.style.display = 'none'; // Hide end button again
         textarea.value = '';
         textarea.style.height = 'auto';

         // Show initial message again
         const initialAIMessage = "Hello! Select a skill from the dropdown above to begin a leadership scenario.";
         setTimeout(() => {
              displayMessage(initialAIMessage, "ai", true);
         }, 500); // Short delay

     } catch (error) {
         console.error('Error ending conversation:', error);
         feedbackDetails.innerHTML = `<p>Error generating feedback: ${error.message}</p>`;
          // Reset the chat even if feedback fails
          activeSkill = null;
          chatHistory = [];
          chatBox.innerHTML = '';
          skillSelect.value = ''; // Reset dropdown
          endButton.style.display = 'none'; // Hide end button again
          textarea.value = '';
          textarea.style.height = 'auto';

          // Show initial message again
         const initialAIMessage = "Hello! Select a skill from the dropdown above to begin a leadership scenario.";
         setTimeout(() => {
              displayMessage(initialAIMessage, "ai", true);
         }, 500); // Short delay

     } finally {
          // Re-enable skill selection and input area after feedback
          sendButton.disabled = false;
          textarea.disabled = false;
          // The end button display is handled by skill selection logic
     }
});


// Optional: Auto-resize the textarea based on content
if (textarea) {
     textarea.addEventListener('input', function() {
         this.style.height = 'auto'; // Reset height to auto
         this.style.height = (this.scrollHeight) + 'px'; // Set height to scroll height
          // Optional: Limit max height to prevent it from getting too big
          const maxHeight = 200; // pixels
          if (this.scrollHeight > maxHeight) {
              this.style.overflowY = 'scroll'; // Enable scrolling
              this.style.height = maxHeight + 'px'; // Set max height
          } else {
              this.style.overflowY = 'hidden'; // Hide scrollbar if not needed
          }
     });
      // Set initial height on page load
      textarea.style.height = 'auto';
      textarea.style.height = (textarea.scrollHeight) + 'px';
      textarea.style.overflowY = 'hidden'; // Hide scrollbar initially

      // Optional: Handle sending message on Enter key (without Shift)
      textarea.addEventListener('keypress', function(event) {
          if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault(); // Prevent default newline
              chatForm.dispatchEvent(new Event('submit')); // Trigger form submit
          }
      });
}

// --- Initial Setup ---
// Hide the End button initially
endButton.style.display = 'none';

// Type the introductory paragraph on page load
const introText = "Practice leadership scenarios with an AI.";
typeWriter(practiceTextElement, introText);

// Display the very first AI message with typing effect after the intro paragraph
// Use a small delay to allow the intro paragraph typing to finish
setTimeout(() => {
     const initialAIMessage = "Hello! Select a skill from the dropdown above to begin a leadership scenario.";
     displayMessage(initialAIMessage, "ai", true); // Use typing effect for the very first message
}, introText.length * 50 + 500); // Delay based on intro text length and a buffer