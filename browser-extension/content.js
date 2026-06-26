(function initContentBridge() {
  const extractors = window.RecruitmentExtractors;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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
