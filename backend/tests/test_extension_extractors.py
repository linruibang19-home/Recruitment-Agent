from pathlib import Path

from playwright.sync_api import sync_playwright


EXTRACTOR_PATH = Path(__file__).resolve().parents[2] / "browser-extension" / "extractors.js"


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
