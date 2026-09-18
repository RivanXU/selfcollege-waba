# 第三方组件与资料

selfcollege-waba 的原创文件适用根目录 [LICENSE](LICENSE) 及 [NOTICE](NOTICE)。第三方组件保留自己的许可。

## PDF 工具依赖

下列 Python 库由使用者的运行环境单独安装，本包不分发它们的代码：

| 组件 | 用途 | 许可 |
| --- | --- | --- |
| [ReportLab](https://pypi.org/project/reportlab/) | 文字、表格和 PDF 版式 | [BSD 许可文本](licenses/REPORTLAB.txt) |
| [pypdf](https://pypi.org/project/pypdf/) | 原页保留、矢量合成与 PDF 文件处理 | [BSD 许可文本](licenses/PYPDF.txt) |

随包许可文本用于方便查阅；安装其他发行版时，仍应保留并遵守该发行包自带的许可。

## 随包字体

[`assets/fonts/NotoSansSC-Regular.ttf`](assets/fonts/NotoSansSC-Regular.ttf) 是从 [Google Fonts 官方下载源](https://fonts.google.com/download/list?family=Noto%20Sans%20SC) 获取的完整静态 Noto Sans SC Regular 字体，文件未经修改。其原始版权与 [SIL Open Font License](assets/fonts/OFL.txt) 随包保留。字体独立适用该许可，不适用项目的 PolyForm 许可。

该字体可随软件分发并嵌入 PDF；其许可不要求生成的文档采用字体许可。也可通过生成器的 `--font` 参数指定自己有权使用和嵌入的 TTF 字体。

## 学习资料与成果

`examples/` 中的教学内容由本项目编写，用于展示排版与学习流程，不来自真实课程或考试。

用户提供的课件、教材、课堂记录、图片及其他资料保留原有权利。使用或分享包含这些资料的学习成果时，仍应遵守资料本身的许可与使用范围。生成 PDF 不表示项目作者取得了输入资料的权利，也不自动把学习者独立撰写的内容改为本项目许可。
