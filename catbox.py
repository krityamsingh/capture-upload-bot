import aiohttp
import asyncio
import json
import time
import hashlib
from typing import Dict, Any, Optional, Tuple
from io import BytesIO
import logging
from config import CATBOX_API_KEY, CATBOX_UPLOAD_URL, CATBOX_TIMEOUT, CATBOX_MAX_RETRIES

logger = logging.getLogger(__name__)

class CatboxUploader:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or CATBOX_API_KEY
        self.upload_url = CATBOX_UPLOAD_URL
        self.session = None
        self.timeout = CATBOX_TIMEOUT
        self.max_retries = CATBOX_MAX_RETRIES
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def upload_bytes(self, file_bytes: BytesIO, filename: str) -> Dict[str, Any]:
        """Ultra-fast upload to Catbox.moe - optimized for speed"""
        start_time = time.time()
        
        # Prepare form data
        data = aiohttp.FormData()
        
        # Add file
        file_data = file_bytes.getvalue() if hasattr(file_bytes, 'getvalue') else file_bytes
        data.add_field('fileToUpload', 
                      file_data,
                      filename=filename,
                      content_type=self._get_content_type(filename))
        
        # Add required parameters
        data.add_field('reqtype', 'fileupload')
        
        # Add user hash if API key is provided
        if self.api_key:
            data.add_field('userhash', self.api_key)
        
        headers = {
            'User-Agent': 'Catbox-Upload-Bot/2.0',
            'Accept': 'application/json',
        }
        
        # Upload with retry mechanism
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=self.timeout)
                    
                    async with session.post(
                        self.upload_url,
                        data=data,
                        headers=headers,
                        timeout=timeout
                    ) as response:
                        
                        response_text = await response.text()
                        upload_time = time.time() - start_time
                        
                        if response.status == 200:
                            # Catbox returns just the URL on success
                            result_url = response_text.strip()
                            
                            if result_url and result_url.startswith('http'):
                                # Extract file ID from URL
                                file_id = result_url.split('/')[-1].split('.')[0]
                                
                                return {
                                    'success': True,
                                    'url': result_url,
                                    'direct_url': result_url,
                                    'view_url': result_url,
                                    'file_id': file_id,
                                    'filename': filename,
                                    'size': len(file_data),
                                    'upload_time': upload_time,
                                    'attempt': attempt + 1,
                                    'message': 'File uploaded successfully to Catbox.moe'
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': f'Invalid response from Catbox: {response_text}',
                                    'upload_time': upload_time,
                                    'attempt': attempt + 1
                                }
                        else:
                            error_msg = f"HTTP {response.status}: {response_text[:200]}"
                            logger.warning(f"Upload attempt {attempt + 1} failed: {error_msg}")
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(1)  # Wait before retry
                                continue
                            else:
                                return {
                                    'success': False,
                                    'error': error_msg,
                                    'upload_time': upload_time,
                                    'attempt': attempt + 1
                                }
                                
            except asyncio.TimeoutError:
                error_msg = f"Timeout after {self.timeout} seconds (attempt {attempt + 1})"
                logger.warning(error_msg)
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'Upload timeout after {self.timeout} seconds',
                        'upload_time': self.timeout
                    }
                    
            except Exception as e:
                error_msg = f"Upload error (attempt {attempt + 1}): {str(e)}"
                logger.error(error_msg)
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'upload_time': time.time() - start_time
                    }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Catbox connection and speed"""
        try:
            start_time = time.time()
            
            # Create a small test file (1KB)
            test_data = b"A" * 1024
            test_bytes = BytesIO(test_data)
            
            result = await self.upload_bytes(test_bytes, "test.txt")
            
            if result['success']:
                return {
                    'success': True,
                    'service': 'Catbox.moe',
                    'url': result['url'],
                    'upload_time': result['upload_time'],
                    'speed': f"{1024 / result['upload_time']:.2f} KB/s",
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
            return {
                'success': False,
                'service': 'Catbox.moe',
                'error': str(e),
                'message': 'Connection test failed'
            }
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on filename"""
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
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    @staticmethod
    def calculate_md5(file_bytes: BytesIO) -> str:
        """Calculate MD5 hash of file for duplicate checking"""
        file_bytes.seek(0)
        md5_hash = hashlib.md5()
        
        # Read in chunks for large files
        for chunk in iter(lambda: file_bytes.read(4096), b""):
            md5_hash.update(chunk)
        
        file_bytes.seek(0)
        return md5_hash.hexdigest()
