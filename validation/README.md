# 资源验收

```sh
python tools/validate.py --report validation/local-sample.json
python -m unittest discover -s validation -v
python tools/check_isolation.py
```

检查真实 PNG 解码、像素尺寸、透明区、SHA-256、帧网格/索引、动作完整性、锚点、拉伸边框、解码内存、资源引用、来源登记及交付目录内容。schema 拒绝未定义字段，防止视觉清单夹入玩法参数。

测试包含完整样例、无游戏输入的独立重建，以及缺图、目录逃逸、篡改图片、重复 ID、越界帧、缺少状态、额外规则字段、未登记文件、未知来源、越界锚点和全球引用错误。独立目录运行不要求游戏仓库、平台工具或设备。

浏览器预览人工验证：载入 27 项资源，切换 UI 状态与单位动作、左右向、暂停和重播，点击中性格网得到行列与中心坐标；错误路径显示具体 404，恢复有效清单后重新载入。浏览器未出现脚本错误。

已发布的 `sample-validation.json` 绑定当前样例字节。后续批次需要重新校验；样例通过不代表 Claude 的最终美术、历史考证或全部 Android 视觉替换已完成。
