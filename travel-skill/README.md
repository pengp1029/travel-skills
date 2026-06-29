<p align="center">
  <h1 align="center">travel-skill</h1>
</p>

面向 OpenClaw 的轻量旅行推荐 skill：按用户偏好、时间、预算和场景组织城市游玩、吃饭、天气、路线和最新信息检索。

## 核心能力

- 景点推荐
- 美食推荐
- 玩 + 吃组合路线
- 热闹 / 适中 / 人少差异化输出
- 天气查询与出游建议
- 高德路线规划
- 联网搜索最新开放时间、门票和预约政策

## 安装

见 `INSTALL.md`。

## 结构

```text
travel-skill/
├── SKILL.md
├── reference.md
├── examples.md
├── INSTALL.md
├── README.md
├── requirements.md
├── scripts/
│   └── helper.py
└── tools/
    ├── config.py
    ├── tool_types.py
    ├── weather_client.py
    ├── amap_client.py
    ├── web_search.py
    ├── snapshot_store.py
    └── version_manager.py
```
