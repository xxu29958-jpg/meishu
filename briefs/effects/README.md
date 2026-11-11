# 特效

制作 attack/hit/explosion/smoke/capture 的透明帧序列，打包成 PNG 网格。play 非循环；声明 fps/锚点/blend，建议 250..1000ms，烟雾可延长至 1500ms。命中点固定为世界落点，不能夹带规则或伤害；首批 effects.hit.spark。预览必须显示锚点与暂停/播放，查看第一帧、末帧与左右向。

通过条件：声明文件存在、schema/哈希/帧/内存校验通过；在预览中实际可见且锚点、透明边和尺寸稳定。Codex 负责游戏接入及 Android 验收。
