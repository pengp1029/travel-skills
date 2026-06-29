# 小红书调研工作流

## 前提

小红书用于软信号：近期体验、氛围、拍照、排队体感、踩空提醒。不要把小红书内容当作营业时间、票务政策、官方地址等硬事实。

稳定方案是 OpenCLI + Chrome CDP。OpenCLI 内置 `xiaohongshu` 适配器可作为优先尝试，若 Browser Bridge 不稳定，再走 CDP 直连页面。

## OpenCLI 安装

```bash
npm install -g @jackwener/opencli
opencli --version
opencli doctor
```

若全局 npm 在 `~/.npm-global/bin`，需要确保 PATH 包含该目录。

## Browser Bridge 扩展

1. 从 OpenCLI releases 下载 `opencli-extension.zip`。
2. 解压到 `~/.opencli/extensions/opencli-extension`。
3. Chrome 打开 `chrome://extensions`，开启开发者模式，加载已解压扩展。

## 内置命令

```bash
opencli xiaohongshu search '玉ひで 东京' --limit 10 -f json
```

若这条路不稳定，使用下面的 CDP 直连方案。

## CDP 最小流程

启动可调试 Chrome：

```bash
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --user-data-dir=/tmp/opencli-chrome-cdp \
  --profile-directory=Default \
  --remote-debugging-port=9223 \
  'https://www.xiaohongshu.com/explore'
```

直接导航到搜索结果页，不模拟输入框：

```js
await bridge.send('Page.navigate', {
  url: 'https://www.xiaohongshu.com/search_result?keyword=' + encodeURIComponent(query)
});
```

监听搜索 API：

```text
POST https://edith.xiaohongshu.com/api/sns/web/v1/search/notes
```

搜索结果通常足够做第一轮筛选；只打开最相关的 2-3 条详情页。

## 筛选标准

保留：

- 店名、地址、菜品或地点明确。
- 有真实体验，而不是合集里顺手提一句。
- 多条笔记重复出现同一高频词。
- 能帮助判断要不要排队、适合白天还是晚上、打卡还是稳饭、是否容易踩空。

不保留：

- 泛合集弱提及。
- 标题是酒店/散步，正文才顺手带店。
- 明显搬运。
- 只有情绪形容，没有决策信息。

## 写回格式

只留一层结论，不搬运笔记原文：

```md
- 店名
- 代表笔记链接：xhsUrl
- 图片示例/封面入口：imageUrl 或 imageKey（没有真实图片时使用图片搜索入口）
- 大众点评入口：dianpingUrl（如果有）
- 详情链接：detailUrl（优先真实详情页，没有时使用搜索入口）
- 两三句压缩判断：近期反馈、适合场景、风险提醒
- 来源说明：sourceNote，说明代表笔记、图片入口或搜索入口的可信度边界
```
