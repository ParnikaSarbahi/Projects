function openDashboard() {
  chrome.tabs.create({ url: chrome.runtime.getURL("pages/dashboard.html") });
}
document.getElementById("btn-dashboard").addEventListener("click", function(e) {
  e.preventDefault(); openDashboard();
});
document.getElementById("btn-dashboard-footer").addEventListener("click", function(e) {
  e.preventDefault(); openDashboard();
});