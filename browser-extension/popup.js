async function refreshStatus() {
  const status = document.querySelector("#status");
  const detail = document.querySelector("#detail");
  const dot = document.querySelector("#dot");
  try {
    const response = await fetch("http://127.0.0.1:8000/api/extension/status");
    if (!response.ok) throw new Error("后端未启动");
    const data = await response.json();
    status.textContent = data.connected ? "扩展已连接" : "等待 BOSS 页面";
    detail.textContent = data.page_title || "请打开并登录 BOSS 直聘";
    dot.className = `dot ${data.connected ? "online" : "offline"}`;
  } catch {
    status.textContent = "本地后端未连接";
    detail.textContent = "请先运行 scripts/start.ps1";
    dot.className = "dot offline";
  }
}

document.querySelector("#dashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:5173" });
});

refreshStatus();
