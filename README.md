# Meishu · 原创美术制作工程

**本工作包提供项目自研接口、原创设计规格和原创测试样例。**

这里是现有策略游戏的独立视觉制作工程。资源接口、制作工具、预览器和测试样例均由本项目自行编写；样例图由仓库内程序原创绘制。它们用于验证接入格式，最终美术由 Claude 制作。无需取得其他仓库，也无需安装游戏引擎或 Android 工具。

## Claude 从这里开始

1. 读 [美术任务](ART-BRIEF.md) 和 [视觉方向](ART-DIRECTION.md)。请制作兵模、立绘、建筑、特效、地图和完整 UI，可提出更好的原创布局。
2. 打开 [六类规格](ASSET-SPEC.md)。按稳定资源编号制作，不需要知道游戏里的旧文件名。
3. 运行预览与校验，按 [提交合同](DELIVERY-CONTRACT.md) 分批交付。Codex 负责接回游戏、内部映射和 Android 验收。

```sh
python -m pip install -r requirements.txt
python tools/validate.py
python -m http.server 8000 --bind 127.0.0.1
```

打开 **http://127.0.0.1:8000/previews/**，可以切换动作、交互状态、朝向，查看锚点和六角格；也可以加载 `submissions/你的批次/manifest.json`。预览器无在线依赖。

首批完整样例为 [samples/manifest.json](samples/manifest.json)，包含 UI 四态、地形、两类单位动画、历史人物肖像占位、八类建筑、特效及法国视觉身份。`python tools/generate_samples.py --output 新目录` 可独立重新生成；不会读取外部游戏数据。

## 分工与入口

| 入口 | 用途 |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | 给 Claude 的直接开工指令 |
| [ASSET-SPEC.md](ASSET-SPEC.md) | 画布、动作、锚点、地图和 UI 合同 |
| [briefs](briefs) | 六类生产任务与全球视觉接口 |
| [schemas](schemas) | 可执行 JSON Schema |
| [validation](validation) | 测试及交付验证结果 |
| [references/SOURCES.json](references/SOURCES.json) | 自研来源与参考资料记录 |

这里只维护美术制作与交付。游戏逻辑、关卡、存档、平台构建和实体映射由 Codex 在游戏工程维护。全球视觉包使用独立版本身份，不替换现有剧本。
