import aiohttp
import asyncio
import json
import time
import hashlib
import os
import logging
from typing import Dict, Any, Optional, Union, BinaryIO
from io import BytesIO

# Import config module and access attributes safely with defaults
import config

logger = logging.getLogger(__name__)


class CatboxUploader:
    """
    Async uploader for Catbox.moe with support for both in-memory bytes and file paths.
    Optimised for reliability and speed with proper error handling and retries.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        max_file_size: Optional[int] = None
    ):
        # Use provided values, otherwise fall back to config, then hardcoded defaults
        self.api_key = api_key or getattr(config, 'CATBOX_API_KEY', None)
        self.upload_url = getattr(config, 'CATBOX_UPLOAD_URL', 'https://catbox.moe/user/api.php')
        self.timeout = timeout or getattr(config, 'CATBOX_TIMEOUT', 300)  # 5 minutes default
        self.max_retries = max_retries or getattr(config, 'CATBOX_MAX_RETRIES', 3)
        # Default max file size: 200 MB for registered users, 100 MB for anonymous
        default_max_size = 200 * 1024 * 1024 if self.api_key else 100 * 1024 * 1024
        self.max_file_size = max_file_size or getattr(config, 'CATBOX_MAX_FILE_SIZE', default_max_size)

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def close(self):
        """Manually close the session if not using context manager."""
        if self.session:
            await self.session.close()
            self.session = None

    # ==================== Public Methods ====================

    async def upload_bytes(self, file_bytes: BytesIO, filename: str) -> Dict[str, Any]:
        """
        Upload a file from an in-memory BytesIO object.
        Recommended for small files only (e.g., < 10 MB) to avoid memory issues.
        For larger files, use `upload_file()` instead.
        """
        # Get the size
        file_bytes.seek(0, os.SEEK_END)
        size = file_bytes.tell()
        file_bytes.seek(0)

        # Warn if file is large
        if size > 10 * 1024 * 1024:  # 10 MB
            logger.warning(f"Large file ({size / 1024 / 1024:.2f} MB) uploaded via upload_bytes(). "
                           f"Consider using upload_file() for better memory efficiency.")

        # Check size limit
        if size > self.max_file_size:
            return {
                'success': False,
                'error': f'File size ({size} bytes) exceeds the maximum allowed ({self.max_file_size} bytes).',
                'filename': filename,
                'size': size
            }

        # Read all bytes (still in memory, but we already warned)
        data = file_bytes.getvalue()
        return await self._upload(data, filename, size)

    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file directly from disk by streaming it.
        This is the preferred method for large files.
        """
        if not os.path.isfile(file_path):
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }

        size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        # Check size limit
        if size > self.max_file_size:
            return {
                'success': False,
                'error': f'File size ({size} bytes) exceeds the maximum allowed ({self.max_file_size} bytes).',
                'filename': filename,
                'size': size
            }

        # Open the file and pass the file object to the upload routine
        # The file will be closed automatically after the upload
        with open(file_path, 'rb') as f:
            return await self._upload(f, filename, size)

    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity and speed by uploading a tiny 1KB file."""
        try:
            test_data = b"A" * 1024
            test_bytes = BytesIO(test_data)
            result = await self.upload_bytes(test_bytes, "test.txt")
            if result['success']:
                speed_kbps = 1024 / result['upload_time'] if result['upload_time'] > 0 else 0
                return {
                    'success': True,
                    'service': 'Catbox.moe',
                    'url': result['url'],
                    'upload_time': result['upload_time'],
                    'speed': f"{speed_kbps:.2f} KB/s",
                    'api_key_status': 'Active' if self.api_key else 'Anonymous',
                    'message': 'Catbox connection test successful'
                }
            else:
                return {
                    'success': False,
                    'service': 'Catbox.moe',
                    'error': result.get('error', 'Unknown error'),
                    'message': 'Catbox connection test failed'
                }
        except Exception as e:
            logger.exception("Connection test failed")
            return {
                'success': False,
                'service': 'Catbox.moe',
                'error': str(e),
                'message': 'Connection test failed'
            }

    # ==================== Internal Upload Logic ====================

    async def _upload(self, file_data: Union[bytes, BinaryIO], filename: str, size: int) -> Dict[str, Any]:
        """
        Core upload routine.
        :param file_data: Either bytes or an open binary file-like object (will be read as needed).
        :param filename: Name of the file.
        :param size: File size in bytes (used for logging and stats).
        """
        start_time = time.time()
        session = self.session or aiohttp.ClientSession()
        close_session = self.session is None

        try:
            for attempt in range(self.max_retries):
                try:
                    # Create a fresh FormData for each attempt (required because streams are consumed)
                    data = aiohttp.FormData(quote_fields=False)

                    # Add the file field
                    # If file_data is bytes, it will be sent as a chunk; if it's a file-like, it will be streamed
                    data.add_field(
                        'fileToUpload',
                        file_data if isinstance(file_data, bytes) else file_data,  # aiohttp handles both
                        filename=filename,
                        content_type=self._get_content_type(filename)
                    )
                    data.add_field('reqtype', 'fileupload')
                    if self.api_key:
                        data.add_field('userhash', self.api_key)

                    timeout = aiohttp.ClientTimeout(total=self.timeout)
                    async with session.post(
                        self.upload_url,
                        data=data,
                        timeout=timeout
                    ) as response:
                        response_text = await response.text()
                        upload_time = time.time() - start_time

                        # Success case: Catbox returns the URL as plain text
                        if response.status == 200 and response_text.startswith('http'):
                            file_id = response_text.split('/')[-1].split('.')[0]
                            return {
                                'success': True,
                                'url': response_text,
                                'direct_url': response_text,
                                'view_url': response_text,
                                'file_id': file_id,
                                'filename': filename,
                                'size': size,
                                'upload_time': upload_time,
                                'attempt': attempt + 1,
                                'message': 'File uploaded successfully to Catbox.moe'
                            }

                        # Error handling
                        error_msg = f"HTTP {response.status}: {response_text[:200]}"
                        logger.error(f"Upload failed (attempt {attempt + 1}): {error_msg}")

                        # Decide whether to retry
                        if response.status >= 500 and attempt < self.max_retries - 1:
                            # Server error – may be temporary
                            await asyncio.sleep(1)
                            continue
                        else:
                            # Client error (4xx) or final attempt
                            return {
                                'success': False,
                                'error': error_msg,
                                'upload_time': upload_time,
                                'attempt': attempt + 1
                            }

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout on attempt {attempt + 1}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1)
                    else:
                        return {
                            'success': False,
                            'error': f'Upload timeout after {self.timeout} seconds',
                            'upload_time': self.timeout,
                            'attempt': attempt + 1
                        }

                except Exception as e:
                    logger.exception(f"Unexpected error on attempt {attempt + 1}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1)
                    else:
                        return {
                            'success': False,
                            'error': str(e),
                            'upload_time': time.time() - start_time,
                            'attempt': attempt + 1
                        }

        finally:
            if close_session:
                await session.close()

    # ==================== Helpers ====================

    def _get_content_type(self, filename: str) -> str:
        """Return MIME type based on file extension."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo',
            'webp': 'image/webp',
            'webm': 'video/webm',
            'txt': 'text/plain',
            'pdf': 'application/pdf',
            'zip': 'application/zip',
        }
        return content_types.get(ext, 'application/octet-stream')

    @staticmethod
    def calculate_md5(file_bytes: BytesIO) -> str:
        """Calculate MD5 hash of a BytesIO object (seek to 0 after)."""
        file_bytes.seek(0)
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file_bytes.read(4096), b""):
            hash_md5.update(chunk)
        file_bytes.seek(0)
        return hash_md5.hexdigest()
