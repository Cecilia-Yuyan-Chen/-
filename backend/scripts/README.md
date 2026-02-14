# 批量随机测试

## 功能

- 跑 **10 局**游戏，每局 **20–30 人**（随机），共 15 轮。
- 每局内所有玩家的**选择完全随机**：有机肥/无机肥、是否申请补贴（Phase 2/3）均随机。
- 用于观察当前数值设计是否能在最终 NT/生态值上**拉开差距**。
- 跑完后将 **10 局结果** 导出到**同一个 Excel**：**每局一页**（游戏1 … 游戏10），每页格式与单局导出的 Excel 一致（玩家、每轮 NT/ENV、结算前 NT、最终 ENV、生态结算、最终 NT、总收益、是否获胜）。

## 如何运行

在项目根目录下，进入后端目录再执行脚本（保证能正确加载 `app`）：

```bash
cd backend
python scripts/batch_test.py
```

或使用模块方式（同样需在 `backend` 下）：

```bash
cd backend
python -m scripts.batch_test
```

## 输出

- 控制台：每局结束会打印 `完成第 i/10 局：game_id=xxx，玩家数=xx`，最后打印导出路径。
- Excel 文件：`backend/exports/batch_test_10games.xlsx`
  - 共 10 个工作表：**游戏1**、**游戏2**、…、**游戏10**。
  - 每个工作表的列与单局导出一致：玩家、用户名、Round1 NT/ENV … Round15 NT/ENV、NT(结算前)、最终ENV、生态结算、最终NT、总收益、是否获胜。

## 注意

- 测试数据**不写入真实数据库**：脚本使用内存 SQLite（`sqlite:///:memory:`）运行 10 局，只生成 Excel 文件，**不会**向 `backend/game.db` 写入任何测试游戏或轮次数据。
