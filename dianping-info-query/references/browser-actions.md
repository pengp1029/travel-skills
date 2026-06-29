# 浏览器工具 Action 使用指南

## 核心 Action

- `navigate`：访问大众点评首页或具体商户页面。
- `backbone`：获取页面结构，识别关键元素和登录状态。
- `search`：动态定位搜索框、登录按钮、商户卡片、评分元素。优先用它而不是硬编码 ref。
- `type`：向搜索框输入关键词，可配合提交。
- `click`：点击搜索按钮、商户链接、城市入口。
- `press`：模拟 Enter、Tab 等键盘动作。
- `readability`：首选内容提取方式，适合商户详情、商圈信息和评论摘要。
- `snapshot`：备用 DOM 方案，用于 readability 无法覆盖的页面。
- `list_tabs` / `focus_tab`：处理新标签页。

## 标准搜索流程

```javascript
navigate(url="https://www.dianping.com")
backbone()
search(query="input[placeholder*='搜索'],#myInput,#J-search-input,input.j-search-input")
type(ref="found-ref", text="北京 咖啡店", submit=true)
list_tabs()
focus_tab(targetId="latest-or-matched-tab")
readability()
```

## 登录检测

- 未登录：查找“请登录/注册”、登录二维码、`account.dianping.com/pclogin`。
- 已登录：查找 `.username`、`.nick-name`、`.user-face`、个人中心链接。

未登录时暂停自动化，说明需要用户扫码或手动登录。不要尝试绕过验证码或滑块。

## 信息提取优先级

1. `readability`
2. `backbone`
3. `snapshot`

## 最佳实践

- 使用动态定位，避免固定 ref。
- 搜索后检查是否打开新标签页。
- 对评分、人均、营业时间、推荐菜、评论标签分别标准化。
- 把评论标签当作决策信号，不当作实时排队数据。
