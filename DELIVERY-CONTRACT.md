# 分批交付

1. 从 main 建立 `art/<主题>` 分支，将批次放入 `submissions/<主题>/`。
2. 按 samples 结构提交 `manifest.json`、`theme.json`、`sources.json` 和图片。允许局部主题，只列本批已完成资产。中性 ID 稳定，Codex 维护游戏内绑定。
3. 用 `python tools/seal.py submissions/<主题>/manifest.json` 根据实际文件更新尺寸与 SHA-256，再执行 `python tools/validate.py submissions/<主题>/manifest.json`。seal 不修改作者和来源声明，不替代内容审查。
4. 启动预览，切换每个动作、左右向与锚点，检查四态、裁切、透明边、大小和文字留白。提交预览截图及简短说明。
5. PR 描述列出新增/替换 ID、来源、完成与未完成内容、校验结果。不要提交临时缓存、安装包、存档或平台构建文件。

manifest v1 的 `theme` 和 `sources` 是相对 JSON 路径。每张图片的 `source_id` 指向 sources.sources 中的唯一记录，记录作者、制作方法、许可/使用约定、参考链接及说明。项目程序样例真实标记为 procedural-original；后续 AI 生成作品标记为 ai-generated-original 并记实际模型/工具，不伪称人工手绘。

可选 `preview` 指向同批的场景 JSON，规格为 `schemas/preview-scene.schema.json`。画布、格网间距、地块、任意资源编号、动作和摆放位置均从数据读取。不提供场景也能完整校验和逐项预览，不能要求为新主题修改程序。

来源记录声明图像来源，哈希绑定具体字节。自动检查能发现目录逃逸、缺图、帧越界、预算错误、未知字段及未声明文件；“没有复制外部画面”仍需结合来源、源文件和内容审查，不能靠后缀证明。

PNG 是 v1 唯一运行图片格式。编辑源放同批 `sources/`，在 sources.json 的 `editable_files` 显式登记；允许 SVG、KRA、ORA、PSD、BLEND（编辑源不进入 Android），压缩项目需先商定，避免无法审查的嵌套内容。字体和音频不在当前 v1 交付范围。

Codex 的接入顺序：同一校验器检查 → 审核来源 → 打包 manifest 与声明图片 → 内部中性 ID 映射 → 原显示路径加载 → Android 显示/触控/状态验收。未映射资源可先在预览/Android 样例浏览器验收；不把尚未映射的成品谎报为全游戏替换完成。
