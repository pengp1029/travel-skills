# 多标签页处理

大众点评搜索、点击商户、城市切换时可能打开新标签页。

## 标准流程

1. 执行可能产生新标签页的操作。
2. 调用 `list_tabs` 获取所有标签页。
3. 优先按 URL 匹配 `/shop/`、搜索结果页或目标城市；其次选择最新标签页。
4. 调用 `focus_tab` 切换。
5. 用 `backbone` 或 `readability` 验证页面正确。

## 示例

```javascript
use_browser(action="type", ref="search-input", text="西安回民街", submit=true)
const tabs = use_browser(action="list_tabs")
const target = tabs.find(tab => tab.url.includes("dianping.com")) || tabs[tabs.length - 1]
use_browser(action="focus_tab", targetId=target.targetId)
use_browser(action="readability")
```

## 错误处理

- 标签页未打开：等待 2 秒后重新 `list_tabs`。
- 多个相似标签页：用 URL + 标题组合匹配。
- 切换失败：回到当前标签页继续读取，明确告知结果可能不完整。
