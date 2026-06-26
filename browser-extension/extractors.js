(function initRecruitmentExtractors(globalScope) {
  const CHAT_ITEM_SELECTORS = [
    ".user-list .user-item",
    ".chat-list .chat-item",
    ".chat-list .friend-item",
    ".friend-list .friend-item",
    "[class*='chat-list'] [class*='item']",
    "[data-recruitment-agent-chat-item]"
  ];
  const MESSAGE_SELECTORS = [
    ".chat-message",
    ".message-item",
    "[class*='message-item']",
    "[data-recruitment-agent-message]"
  ];
  const ATTACHMENT_SELECTORS = [
    "a[href*='.pdf']",
    "[class*='attachment']",
    "[class*='resume']",
    "[class*='file-card']",
    "[data-recruitment-agent-attachment]"
  ];
  const TALENT_CARD_SELECTORS = [
    "[data-recruitment-agent-talent-card]",
    ".recommend-list .candidate-card",
    ".recommend-list .recommend-card",
    ".recommend-card",
    "[class*='recommend-list'] [class*='card']",
    "[class*='geek-card']"
  ];
  const SKILLS = [
    "Python", "Java", "C++", "Go", "JavaScript", "TypeScript", "React", "Vue",
    "Spring", "SpringBoot", "FastAPI", "Django", "MySQL", "PostgreSQL", "Redis",
    "Docker", "Kubernetes", "Linux", "PyTorch", "TensorFlow", "LangChain",
    "LangGraph", "RAG", "LLM", "NLP", "OCR", "机器学习", "深度学习", "数据分析"
  ];

  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function firstMatchingElements(selectors) {
    for (const selector of selectors) {
      const elements = Array.from(document.querySelectorAll(selector));
      if (elements.length) return elements;
    }
    return [];
  }

  function visibleRect(element) {
    const rect = element.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return null;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
      return null;
    }
    return rect;
  }

  function isNestedDuplicate(element, elements) {
    return elements.some((other) => {
      if (other === element || !other.contains(element)) return false;
      const outer = visibleRect(other);
      const inner = visibleRect(element);
      if (!outer || !inner) return false;
      return Math.abs(outer.width - inner.width) < 12 && Math.abs(outer.height - inner.height) < 12;
    });
  }

  function fallbackChatItems() {
    const all = Array.from(document.querySelectorAll("li, div, a, button"));
    const candidates = all.filter((element) => {
      const rect = visibleRect(element);
      if (!rect) return false;
      const text = normalizeText(element.textContent);
      if (text.length < 8 || text.length > 220) return false;
      if (/(全部职位|全部 未读|未选中联系人|暂无牛人|在线简历|附件简历|招聘规范)/.test(text)) {
        return false;
      }
      const inLeftPane = rect.left > 180
        && rect.left < window.innerWidth * 0.52
        && rect.top > 140
        && rect.width >= 220
        && rect.width <= 560
        && rect.height >= 48
        && rect.height <= 140;
      if (!inLeftPane) return false;
      return /(\d{2}:\d{2}|昨天|前天|Agent|实习生|求职者|您好|Boss)/.test(text);
    });
    return candidates
      .filter((element) => !isNestedDuplicate(element, candidates))
      .sort((left, right) => left.getBoundingClientRect().top - right.getBoundingClientRect().top);
  }

  function chatItems() {
    const matched = firstMatchingElements(CHAT_ITEM_SELECTORS);
    return matched.length ? matched : fallbackChatItems();
  }

  function childText(element, selectors) {
    for (const selector of selectors) {
      const child = element.querySelector(selector);
      const value = normalizeText(child?.textContent);
      if (value) return value;
    }
    return null;
  }

  function absoluteHref(element) {
    const anchor = element.matches("a") ? element : element.querySelector("a");
    const href = anchor?.getAttribute("href");
    if (!href) return null;
    try {
      const baseUrl = location.protocol === "http:" || location.protocol === "https:"
        ? location.href
        : "https://www.zhipin.com/";
      return new URL(href, baseUrl).href;
    } catch {
      return href;
    }
  }

  function stableUid(href, text) {
    if (href) {
      try {
        const baseUrl = location.protocol === "http:" || location.protocol === "https:"
          ? location.href
          : "https://www.zhipin.com/";
        const url = new URL(href, baseUrl);
        for (const key of ["uid", "geekId", "encryptGeekId", "id"]) {
          const value = url.searchParams.get(key);
          if (value) return value;
        }
        const tail = url.pathname.split("/").filter(Boolean).pop();
        if (tail && !["recommend", "geek"].includes(tail)) return tail;
      } catch {
        // Fall through to the deterministic text hash.
      }
    }
    let hash = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return `card-${(hash >>> 0).toString(16)}`;
  }

  function pageType() {
    if (location.pathname.includes("/web/chat/recommend")) return "talents";
    if (location.pathname.includes("/web/chat")) return "chat";
    return "unsupported";
  }

  function extractChatSummaries(limit = 30) {
    return chatItems().slice(0, limit).flatMap((item, index) => {
      const rawText = normalizeText(item.textContent);
      if (!rawText) return [];
      const unreadText = childText(item, [".badge", ".unread", "[class*='unread']"]) || "";
      const hasUnreadMarker = Boolean(item.querySelector(".badge, .unread, [class*='unread']"))
        || /(^|\D)[1-9]\d?($|\D)/.test(unreadText)
        || Array.from(item.querySelectorAll("*")).some((child) => {
          const rect = visibleRect(child);
          if (!rect || rect.width > 32 || rect.height > 32) return false;
          const style = window.getComputedStyle(child);
          const color = `${style.backgroundColor} ${style.color} ${style.borderColor}`;
          return /(rgb\(255,\s*|rgb\(244,\s*|#f|red)/i.test(color)
            && /[1-9]\d?/.test(normalizeText(child.textContent));
        });
      const compactText = rawText.replace(/\d{2}:\d{2}.*/, "").trim();
      const fallbackName = compactText
        .replace(/Agent应用开发实习生.*/, "")
        .replace(/您好.*/, "")
        .trim()
        .split(" ")[0];
      return [{
        index,
        name: childText(item, [".name", ".user-name", ".friend-name", "[class*='name']"]) || fallbackName || rawText.split(" ")[0],
        preview: childText(item, [".last-msg", ".preview", ".message-text", "[class*='last']"]),
        unread_count: Number((unreadText.match(/\d+/) || ["0"])[0]),
        has_unread: hasUnreadMarker,
        href: absoluteHref(item),
        raw_text: rawText
      }];
    });
  }

  function messageDirection(element) {
    const classes = `${element.className || ""} ${element.parentElement?.className || ""}`.toLowerCase();
    if (/(self|mine|right|outgoing|send)/.test(classes)) return "out";
    if (/(system|notice|tip)/.test(classes)) return "system";
    return "in";
  }

  function extractChatDetail() {
    const nameSelectors = [
      ".chat-header .name",
      ".conversation-header [class*='name']",
      "[data-recruitment-agent-candidate-name]"
    ];
    let candidateName = null;
    for (const selector of nameSelectors) {
      candidateName = normalizeText(document.querySelector(selector)?.textContent) || null;
      if (candidateName) break;
    }
    const messageElements = firstMatchingElements(MESSAGE_SELECTORS);
    const fallbackMessages = messageElements.length ? [] : Array.from(document.querySelectorAll("div, p, span")).filter((element) => {
      const rect = visibleRect(element);
      if (!rect) return false;
      const content = normalizeText(element.textContent);
      if (content.length < 2 || content.length > 500) return false;
      if (/(在线简历|附件简历|求简历|换电话|换微信|约面试|不合适|招聘规范|我的客服)/.test(content)) {
        return false;
      }
      return rect.left > window.innerWidth * 0.42
        && rect.top > 280
        && rect.bottom < window.innerHeight - 90
        && rect.width > 40
        && rect.height > 16;
    });
    const seenMessages = new Set();
    const messages = (messageElements.length ? messageElements : fallbackMessages).slice(0, 200).flatMap((element) => {
      const content = normalizeText(element.textContent);
      if (!content || seenMessages.has(content)) return [];
      seenMessages.add(content);
      return [{ content, direction: messageDirection(element) }];
    });
    const seenAttachments = new Set();
    const attachments = [];
    for (const element of Array.from(document.querySelectorAll(ATTACHMENT_SELECTORS.join(","))).slice(0, 80)) {
      const previewText = normalizeText(element.textContent);
      const href = absoluteHref(element);
      const filename = (previewText.match(/[^\\/:*?"<>|\r\n]+\.pdf/i) || href?.match(/[^/?#]+\.pdf/i) || [null])[0];
      const isResume = filename || /\.pdf/i.test(href || "") || /(附件简历|在线简历|预览附件|简历)/.test(previewText);
      if (!isResume) continue;
      const key = `${filename || ""}|${href || ""}|${previewText}`;
      if (seenAttachments.has(key)) continue;
      seenAttachments.add(key);
      attachments.push({
        filename,
        attachment_type: filename || /\.pdf/i.test(href || "") ? "pdf" : "resume_card",
        preview_text: previewText || null,
        href
      });
    }
    return {
      candidate_name: candidateName,
      href: location.href,
      messages,
      attachments
    };
  }

  function clickChatByIndex(index) {
    const item = chatItems()[index];
    if (!item) return false;
    item.scrollIntoView({ block: "center", inline: "nearest" });
    item.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, cancelable: true, view: window }));
    item.click();
    return true;
  }

  function findVisibleByText(selectors, patterns) {
    const elements = Array.from(document.querySelectorAll(selectors.join(",")));
    return elements.find((element) => {
      if (!visibleRect(element)) return false;
      const text = normalizeText(element.textContent || element.getAttribute("aria-label"));
      return patterns.some((pattern) => pattern.test(text));
    }) || null;
  }

  function findComposer() {
    const candidates = Array.from(document.querySelectorAll("textarea, input[type='text'], [contenteditable='true']"));
    return candidates.find((element) => {
      const rect = visibleRect(element);
      if (!rect) return false;
      return rect.top > window.innerHeight * 0.62
        && rect.left > window.innerWidth * 0.34
        && rect.width > 120
        && rect.height > 14;
    }) || null;
  }

  function setComposerText(element, message) {
    element.focus();
    if ("value" in element) {
      element.value = message;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    element.textContent = message;
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: message }));
    return true;
  }

  function clickSendButton() {
    const button = findVisibleByText(["button", "span", "div"], [/^发送$/, /^鍙戦€?$/]);
    if (!button) return false;
    const disabled = button.matches?.(":disabled")
      || button.getAttribute("aria-disabled") === "true"
      || /disabled|forbid/.test(String(button.className || ""));
    if (disabled) return false;
    button.click();
    return true;
  }

  async function sendResumeRequest(message) {
    const quickResumeButton = findVisibleByText(["button", "span", "div"], [/^求简历$/, /^姹傜畝鍘?$/]);
    if (quickResumeButton) {
      quickResumeButton.click();
      await new Promise((resolve) => setTimeout(resolve, 250));
      const phrase = findVisibleByText(["li", "button", "span", "div", "p"], [
        /方便发一份你的简历过来吗/,
        /鏂逛究鍙戦€佷竴浠?.*绠€鍘?/
      ]);
      if (phrase) {
        phrase.click();
        await new Promise((resolve) => setTimeout(resolve, 250));
        if (clickSendButton()) return { sent: true, method: "common_phrase" };
      }
    }

    const composer = findComposer();
    if (!composer) return { sent: false, method: "none", error: "未找到聊天输入框" };
    setComposerText(composer, message);
    await new Promise((resolve) => setTimeout(resolve, 250));
    if (!clickSendButton()) return { sent: false, method: "composer", error: "未找到可点击的发送按钮" };
    return { sent: true, method: "composer" };
  }

  function extractTalentCards(limit = 30) {
    return firstMatchingElements(TALENT_CARD_SELECTORS).slice(0, limit).flatMap((card) => {
      const rawText = normalizeText(card.textContent);
      if (!rawText) return [];
      const href = absoluteHref(card);
      const age = rawText.match(/(\d{2})岁/);
      const graduationYear = rawText.match(/(20\d{2})年?(?:毕业|应届)/);
      const salary = rawText.match(/(\d+(?:-\d+)?K|\d+-\d+元\/天|薪资面议)/i);
      const education = ["博士", "硕士", "本科", "大专", "高中"].find((item) => rawText.includes(item)) || null;
      return [{
        boss_uid: stableUid(href, rawText),
        name: childText(card, [".name", "[class*='name']", "[data-name]"]) || rawText.split(" ")[0],
        age: age ? Number(age[1]) : null,
        city: childText(card, [".city", "[class*='city']", "[data-city]"]),
        education_level: education,
        school: childText(card, [".school", "[class*='school']", "[data-school]"]),
        major: childText(card, [".major", "[class*='major']", "[data-major]"]),
        graduation_year: graduationYear ? Number(graduationYear[1]) : null,
        candidate_type: /(应届|在校|校招)/.test(rawText) ? "校招" : null,
        experience: childText(card, [".experience", "[class*='experience']", "[data-experience]"]),
        intention: childText(card, [".expect", ".intention", "[class*='expect']", "[data-intention]"]),
        expected_salary: salary ? salary[1] : null,
        skills: SKILLS.filter((skill) => rawText.toLowerCase().includes(skill.toLowerCase())),
        href,
        raw_text: rawText
      }];
    });
  }

  globalScope.RecruitmentExtractors = {
    pageType,
    extractChatSummaries,
    extractChatDetail,
    clickChatByIndex,
    sendResumeRequest,
    extractTalentCards
  };
})(typeof window !== "undefined" ? window : globalThis);
