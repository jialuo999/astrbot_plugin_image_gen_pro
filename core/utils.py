from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from io import BytesIO

from PIL import Image

from astrbot.api import logger

from .constants import (
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_RESOLUTIONS,
)
from .logging_utils import (
    log_prefix,
    mask_sensitive as mask_sensitive,
    safe_log_error_body as safe_log_error_body,
    safe_log_mapping as safe_log_mapping,
    safe_log_text as safe_log_text,
    safe_log_url as safe_log_url,
)
from .types import ImageData

SUPPORTED_IMAGE_FORMATS = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}

# 使用 constants.py 中的定义，转换为 set 以保持向后兼容
ALLOWED_ASPECT_RATIOS = set(SUPPORTED_ASPECT_RATIOS)
ALLOWED_RESOLUTIONS = set(SUPPORTED_RESOLUTIONS)
LOG = log_prefix("Utils")


def detect_mime_type(data: bytes) -> str:
    """根据魔数（Magic Numbers）尽力检测 MIME 类型。"""

    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if len(data) > 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"heim", b"heis"):
            return "image/heic"
        if brand in (b"mif1", b"msf1", b"heif"):
            return "image/heif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _sync_convert_image_format(image_data: bytes, mime_type: str) -> ImageData:
    """同步将不支持的图像转换为 JPEG。"""

    try:
        img = Image.open(BytesIO(image_data))

        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            elif img.mode == "LA":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3])
            img = background

        output = BytesIO()
        img.save(output, format="JPEG", quality=95)
        logger.debug(f"{LOG} 已将图像转换为 JPEG")
        return ImageData(data=output.getvalue(), mime_type="image/jpeg")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"{LOG} 图像转换失败: {exc}")
        return ImageData(data=image_data, mime_type=mime_type)


async def convert_image_format(image_data: bytes, mime_type: str) -> ImageData:
    """如果 MIME 类型不支持，则转换图像。"""

    real_mime = detect_mime_type(image_data)
    if real_mime in SUPPORTED_IMAGE_FORMATS:
        return ImageData(data=image_data, mime_type=real_mime)
    logger.info(f"{LOG} 正在转换图像格式: {mime_type} -> image/jpeg")
    return await asyncio.to_thread(_sync_convert_image_format, image_data, mime_type)


async def convert_images_batch(images: Iterable[ImageData]) -> list[ImageData]:
    """并行批量转换图像。"""

    tasks = [convert_image_format(img.data, img.mime_type) for img in images]
    return await asyncio.gather(*tasks)


def validate_aspect_ratio(value: str | None) -> str | None:
    """验证宽高比是否在允许的集合中。"""

    if value is None:
        return None
    return value if value in ALLOWED_ASPECT_RATIOS else None


def validate_resolution(value: str | None) -> str | None:
    """验证分辨率是否在允许的集合中。"""

    if value is None:
        return None
    return value if value in ALLOWED_RESOLUTIONS else None


def apply_template_variables(template: str, extra_text: str) -> tuple[str, str]:
    """替换预设模板中的 {变量名} 占位符。

    从 extra_text 中提取 key=value 格式的变量赋值，
    替换 template 中对应的 {key} 占位符，
    返回 (替换后的模板, 剩余未被提取的文本)。
    """
    placeholders = re.findall(r"\{(\w+)\}", template)
    if not placeholders:
        return template, extra_text

    replacements = {}
    # 匹配 key=value 或 key="带空格的value"
    pattern = r'(\w+)=(?:"([^"]*)"|(\S+))'
    remaining = extra_text

    for match in re.finditer(pattern, remaining):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        if key in placeholders:
            replacements[key] = value

    # 从原文本中移除已提取的 key=value 片段
    remaining = re.sub(pattern, "", remaining).strip()
    remaining = re.sub(r"\s+", " ", remaining).strip()

    # 替换模板中的占位符
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{key}}}", value)
    # 清理未填的占位符，去掉 {变量名}
    result = re.sub(r"\{\w+\}", "", result).strip()
    result = re.sub(r"\s+", " ", result).strip()

    return result, remaining
