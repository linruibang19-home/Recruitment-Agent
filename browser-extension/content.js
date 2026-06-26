(function initContentBridge() {
  const extractors = window.RecruitmentExtractors;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const API_BASE = "http://127.0.0.1:8000/api/extension";

  async function commandControl(commandId) {
    try {
      const response = await fetch(`${API_BASE}/commands/${commandId}/control`);
      if (!response.ok) return { control: "running" };
      return response.json();
    } catch {
      return { control: "running" };
    }
  }

  async function waitWhilePaused(commandId) {
    while (true) {
      const state = await commandControl(commandId);
      if (state.control === "stopped") return "stopped";
      if (state.control !== "paused") return "running";
      await sleep(1200);
    }
  }

  async function scanChatDetails(limit, delayMs) {
    const conversations = extractors.extractChatSummaries(limit);
    const details = [];
    for (let index = 0; index < conversations.length; index += 1) {
      const summary = conversations[index];
      if (!extractors.clickChatByIndex(index)) continue;
      await sleep(delayMs);
      const detail = extractors.extractChatDetail();
      details.push({
        ...detail,
        candidate_name: detail.candidate_name || summary.name,
        summary,
        collected_index: index
      });
    }
    return {
      page_url: location.href,
      conversations,
      details
    };
  }

  async function requestResumesBatch(command, limit, delayMs) {
    const message = String(
      command.payload?.message || "方便发一份你的简历过来吗？"
    );
    const onlyUnread = command.payload?.only_unread !== false;
    const conversations = extractors.extractChatSummaries(Math.max(limit * 2, limit));
    const targets = conversations
      .filter((item) => !onlyUnread || item.has_unread || Number(item.unread_count || 0) > 0)
      .slice(0, limit);
    const details = [];
    let sentCount = 0;
    let skippedWithResume = 0;

    for (const summary of targets) {
      const control = await waitWhilePaused(command.id);
      if (control === "stopped") {
        return {
          page_url: location.href,
          conversations: targets,
          details,
          sent_count: sentCount,
          skipped_with_resume: skippedWithResume,
          stopped: true
        };
      }
      if (!extractors.clickChatByIndex(Number(summary.index))) continue;
      await sleep(delayMs);
      const detail = extractors.extractChatDetail();
      const hasResume = Boolean(detail.attachments?.length);
      let requestResult = { sent: false, method: "skipped" };
      if (hasResume) {
        skippedWithResume += 1;
      } else {
        requestResult = await extractors.sendResumeRequest(message);
        if (requestResult.sent) {
          sentCount += 1;
          detail.messages = [
            ...(detail.messages || []),
            { content: message, direction: "out", time: new Date().toISOString() }
          ];
        }
      }
      details.push({
        ...detail,
        candidate_name: detail.candidate_name || summary.name,
        summary,
        collected_index: summary.index,
        resume_request_sent: Boolean(requestResult.sent),
        request_result: requestResult
      });
      await sleep(delayMs);
    }
    return {
      page_url: location.href,
      conversations: targets,
      details,
      sent_count: sentCount,
      skipped_with_resume: skippedWithResume,
      stopped: false
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "page_status") {
      sendResponse({
        page_url: location.href,
        page_title: document.title,
        page_type: extractors.pageType()
      });
      return false;
    }
    if (message?.type !== "run_command") return false;

    (async () => {
      const command = message.command;
      const limit = Number(command.payload?.limit || 30);
      const delayMs = Number(command.payload?.delay_ms || 1400);
      let result;
      if (command.command_type === "scan_chats") {
        result = {
          page_url: location.href,
          conversations: extractors.extractChatSummaries(limit)
        };
      } else if (command.command_type === "scan_chat_details") {
        result = await scanChatDetails(limit, delayMs);
      } else if (command.command_type === "request_resumes_batch") {
        result = await requestResumesBatch(command, limit, delayMs);
      } else if (command.command_type === "read_current_chat") {
        result = {
          page_url: location.href,
          conversations: [],
          detail: extractors.extractChatDetail()
        };
      } else if (command.command_type === "scan_talents") {
        result = {
          page_url: location.href,
          cards: extractors.extractTalentCards(limit)
        };
      } else {
        throw new Error(`不支持的任务类型：${command.command_type}`);
      }
      sendResponse({ ok: true, result });
    })().catch((error) => {
      sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) });
    });
    return true;
  });

  setInterval(() => {
    chrome.runtime.sendMessage({ type: "content_tick" }).catch(() => null);
  }, 2500);
})();
