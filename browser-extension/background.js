const API_BASE = "http://127.0.0.1:8000/api/extension";
const POLL_INTERVAL_MS = 2500;
const HEARTBEAT_INTERVAL_MS = 5000;

async function getExtensionId() {
  const stored = await chrome.storage.local.get("extensionId");
  if (stored.extensionId) return stored.extensionId;
  const extensionId = crypto.randomUUID();
  await chrome.storage.local.set({ extensionId });
  return extensionId;
}

async function api(path, init = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function activeBossTab() {
  const tabs = await chrome.tabs.query({ url: "https://www.zhipin.com/*" });
  const candidates = tabs.filter((tab) => tab.id && tab.url?.startsWith("https://www.zhipin.com/"));
  return candidates.sort((left, right) => {
    if (left.active !== right.active) return left.active ? -1 : 1;
    return Number(right.lastAccessed || 0) - Number(left.lastAccessed || 0);
  })[0] || null;
}

function sendToTab(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) reject(new Error(error.message));
      else resolve(response);
    });
  });
}

async function heartbeat() {
  const extensionId = await getExtensionId();
  const tab = await activeBossTab();
  let page = { page_url: null, page_title: null, page_type: "unsupported" };
  if (tab) {
    try {
      page = await sendToTab(tab.id, { type: "page_status" });
    } catch {
      page = { page_url: tab.url, page_title: tab.title, page_type: "unsupported" };
    }
  }
  await api("/heartbeat", {
    method: "POST",
    body: JSON.stringify({
      extension_id: extensionId,
      status: tab ? "online" : "unsupported_page",
      ...page,
      metadata: { version: chrome.runtime.getManifest().version }
    })
  });
}

function filenameFromUrl(url) {
  try {
    const name = decodeURIComponent(new URL(url).pathname.split("/").pop() || "boss-resume.pdf");
    return name.toLowerCase().endsWith(".pdf") ? name : "boss-resume.pdf";
  } catch {
    return "boss-resume.pdf";
  }
}

async function uploadAttachments(candidateId, jobId, urls) {
  for (const url of urls) {
    try {
      const response = await fetch(url, { credentials: "include" });
      const bytes = await response.arrayBuffer();
      if (!response.ok || bytes.byteLength < 4) continue;
      const header = new TextDecoder().decode(bytes.slice(0, 4));
      if (header !== "%PDF") continue;
      const formData = new FormData();
      formData.append("file", new File([bytes], filenameFromUrl(url), { type: "application/pdf" }));
      const query = jobId ? `?job_id=${jobId}` : "";
      await fetch(`http://127.0.0.1:8000/api/candidates/${candidateId}/resumes${query}`, {
        method: "POST",
        body: formData
      });
    } catch {
      // The dashboard keeps the detected attachment for manual review when a protected URL cannot be fetched.
    }
  }
}

async function poll() {
  const extensionId = await getExtensionId();
  const command = await api(`/commands/next?extension_id=${encodeURIComponent(extensionId)}`);
  if (!command) return;
  const tab = await activeBossTab();
  if (!tab) {
    await api(`/commands/${command.id}/fail`, {
      method: "POST",
      body: JSON.stringify({
        extension_id: extensionId,
        error_message: "请先在当前 Chrome 窗口打开已登录的 BOSS 直聘页面"
      })
    });
    return;
  }
  try {
    const response = await sendToTab(tab.id, { type: "run_command", command });
    if (!response?.ok) throw new Error(response?.error || "页面采集失败");
    const completed = await api(`/commands/${command.id}/complete`, {
      method: "POST",
      body: JSON.stringify({ extension_id: extensionId, result: response.result })
    });
    if (completed.candidate_id && completed.attachment_urls?.length) {
      await uploadAttachments(
        completed.candidate_id,
        command.payload?.job_id,
        completed.attachment_urls
      );
    }
  } catch (error) {
    await api(`/commands/${command.id}/fail`, {
      method: "POST",
      body: JSON.stringify({
        extension_id: extensionId,
        error_message: error instanceof Error ? error.message : String(error)
      })
    }).catch(() => null);
  }
}

async function runSafely(task) {
  try {
    await task();
  } catch {
    // The popup and dashboard surface connection failures; the worker keeps retrying.
  }
}

setInterval(() => runSafely(heartbeat), HEARTBEAT_INTERVAL_MS);
setInterval(() => runSafely(poll), POLL_INTERVAL_MS);
chrome.runtime.onInstalled.addListener(() => runSafely(heartbeat));
chrome.runtime.onStartup.addListener(() => runSafely(heartbeat));
chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "content_tick") {
    runSafely(async () => {
      await heartbeat();
      await poll();
    });
  }
});
runSafely(heartbeat);
