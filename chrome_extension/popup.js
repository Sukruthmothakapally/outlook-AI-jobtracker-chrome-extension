document.addEventListener('DOMContentLoaded', function () {
    // Previous button handlers remain the same
    document.querySelector('.close-btn').addEventListener('click', function() {
        window.close();
    });

    const showFormButton = document.getElementById('showFormButton');
    const formContainer = document.getElementById('formContainer');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('resultDiv');

    // Function to clear previous output
    function clearOutput() {
        resultDiv.innerHTML = ''; // Clear the output container
        statusDiv.innerHTML = ''; // Clear any status messages
    }

    document.querySelector('.back-btn').addEventListener('click', function() {
        formContainer.style.display = 'none';
        showFormButton.style.display = 'block';
        clearOutput(); // Clear output when going back
        loadJobInfo();
    });

    showFormButton.addEventListener('click', function() {
        formContainer.style.display = 'block'; // Show the input form on button click
        showFormButton.style.display = 'none'; // Hide the button
        document.querySelector('.back-btn').style.display = 'inline'; // Show back button
        clearOutput(); // Clear output when showing the form
    });

    // Updated form submission handler
    const form = document.getElementById('queryForm');

    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        const userInput = document.getElementById('userInput').value;

        if (userInput) {
            clearOutput(); // Clear previous output immediately

            try {
                // Create and display the loading logo
                statusDiv.innerHTML = '<div class="loading"><img src="batman_logo.png" alt="Loading..."></div>';
                
                const response = await fetch('http://54.183.74.135:8000/get_user_query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: userInput }),
                });

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                // Get the response data
                const arrayBuffer = await response.arrayBuffer();
                const contentType = response.headers.get('content-type');

                statusDiv.innerHTML = ''; // Clear status before displaying new content

                if (contentType && contentType.includes('image')) {
                    // Convert array buffer to base64 for image
                    const base64String = btoa(
                        new Uint8Array(arrayBuffer)
                            .reduce((data, byte) => data + String.fromCharCode(byte), '')
                    );

                    // Display the image
                    const img = document.createElement('img');
                    img.src = `data:${contentType};base64,${base64String}`;
                    img.alt = "Generated Chart";
                    img.style.maxWidth = "100%";
                    img.style.height = "auto";
                    img.style.marginTop = "20px";
                    img.style.borderRadius = "8px";
                    img.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.1)";

                    resultDiv.appendChild(img);
                    resultDiv.style.display = "block";
                    resultDiv.style.marginTop = "20px";
                    resultDiv.style.textAlign = "center";
                } else if (contentType && contentType.includes('application/json')) {
                    // Handle JSON response
                    const textDecoder = new TextDecoder('utf-8');
                    const jsonString = textDecoder.decode(arrayBuffer);
                    const data = JSON.parse(jsonString);

                    const table = document.createElement('table');

                    // Create table headers
                    const headers = Object.keys(data[0]);
                    const headerRow = document.createElement('tr');
                    headers.forEach(header => {
                        const th = document.createElement('th');
                        th.textContent = header;
                        headerRow.appendChild(th);
                    });
                    table.appendChild(headerRow);

                    // Create table rows
                    data.forEach(row => {
                        const tableRow = document.createElement('tr');
                        headers.forEach(header => {
                            const td = document.createElement('td');
                            td.textContent = row[header];
                            tableRow.appendChild(td);
                        });
                        table.appendChild(tableRow);
                    });

                    resultDiv.appendChild(table);
                } else if (contentType && contentType.includes('text/plain')) {
                    // Handle plain text response with typewriter effect
                    const textDecoder = new TextDecoder('utf-8');
                    const text = textDecoder.decode(arrayBuffer);

                    // Create the response box container first
                    const responseBox = document.createElement('div');
                    responseBox.style.backgroundColor = '#000000';
                    responseBox.style.border = '2px solid #333333';
                    responseBox.style.borderRadius = '8px';
                    responseBox.style.padding = '20px';
                    responseBox.style.marginTop = '20px';
                    responseBox.style.width = 'fit-content';
                    responseBox.style.maxWidth = '100%';
                    responseBox.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
                    statusDiv.appendChild(responseBox);

                    // Use typeWriter function to display text in typing effect
                    await typeWriter(text, responseBox);
                } else {
                    // Fallback in case of unrecognized content type
                    statusDiv.innerHTML = '<div class="no-info">Unexpected response type</div>';
                }
            } catch (error) {
                console.error('Error in API call:', error);
                statusDiv.innerHTML = '<div class="no-info">Error in processing the request</div>';
            }
        } else {
            statusDiv.innerHTML = '<div class="no-info">Please enter a query</div>';
        }
    });

    function typeWriter(text, container, index = 0, processedText = null) {
        return new Promise(resolve => {
            // Process text only on first run
            if (index === 0) {
                // Create text element with proper styling
                const textElement = document.createElement('div');
                textElement.style.color = '#ffffff';
                textElement.style.fontSize = '16px';
                textElement.style.fontFamily = 'Arial, sans-serif';
                textElement.style.lineHeight = '1.5';
                textElement.style.whiteSpace = 'pre-wrap';
                textElement.style.wordBreak = 'keep-all';
                textElement.id = 'typewriter-text';
                container.appendChild(textElement);
    
                // Process text for line breaks
                const words = text.split(' ');
                let currentLine = '';
                processedText = '';
    
                words.forEach((word, i) => {
                    if (currentLine.length + word.length + 1 <= 80) {
                        currentLine += (currentLine.length === 0 ? '' : ' ') + word;
                    } else {
                        processedText += currentLine + '\n';
                        currentLine = word;
                    }
                    
                    if (i === words.length - 1) {
                        processedText += currentLine;
                    }
                });
            }
    
            if (index < processedText.length) {
                const textElement = container.querySelector('#typewriter-text');
                const currentChar = processedText.charAt(index);
                
                textElement.textContent += currentChar;
                
                setTimeout(() => {
                    typeWriter(text, container, index + 1, processedText).then(resolve);
                }, 20);
            } else {
                resolve();
            }
        });
    }

    // LoadJobInfo function remains the same
    function loadJobInfo() {
        chrome.storage.local.get(['jobInfo'], function (result) {
            if (result.jobInfo) {
                const jobData = result.jobInfo;
                if (jobData.message.includes('Applied for')) {
                    let tableHTML = `
                      <table>
                        <tr>
                          <th>Company Website</th>
                          <th>Job Position</th>
                          <th>Applied Date</th>
                          <th>Application Status</th>
                        </tr>`;
                    
                    jobData.applications.forEach(app => {
                        tableHTML += `
                          <tr>
                            <td>${jobData.company_website || 'N/A'}</td>
                            <td>${app.job_position}</td>
                            <td>${app.applied_date}</td>
                            <td>${app.application_status}</td>
                          </tr>`;
                    });
                    tableHTML += '</table>';
                    statusDiv.innerHTML = tableHTML;
                } else if (jobData.message.includes('Not yet applied')) {
                    statusDiv.innerHTML = `<div class="no-info">Not yet applied to ${jobData.company_website || 'the company'}</div>`;
                } else {
                    statusDiv.innerHTML = `<div class="no-info">No information available</div>`;
                }
            } else {
                statusDiv.innerHTML = `<div class="no-info">No job information found</div>`;
            }
        });
    }

    loadJobInfo();
});