# 通用生图插件 (Image Generation)

> 本插件基于 [railgun19457/astrbot_plugin_image_generation](https://github.com/railgun19457/astrbot_plugin_image_generation) 项目二次开发。
> 这里先保留原作者内容的简化版说明，后续会继续补充本项目自己的内容。

## 我的内容

待补充。

## 简介

面向 AstrBot 的通用图像生成插件，支持多供应商、文生图、图生图、LLM 工具调用、预设、限流和安全审核。

## 主要功能

- 多供应商配置：可同时接入多个生图服务。
- 模型切换：通过 `/生图模型` 查看和切换模型。
- 文生图和图生图：支持消息图片、引用图片和 @ 头像作为参考图。
- LLM 工具调用：可作为对话中的生图工具使用。
- 预设和人设：支持提示词模板和带参考图的人设。
- 限流与审核：支持频率限制、每日额度、屏蔽词和图片审核。

## 常用命令

| 命令 | 说明 |
| :-- | :-- |
| `/生图 <提示词、预设名称或人设名称> [额外提示词]` | 生成图片。 |
| `/生图模型` | 查看可用模型和当前模型。 |
## 变更说明（适配器兼容性更新）

- **影响文件**: [adapter/openai_adapter.py](adapter/openai_adapter.py)
- **要点**:
	- **multipart 字段名**: 将上传参考图的 multipart 字段由 `image[]` 改为 `image`（重复的 `image` 字段），以兼容 OpenAI 官方客户端和多数代理。
	- **文件名**: 为 multipart 文件补充合理的文件名（如 image.png / image.jpg / image.webp），提高代理/上游解析兼容性。
	- **MaiziAI(v2) 兼容**: 当配置的 base URL 明确指向 `/images/generations`（例如 MaiziAI v2）且请求包含参考图时，改为在 JSON body 中通过 `images` 字段传递 data URI（data:{mime};base64,...），而不是走 `/images/edits` 的 multipart 路径。
	- **诊断改进**: 在遇到 502 且上游返回 `upstream_error` 时，增加日志提示，帮助排查代理不支持 edits 路径或模型不匹配的问题。
- **理由**: 避免在一些 OpenAI 兼容网关（如 api.xstx.info / MaiziAI）上因端点或请求格式差异导致的 500/502 错误，提升参考图（图生图/编辑）功能的稳定性。
- **后续建议**: 如果使用第三方网关，建议直接配置完整的 images/generations 或 images/edits URL（根据厂商文档），以避免自动路由判断带来的兼容性风险。
| `/预设 删除 <预设名>` | 删除预设。 |

## 原作者内容简化版

### 适配器

支持 Gemini、OpenAI、火山方舟、Gitee AI、即梦、Grok、SiliconFlow 等适配器，覆盖常见文生图和图生图接口。

### 配置概览

插件提供基础生图配置、供应商配置、用户限制配置、安全审核配置和提示词模板配置，适合按需开启。

### 使用示例

```text
/生图 一只在森林里野餐的兔子
/生图模型
```

### 注意事项

- 火山方舟的可用模型列表需要按控制台实际 Model ID 或 Endpoint ID 配置。
- 配置 `jimeng2api` 后，插件会在启动时和每天凌晨自动领取积分。
- 欢迎后续补充本项目自己的说明、示例和维护信息。
