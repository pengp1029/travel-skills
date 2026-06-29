# 大众点评常用选择器

## 搜索框

- `#myInput`
- `#J-search-input`
- `input.j-search-input`
- `input[placeholder*='搜索']`

推荐组合：

```javascript
input[placeholder*='搜索'],#myInput,#J-search-input,input.j-search-input
```

## 登录状态

已登录：

- `.username`
- `.nick-name`
- `.user-face`
- `a[href*='/member/']`

未登录：

- `.login-link`
- 文本“请登录/注册”
- `#account-login`
- `[src*='qrcode']`

## 商户信息

- `#pc-shop-head`
- `.shop-name`
- `.address`
- `.tel`
- `.star-container`
- `.score`
- `.comment-condition`
- `.tag-list`
- `.tag-item`
- `.count`

## 城市切换

- `.city`
- `.city-select-icon`
- `a[href*='/citylist']`
