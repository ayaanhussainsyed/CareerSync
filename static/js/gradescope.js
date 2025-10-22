        // Three.js setup (Keep your existing Three.js code)
        const canvas = document.getElementById('backgroundCanvas');
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });

        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setClearColor(0x000000, 1); // Set canvas clear color to black

        // Add some basic lighting (optional, but can make lines more visible)
        const ambientLight = new THREE.AmbientLight(0x404040); // soft white light
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight.position.set(1, 1, 1).normalize();
        scene.add(directionalLight);

        // Create the dynamic background geometry
        const numPoints = 2000;
        const positions = new Float32Array(numPoints * 3);
        const colors = new Float32Array(numPoints * 3);

        const geometry = new THREE.BufferGeometry();

        // Black and white color scheme
        const color1 = new THREE.Color(0x1a1a1a); // Dark grey
        const color2 = new THREE.Color(0xf0f0f0); // Light grey

        for (let i = 0; i < numPoints; i++) {
            // Random positions
            positions[i * 3] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 20;

            // Interpolate colors
            const mixedColor = color1.clone().lerp(color2, Math.random());
            colors[i * 3] = mixedColor.r;
            colors[i * 3 + 1] = mixedColor.g;
            colors[i * 3 + 2] = mixedColor.b;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        // Create a material for the points
        const material = new THREE.PointsMaterial({
            size: 0.1,
            vertexColors: true, // Use vertex colors
            transparent: true,
            opacity: 0.8
        });

        // Create the points object and add to the scene
        const points = new THREE.Points(geometry, material);
        scene.add(points);

        // Create lines connecting some points (optional, adds complexity)
        const maxLines = 500;
        const lineGeometry = new THREE.BufferGeometry();
        const linePositions = new Float32Array(maxLines * 2 * 3); // 2 points per line, 3 coords per point
        const lineColors = new Float32Array(maxLines * 2 * 3);

        let lineIndex = 0;
        for (let i = 0; i < numPoints; i += 2) { // Connect every other point
            if (lineIndex >= maxLines * 6) break;

            linePositions[lineIndex++] = positions[i * 3];
            linePositions[lineIndex++] = positions[i * 3 + 1];
            linePositions[lineIndex++] = positions[i * 3 + 2];

            linePositions[lineIndex++] = positions[(i + 1) * 3];
            linePositions[lineIndex++] = positions[(i + 1) * 3 + 1];
            linePositions[lineIndex++] = positions[(i + 1) * 3 + 2];

            // Use the same colors as the points
            lineColors[lineIndex - 6] = colors[i * 3];
            lineColors[lineIndex - 5] = colors[i * 3 + 1];
            lineColors[lineIndex - 4] = colors[i * 3 + 2];

            lineColors[lineIndex - 3] = colors[(i + 1) * 3];
            lineColors[lineIndex - 2] = colors[(i + 1) * 3 + 1];
            lineColors[lineIndex - 1] = colors[(i + 1) * 3 + 2];
        }

        lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        lineGeometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));

        const lineMaterial = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.5
        });

        const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
        scene.add(lines);


        // Set camera position
        camera.position.z = 5;

        // Animation loop
        const animate = function () {
            requestAnimationFrame(animate);

            // Rotate the points and lines
            points.rotation.x += 0.001;
            points.rotation.y += 0.001;
            lines.rotation.x += 0.001;
            lines.rotation.y += 0.001;

            renderer.render(scene, camera);
        };

        // Handle window resizing
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // Start the animation on window load.
        window.onload = function () {
            animate();
        }

        // --- Report Card Upload and Analysis ---
        const uploadButton = document.getElementById('uploadButton');
        const reportCardInput = document.getElementById('reportCardInput');
        const responseArea = document.getElementById('responseArea');
        const voiceSection = document.querySelector('.voice-section'); // Get the voice section div
        const startVoiceInputButton = document.getElementById('startVoiceInput');
        const voiceInputStatus = document.getElementById('voiceInputStatus');
        const customUploadButtonText = document.getElementById('customUploadButtonText'); // Get the label element

        let lastAnalysis = null; // Variable to store the last analysis result

        // Update the custom button text when a file is selected
        reportCardInput.addEventListener('change', () => {
            if (reportCardInput.files.length > 0) {
                customUploadButtonText.innerText = reportCardInput.files[0].name;
            } else {
                customUploadButtonText.innerText = 'Choose Report Card Image';
            }
        });


        uploadButton.addEventListener('click', async () => {
            const file = reportCardInput.files[0];

            if (!file) {
                responseArea.innerText = 'Please select an image file to upload.';
                return;
            }

            responseArea.innerText = 'Analyzing report card...'; // Indicate processing
            voiceSection.style.display = 'none'; // Hide voice input while analyzing

            const formData = new FormData();
            formData.append('report_card', file);

            try {
                const response = await fetch('/upload-reportcard', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                if (result.error) {
                    responseArea.innerText = `Error: ${result.error}`;
                    lastAnalysis = null; // Clear analysis on error
                    voiceSection.style.display = 'none'; // Keep voice input hidden
                } else {
                    responseArea.innerText = result.analysis; // Display the AI analysis
                    lastAnalysis = result.analysis; // Store the analysis
                    voiceSection.style.display = 'flex'; // Show voice input after successful analysis
                }

            } catch (error) {
                console.error('Upload failed:', error);
                responseArea.innerText = `Analysis failed: ${error.message}`;
                lastAnalysis = null; // Clear analysis on error
                voiceSection.style.display = 'none'; // Keep voice input hidden
            }
        });

        // --- Voice Input for Follow-up Questions ---

        // Check for Web Speech API compatibility
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            voiceInputStatus.innerText = 'Voice input not supported in this browser.';
            startVoiceInputButton.disabled = true; // Disable the button
        } else {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();

            recognition.continuous = false; // Stop after a single utterance
            recognition.lang = 'en-US'; // Set language

            recognition.onstart = () => {
                voiceInputStatus.innerText = 'Listening... Speak now.';
                startVoiceInputButton.disabled = true; // Disable button while listening
            };

            recognition.onresult = async (event) => {
                const transcript = event.results[0][0].transcript;
                voiceInputStatus.innerText = `You said: "${transcript}"`;

                // Send the transcribed text as a follow-up question
                await sendFollowUpQuestion(transcript);

                startVoiceInputButton.disabled = false; // Re-enable button
            };

            recognition.onerror = (event) => {
                voiceInputStatus.innerText = `Voice input error: ${event.error}`;
                startVoiceInputButton.disabled = false; // Re-enable button
            };

            recognition.onend = () => {
                if (!voiceInputStatus.innerText.startsWith('You said:')) {
                     voiceInputStatus.innerText = 'Voice input ended.';
                }
                startVoiceInputButton.disabled = false; // Re-enable button
            };

            startVoiceInputButton.addEventListener('click', () => {
                 if (lastAnalysis) { // Only start voice input if there's an analysis
                     recognition.start();
                 } else {
                     voiceInputStatus.innerText = 'Please upload and analyze a report card first.';
                 }
            });

            async function sendFollowUpQuestion(question) {
                responseArea.innerText += '\n\nAsking AI...'; // Indicate processing

                try {
                    const response = await fetch('/ask-followup', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            question: question,
                            analysis_context: lastAnalysis // Send the previous analysis as context
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const result = await response.json();

                    if (result.error) {
                        responseArea.innerText += `\nError: ${result.error}`;
                    } else {
                        responseArea.innerText += `\n\nAI Response: ${result.answer}`; // Display AI's answer
                    }

                } catch (error) {
                    console.error('Follow-up question failed:', error);
                    responseArea.innerText += `\nAnalysis failed: ${error.message}`;
                }
            }
        }
