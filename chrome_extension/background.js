chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    checkCompanyWebsite(tab.url);
  }
});

function checkCompanyWebsite(url) {
  // Extract domain without the 'www.' prefix
  const domain = new URL(url).hostname.replace(/^www\./, '');
  console.log(`Checking domain: ${domain}`);

  fetch('http://localhost:8000/check-url', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ url: domain })
  })
    .then(response => response.json())
    .then(data => {
      console.log("Received API response: ", data);
      chrome.storage.local.set({ jobInfo: data });

      // Automatically open popup if the response contains "Applied for"
      if (data.message && data.message.includes('Applied for')) {
        console.log("Match found, opening popup.");
        chrome.action.openPopup();
      } else {
        console.log("No match found.");
      }
    })
    .catch(error => console.error('Error in API call:', error));
}
