# 欧洲、美洲、全球地图

三种 region 独立提供视觉。制作 plain/forest/mountain/water/coast/river/snow/desert/wetland/road 与边缘过渡。样例用 maps.terrain.plain 等；无任何真实关卡排列。地块画布和中性格坐标见 ASSET-SPEC。全球以可追溯地理资料独立绘制，4096×2048 设计画布分块；国界/所属/城市/部队是动态层，不能烘焙。

通过条件：声明文件存在、schema/哈希/帧/内存校验通过；在预览中实际可见且锚点、透明边和尺寸稳定。Codex 负责游戏接入及 Android 验收。
