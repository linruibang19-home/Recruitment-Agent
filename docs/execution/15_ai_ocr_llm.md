# AI / OCR / LLM 配置

## OCR

当前 OCR 使用本机 Tesseract，不调用外部 OCR 服务。

原因：

- 简历属于敏感个人信息，本地 OCR 更适合默认方案。
- Tesseract 可以被 PyMuPDF 直接调用，和现有 PDF 解析链路集成简单。
- 对扫描版 PDF 作为兜底能力足够；原生文本 PDF 仍优先直接提取文本。

配置项：

```text
TESSDATA_DIR=data/tessdata
```

默认语言：

```text
chi_sim+eng
```

健康检查：

```text
GET /api/health/ai
```

返回 `ocr.available=true` 表示本机已找到 Tesseract。

## LLM

LLM 用于增强简历结构化解析，默认 provider 为 DeepSeek。

配置项：

```text
LLM_ENABLED=true
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=...
```

注意：

- `.env` 不进入 Git。
- 健康检查只返回 key 是否已配置，不返回 key 内容。
- 发送给 LLM 前会先脱敏手机号、邮箱、身份证号、微信号和本地路径。

## 当前策略

1. PDF 有原生文本：直接解析原生文本。
2. PDF 原生文本不足：使用 Tesseract OCR。
3. 附件没有 PDF 直链但可预览：提取预览层文本。
4. 得到文本后：规则解析先生成 fallback 画像。
5. `LLM_ENABLED=true` 且 key 已配置时：调用 DeepSeek 增强结构化字段。
6. 失败时回退规则解析，不阻断候选人入库。
