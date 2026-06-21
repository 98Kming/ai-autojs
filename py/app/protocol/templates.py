"""AutoJS6 JavaScript 代码模板，对应 src/types/autojs.ts"""

# 截图模板：截取屏幕并返回 JPEG 字节数组
SCREENSHOT_TEMPLATE = """(function () {
    if (!requestScreenCapture()) return "请求截图失败";
    let img = images.captureScreen();
    let arr = images.toBytes(img, 'jpg');
    img.recycle();
    return arr;
}())"""


def find_image_template(template_base64: str, x: int, y: int, w: int, h: int, threshold: float = 0.9) -> str:
    """生成找图代码

    Args:
        template_base64: 模板图片的 Base64 编码
        x, y, w, h: 搜索区域
        threshold: 匹配阈值 (0~1)，默认 0.9
    """
    return f"""(function () {{
    if (!requestScreenCapture()) return "请求截图失败";
    let img = images.captureScreen();
    // 从 Base64 解码模板图片
    let templateBytes = images.fromBase64("{template_base64}");
    let template = images.toImage(templateBytes);
    // 在指定区域查找
    let result = images.findImage(img, template, {{
        region: [{x}, {y}, {w}, {h}],
        threshold: {threshold}
    }});
    img.recycle();
    template.recycle();
    if (result) {{
        return JSON.stringify({{ found: true, x: result.x, y: result.y }});
    }} else {{
        return JSON.stringify({{ found: false }});
    }}
}}())"""
