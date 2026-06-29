# 城市切换操作指南

## 流程

1. 识别当前城市：页面顶部 `a.city`。
2. 点击城市选择入口：`.city-select-icon` 或城市列表链接。
3. 在城市列表页搜索目标城市。
4. 点击目标城市链接。
5. 验证 URL 和页面城市显示。
6. 切换成功后再执行搜索。

## 示例

```javascript
navigate(url="https://www.dianping.com")
backbone()
search(query=".city-select-icon")
click(ref="city-select-icon-ref")
search(query="北京")
click(ref="beijing-city-ref")
backbone()
```

## 注意事项

- 使用标准中文城市名。
- 切换后等待页面加载。
- 如果城市不支持，说明大众点评覆盖不足，不要编造结果。
