from pathlib import Path

from playwright.sync_api import sync_playwright


EXTRACTOR_PATH = Path(__file__).resolve().parents[2] / "browser-extension" / "extractors.js"
CONTENT_PATH = Path(__file__).resolve().parents[2] / "browser-extension" / "content.js"


def _page():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()
    return playwright, browser, page


def test_extracts_chat_summary_detail_and_attachment() -> None:
    playwright, browser, page = _page()
    try:
        page.set_content(
            """
            <div class="chat-list">
              <div class="chat-item">
                <span class="name">张同学</span>
                <span class="last-msg">这是我的简历</span>
                <span class="unread">2</span>
              </div>
            </div>
            <div class="chat-header"><span class="name">张同学</span></div>
            <div class="message-item outgoing">请发送 PDF 简历</div>
            <div class="message-item incoming">好的，这是我的简历</div>
            <a class="file-card" href="/files/resume.pdf">张同学-简历.pdf</a>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """() => ({
              summaries: RecruitmentExtractors.extractChatSummaries(10),
              detail: RecruitmentExtractors.extractChatDetail()
            })"""
        )
        assert result["summaries"][0]["name"] == "张同学"
        assert result["summaries"][0]["unread_count"] == 2
        assert result["detail"]["candidate_name"] == "张同学"
        assert [item["direction"] for item in result["detail"]["messages"]] == ["out", "in"]
        assert result["detail"]["attachments"][0]["filename"] == "张同学-简历.pdf"
    finally:
        browser.close()
        playwright.stop()


def test_clicks_chat_item_by_index() -> None:
    playwright, browser, page = _page()
    try:
        page.set_content(
            """
            <div class="chat-list">
              <button class="chat-item" onclick="window.clicked='first'">
                <span class="name">候选人A</span>
              </button>
              <button class="chat-item" onclick="window.clicked='second'">
                <span class="name">候选人B</span>
              </button>
            </div>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        clicked = page.evaluate(
            """() => {
              const ok = RecruitmentExtractors.clickChatByIndex(1);
              return { ok, clicked: window.clicked };
            }"""
        )
        assert clicked == {"ok": True, "clicked": "second"}
    finally:
        browser.close()
        playwright.stop()


def test_detects_unread_red_dot_without_number() -> None:
    playwright, browser, page = _page()
    try:
        page.set_content(
            """
            <div class="chat-list">
              <div class="chat-item">
                <span class="name">候选人A</span>
                <span class="last-msg">您好，我想了解岗位</span>
                <span class="red-dot" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff4d4f;"></span>
              </div>
            </div>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate("() => RecruitmentExtractors.extractChatSummaries(10)[0]")
        assert result["has_unread"] is True
    finally:
        browser.close()
        playwright.stop()


def test_fallback_extracts_visible_boss_chat_cards() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1940, "height": 1080})
        page.set_content(
            """
            <main>
              <section style="position:absolute; left:420px; top:185px; width:430px;">
                <div style="height:86px; width:410px;" onclick="window.clicked='first'">
                  <strong>何瑞</strong>
                  <span>Agent应用开发实习生</span>
                  <small>23:09</small>
                  <p>您好，我是华南理工大学电子信息...</p>
                </div>
                <div style="height:86px; width:410px;" onclick="window.clicked='second'">
                  <strong>朱福培</strong>
                  <span>Agent应用开发实习生</span>
                  <small>21:26</small>
                  <p>您好，我是大模型应用开发岗位的求职者...</p>
                </div>
              </section>
              <section style="position:absolute; left:900px; top:280px; width:900px;">
                <div style="margin-top:260px; width:620px;">
                  您好，我是大模型应用开发岗位的求职者，基于langchain框架设计搭建RAG知识库。
                </div>
              </section>
            </main>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """() => {
              const summaries = RecruitmentExtractors.extractChatSummaries(10);
              const clicked = RecruitmentExtractors.clickChatByIndex(1);
              const detail = RecruitmentExtractors.extractChatDetail();
              return { summaries, clicked, clickedValue: window.clicked, detail };
            }"""
        )
        assert [item["name"] for item in result["summaries"]] == ["何瑞", "朱福培"]
        assert result["clicked"] is True
        assert result["clickedValue"] == "second"
        assert "langchain" in result["detail"]["messages"][0]["content"]
    finally:
        browser.close()
        playwright.stop()


def test_send_resume_request_uses_composer_fallback() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.set_content(
            """
            <textarea style="position:absolute; left:620px; top:720px; width:520px; height:80px;"></textarea>
            <button style="position:absolute; left:1180px; top:760px;" onclick="window.sent=document.querySelector('textarea').value">
              发送
            </button>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """async () => {
              const result = await RecruitmentExtractors.sendResumeRequest("方便发一份你的简历过来吗？");
              return { result, sent: window.sent };
            }"""
        )
        assert result["result"]["sent"] is True
        assert result["sent"] == "方便发一份你的简历过来吗？"
    finally:
        browser.close()
        playwright.stop()


def test_send_resume_request_uses_common_phrase_entry() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.set_content(
            """
            <button style="position:absolute; left:720px; top:760px;" onclick="document.querySelector('#phrases').style.display='block'">
              常用语
            </button>
            <div id="phrases" style="display:none; position:absolute; left:720px; top:620px; width:360px;">
              <button onclick="document.querySelector('textarea').value=this.textContent; document.querySelector('textarea').dispatchEvent(new Event('input', { bubbles: true }))">
                方便发一份你的简历过来吗？
              </button>
            </div>
            <textarea style="position:absolute; left:620px; top:720px; width:520px; height:80px;"></textarea>
            <button style="position:absolute; left:1180px; top:760px;" onclick="window.sent=document.querySelector('textarea').value">
              发送
            </button>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """async () => {
              const result = await RecruitmentExtractors.sendResumeRequest("方便发一份你的简历过来吗？");
              return { result, sent: window.sent };
            }"""
        )
        assert result["result"]["sent"] is True
        assert result["result"]["method"] == "common_phrase"
        assert result["sent"] == "方便发一份你的简历过来吗？"
    finally:
        browser.close()
        playwright.stop()


def test_detects_existing_resume_request_history() -> None:
    playwright, browser, page = _page()
    try:
        page.set_content("<main></main>")
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """() => ({
              asked: RecruitmentExtractors.hasResumeRequestHistory({
                messages: [
                  { direction: "out", content: "方便发一份你的简历过来吗？" }
                ]
              }, "方便发一份你的简历过来吗？"),
              received: RecruitmentExtractors.hasResumeRequestHistory({
                messages: [
                  { direction: "in", content: "您好，我的简历已发送啦，希望您能看看～" }
                ]
              }, "方便发一份你的简历过来吗？"),
              unrelated: RecruitmentExtractors.hasResumeRequestHistory({
                messages: [
                  { direction: "in", content: "您好，我对这个岗位很感兴趣。" }
                ]
              }, "方便发一份你的简历过来吗？")
            })"""
        )
        assert result == {"asked": True, "received": True, "unrelated": False}
    finally:
        browser.close()
        playwright.stop()


def test_enriches_attachment_with_preview_text() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.set_content(
            """
            <button
              data-recruitment-agent-attachment
              onclick="document.querySelector('[data-recruitment-agent-preview]').style.display='block'"
            >
              郑志.pdf 点击预览附件简历
            </button>
            <section
              data-recruitment-agent-preview
              style="display:none; position:absolute; left:300px; top:80px; width:800px; height:700px;"
            >
              <button onclick="this.closest('[data-recruitment-agent-preview]').style.display='none'">关闭</button>
              <article>
                郑志 男 年龄 21岁 13322776874 2245769434@qq.com
                求职意向 Python 期望城市 广州
                广东工业大学 大数据管理与应用 本科 2023-2027
                熟悉 Python FastAPI SQL pandas LangChain RAG 机器学习 深度学习
                项目经历 智能数据分析平台 使用 Docker 部署并完成接口开发
              </article>
            </section>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        result = page.evaluate(
            """async () => {
              const detail = RecruitmentExtractors.extractChatDetail();
              const attachments = await RecruitmentExtractors.enrichAttachmentPreviews(detail.attachments, 20);
              return attachments[0];
            }"""
        )
        assert result["filename"] == "郑志.pdf"
        assert result["extraction_method"] == "preview_dom"
        assert "广东工业大学" in result["extracted_text"]
        assert "FastAPI" in result["extracted_text"]
    finally:
        browser.close()
        playwright.stop()


def test_request_resumes_batch_skips_existing_request() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.set_content(
            """
            <div class="chat-list" style="position:absolute; left:320px; top:180px; width:360px;">
              <button class="chat-item" data-index="0" onclick="selectChat(0)">
                <span class="name">候选人A</span>
                <span class="unread">1</span>
                <span class="last-msg">您好，我想了解岗位</span>
              </button>
              <button class="chat-item" data-index="1" onclick="selectChat(1)">
                <span class="name">候选人B</span>
                <span class="unread">1</span>
                <span class="last-msg">您好，我很感兴趣</span>
              </button>
            </div>
            <section id="chat" style="position:absolute; left:720px; top:180px; width:600px; height:520px;"></section>
            <textarea style="position:absolute; left:720px; top:740px; width:420px; height:60px;"></textarea>
            <button style="position:absolute; left:1160px; top:748px;" onclick="window.sentMessages.push(document.querySelector('textarea').value); document.querySelector('#chat').insertAdjacentHTML('beforeend', '<div class=&quot;message-item outgoing&quot;>' + document.querySelector('textarea').value + '</div>')">
              发送
            </button>
            <script>
              window.sentMessages = [];
              window.selectChat = (index) => {
                const chat = document.querySelector("#chat");
                if (index === 0) {
                  chat.innerHTML = `
                    <div class="chat-header"><span class="name">候选人A</span></div>
                    <div class="message-item incoming">您好，我想了解岗位。</div>
                  `;
                } else {
                  chat.innerHTML = `
                    <div class="chat-header"><span class="name">候选人B</span></div>
                    <div class="message-item outgoing">方便发一份你的简历过来吗？</div>
                  `;
                }
              };
              window.selectChat(0);
            </script>
            """
        )
        page.evaluate(
            """
            () => {
              window.fetch = async () => ({ ok: true, json: async () => ({ control: "running" }) });
              window.chrome = {
                runtime: {
                  onMessage: { addListener: (fn) => { window.__contentListener = fn; } },
                  sendMessage: () => ({ catch: () => null })
                }
              };
            }
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        page.add_script_tag(path=str(CONTENT_PATH))
        result = page.evaluate(
            """() => new Promise((resolve) => {
              window.__contentListener({
                type: "run_command",
                command: {
                  id: 10,
                  command_type: "request_resumes_batch",
                  payload: {
                    limit: 20,
                    delay_ms: 10,
                    only_unread: true,
                    message: "方便发一份你的简历过来吗？"
                  }
                }
              }, null, resolve);
            }).then((response) => ({
              response,
              sentMessages: window.sentMessages
            }))"""
        )
        batch = result["response"]["result"]
        assert result["response"]["ok"] is True
        assert result["sentMessages"] == ["方便发一份你的简历过来吗？"]
        assert batch["sent_count"] == 1
        assert batch["skipped_already_requested"] == 1
        assert batch["failed_count"] == 0
        assert batch["summary"]["target_count"] == 2
        assert [item["status"] for item in batch["execution_trace"]] == [
            "sent",
            "skipped_already_requested",
        ]
    finally:
        browser.close()
        playwright.stop()


def test_request_resumes_batch_collects_targets_after_scroll() -> None:
    playwright, browser, page = _page()
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.set_content(
            """
            <div class="chat-list" style="position:absolute; left:320px; top:180px; width:360px; height:120px; overflow:auto;">
              <button class="chat-item" onclick="selectChat(0)" style="display:block; height:80px;">
                <span class="name">候选人A</span>
                <span class="last-msg">普通已读</span>
              </button>
              <button class="chat-item" onclick="selectChat(1)" style="display:block; height:80px;">
                <span class="name">候选人B</span>
                <span class="unread">1</span>
                <span class="last-msg">您好，我很感兴趣</span>
              </button>
              <button class="chat-item" onclick="selectChat(2)" style="display:block; height:80px;">
                <span class="name">候选人C</span>
                <span class="unread">1</span>
                <span class="last-msg">想投递岗位</span>
              </button>
            </div>
            <section id="chat" style="position:absolute; left:720px; top:180px; width:600px; height:520px;"></section>
            <textarea style="position:absolute; left:720px; top:740px; width:420px; height:60px;"></textarea>
            <button style="position:absolute; left:1160px; top:748px;" onclick="window.sentMessages.push(document.querySelector('textarea').value); document.querySelector('#chat').insertAdjacentHTML('beforeend', '<div class=&quot;message-item outgoing&quot;>' + document.querySelector('textarea').value + '</div>')">
              发送
            </button>
            <script>
              window.sentMessages = [];
              window.selectChat = (index) => {
                document.querySelector("#chat").innerHTML = `
                  <div class="chat-header"><span class="name">候选人${index === 1 ? "B" : "C"}</span></div>
                  <div class="message-item incoming">您好，我想了解岗位。</div>
                `;
              };
              window.selectChat(1);
            </script>
            """
        )
        page.evaluate(
            """
            () => {
              window.fetch = async () => ({ ok: true, json: async () => ({ control: "running" }) });
              window.chrome = {
                runtime: {
                  onMessage: { addListener: (fn) => { window.__contentListener = fn; } },
                  sendMessage: () => ({ catch: () => null })
                }
              };
            }
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        page.add_script_tag(path=str(CONTENT_PATH))
        result = page.evaluate(
            """() => new Promise((resolve) => {
              window.__contentListener({
                type: "run_command",
                command: {
                  id: 11,
                  command_type: "request_resumes_batch",
                  payload: {
                    limit: 2,
                    delay_ms: 10,
                    only_unread: true,
                    message: "方便发一份你的简历过来吗？"
                  }
                }
              }, null, resolve);
            }).then((response) => ({
              response,
              sentMessages: window.sentMessages
            }))"""
        )
        batch = result["response"]["result"]
        assert batch["summary"]["target_count"] == 2
        assert batch["sent_count"] == 2
        assert result["sentMessages"] == [
            "方便发一份你的简历过来吗？",
            "方便发一份你的简历过来吗？",
        ]
    finally:
        browser.close()
        playwright.stop()


def test_extracts_talent_card_fields() -> None:
    playwright, browser, page = _page()
    try:
        page.set_content(
            """
            <div data-recruitment-agent-talent-card>
              <a href="/web/geek/detail?encryptGeekId=test-uid"></a>
              <span class="name">李同学</span>
              <span class="city">广州</span>
              <span class="school">测试大学</span>
              <span class="major">软件工程</span>
              <span class="expect">Python 开发</span>
              22岁 2026应届 本科 Python RAG 5-10K
            </div>
            """
        )
        page.add_script_tag(path=str(EXTRACTOR_PATH))
        card = page.evaluate("() => RecruitmentExtractors.extractTalentCards(10)[0]")
        assert card["boss_uid"] == "test-uid"
        assert card["name"] == "李同学"
        assert card["city"] == "广州"
        assert card["education_level"] == "本科"
        assert card["candidate_type"] == "校招"
        assert card["skills"] == ["Python", "RAG"]
    finally:
        browser.close()
        playwright.stop()
