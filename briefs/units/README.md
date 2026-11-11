# 兵模与动画

步兵、骑兵、炮兵、海军及特色历史外观。idle 8fps 循环；move 12fps 循环；attack/recover/finish 12fps 非循环为推荐，实际 fps 可在 1..30 声明。五种动作必须齐备，至少左右向，镜像不能破坏非对称装备时请提议方向扩展。头脚武器均保留 8px 安全边。首批 units.infantry.line、units.cavalry.light；特色单位 units.france.grenadier。测试图不是制服考证。

通过条件：声明文件存在、schema/哈希/帧/内存校验通过；在预览中实际可见且锚点、透明边和尺寸稳定。Codex 负责游戏接入及 Android 验收。
