import aiohttp
import asyncio
import base64
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
from config import PIXELDRAIN_API_KEY
from io import BytesIO
import logging
import time

logger = logging.getLogger(__name__)

class PixelDrainUploader:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://pixeldrain.com/api"
        self.api_key = api_key or PIXELDRAIN_API_KEY
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication header for PixelDrain"""
        headers = {"User-Agent": "PixelDrain-Upload-Bot/1.0"}
        if self.api_key:
            auth_string = f":{self.api_key}"
            auth_encoded = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {auth_encoded}"
        return headers
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test PixelDrain connection and API key"""
        try:
            headers = self._get_auth_header()
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(
                    f"{self.base_url}/user",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'username': data.get('username', 'Unknown'),
                            'email': data.get('email', 'Unknown'),
                            'storage_used': data.get('storage_used', 0),
                            'storage_total': data.get('storage_total', 0),
                            'response_time': f"{response_time:.2f}s"
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}",
                            'status': response.status,
                            'response_time': f"{response_time:.2f}s"
                        }
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    async def upload_bytes(self, file_bytes: BytesIO, filename: str, content_type: str = None) -> Dict[str, Any]:
        """Ultra-fast in-memory upload to PixelDrain with optimized settings"""
        headers = self._get_auth_header()
        
        # Determine content type if not provided
        if not content_type:
            if filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                content_type = 'image/png'
            elif filename.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif filename.lower().endswith('.mp4'):
                content_type = 'video/mp4'
            elif filename.lower().endswith('.mov'):
                content_type = 'video/quicktime'
            elif filename.lower().endswith('.avi'):
                content_type = 'video/x-msvideo'
            elif filename.lower().endswith('.webp'):
                content_type = 'image/webp'
            else:
                content_type = 'application/octet-stream'
        
        try:
            start_time = time.time()
            
            # Use single session for faster upload
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                
                # Optimize form data creation
                file_data = file_bytes.getvalue() if hasattr(file_bytes, 'getvalue') else file_bytes
                
                form_data.add_field(
                    'file',
                    file_data,
                    filename=filename,
                    content_type=content_type
                )
                
                # Optimized timeout settings
                timeout = aiohttp.ClientTimeout(
                    total=60,
                    connect=10,
                    sock_read=30,
                    sock_connect=10
                )
                
                async with session.post(
                    f"{self.base_url}/file",
                    data=form_data,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    upload_time = time.time() - start_time
                    response_text = await response.text()
                    
                    if response.status in [200, 201]:
                        try:
                            result = json.loads(response_text)
                            file_id = result.get('id')
                            
                            if file_id:
                                return {
                                    'success': True,
                                    'file_id': file_id,
                                    'direct_url': f"https://pixeldrain.com/api/file/{file_id}",
                                    'view_url': f"https://pixeldrain.com/u/{file_id}",
                                    'name': filename,
                                    'size': len(file_data),
                                    'upload_time': upload_time,
                                    'message': 'File uploaded successfully'
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': f"No file ID in response",
                                    'response_text': response_text,
                                    'upload_time': upload_time
                                }
                                
                        except json.JSONDecodeError:
                            file_id = response_text.strip().split()[-1] if response_text.strip() else None
                            
                            if file_id:
                                return {
                                    'success': True,
                                    'file_id': file_id,
                                    'direct_url': f"https://pixeldrain.com/api/file/{file_id}",
                                    'view_url': f"https://pixeldrain.com/u/{file_id}",
                                    'name': filename,
                                    'size': len(file_data),
                                    'upload_time': upload_time,
                                    'message': 'File uploaded successfully'
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': f"Invalid response format",
                                    'response_text': response_text,
                                    'upload_time': upload_time
                                }
                    else:
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}: {response_text[:100]}",
                            'status': response.status,
                            'upload_time': upload_time
                        }
                        
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'Upload timeout after 60 seconds',
                'upload_time': 60.0
            }
        except Exception as e:
            logger.error(f"PixelDrain upload error: {e}")
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }