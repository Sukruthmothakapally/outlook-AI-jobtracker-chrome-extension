document.addEventListener('DOMContentLoaded', function () {
  // Close button functionality to close the popup window
  document.querySelector('.close-btn').addEventListener('click', function() {
    window.close();
  });

  // Back button functionality to show the previous state
  document.querySelector('.back-btn').addEventListener('click', function() {
    const formContainer = document.getElementById('formContainer');
    const showFormButton = document.getElementById('showFormButton');
    const statusDiv = document.getElementById('status');

    formContainer.style.display = 'none';
    showFormButton.style.display = 'block';
    statusDiv.innerHTML = ''; // Clear status message
    loadJobInfo(); // Load job info again
  });

  const showFormButton = document.getElementById('showFormButton');
  const formContainer = document.getElementById('formContainer');
  const statusDiv = document.getElementById('status');

  // Show form and back button when "Applied Company Stats" button is clicked
  showFormButton.addEventListener('click', function() {
    formContainer.style.display = 'block';
    showFormButton.style.display = 'none';
    document.querySelector('.back-btn').style.display = 'inline'; // Show the back button
    statusDiv.innerHTML = ''; // Clear status
  });

  // Back button functionality to show the previous state
  document.querySelector('.back-btn').addEventListener('click', function() {
    formContainer.style.display = 'none';
    showFormButton.style.display = 'block';
    document.querySelector('.back-btn').style.display = 'none'; // Hide the back button
    statusDiv.innerHTML = ''; // Clear status message
    loadJobInfo(); // Load job info again
  });

  // Handle form submission
  const form = document.getElementById('queryForm');
  form.addEventListener('submit', function(event) {
    event.preventDefault();
    const userInput = document.getElementById('userInput').value;
    if (userInput) {
      statusDiv.innerHTML = '<div class="loading">Thinking...</div>';
      
      fetch('http://localhost:8000/get_user_query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userInput }),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        statusDiv.innerHTML = ''; // Clear the "Thinking..." message
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        function readStream() {
          return reader.read().then(({ done, value }) => {
            if (done) {
              return;
            }
            const chunk = decoder.decode(value, { stream: true });
            return typeWriter(chunk).then(readStream);
          });
        }

        return readStream();
      })
      .catch(error => {
        console.error('Error in API call:', error);
        statusDiv.innerHTML = '<div class="no-info">Error in processing the request</div>';
      });
    } else {
      statusDiv.innerHTML = '<div class="no-info">Please enter a query</div>';
    }
  });

  // Function to simulate typing effect
  function typeWriter(text, index = 0) {
    return new Promise(resolve => {
      if (index < text.length) {
        statusDiv.innerHTML += text.charAt(index);
        setTimeout(() => typeWriter(text, index + 1).then(resolve), 20); // Adjust the delay here (20ms)
      } else {
        resolve();
      }
    });
  }

  // Load job info on initial load
  function loadJobInfo() {
    chrome.storage.local.get(['jobInfo'], function (result) {
      if (result.jobInfo && result.jobInfo.message.includes('Applied for')) {
        const jobData = result.jobInfo;
        let tableHTML = `
          <table>
            <tr>
              <th>Company Website</th>
              <th>Job Position</th>
              <th>Applied Date</th>
            </tr>`;
        jobData.applications.forEach(app => {
          tableHTML += `
            <tr>
              <td>${jobData.company_website || 'N/A'}</td>
              <td>${app.job_position}</td>
              <td>${app.applied_date}</td>
            </tr>`;
        });
        tableHTML += '</table>';
        statusDiv.innerHTML = tableHTML;
      } else if (result.jobInfo && result.jobInfo.message.includes('Not yet applied')) {
        statusDiv.innerHTML = `<div class="no-info">Not yet applied to ${result.jobInfo.company_website || 'the company'}</div>`;
      } else {
        statusDiv.innerHTML = `<div class="no-info">No information available</div>`;
      }
    });
  }

  loadJobInfo(); // Call the function to load job info on initial load
});
