<!-- Copyright (c) 2026 RivanXU. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0. See LICENSE and NOTICE. -->

# 可调整的PDF初始样式与生成器

没有个人偏好时使用以下样式；可调整颜色、字体、密度与语言。个性化配置保存在自己的课程目录中，与 Skill 默认样式分开。

## 精讲版：A4纵向

- 白底，左右边距约47pt；深蓝顶部细带、课程页眉、青绿色小标题，底部细线和页码。
- 色值：深蓝`#17334D`，青绿`#117E82`，正文`#263746`，次级字`#607485`，浅蓝框`#EDF4FA`，浅绿框`#ECF7F5`，浅橙框`#FFF5E9`，分隔线`#D9E3EA`。
- 正文约10.7-11.5pt，行距17-19pt；主标题约21pt，小标题约13pt；表格9.5-10.5pt，次级定位9pt左右。不要使用小字号塞入过量正文。
- 标题、说明、表格、图示和提示框交替组织，每页聚焦一个合理学习单元；避免不必要的装饰图、长篇密集段落和大量空泛总结。
- 正文使用嵌入的中文字体，数学符号完整；公式可使用可靠的数学排版或矢量图，不能用低清截图代替需要读取的数学表达式。颜色只作辅助，信息仍须由文字明确表达。
- 表格深蓝表头、浅色交替行、自动换行；提示框用浅绿/蓝，易错和原文疑点用浅橙。提供书签以及原页定位。

## 对照版：宽幅横向

- 默认A3横向，左侧英文完整原页约540pt宽，右侧完整中文译文，正文约14pt、行距23.5pt。
- 英文原页优先通过PDF矢量嵌入完整保留，不裁掉页边、图、底注或渐进页。扫描原稿可保持原像素，不虚称矢量。
- 左下术语表，右侧译文之后为理解提示与课堂批注；页脚标源文件/物理页码、精讲页码。第n页就是原第n页。
- 长注释转到精讲并加具体页码；译文不能删减或转移成“不译”。密集页可加宽/加高对照页或另做更适合原稿比例的版式，仍保持一个原页对应一个成品页。
- 本包生成器会在溢出时明确失败，不能忽略失败或通过无边界缩小字号继续输出。

## 使用生成器

`scripts/render_study_pdfs.py`接受内容清单JSON，生成两份PDF或其中一份。它只负责本地排版与原页映射；所有翻译、讲解、来源和答案必须先由助教基于原资料编写。运行环境需要Python、`reportlab`与`pypdf`，依赖见`requirements.txt`。有PDF技能时按其要求执行制作准备和操作记录；没有时仍须提取、排版、逐页渲染和核验。可使用当前环境已有的PDF渲染工具或本地PDF阅读器完成视觉核查。

```bash
python3 <技能目录>/scripts/render_study_pdfs.py --spec /absolute/path/content.json --output-dir /absolute/path/output
```

使用外部个人风格时增加`--style /absolute/path/pdf-style-overrides.json`。该文件只写需要覆盖的已知键，例如：

```json
{"navy":"#473366","teal":"#75509B","guide_body_size":11.2,"guide_body_leading":18.0}
```

允许键是默认`assets/style_tokens.json`中的13项；颜色须为`#RRGGBB`，字号/行距须为有限正数，行距不得小于字号。未知键会报错；覆盖文件不会改动默认样式资产。尺寸变大引起溢出时重新分页，不删教学内容。

非英文原稿、非中文目标语言或个人命名需求，必须在内容清单中显式设置准确的`labels`，不能照搬默认英文原页标签。例如：

```json
{"labels":{"source_heading":"SOURCE ORIGINAL｜完整原页","translation_heading":"译文与注释｜逐条对应","terms_heading":"本页专业词汇","bilingual_name":"逐页原文对照","guide_name":"课程精讲"}}
```

`labels`还支持`guide_header`、`bilingual_header`、`source_footer`、`guide_reference_footer`。两种header省略时跟随产物名称；source_footer仅接受`{filename}`和`{page}`，guide_reference_footer仅接受`{pages}`。文件名后缀不能含路径分隔符，两个产物不能同名；标签内的`&`、`<`由生成器转义。正文与标题内的轻量排版标签仍按下述规则处理。未提供覆盖时原中英版式保持不变。

内容清单最小示例（示例仅说明结构，不是课程内容）：

```json
{
  "course_code": "COURSE-CODE",
  "course_name": "课程中文名 / English Course Name",
  "lecture": "Lecture 1",
  "file_stem": "COURSE-CODE_Lecture1",
  "source_pdf": "/absolute/path/source.pdf",
  "bilingual": [
    {
      "source_page": 1,
      "title_zh": "本页中文标题",
      "title_en": "Original page title",
      "translation": ["按顺序完整翻译的段落"],
      "terms": [["English term", "中文术语与解释"]],
      "notes": [{"label": "理解提示｜资料内推导", "text": "根据本页定义解释", "source": "原稿第1页"}],
      "guide_pages": "1-2"
    }
  ],
  "guide": [
    {
      "title": "学习单元标题",
      "subtitle": "English title / 模块定位",
      "source": "source.pdf，第1页",
      "blocks": [
        {"type": "heading", "text": "核心问题"},
        {"type": "text", "text": "完整教学文字"},
        {"type": "box", "label": "直觉解释", "text": "解释", "tone": "green"},
        {"type": "table", "header": ["英文", "中文"], "rows": [["term", "术语"]], "widths": [1, 1]},
        {"type": "formula", "text": "x<sub>1</sub> + x<sub>2</sub> = c"},
        {"type": "image", "path": "/absolute/path/verified-diagram.png", "caption": "原稿第1页图的说明"},
        {"type": "source_crop", "source_pdf": "/absolute/path/source.pdf", "page": 1, "clip": [20, 40, 330, 250], "height": 200, "caption": "原图局部；来源与裁切范围明确"}
      ]
    }
  ]
}
```

- `bilingual`须列出原PDF全部页，每个`source_page`严格依次为1至N。只需某一产物时省略另一字段；用户指定原页子集时先明确导出子集副本并另保留原物理页映射，或调整生成器，不能伪造全稿覆盖。
- `translation`为完整译文；图中文字也需译。`notes`可包含课堂批注，`label`与`source`中写实际转写定位和来源类别。没有转写不填虚构课堂标签。
- 为保持兼容，`title_zh`作为主标题、`title_en`作为第二语言/原稿标题字段；字段名不要求材料必须为中英文。实际显示文本应符合当前语言设置。
- 精讲`guide`按页构造，每页`blocks`自动计算高度；溢出须将精讲内容合理拆页。`source_crop`只用于精讲，原页完整对照不裁切。原页和裁切区域通过PDF页面内容合成，原稿中的矢量文字与图形保留矢量；扫描图仍保持原始图像。
- `source_crop.clip`为`[左, 上, 右, 下]`，以原PDF旋转后可见页面的左上角为原点，单位为PDF点（1/72英寸），范围须在页面内。它只控制显示区域，不会删除原PDF区域外的隐藏内容，不能用于隐私遮盖或脱敏。合成的是页面文字、图形与图像；交互表单、链接及批注不会复制，有批注的资料应先保存一份已将批注转成页面内容的副本。
- 文本允许不带属性的`<b>`、`<strong>`、`<i>`、`<em>`、`<u>`、`<strike>`、`<sub>`、`<super>`、`<sup>`与`<br/>`轻量标签；其他标签及属性会被拒绝。原文中的`&`与`<`须写为`&amp;`与`&lt;`。图片通过`image`块引用已有本地文件，不能在正文中嵌入图片或远程URL。生成器不会下载外部图片。
- 默认嵌入包内的`assets/fonts/NotoSansSC-Regular.ttf`，字体许可见同目录的`OFL.txt`。可用`--font /absolute/path/cjk.ttf`指定另一个允许嵌入且覆盖所用文字的TrueType字体。生成器会检查文字字形；遇到缺字会在替换成品前报错并列出字符与Unicode编号。默认字体覆盖中文、拉丁文及常用数学符号，但不包含所有语言或符号，例如`ℝ`、`ℕ`、`ℤ`。遇到缺字须改用合适字体，或将公式用可靠数学工具排版为清晰的本地图片；不能删除或擅自替换原公式符号。
- 所有输入须为已有本地文件。原PDF、裁切来源、插图、内容清单、样式配置、字体与输出必须不同；生成器会检查实际路径与硬链接，拒绝用成品覆盖引用输入。文件名不得含路径分隔符。两份文件名分别为`<file_stem>_逐页中英对照.pdf`和`<file_stem>_零基础精讲.pdf`。
- 上述文件名是未提供`labels`时的默认值；设置`guide_name`或`bilingual_name`后对应后缀和PDF标题随之改变。

## 交付核查

核对页数、所有原页的英文内容、完整中文译文、图表标签、数学、原文疑点、课堂定位、练习答案和互相页码指引。逐页渲染看图；文本提取相同并不能证明图形/公式没问题。确认无乱码、黑框、重叠、裁切与过小字号，再按当前环境保存PDF和课程档案。生成器会保留书签，但不会核查教学结论或自动证明来源正确。
