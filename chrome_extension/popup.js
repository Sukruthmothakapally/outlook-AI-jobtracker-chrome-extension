document.addEventListener('DOMContentLoaded', function () {
  // Close button functionality to close the popup window
  document.querySelector('.close-btn').addEventListener('click', function() {
    window.close();
  });

  chrome.storage.local.get(['jobInfo'], function (result) {
    const statusDiv = document.getElementById('status');
    
    if (result.jobInfo && result.jobInfo.message.includes('Applied for')) {
      const jobData = result.jobInfo;

      // Generate a table for all applications
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

      // Set the HTML content
      statusDiv.innerHTML = tableHTML;
    } else if (result.jobInfo && result.jobInfo.message.includes('Not yet applied')) {
      const companyWebsite = result.jobInfo.company_website || 'the company';
      statusDiv.innerHTML = `<div class="no-info">Not yet applied to ${companyWebsite}</div>`;
    } else {
      statusDiv.innerHTML = `<div class="no-info">No information available</div>`;
    }
  });
});
