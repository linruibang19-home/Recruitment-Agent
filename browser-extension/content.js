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

  function detailMatchesSummary(detail, summary) {
    const name = String(detail?.candidate_name || "").trim();
    const summaryName = String(summary?.name || "").trim();
    if (!summaryName || !name) return true;
    return name.includes(summaryName) || summaryName.includes(name);
  }

  async function openChatAndRead(summary, delayMs, retries = 2) {
    let detail = null;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      if (!extractors.clickChatByIndex(Number(summary.index))) {
        return { ok: false, detail: null, reason: "click_failed" };
      }
      await sleep(delayMs + attempt * 300);
      detail = extractors.extractChatDetail();
      const hasContent = Boolean(detail?.candidate_name || detail?.messages?.length || detail?.attachments?.length);
      if (hasContent && detailMatchesSummary(detail, summary)) {
        return { ok: true, detail, reason: null };
      }
    }
    return { ok: Boolean(detail), detail, reason: "detail_not_stable" };
  }

  async function collectChatTargets(limit, onlyUnread) {
    const seen = new Set();
    const targets = [];
    const snapshots = [];
    for (let round = 0; round < 4 && targets.length < limit; round += 1) {
      const conversations = extractors.extractChatSummaries(Math.max(limit * 2, limit, 20));
      snapshots.push({ round, read_count: conversations.length, target_count: targets.length });
      for (const item of conversations) {
        const key = `${item.href || ""}|${item.name || ""}|${item.raw_text || ""}`.slice(0, 260);
        if (seen.has(key)) continue;
        seen.add(key);
        if (onlyUnread && !item.has_unread && Number(item.unread_count || 0) <= 0) continue;
        targets.push(item);
        if (targets.length >= limit) break;
      }
      if (targets.length >= limit) break;
      const moved = extractors.scrollChatList?.("down");
      await sleep(350);
      if (!moved?.moved) break;
    }
    return { targets: targets.slice(0, limit), snapshots };
  }

  function traceEntry(summary) {
    return {
      candidate_name: summary?.name || null,
      summary,
      steps: [],
      status: "running"
    };
  }

  function addTrace(trace, step, status, detail = {}) {
    trace.steps.push({
      step,
      status,
      at: new Date().toISOString(),
      ...detail
    });
  }

  async function scanChatDetails(limit, delayMs) {
    const conversations = extractors.extractChatSummaries(limit);
    const details = [];
    const failures = [];
    for (let index = 0; index < conversations.length; index += 1) {
      const summary = conversations[index];
      const opened = await openChatAndRead(summary, delayMs);
      if (!opened.ok || !opened.detail) {
        failures.push({
          summary,
          reason: opened.reason || "open_failed",
          message: "未能稳定读取候选人聊天详情"
        });
        continue;
      }
      const detail = opened.detail;
      if (detail.attachments?.length) {
        detail.attachments = await extractors.enrichAttachmentPreviews(detail.attachments, Math.max(500, delayMs));
      }
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
      details,
      failures
    };
  }

  async function requestResumesBatch(command, limit, delayMs) {
    const message = String(
      command.payload?.message || "方便发一份你的简历过来吗？"
    );
    const onlyUnread = command.payload?.only_unread !== false;
    const { targets, snapshots } = await collectChatTargets(limit, onlyUnread);
    const details = [];
    const failures = [];
    const executionTrace = [];
    let sentCount = 0;
    let skippedWithResume = 0;
    let skippedAlreadyRequested = 0;
    let failedCount = 0;

    for (const summary of targets) {
      const trace = traceEntry(summary);
      executionTrace.push(trace);
      addTrace(trace, "pause_control", "ok");
      const control = await waitWhilePaused(command.id);
      if (control === "stopped") {
        addTrace(trace, "pause_control", "stopped");
        trace.status = "stopped";
        return {
          page_url: location.href,
          conversations: targets,
          details,
          failures,
          execution_trace: executionTrace,
          target_snapshots: snapshots,
          sent_count: sentCount,
          skipped_with_resume: skippedWithResume,
          skipped_already_requested: skippedAlreadyRequested,
          failed_count: failedCount,
          stopped: true
        };
      }
      const opened = await openChatAndRead(summary, delayMs);
      if (!opened.ok || !opened.detail) {
        failedCount += 1;
        addTrace(trace, "open_chat", "failed", { reason: opened.reason || "click_failed" });
        trace.status = "failed";
        failures.push({
          summary,
          reason: opened.reason || "click_failed",
          message: "未能稳定打开并读取候选人会话"
        });
        continue;
      }
      addTrace(trace, "open_chat", "ok");
      const detail = opened.detail;
      if (detail.attachments?.length) {
        detail.attachments = await extractors.enrichAttachmentPreviews(detail.attachments, Math.max(500, delayMs));
        addTrace(trace, "preview_resume", "ok", { attachment_count: detail.attachments.length });
      }
      const hasResume = Boolean(detail.attachments?.length);
      const alreadyRequested = extractors.hasResumeRequestHistory(detail, message);
      let requestResult = { sent: false, method: "skipped" };
      if (hasResume) {
        skippedWithResume += 1;
        requestResult = { sent: false, method: "skipped_with_resume" };
        addTrace(trace, "request_resume", "skipped", { reason: "resume_exists" });
        trace.status = "skipped_with_resume";
      } else if (alreadyRequested) {
        skippedAlreadyRequested += 1;
        requestResult = { sent: false, method: "skipped_already_requested" };
        addTrace(trace, "request_resume", "skipped", { reason: "already_requested" });
        trace.status = "skipped_already_requested";
      } else {
        requestResult = await extractors.sendResumeRequest(message);
        if (requestResult.sent) {
          await sleep(Math.max(350, Math.floor(delayMs / 2)));
          const verifyDetail = extractors.extractChatDetail();
          const verified = extractors.hasResumeRequestHistory(verifyDetail, message);
          sentCount += 1;
          detail.messages = [
            ...(detail.messages || []),
            { content: message, direction: "out", time: new Date().toISOString() }
          ];
          addTrace(trace, "request_resume", verified ? "ok" : "sent_unverified", {
            method: requestResult.method,
            verified
          });
          trace.status = verified ? "sent" : "sent_unverified";
        } else {
          failedCount += 1;
          addTrace(trace, "request_resume", "failed", {
            method: requestResult.method,
            error: requestResult.error || "索要简历话术发送失败"
          });
          trace.status = "failed";
          failures.push({
            summary,
            reason: requestResult.method || "send_failed",
            message: requestResult.error || "索要简历话术发送失败"
          });
        }
      }
      details.push({
        ...detail,
        candidate_name: detail.candidate_name || summary.name,
        summary,
        collected_index: summary.index,
        resume_request_sent: Boolean(requestResult.sent),
        resume_request_already_exists: alreadyRequested,
        request_result: requestResult
      });
      await sleep(delayMs);
    }
    return {
      page_url: location.href,
      conversations: targets,
      details,
      failures,
      execution_trace: executionTrace,
      target_snapshots: snapshots,
      summary: {
        target_count: targets.length,
        sent_count: sentCount,
        skipped_with_resume: skippedWithResume,
        skipped_already_requested: skippedAlreadyRequested,
        failed_count: failedCount
      },
      sent_count: sentCount,
      skipped_with_resume: skippedWithResume,
      skipped_already_requested: skippedAlreadyRequested,
      failed_count: failedCount,
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
