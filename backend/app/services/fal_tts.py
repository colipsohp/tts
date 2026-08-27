"""fal.ai Index TTS 2.0 语音合成封装。

提供：synthesize（文字+参考音频 URL → 生成音频 URL）、upload_reference_audio（本地音频上传）、
download_audio（把生成的远程音频落盘到本地 workplace/）。
所有跨边界调用 catch + log，绝不静默抛出原始异常导致上层崩溃。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import fal_client
import httpx

from app.config import get_settings

logger = logging.getLogger("tts.services.fal_tts")


class FalTtsError(RuntimeError):
    """fal.ai 调用失败（可读错误信息供前端展示）。"""


def synthesize(audio_url: str, prompt: str, client_timeout: int | None = None) -> str:
    """调用 fal.ai Index TTS 2.0 生成语音，返回生成的音频 URL。

    :param audio_url: 参考音频 URL（fal 托管 / 公开 URL）
    :param prompt: 要合成的文字
    :param client_timeout: 客户端总超时秒数（排队 + 推理），默认取配置 fal_request_timeout
    :raises FalTtsError: 调用失败或超时
    """
    settings = get_settings()
    total_timeout = client_timeout or settings.fal_request_timeout
    start_timeout = settings.fal_start_timeout
    try:
        result: dict[str, Any] = fal_client.subscribe(
            settings.fal_model,
            arguments={"audio_url": audio_url, "prompt": prompt},
            # start_timeout：服务端开始处理前的排队等待上限；
            # client_timeout：整个请求（排队+推理）的总时长上限
            start_timeout=start_timeout,
            client_timeout=total_timeout,
        )
    except fal_client.client.FalClientTimeoutError as exc:  # noqa: BLE001
        logger.warning("fal synthesize timed out after %ss: %s", total_timeout, exc)
        raise FalTtsError(
            f"语音生成超时（已等待 {total_timeout} 秒，fal 队列或生成较慢），"
            "请稍后点击「重新生成」重试"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("fal synthesize failed: %s", exc, exc_info=True)
        raise FalTtsError(f"语音合成调用失败：{exc}") from exc

    audio = result.get("audio") if isinstance(result, dict) else None
    url = audio.get("url") if isinstance(audio, dict) else None
    if not url:
        logger.warning("fal synthesize 返回缺少 audio.url: %r", result)
        raise FalTtsError("语音合成返回结果异常：缺少音频地址")
    return str(url)


def upload_reference_audio(local_path: str | Path) -> str:
    """把本地参考音频上传到 fal 存储，返回可用的 URL。

    内置音色文件常含中文名，fal_client 的 v3 上传路径对非 ASCII 路径存在
    ascii codec 缺陷，因此先复制为 ASCII 文件名的临时文件再上传。
    """
    import shutil
    import tempfile

    path = Path(local_path)
    upload_path = path
    tmp: Path | None = None

    if not path.name.isascii():
        tmp = (
            Path(tempfile.gettempdir())
            / f"tts_upload_{uuid.uuid4().hex}{path.suffix.lower() or '.wav'}"
        )
        try:
            shutil.copy2(path, tmp)
            upload_path = tmp
        except Exception as exc:  # noqa: BLE001
            logger.warning("复制临时上传文件失败（尝试直接上传）: %s", exc)

    try:
        url: str = fal_client.upload_file(str(upload_path))
        return url
    except Exception as exc:  # noqa: BLE001
        logger.warning("fal upload reference audio failed: %s", exc, exc_info=True)
        raise FalTtsError(f"参考音频上传失败：{exc}") from exc
    finally:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except Exception:  # noqa: BLE001
                pass


def download_audio(url: str, dest_dir: str | Path, file_name: str | None = None) -> Path:
    """把生成的音频 URL 下载到本地目录，返回本地文件路径。

    :param url: 生成的音频 URL
    :param dest_dir: 目标目录（自动创建）
    :param file_name: 目标文件名；缺省时从 URL 推断或随机生成
    :raises FalTtsError: 下载失败
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    name = file_name or _guess_file_name(url)
    dest_path = dest / name
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            with dest_path.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    fh.write(chunk)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fal download audio failed: %s", exc, exc_info=True)
        raise FalTtsError(f"生成音频下载失败：{exc}") from exc
    return dest_path


def _guess_file_name(url: str) -> str:
    """从 URL 猜测文件名（含扩展名），失败时回退为随机 mp3。"""
    try:
        from urllib.parse import unquote, urlparse

        name = Path(unquote(urlparse(url).path)).name
        if name and Path(name).suffix:
            return name
    except Exception:  # noqa: BLE001
        pass
    return f"tts_{uuid.uuid4().hex[:8]}.mp3"
