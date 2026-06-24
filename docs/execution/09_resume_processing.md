# Resume Processing and Scoring

## 处理流程

```text
PDF 上传
  -> 文件类型和大小校验
  -> PyMuPDF 原生文本提取
  -> 文本不足时 Tesseract OCR
  -> 规则结构化解析
  -> 可选 LLM 增强
  -> 候选人画像入库
  -> 按岗位生成可解释评分
  -> 审计日志
```

## 本地目录

- 简历文件：`data/resumes/{candidate_id}/`
- OCR 模型：`data/tessdata/`

这两个目录均不进入 Git。

## OCR

Windows 使用 Tesseract OCR。当前本机安装路径：

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

项目本地 `data/tessdata/` 需要包含：

- `chi_sim.traineddata`
- `eng.traineddata`
- `osd.traineddata`

可使用 `TESSDATA_DIR` 指定其他模型目录。未安装 OCR 或识别文本过少时，简历状态为 `needs_review`，不会伪造结构化字段。

## 结构化字段

- 学历
- 学校
- 专业
- 毕业年份
- 校招或社招
- 工作年限
- 技能
- 项目经历
- 亮点
- 风险点
- 画像摘要

默认解析器为本地规则引擎，保证无模型密钥时仍可运行。

## LLM 增强

默认关闭：

```text
LLM_ENABLED=false
```

显式开启并配置 `DEEPSEEK_API_KEY` 后，系统会对手机号和邮箱脱敏，再调用兼容 Chat Completions 的模型进行结构化增强。调用失败时自动回退本地规则解析。

## 评分维度

总分 100：

- 技能匹配：40
- 学历要求：20
- 项目与经验：20
- 信息完整度：10
- 基础匹配：10

评分保存总分、各维度分、关键词命中和文字理由。同一候选人和岗位重复评分时更新原记录。

## API

- `GET /api/candidates/{candidate_id}/detail`
- `POST /api/candidates/{candidate_id}/resumes?job_id={job_id}`
- `POST /api/candidates/{candidate_id}/scores/{job_id}`

上传限制：

- 仅 PDF
- 默认最大 10 MB
- 文件头必须为 `%PDF`
