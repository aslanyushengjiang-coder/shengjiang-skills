# A4 PDF与可编辑版本

本包自带单栏中文HTML样式，不依赖Kami和WeasyPrint。优先使用宿主已有浏览器打印；
也可使用 `scripts/resume_export.py`，它由已安装Playwright驱动已存在的Chromium。
不自动下载浏览器，不使用用户登录态，不加入--no-sandbox参数，HTML不加载远程资源。

```text
python <SKILL_DIR>/scripts/resume_export.py --input <resume.json> --facts <profile.json> --out <新版本目录> --approved --pdf --browser <本机浏览器绝对路径>
```

`--approved`仅在用户已确认内容/允许输出投递版后使用；演示用 `--demo`，始终显示不可投递标识。
不带这两个参数仅导出标注待确认的草稿。无PDF能力时不带--pdf，交付HTML/TXT。
Python依赖见requirements.txt；安装须先获授权。脚本导出的 `qa.json` 会说明每一步是否完成。

PDF设置A4、prefer_css_page_size=true，默认校招1页；社招经用户确认可用--max-pages 2。
输出后检查实际MediaBox约595.28×841.89pt、页数、可提取文字、关键姓名文本和模板残留。
页数超标时报错，不偷偷删事实、不把字号压到不可读；调整内容后生成新版本再验收。
最终还必须渲染每页图像，目视检查截断、乱码、重叠、空白照片框。程序检查通过不等于目视通过。

输出 `resume.html`、`resume.txt`、实际生成的 `resume.pdf`、`qa.json`、`manifest.json`。
manifest含文件指纹；文件存在≠可投递。注册版本时 `jobctl resume register` 会核对哈希，
并要求 approved_for_use 与 visual_checked 均为true。只有实际完成后才在manifest写入对应状态。
对于宿主其他导出路线，同样保留以上检查，别把截图改后缀叫PDF。

## 单页A4专业排版验收

应届生演示与校招简历必须交付恰好1页A4纵向PDF（210×297mm），仅设置A4纸型不算验收。
默认页边距上下14mm、左右16mm；正文10.5–11pt、行距1.45–1.6，姓名24–28pt，章节标题11–12pt。
内容应合理铺满可用版心，正文末端通常落在页面底部边距上方约0–20mm；根据实际内容调整段距与模块间距，不能靠空白块、纵向缩放或裁切隐藏溢出来制造单页。
材料太少时先补问真实经历、职责与交付物，不捏造成果或堆无关自评。内容过多先删除重复句并按目标岗位取舍，不把正文字号压到10pt以下。
有用户指定照片时用原图的头肩取景，保持比例，不拉伸；推荐放在页眉右侧。
导出后须检查页数、纸型、文本可提取、最后一行位置及所有页面实际渲染；有第二页必须重新排版后再交付。
修改前后演示使用相同事实基础和相同纸型；前稿呈现职责笼统、结果不突出等真实表达问题，后稿突出本人动作、依据及成果。不能把前稿故意做成残缺半页来制造效果。
