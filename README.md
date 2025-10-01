<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,2,5,30&height=160&section=header&text=🌈%20你好啊，欢迎来到OpenWebUI-Base64-Image部署指南%20✨&fontSize=28&fontColor=fff&animation=twinkling&fontAlignY=40" />

# OpenWebUI-Base64-Image部署指南
最近在使用OpenWebUI接入某些图像生成模型时发现不是直接返回图片，而是返回Base64编码，于是做了个Pipe来对其进行处理，同时兼容了扣费插件的前端显示（如果你有的话）

## 部署步骤

### 1. 在OpenWebUI ▸ 管理面板 ▸ 功能 中，单击从链接导入 。
 <img width="450" alt="image" src="https://github.com/user-attachments/assets/4a5a0355-e0af-4fb8-833e-7d3dfb7f10e3" />

### 2. 在弹出的对话框中，输入以下URL，然后单击导入按钮：
```bash
https://github.com/Besty0728/OpenWebUI-Base64-Image/blob/main/image_decoder_pipe.py
```
### 3.⚠️ 重要提示，不要改动Pipe的Pipe ID，必须保持为 `image_decoder_pipe`，否则无法正常工作。（除非你将我们的文件名称一并改动）
这个值目前是硬编码，必须完全匹配，未来版本或许可配置

### 4. 导入后，您应该会在功能列表中看到 `OpenWebUI-Base图片解码器` 。
填入你的
- 自定义API请求地址
- 你的 API Key
- 模型名称
