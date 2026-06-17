---
name: autojs-image
description: autojs image 代码片段参考，image 相关函数在`resources/image.html`中
---

## 示例

### 截图代码片段
```js
(function(){
if(!requestScreenCapture()){
    return "请求截图失败";
}
let img = images.captureScreen()
let arr = images.toBytes(img)
img.recycle()
return arr
}())
```