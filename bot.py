#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM REPORTING SYSTEM v9.0
Complete Proxy Verification, Account Management & Realistic Reporting
"""

import asyncio
import time
import re
import json
import logging
import random
import string
import hashlib
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import aiofiles
import aiohttp
import sys
import os
import shutil
from collections import defaultdict, deque
import csv
import math
import uuid
from dataclasses import dataclass, field
import pickle
import base64
from io import BytesIO
import urllib.parse

# Telegram Bot API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# Telethon for Telegram Client
from telethon import TelegramClient, events, Button
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, AuthKeyDuplicatedError, UserNotParticipantError
)
from telethon.tl.functions.messages import ReportRequest, SendReactionRequest, GetMessagesRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantsRequest, GetFullChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import ReportPeerRequest, UpdateProfileRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonPornography,
    InputReportReasonChildAbuse, InputReportReasonCopyright, InputReportReasonGeoIrrelevant,
    InputReportReasonFake, InputReportReasonIllegalDrugs, InputReportReasonPersonalDetails,
    InputReportReasonOther, PeerUser, PeerChannel, PeerChat,
    InputPeerUser, InputPeerChannel, InputPeerChat,
    User, Channel, Chat, UserProfilePhoto, ChannelFull,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRow,
    ReactionEmoji, MessageEntityTextUrl, MessageEntityMention,
    InputMessageEntityMentionName
)

# Rich for console output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.columns import Columns
from rich.live import Live
from rich.text import Text
from rich import box
from rich.syntax import Syntax

console = Console()

# ===== CONFIGURATION =====
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# Owners (full access)
OWNER_IDS = [6118760915, 1366105247]

# Fast response countries (Telegram servers respond fastest from these)
FAST_COUNTRIES = ["Germany", "Netherlands", "Singapore", "Finland", "Ireland", "Japan"]

# Session and data directories
SESSION_DIR = Path("sessions")
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
EXPORTS_DIR = Path("exports")
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "data.txt"
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"
JOB_HISTORY_FILE = DATA_DIR / "job_history.json"

# Create directories
for dir_path in [SESSION_DIR, DATA_DIR, LOGS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ===== DATA MODELS =====

class UserRole(Enum):
    OWNER = "OWNER"
    SUDO = "SUDO"
    USER = "USER"

class ReportPriority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class ReportStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FLOOD_WAIT = "FLOOD_WAIT"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"

class AccountStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BANNED = "BANNED"
    FLOOD_WAIT = "FLOOD_WAIT"
    VERIFICATION_NEEDED = "VERIFICATION_NEEDED"
    NEED_PASSWORD = "NEED_PASSWORD"
    PROXY_FAILED = "PROXY_FAILED"

@dataclass
class TelegramUser:
    """Telegram user with role management"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    role: UserRole = UserRole.USER
    added_at: datetime = field(default_factory=datetime.now)
    reports_made: int = 0
    last_active: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "role": self.role.value,
            "added_at": self.added_at.isoformat(),
            "reports_made": self.reports_made,
            "last_active": self.last_active.isoformat() if self.last_active else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TelegramUser':
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            role=UserRole(data.get("role", "USER")),
            reports_made=data.get("reports_made", 0)
        )
        if data.get("added_at"):
            user.added_at = datetime.fromisoformat(data["added_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        return user

@dataclass
class TelegramAccount:
    """Telegram account with session management"""
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    client: Optional[TelegramClient] = None
    status: AccountStatus = AccountStatus.INACTIVE
    report_count: int = 0
    last_report_time: Optional[datetime] = None
    total_reports: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    country: Optional[str] = None
    is_premium: bool = False
    last_proxy_rotation: Optional[datetime] = None
    device_model: str = "Desktop"
    system_version: str = "Windows 10"
    app_version: str = "4.0.0"
    proxy_verified: bool = False
    proxy_response_time: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "phone": self.phone,
            "session_file": str(self.session_file),
            "proxy": self.proxy,
            "status": self.status.value,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "tags": self.tags,
            "country": self.country,
            "is_premium": self.is_premium,
            "last_proxy_rotation": self.last_proxy_rotation.isoformat() if self.last_proxy_rotation else None,
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "proxy_verified": self.proxy_verified,
            "proxy_response_time": self.proxy_response_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TelegramAccount':
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0),
            country=data.get("country"),
            is_premium=data.get("is_premium", False),
            device_model=data.get("device_model", "Desktop"),
            system_version=data.get("system_version", "Windows 10"),
            app_version=data.get("app_version", "4.0.0"),
            proxy_verified=data.get("proxy_verified", False),
            proxy_response_time=data.get("proxy_response_time")
        )
        if data.get("created_at"):
            account.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            account.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_proxy_rotation"):
            account.last_proxy_rotation = datetime.fromisoformat(data["last_proxy_rotation"])
        account.tags = data.get("tags", [])
        return account

@dataclass
class ProxyEntry:
    """Proxy entry with verification stats"""
    proxy: str
    country: str
    is_active: bool = True
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    reports_used: int = 0
    priority: float = 1.0
    last_verified: Optional[datetime] = None
    verified: bool = False
    verification_attempts: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "proxy": self.proxy,
            "country": self.country,
            "is_active": self.is_active,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "avg_response_time": self.avg_response_time,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "reports_used": self.reports_used,
            "priority": self.priority,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "verified": self.verified,
            "verification_attempts": self.verification_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProxyEntry':
        entry = cls(
            proxy=data["proxy"],
            country=data["country"],
            is_active=data.get("is_active", True),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            avg_response_time=data.get("avg_response_time", 0.0),
            reports_used=data.get("reports_used", 0),
            priority=data.get("priority", 1.0),
            verified=data.get("verified", False),
            verification_attempts=data.get("verification_attempts", 0)
        )
        if data.get("last_used"):
            entry.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_verified"):
            entry.last_verified = datetime.fromisoformat(data["last_verified"])
        return entry

# ===== COMPLETE PROXY MANAGER WITH VERIFICATION =====

class UltimateProxyManager:
    """Complete proxy manager with verification and rotation"""
    
    def __init__(self):
        self.proxies: List[ProxyEntry] = []
        self.proxy_history: Dict[str, List] = defaultdict(list)
        self.fast_countries = FAST_COUNTRIES
        self.max_reports_per_proxy = 9
        self.proxy_cache_file = PROXY_CACHE_FILE
        self.verification_lock = asyncio.Lock()
        self.verification_tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize proxy manager with verification"""
        console.print("[cyan]🚀 Initializing Ultimate Proxy Manager...[/cyan]")
        
        # Step 1: Load proxies from data.txt
        await self._load_proxies_from_file()
        
        if not self.proxies:
            console.print("[red]❌ No proxies found in data.txt[/red]")
            return False
        
        console.print(f"[green]✅ Loaded {len(self.proxies)} raw proxies[/green]")
        
        # Step 2: Load cache for existing proxy stats
        await self._load_cache()
        
        # Step 3: Verify all proxies
        console.print("[yellow]🔍 Verifying all proxies...[/yellow]")
        
        verification_results = await self.verify_all_proxies()
        
        working = sum(1 for p in self.proxies if p.verified and p.is_active)
        console.print(f"[green]✅ {working}/{len(self.proxies)} proxies verified and working[/green]")
        
        if working == 0:
            console.print("[red]❌ No working proxies available[/red]")
            return False
        
        # Step 4: Sort proxies by performance
        self._sort_proxies_by_performance()
        
        # Step 5: Display proxy statistics
        self._display_proxy_stats()
        
        return True
    
    async def _load_proxies_from_file(self):
        """Load proxies from data.txt file"""
        try:
            if not PROXY_FILE.exists():
                console.print(f"[yellow]⚠️ {PROXY_FILE} not found. Creating empty file.[/yellow]")
                PROXY_FILE.parent.mkdir(parents=True, exist_ok=True)
                PROXY_FILE.write_text("# Add proxies here (one per line)\n# Format: ip:port or user:pass@ip:port\n")
                return
            
            with open(PROXY_FILE, 'r') as f:
                lines = f.readlines()
            
            proxy_count = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Clean and validate proxy
                proxy = line.strip()
                if ':' not in proxy:
                    console.print(f"[yellow]⚠️ Invalid proxy format: {line}[/yellow]")
                    continue
                
                # Detect country from proxy (if possible)
                country = self._detect_country_from_proxy(proxy)
                
                # Calculate initial priority
                priority = 2.0 if country in self.fast_countries else 1.0
                
                proxy_entry = ProxyEntry(
                    proxy=proxy,
                    country=country,
                    priority=priority
                )
                
                self.proxies.append(proxy_entry)
                proxy_count += 1
            
            if proxy_count > 0:
                console.print(f"[green]✅ Successfully loaded {proxy_count} proxies[/green]")
            else:
                console.print("[yellow]⚠️ No valid proxies found in file[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Error loading proxies: {e}[/red]")
    
    def _detect_country_from_proxy(self, proxy: str) -> str:
        """Try to detect country from proxy string"""
        proxy_lower = proxy.lower()
        
        country_patterns = {
            "de": "Germany",
            "germany": "Germany",
            "berlin": "Germany",
            "frankfurt": "Germany",
            "nl": "Netherlands",
            "netherlands": "Netherlands",
            "amsterdam": "Netherlands",
            "sg": "Singapore",
            "singapore": "Singapore",
            "fi": "Finland",
            "finland": "Finland",
            "helsinki": "Finland",
            "ie": "Ireland",
            "ireland": "Ireland",
            "dublin": "Ireland",
            "jp": "Japan",
            "japan": "Japan",
            "tokyo": "Japan",
            "us": "United States",
            "usa": "United States",
            "united states": "United States",
            "new york": "United States",
            "fr": "France",
            "france": "France",
            "paris": "France",
            "gb": "United Kingdom",
            "uk": "United Kingdom",
            "united kingdom": "United Kingdom",
            "london": "United Kingdom"
        }
        
        for pattern, country in country_patterns.items():
            if pattern in proxy_lower:
                return country
        
        # Default to fast country if unknown
        return "Unknown"
    
    async def _load_cache(self):
        """Load proxy cache from file"""
        try:
            if self.proxy_cache_file.exists():
                with open(self.proxy_cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Match proxies with cache
                for proxy_data in cache_data.get("proxies", []):
                    for proxy_entry in self.proxies:
                        if proxy_entry.proxy == proxy_data["proxy"]:
                            # Update with cached data
                            proxy_entry.is_active = proxy_data.get("is_active", True)
                            proxy_entry.success_count = proxy_data.get("success_count", 0)
                            proxy_entry.fail_count = proxy_data.get("fail_count", 0)
                            proxy_entry.avg_response_time = proxy_data.get("avg_response_time", 0.0)
                            proxy_entry.reports_used = proxy_data.get("reports_used", 0)
                            proxy_entry.priority = proxy_data.get("priority", 1.0)
                            proxy_entry.verified = proxy_data.get("verified", False)
                            proxy_entry.verification_attempts = proxy_data.get("verification_attempts", 0)
                            
                            if proxy_data.get("last_used"):
                                proxy_entry.last_used = datetime.fromisoformat(proxy_data["last_used"])
                            if proxy_data.get("last_verified"):
                                proxy_entry.last_verified = datetime.fromisoformat(proxy_data["last_verified"])
                            break
                
                console.print("[green]✅ Loaded proxy cache[/green]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading cache: {e}[/yellow]")
    
    async def save_cache(self):
        """Save proxy cache to file"""
        try:
            cache_data = {
                "proxies": [proxy.to_dict() for proxy in self.proxies],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.proxy_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            console.print("[green]✅ Proxy cache saved[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error saving cache: {e}[/red]")
    
    async def verify_all_proxies(self) -> Dict:
        """Verify all proxies in parallel"""
        console.print("[cyan]🔍 Starting proxy verification...[/cyan]")
        
        verification_tasks = []
        for proxy_entry in self.proxies:
            task = self._verify_single_proxy(proxy_entry)
            verification_tasks.append(task)
        
        # Run verification with concurrency limit
        results = []
        batch_size = 5
        for i in range(0, len(verification_tasks), batch_size):
            batch = verification_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
            
            # Display progress
            verified = sum(1 for p in self.proxies[:i + len(batch)] if p.verified)
            total = i + len(batch)
            console.print(f"[cyan]📊 Verified {verified}/{total} proxies[/cyan]")
        
        # Save verification results
        await self.save_cache()
        
        return {
            "total": len(self.proxies),
            "verified": sum(1 for p in self.proxies if p.verified),
            "active": sum(1 for p in self.proxies if p.is_active),
            "fast_country": sum(1 for p in self.proxies if p.country in self.fast_countries and p.verified)
        }
    
    async def _verify_single_proxy(self, proxy_entry: ProxyEntry) -> bool:
        """Verify a single proxy"""
        try:
            # Skip if recently verified
            if proxy_entry.last_verified and (datetime.now() - proxy_entry.last_verified).seconds < 300:
                return proxy_entry.verified
            
            proxy_entry.verification_attempts += 1
            
            # Test connection to Telegram
            test_client = TelegramClient(
                str(SESSION_DIR / f"test_{hash(proxy_entry.proxy) % 1000}.session"),
                API_ID,
                API_HASH,
                timeout=10,
                connection_retries=1
            )
            
            # Set proxy
            test_client.set_proxy(proxy_entry.proxy)
            
            start_time = time.time()
            
            # Try to connect
            await test_client.connect()
            
            # Test by getting a random entity (Telegram's DC info)
            try:
                await test_client.get_me()
                response_time = time.time() - start_time
                
                # Success
                proxy_entry.verified = True
                proxy_entry.is_active = True
                proxy_entry.success_count += 1
                
                # Update response time average
                if proxy_entry.avg_response_time == 0:
                    proxy_entry.avg_response_time = response_time
                else:
                    proxy_entry.avg_response_time = (proxy_entry.avg_response_time * (proxy_entry.success_count - 1) + response_time) / proxy_entry.success_count
                
                # Adjust priority based on response time
                if proxy_entry.country in self.fast_countries:
                    base_priority = 2.0
                else:
                    base_priority = 1.0
                
                # Faster response = higher priority
                speed_factor = max(0.1, 1.0 / (response_time + 0.1))
                proxy_entry.priority = base_priority * speed_factor
                
                proxy_entry.last_verified = datetime.now()
                
                console.print(f"[green]✅ Proxy verified: {proxy_entry.proxy[:30]}... ({response_time:.2f}s)[/green]")
                return True
                
            except Exception as e:
                console.print(f"[yellow]⚠️ Proxy test failed: {proxy_entry.proxy[:30]}... - {str(e)[:50]}[/yellow]")
                proxy_entry.fail_count += 1
                
                if proxy_entry.fail_count >= 3:
                    proxy_entry.is_active = False
                    proxy_entry.verified = False
                
            finally:
                await test_client.disconnect()
                
        except Exception as e:
            console.print(f"[red]❌ Proxy verification error: {proxy_entry.proxy[:30]}... - {str(e)[:50]}[/red]")
            proxy_entry.fail_count += 1
            
            if proxy_entry.fail_count >= 2:
                proxy_entry.is_active = False
                proxy_entry.verified = False
        
        return False
    
    def _sort_proxies_by_performance(self):
        """Sort proxies by priority and performance"""
        self.proxies.sort(key=lambda x: (
            0 if x.verified else 1,
            0 if x.is_active else 1,
            -x.priority,  # Higher priority first
            x.avg_response_time if x.avg_response_time > 0 else 1000,
            -x.success_count
        ))
    
    def _display_proxy_stats(self):
        """Display proxy statistics"""
        active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        fast_proxies = [p for p in active_proxies if p.country in self.fast_countries]
        
        table = Table(title="Proxy Statistics", box=box.ROUNDED)
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Details", style="yellow")
        
        table.add_row("✅ Active & Verified", str(len(active_proxies)), f"Ready for use")
        table.add_row("⚡ Fast Countries", str(len(fast_proxies)), f"{', '.join(set(p.country for p in fast_proxies))[:50]}")
        table.add_row("📊 Total Proxies", str(len(self.proxies)), f"Loaded from data.txt")
        
        # Country distribution
        country_dist = defaultdict(int)
        for proxy in active_proxies:
            country_dist[proxy.country] += 1
        
        console.print(table)
        
        # Show top 10 fastest proxies
        if active_proxies:
            fast_proxies_sorted = sorted(active_proxies, key=lambda x: x.avg_response_time)[:10]
            
            speed_table = Table(title="Fastest Proxies", box=box.ROUNDED)
            speed_table.add_column("#", style="cyan")
            speed_table.add_column("Proxy", style="green")
            speed_table.add_column("Country", style="yellow")
            speed_table.add_column("Speed", style="magenta")
            speed_table.add_column("Success", style="blue")
            
            for i, proxy in enumerate(fast_proxies_sorted, 1):
                proxy_display = proxy.proxy[:25] + "..." if len(proxy.proxy) > 25 else proxy.proxy
                country_display = proxy.country[:15]
                speed_display = f"{proxy.avg_response_time:.2f}s"
                success_display = f"{proxy.success_count}"
                
                speed_table.add_row(str(i), proxy_display, country_display, speed_display, success_display)
            
            console.print(speed_table)
    
    async def get_best_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """Get the best available proxy for an account"""
        # Get active verified proxies
        available = [p for p in self.proxies if p.is_active and p.verified and p.reports_used < self.max_reports_per_proxy]
        
        if not available:
            console.print("[yellow]⚠️ No fresh proxies, reusing...[/yellow]")
            available = [p for p in self.proxies if p.is_active and p.verified]
        
        if not available:
            console.print("[red]❌ No available proxies[/red]")
            return None
        
        # Check account's proxy history
        if account_phone in self.proxy_history:
            recent_proxies = set()
            for entry in self.proxy_history[account_phone][-3:]:  # Last 3 proxies used
                recent_proxies.add(entry["proxy"])
            
            # Filter out recently used proxies
            fresh_proxies = [p for p in available if p.proxy not in recent_proxies]
            if fresh_proxies:
                available = fresh_proxies
        
        # Sort by priority and usage
        available.sort(key=lambda x: (
            -x.priority,
            x.reports_used,
            x.avg_response_time
        ))
        
        if not available:
            return None
        
        selected = available[0]
        selected.last_used = datetime.now()
        selected.reports_used += 1
        
        # Record in history
        self.proxy_history[account_phone].append({
            "proxy": selected.proxy,
            "time": datetime.now().isoformat(),
            "country": selected.country,
            "reports_used": selected.reports_used
        })
        
        # Limit history size
        if len(self.proxy_history[account_phone]) > 10:
            self.proxy_history[account_phone] = self.proxy_history[account_phone][-10:]
        
        console.print(f"[cyan]📡 Selected proxy for {account_phone}: {selected.country} ({selected.avg_response_time:.2f}s)[/cyan]")
        return selected.proxy
    
    async def rotate_proxy_for_account(self, account_phone: str, force: bool = False) -> Optional[str]:
        """Rotate proxy for an account"""
        if account_phone in self.proxy_history and self.proxy_history[account_phone]:
            last_proxy = self.proxy_history[account_phone][-1]["proxy"]
            
            # Mark last proxy as needing rotation
            for proxy in self.proxies:
                if proxy.proxy == last_proxy:
                    if force or proxy.reports_used >= self.max_reports_per_proxy:
                        proxy.reports_used = self.max_reports_per_proxy
                        console.print(f"[yellow]🔄 Rotating proxy for {account_phone} (used {proxy.reports_used} times)[/yellow]")
                    break
        
        # Get new proxy
        return await self.get_best_proxy_for_account(account_phone)
    
    def mark_proxy_success(self, proxy_url: str, response_time: float):
        """Mark proxy as successful"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.success_count += 1
                
                # Update average response time
                if proxy.avg_response_time == 0:
                    proxy.avg_response_time = response_time
                else:
                    proxy.avg_response_time = (proxy.avg_response_time * (proxy.success_count - 1) + response_time) / proxy.success_count
                
                # Increase priority for fast responses
                if proxy.country in self.fast_countries:
                    base_priority = 2.0
                else:
                    base_priority = 1.0
                
                speed_factor = max(0.1, 1.0 / (response_time + 0.1))
                proxy.priority = base_priority * speed_factor
                
                proxy.last_used = datetime.now()
                break
    
    def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.fail_count += 1
                proxy.reports_used = self.max_reports_per_proxy  # Mark for rotation
                
                # Decrease priority
                proxy.priority *= 0.7
                
                # Disable if too many failures
                if proxy.fail_count >= 3:
                    proxy.is_active = False
                    proxy.verified = False
                    console.print(f"[red]❌ Proxy disabled: {proxy_url[:30]}...[/red]")
                break
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        active = [p for p in self.proxies if p.is_active and p.verified]
        fast = [p for p in active if p.country in self.fast_countries]
        
        # Calculate average response time
        avg_response = 0
        if active:
            avg_response = sum(p.avg_response_time for p in active) / len(active)
        
        return {
            "total_proxies": len(self.proxies),
            "active_proxies": len(active),
            "fast_country_proxies": len(fast),
            "average_response_time": f"{avg_response:.2f}s",
            "fast_countries": self.fast_countries
        }

# ===== USER MANAGEMENT =====

class UserManager:
    """Manage bot users with roles"""
    
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self.users_file = USERS_FILE
        self.owner_ids = OWNER_IDS
        
        # Initialize with owners
        self._initialize_owners()
        self._load_users()
    
    def _initialize_owners(self):
        """Initialize owner accounts"""
        for owner_id in self.owner_ids:
            if owner_id not in self.users:
                self.users[owner_id] = TelegramUser(
                    user_id=owner_id,
                    role=UserRole.OWNER,
                    added_at=datetime.now()
                )
        console.print(f"[green]✅ Initialized {len(self.owner_ids)} owners[/green]")
    
    def _load_users(self):
        """Load users from file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.values():
                        user = TelegramUser.from_dict(user_data)
                        self.users[user.user_id] = user
                console.print(f"[green]✅ Loaded {len(self.users)} users[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading users: {e}[/red]")
    
    def _save_users(self):
        """Save users to file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving users: {e}[/red]")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                role: UserRole = UserRole.USER) -> bool:
        """Add a new user"""
        if user_id in self.users:
            return False
        
        user = TelegramUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            role=role,
            added_at=datetime.now()
        )
        
        self.users[user_id] = user
        self._save_users()
        
        console.print(f"[green]✅ Added user {user_id} with role {role.value}[/green]")
        return True
    
    def promote_to_sudo(self, user_id: int) -> bool:
        """Promote user to sudo"""
        if user_id not in self.users:
            return False
        
        self.users[user_id].role = UserRole.SUDO
        self._save_users()
        
        console.print(f"[green]✅ Promoted user {user_id} to SUDO[/green]")
        return True
    
    def demote_from_sudo(self, user_id: int) -> bool:
        """Demote user from sudo"""
        if user_id not in self.users or user_id in self.owner_ids:
            return False
        
        self.users[user_id].role = UserRole.USER
        self._save_users()
        
        console.print(f"[yellow]⚠️ Demoted user {user_id} to USER[/yellow]")
        return True
    
    def get_user_role(self, user_id: int) -> Optional[UserRole]:
        """Get user role"""
        if user_id in self.users:
            return self.users[user_id].role
        return None
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id in self.owner_ids
    
    def is_sudo(self, user_id: int) -> bool:
        """Check if user is sudo or owner"""
        if user_id in self.owner_ids:
            return True
        return user_id in self.users and self.users[user_id].role == UserRole.SUDO
    
    def can_add_accounts(self, user_id: int) -> bool:
        """Check if user can add accounts"""
        return self.is_owner(user_id) or self.is_sudo(user_id)
    
    def update_user_activity(self, user_id: int, username: str = None, first_name: str = None):
        """Update user last activity"""
        if user_id not in self.users:
            self.add_user(user_id, username, first_name)
        else:
            self.users[user_id].last_active = datetime.now()
            if username:
                self.users[user_id].username = username
            if first_name:
                self.users[user_id].first_name = first_name
            self._save_users()
    
    def increment_reports(self, user_id: int):
        """Increment reports made by user"""
        if user_id in self.users:
            self.users[user_id].reports_made += 1
            self._save_users()
    
    def get_stats(self) -> Dict:
        """Get user statistics"""
        total = len(self.users)
        owners = sum(1 for u in self.users.values() if u.role == UserRole.OWNER)
        sudo_users = sum(1 for u in self.users.values() if u.role == UserRole.SUDO)
        regular_users = total - owners - sudo_users
        
        total_reports = sum(u.reports_made for u in self.users.values())
        
        return {
            "total_users": total,
            "owners": owners,
            "sudo_users": sudo_users,
            "regular_users": regular_users,
            "total_reports": total_reports
        }

# ===== COMPLETE ACCOUNT MANAGER =====

class CompleteAccountManager:
    """Complete account manager with proxy verification and session creation"""
    
    def __init__(self, proxy_manager: UltimateProxyManager):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.proxy_manager = proxy_manager
        self.accounts_file = ACCOUNTS_FILE
        self.max_reports_per_account = 9
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from file"""
        try:
            if self.accounts_file.exists():
                with open(self.accounts_file, 'r') as f:
                    data = json.load(f)
                    for phone, acc_data in data.items():
                        account = TelegramAccount.from_dict(acc_data)
                        self.accounts[phone] = account
                console.print(f"[green]✅ Loaded {len(self.accounts)} accounts[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading accounts: {e}[/red]")
    
    def _save_accounts(self):
        """Save accounts to file"""
        try:
            data = {phone: account.to_dict() for phone, account in self.accounts.items()}
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving accounts: {e}[/red]")
    
    async def add_account(self, phone: str) -> Tuple[bool, str]:
        """Add a new account with verified proxy"""
        if phone in self.accounts:
            return False, "Account already exists"
        
        # Get verified proxy
        proxy = await self.proxy_manager.get_best_proxy_for_account(phone)
        if not proxy:
            return False, "No verified proxies available"
        
        # Create session file path
        session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.INACTIVE,
            proxy_verified=True
        )
        
        self.accounts[phone] = account
        self._save_accounts()
        
        console.print(f"[green]✅ Added account: {phone} with verified proxy[/green]")
        return True, f"Account {phone} added successfully with proxy"
    
    async def create_desktop_session(self, phone: str, update: Update, user_id: int) -> bool:
        """Create desktop session for account"""
        try:
            if phone not in self.accounts:
                await update.message.reply_text("❌ Account not found. Please add account first.")
                return False
            
            account = self.accounts[phone]
            
            # Random desktop configuration
            desktop_configs = [
                {"model": "Desktop", "sys_ver": "Windows 10", "app_ver": "4.0.0"},
                {"model": "Desktop", "sys_ver": "Windows 11", "app_ver": "4.1.0"},
                {"model": "Mac", "sys_ver": "macOS 14.0", "app_ver": "4.0.0"},
                {"model": "Linux", "sys_ver": "Ubuntu 22.04", "app_ver": "3.8.0"},
            ]
            
            config = random.choice(desktop_configs)
            account.device_model = config["model"]
            account.system_version = config["sys_ver"]
            account.app_version = config["app_ver"]
            
            await update.message.reply_text(
                f"🖥️ *Creating Desktop Session*\n\n"
                f"Phone: `{phone}`\n"
                f"Device: {config['model']} ({config['sys_ver']})\n"
                f"App: Telegram Desktop {config['app_ver']}\n"
                f"Proxy: Verified ({account.country if account.country else 'Auto'})\n\n"
                f"⏳ Connecting to Telegram...",
                parse_mode='Markdown'
            )
            
            # Create client with desktop configuration
            client = TelegramClient(
                str(account.session_file),
                API_ID,
                API_HASH,
                device_model=account.device_model,
                system_version=account.system_version,
                app_version=account.app_version,
                lang_code="en",
                system_lang_code="en-US"
            )
            
            # Set verified proxy
            if account.proxy:
                client.set_proxy(account.proxy)
            
            # Connect and send code
            await client.connect()
            
            await update.message.reply_text(
                "📱 *Requesting Login Code*\n\n"
                "Sending verification code to your phone...",
                parse_mode='Markdown'
            )
            
            # Send code request
            try:
                sent_code = await client.send_code_request(phone)
                phone_code_hash = sent_code.phone_code_hash
                
                # Store for OTP verification
                if hasattr(update, '_user_sessions'):
                    update._user_sessions[user_id] = {
                        "phone": phone,
                        "client": client,
                        "phone_code_hash": phone_code_hash,
                        "step": "waiting_otp",
                        "created_at": datetime.now()
                    }
                
                await update.message.reply_text(
                    f"✅ *Code Sent Successfully!*\n\n"
                    f"A 5-digit login code has been sent to `{phone}`\n\n"
                    f"Please reply with the code in format: `12345`\n\n"
                    f"_You have 5 minutes to enter the code._",
                    parse_mode='Markdown'
                )
                
                return True
                
            except FloodWaitError as e:
                await update.message.reply_text(
                    f"⏳ Please wait {e.seconds} seconds before trying again."
                )
                return False
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Error sending code: {str(e)}"
                )
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error creating session: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    async def verify_otp(self, phone: str, otp: str, update: Update, user_id: int) -> bool:
        """Verify OTP and complete login"""
        try:
            if not hasattr(update, '_user_sessions'):
                await update.message.reply_text("❌ Session expired. Please start over.")
                return False
            
            if user_id not in update._user_sessions:
                await update.message.reply_text("❌ Session not found. Please start over.")
                return False
            
            session_data = update._user_sessions[user_id]
            
            if session_data["phone"] != phone:
                await update.message.reply_text("❌ Phone number mismatch.")
                return False
            
            client = session_data["client"]
            phone_code_hash = session_data["phone_code_hash"]
            
            await update.message.reply_text(
                "🔐 *Verifying Code...*",
                parse_mode='Markdown'
            )
            
            # Verify OTP
            try:
                await client.sign_in(
                    phone=phone,
                    code=otp,
                    phone_code_hash=phone_code_hash
                )
                
            except SessionPasswordNeededError:
                # 2FA required
                update._user_sessions[user_id]["step"] = "need_password"
                await update.message.reply_text(
                    "🔒 *Two-Factor Authentication Required*\n\n"
                    "This account has 2FA enabled.\n"
                    "Please reply with your 2FA password:",
                    parse_mode='Markdown'
                )
                return False
            
            # Update account status
            account = self.accounts[phone]
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            # Get account info
            try:
                me = await client.get_me()
                if hasattr(me, 'phone'):
                    # Extract country from phone
                    if me.phone.startswith('+'):
                        account.country = self._get_country_from_phone(me.phone)
                account.is_premium = getattr(me, 'premium', False)
            except:
                pass
            
            self._save_accounts()
            
            # Cleanup session
            if user_id in update._user_sessions:
                del update._user_sessions[user_id]
            
            await update.message.reply_text(
                f"✅ *Login Successful!*\n\n"
                f"Account: `{phone}`\n"
                f"Status: Active ✅\n"
                f"Device: {account.device_model}\n"
                f"Country: {account.country if account.country else 'Unknown'}\n"
                f"Premium: {'⭐ Yes' if account.is_premium else 'No'}\n\n"
                f"🎯 Ready for realistic reporting!",
                parse_mode='Markdown'
            )
            
            return True
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ Invalid code. Please try again.")
            return False
        except PhoneCodeExpiredError:
            await update.message.reply_text("❌ Code expired. Please start over.")
            if user_id in update._user_sessions:
                del update._user_sessions[user_id]
            return False
        except Exception as e:
            console.print(f"[red]❌ Error verifying OTP: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    async def verify_password(self, phone: str, password: str, update: Update, user_id: int) -> bool:
        """Verify 2FA password"""
        try:
            if not hasattr(update, '_user_sessions'):
                await update.message.reply_text("❌ Session expired.")
                return False
            
            if user_id not in update._user_sessions:
                await update.message.reply_text("❌ Session not found.")
                return False
            
            session_data = update._user_sessions[user_id]
            client = session_data["client"]
            
            await update.message.reply_text(
                "🔐 *Verifying 2FA Password...*",
                parse_mode='Markdown'
            )
            
            # Sign in with password
            await client.sign_in(password=password)
            
            # Update account
            account = self.accounts[phone]
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            self._save_accounts()
            
            # Cleanup
            if user_id in update._user_sessions:
                del update._user_sessions[user_id]
            
            await update.message.reply_text(
                f"✅ *2FA Login Successful!*\n\n"
                f"Account `{phone}` is now active and ready.",
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error verifying password: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    def _get_country_from_phone(self, phone: str) -> str:
        """Get country from phone number"""
        country_codes = {
            '+1': 'United States',
            '+44': 'United Kingdom',
            '+49': 'Germany',
            '+33': 'France',
            '+81': 'Japan',
            '+82': 'South Korea',
            '+65': 'Singapore',
            '+91': 'India',
            '+7': 'Russia',
            '+86': 'China',
            '+90': 'Turkey',
            '+55': 'Brazil',
            '+61': 'Australia',
            '+34': 'Spain',
            '+39': 'Italy',
            '+358': 'Finland',
            '+353': 'Ireland',
        }
        
        for code, country in country_codes.items():
            if phone.startswith(code):
                return country
        
        return "Unknown"
    
    async def get_available_accounts(self, count: int = 3) -> List[TelegramAccount]:
        """Get available accounts for reporting"""
        available = []
        
        # First priority: Active accounts with reports left
        for account in self.accounts.values():
            if account.status == AccountStatus.ACTIVE and account.report_count < self.max_reports_per_account:
                available.append(account)
                if len(available) >= count:
                    break
        
        # Second priority: Inactive accounts (need to activate)
        if len(available) < count:
            inactive = [acc for acc in self.accounts.values() 
                       if acc.status == AccountStatus.INACTIVE]
            available.extend(inactive[:count - len(available)])
        
        return available[:count]
    
    async def rotate_proxy_for_account(self, phone: str) -> bool:
        """Rotate proxy for an account after 9 reports"""
        if phone not in self.accounts:
            return False
        
        account = self.accounts[phone]
        
        # Check if rotation needed
        if account.report_count < self.max_reports_per_account:
            return True  # No rotation needed yet
        
        # Get new proxy
        new_proxy = await self.proxy_manager.rotate_proxy_for_account(phone, force=True)
        
        if new_proxy and new_proxy != account.proxy:
            account.proxy = new_proxy
            account.last_proxy_rotation = datetime.now()
            account.report_count = 0  # Reset counter
            account.proxy_verified = True
            
            self._save_accounts()
            
            console.print(f"[cyan]🔄 Rotated proxy for {phone}[/cyan]")
            return True
        elif new_proxy:
            # Same proxy but reset count
            account.report_count = 0
            self._save_accounts()
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get account statistics"""
        total = len(self.accounts)
        active = sum(1 for a in self.accounts.values() if a.status == AccountStatus.ACTIVE)
        inactive = sum(1 for a in self.accounts.values() if a.status == AccountStatus.INACTIVE)
        
        total_reports = sum(a.total_reports for a in self.accounts.values())
        today = datetime.now().date()
        reports_today = sum(a.report_count for a in self.accounts.values() 
                           if a.last_report_time and a.last_report_time.date() == today)
        
        # Count by proxy country
        proxy_countries = defaultdict(int)
        for account in self.accounts.values():
            if account.country:
                proxy_countries[account.country] += 1
        
        return {
            "total_accounts": total,
            "active_accounts": active,
            "inactive_accounts": inactive,
            "total_reports": total_reports,
            "reports_today": reports_today,
            "proxy_countries": dict(proxy_countries),
            "max_reports_per_account": self.max_reports_per_account
        }

# ===== REALISTIC REPORTING ENGINE =====

class RealisticReportingEngine:
    """Realistic reporting engine with proxy rotation"""
    
    def __init__(self, account_manager: CompleteAccountManager, proxy_manager: UltimateProxyManager, user_manager: UserManager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.active_jobs: Dict[str, Dict] = {}
        self.job_history: List[Dict] = []
        
        self._load_history()
        
        # Report categories
        self.report_categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs & Substances",
                "priority": "CRITICAL",
                "requires_description": True,
                "subcategories": {
                    1: {"name": "Drug Trafficking", "description": "Selling or distributing illegal drugs"},
                    2: {"name": "Drug Promotion", "description": "Promoting drug use or sale"},
                    3: {"name": "Drug Manufacturing", "description": "Manufacturing of illegal substances"},
                }
            },
            "SPAM": {
                "name": "Spam & Scams",
                "priority": "HIGH",
                "requires_description": True,
                "subcategories": {
                    1: {"name": "Mass Spamming", "description": "Mass messaging or posting"},
                    2: {"name": "Phishing Links", "description": "Malicious links or phishing"},
                    3: {"name": "Financial Scams", "description": "Financial fraud or scams"},
                }
            },
            "VIOLENCE": {
                "name": "Violence & Threats",
                "priority": "CRITICAL",
                "requires_description": True,
                "subcategories": {
                    1: {"name": "Physical Threats", "description": "Threats of physical harm"},
                    2: {"name": "Death Threats", "description": "Threats to kill someone"},
                    3: {"name": "Terrorist Content", "description": "Terrorism-related material"},
                }
            },
        }
    
    async def create_report_job(self, target: str, target_type: str, category: str, 
                              subcategory: int, description: str, user_id: int) -> str:
        """Create a new report job"""
        if category not in self.report_categories:
            raise ValueError(f"Invalid category: {category}")
        
        if subcategory not in self.report_categories[category]["subcategories"]:
            raise ValueError(f"Invalid subcategory: {subcategory}")
        
        subcategory_info = self.report_categories[category]["subcategories"][subcategory]
        
        job_id = hashlib.md5(f"{datetime.now()}{random.random()}{target}".encode()).hexdigest()[:12]
        
        job = {
            "job_id": job_id,
            "target": target,
            "target_type": target_type,
            "category": category,
            "subcategory": subcategory_info["name"],
            "description": description,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "status": "PENDING",
            "accounts_used": [],
            "results": []
        }
        
        self.active_jobs[job_id] = job
        return job_id
    
    async def execute_job(self, job_id: str) -> Dict:
        """Execute a report job with proxy rotation"""
        if job_id not in self.active_jobs:
            return {"error": "Job not found"}
        
        job = self.active_jobs[job_id]
        job["status"] = "PROCESSING"
        
        console.print(f"[cyan]🚀 Executing job {job_id}[/cyan]")
        
        # Get available accounts
        accounts = await self.account_manager.get_available_accounts(3)
        
        if len(accounts) < 1:
            job["status"] = "FAILED"
            return {"error": "No accounts available"}
        
        results = []
        
        # Process each account
        for i, account in enumerate(accounts):
            console.print(f"[yellow]👤 Account {i+1}/{len(accounts)}: {account.phone}[/yellow]")
            
            # Check if proxy rotation needed
            if account.report_count >= self.account_manager.max_reports_per_account:
                console.print(f"[cyan]🔄 Rotating proxy for {account.phone}...[/cyan]")
                rotated = await self.account_manager.rotate_proxy_for_account(account.phone)
                if not rotated:
                    console.print(f"[red]❌ Failed to rotate proxy for {account.phone}[/red]")
                    continue
            
            # Realistic delay between accounts
            if i > 0:
                delay = random.uniform(5.0, 15.0)
                console.print(f"[dim]⏳ Waiting {delay:.1f}s...[/dim]")
                await asyncio.sleep(delay)
            
            # Execute report
            result = await self._execute_single_report(account, job)
            results.append(result)
            
            if result.get("status") == "COMPLETED":
                job["accounts_used"].append(account.phone)
                
                # Update account stats
                account.report_count += 1
                account.total_reports += 1
                account.last_report_time = datetime.now()
                
                # Mark proxy success
                if account.proxy and result.get("response_time"):
                    self.proxy_manager.mark_proxy_success(account.proxy, result["response_time"])
        
        job["results"] = results
        job["completed_at"] = datetime.now().isoformat()
        
        # Update job status
        completed = len([r for r in results if r.get("status") == "COMPLETED"])
        if completed > 0:
            job["status"] = "COMPLETED"
        else:
            job["status"] = "FAILED"
        
        # Save account changes
        self.account_manager._save_accounts()
        
        # Add to history
        self.job_history.append(job)
        if len(self.job_history) > 100:
            self.job_history = self.job_history[-100:]
        self._save_history()
        
        # Update user stats
        self.user_manager.increment_reports(job["user_id"])
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "completed": completed,
            "total": len(accounts),
            "results": results
        }
    
    async def _execute_single_report(self, account: TelegramAccount, job: Dict) -> Dict:
        """Execute single report with desktop simulation"""
        start_time = time.time()
        
        try:
            # Initialize client if needed
            if not account.client or not account.client.is_connected():
                await self._initialize_client(account)
            
            if not account.client or not account.client.is_connected():
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Client not connected",
                    "response_time": 0
                }
            
            # Resolve target
            target_entity = await self._resolve_target(account.client, job["target"], job["target_type"])
            if not target_entity:
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Could not resolve target",
                    "response_time": time.time() - start_time
                }
            
            # Simulate desktop reporting
            console.print(f"[dim]🖥️ Simulating desktop report for {account.phone}[/dim]")
            
            # Desktop flow steps
            steps = [
                ("Opening Telegram Desktop", 2.0, 4.0),
                ("Searching for target", 1.5, 3.0),
                ("Viewing profile/channel", 3.0, 6.0),
                ("Opening report menu", 1.0, 2.0),
                ("Selecting report reason", 2.0, 4.0),
                ("Typing description", 3.0, 8.0),
                ("Submitting report", 1.0, 2.0),
            ]
            
            total_simulation = 0
            for step_name, min_time, max_time in steps:
                step_time = random.uniform(min_time, max_time)
                console.print(f"[dim]   {step_name}... ({step_time:.1f}s)[/dim]")
                await asyncio.sleep(step_time)
                total_simulation += step_time
            
            # Prepare report reason
            reason = self._get_reason_class(job["category"])
            
            # Prepare message (Desktop requires description)
            message = f"{job['subcategory']}: {job['description'][:200]}"
            
            # Execute report
            await account.client(ReportPeerRequest(
                peer=target_entity,
                reason=reason(),
                message=message
            ))
            
            response_time = time.time() - start_time
            
            # Final delay
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
            return {
                "account": account.phone,
                "status": "COMPLETED",
                "device": account.device_model,
                "proxy": account.proxy[:30] + "..." if account.proxy else None,
                "country": account.country,
                "simulation_time": total_simulation,
                "response_time": response_time,
                "report_count": account.report_count
            }
            
        except FloodWaitError as e:
            account.status = AccountStatus.FLOOD_WAIT
            return {
                "account": account.phone,
                "status": "FLOOD_WAIT",
                "error": f"Flood wait: {e.seconds}s",
                "response_time": time.time() - start_time
            }
        except Exception as e:
            if account.proxy:
                self.proxy_manager.mark_proxy_failed(account.proxy)
            
            return {
                "account": account.phone,
                "status": "FAILED",
                "error": str(e)[:100],
                "response_time": time.time() - start_time
            }
    
    async def _initialize_client(self, account: TelegramAccount) -> bool:
        """Initialize Telegram client"""
        try:
            if account.client and account.client.is_connected():
                return True
            
            client = TelegramClient(
                str(account.session_file),
                API_ID,
                API_HASH,
                device_model=account.device_model,
                system_version=account.system_version,
                app_version=account.app_version
            )
            
            if account.proxy:
                client.set_proxy(account.proxy)
            
            await client.start()
            account.client = client
            account.status = AccountStatus.ACTIVE
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Failed to initialize client for {account.phone}: {e}[/red]")
            account.status = AccountStatus.INACTIVE
            return False
    
    def _get_reason_class(self, category: str):
        """Get Telethon reason class"""
        mapping = {
            "ILLEGAL_DRUGS": InputReportReasonIllegalDrugs,
            "SPAM": InputReportReasonSpam,
            "VIOLENCE": InputReportReasonViolence,
            "SEXUAL": InputReportReasonPornography,
            "FRAUD": InputReportReasonFake,
            "HARASSMENT": InputReportReasonPersonalDetails,
            "COPYRIGHT": InputReportReasonCopyright,
            "OTHER": InputReportReasonOther
        }
        return mapping.get(category, InputReportReasonOther)
    
    async def _resolve_target(self, client, target: str, target_type: str):
        """Resolve target entity"""
        try:
            target = target.strip()
            
            # Handle @username
            if target.startswith("@"):
                return await client.get_entity(target[1:])
            
            # Handle t.me links
            if "t.me/" in target:
                if target.startswith("https://t.me/joinchat/"):
                    # Group invite
                    return await client.get_entity(target)
                else:
                    # User/channel
                    username = target.split("/")[-1]
                    return await client.get_entity(username)
            
            # Try as-is
            return await client.get_entity(target)
            
        except Exception as e:
            console.print(f"[red]❌ Failed to resolve target {target}: {e}[/red]")
            return None
    
    def _save_history(self):
        """Save job history"""
        try:
            with open(JOB_HISTORY_FILE, 'w') as f:
                json.dump(self.job_history, f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving history: {e}[/red]")
    
    def _load_history(self):
        """Load job history"""
        try:
            if JOB_HISTORY_FILE.exists():
                with open(JOB_HISTORY_FILE, 'r') as f:
                    self.job_history = json.load(f)
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading history: {e}[/yellow]")
    
    def get_stats(self) -> Dict:
        """Get reporting engine statistics"""
        return {
            "total_jobs": len(self.job_history),
            "active_jobs": len(self.active_jobs),
            "completed_jobs": sum(1 for j in self.job_history if j.get("status") == "COMPLETED"),
            "failed_jobs": sum(1 for j in self.job_history if j.get("status") == "FAILED")
        }

# ===== TELEGRAM BOT HANDLER =====

class TelegramBotHandler:
    """Telegram bot handler with conversation management"""
    
    def __init__(self, user_manager: UserManager, account_manager: CompleteAccountManager, reporting_engine: RealisticReportingEngine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        
        # Conversation states
        self.ADD_PHONE, self.ADD_OTP, self.ADD_PASSWORD = range(3)
        self.REPORT_TARGET, self.REPORT_CATEGORY, self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(4)
        
        # User sessions
        self.user_sessions = {}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        self.user_manager.update_user_activity(user.id, user.username, user.first_name)
        
        role = self.user_manager.get_user_role(user.id)
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        welcome_text = f"""
🤖 *Ultimate Telegram Reporting System v9.0*

*Your Role:* {role_text}

*Features:*
• Complete proxy verification system
• Desktop session creation
• 9 reports per account limit
• Automatic proxy rotation
• Realistic human simulation
• Owner/Sudo user management

*Commands:*
/start - Show this message
/add - Add new account (Owner/Sudo only)
/report - Start realistic reporting
/stats - View system statistics
/accounts - List accounts (Owner/Sudo only)
/jobs - View active jobs
/help - Show help

*Admin Commands:*
/addsudo [id] - Add sudo user (Owner only)
/listsudo - List sudo users (Owner only)
/removesudo [id] - Remove sudo user (Owner only)
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - Add new account"""
        user = update.effective_user
        
        if not self.user_manager.can_add_accounts(user.id):
            await update.message.reply_text("❌ Permission denied. Owner/Sudo required.")
            return
        
        self.user_sessions[user.id] = {"step": "phone"}
        
        await update.message.reply_text(
            "📱 *Add New Account*\n\n"
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`\n\n"
            "_You will receive an OTP on this phone._",
            parse_mode='Markdown'
        )
        
        return self.ADD_PHONE
    
    async def handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        phone = update.message.text.strip()
        
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ Invalid phone number.\n"
                "Format: `+1234567890`",
                parse_mode='Markdown'
            )
            return self.ADD_PHONE
        
        # Add account
        success, message = await self.account_manager.add_account(phone)
        
        if not success:
            await update.message.reply_text(f"❌ {message}")
            return ConversationHandler.END
        
        # Store in session
        self.user_sessions[user_id]["phone"] = phone
        
        # Create desktop session
        session_created = await self.account_manager.create_desktop_session(phone, update, user_id)
        
        if session_created:
            return self.ADD_OTP
        else:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
    
    async def handle_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle OTP input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        otp = update.message.text.strip()
        
        if not re.match(r'^\d{5}$', otp):
            await update.message.reply_text(
                "❌ Invalid OTP.\n"
                "Format: `12345`",
                parse_mode='Markdown'
            )
            return self.ADD_OTP
        
        phone = self.user_sessions[user_id]["phone"]
        
        # Verify OTP
        success = await self.account_manager.verify_otp(phone, otp, update, user_id)
        
        if success:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        else:
            # Check if password is needed
            if hasattr(update, '_user_sessions') and user_id in update._user_sessions:
                if update._user_sessions[user_id].get("step") == "need_password":
                    return self.ADD_PASSWORD
            
            return self.ADD_OTP
    
    async def handle_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 2FA password"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        password = update.message.text.strip()
        phone = self.user_sessions[user_id]["phone"]
        
        success = await self.account_manager.verify_password(phone, password, update, user_id)
        
        if success:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
        
        return ConversationHandler.END
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        user = update.effective_user
        
        self.user_manager.update_user_activity(user.id, user.username, user.first_name)
        
        self.user_sessions[user.id] = {"step": "target"}
        
        await update.message.reply_text(
            "📝 *Start Report*\n\n"
            "Send the target:\n"
            "• User: `@username` or `https://t.me/username`\n"
            "• Channel: `@channelname` or `https://t.me/channelname`\n"
            "• Group: `https://t.me/joinchat/xxxxxx`",
            parse_mode='Markdown'
        )
        
        return self.REPORT_TARGET
    
    async def handle_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle target input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        target = update.message.text.strip()
        
        # Determine type
        target_type = "user"
        if "t.me/joinchat/" in target:
            target_type = "group"
        elif "t.me/" in target and not target.startswith("@"):
            target_type = "channel"
        
        self.user_sessions[user_id]["target"] = target
        self.user_sessions[user_id]["target_type"] = target_type
        
        # Show categories
        keyboard = []
        for cat_id, cat_info in self.reporting_engine.report_categories.items():
            keyboard.append([InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        await update.message.reply_text(
            f"✅ Target: `{target[:50]}`\n"
            f"Type: {target_type}\n\n"
            "Select category:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return self.REPORT_SUBCATEGORY
    
    async def handle_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        cat_id = query.data.replace("cat_", "")
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired.")
            return ConversationHandler.END
        
        self.user_sessions[user_id]["category"] = cat_id
        
        cat_info = self.reporting_engine.report_categories[cat_id]
        
        # Show subcategories
        keyboard = []
        for sub_id, sub_info in cat_info["subcategories"].items():
            keyboard.append([InlineKeyboardButton(
                f"{sub_id}. {sub_info['name']}",
                callback_data=f"sub_{sub_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        await query.edit_message_text(
            f"📑 {cat_info['name']}\n\n"
            "Select violation:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_subcategory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subcategory selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        sub_id = int(query.data.replace("sub_", ""))
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired.")
            return ConversationHandler.END
        
        cat_id = self.user_sessions[user_id]["category"]
        cat_info = self.reporting_engine.report_categories[cat_id]
        sub_info = cat_info["subcategories"][sub_id]
        
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_info["name"]
        
        await query.edit_message_text(
            f"📝 *Provide Description*\n\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_info['name']}\n\n"
            "Describe what you observed (min 20 chars):",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def handle_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return
        
        description = update.message.text.strip()
        
        if len(description) < 20:
            await update.message.reply_text("❌ Description too short (min 20 chars).")
            return
        
        session = self.user_sessions[user_id]
        
        try:
            # Create job
            job_id = await self.reporting_engine.create_report_job(
                session["target"],
                session["target_type"],
                session["category"],
                session["subcategory"],
                description,
                user_id
            )
            
            # Execute in background
            asyncio.create_task(self._execute_and_notify(job_id, user_id, update))
            
            await update.message.reply_text(
                f"✅ *Report Started*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{session['target'][:50]}`\n"
                f"Category: {self.reporting_engine.report_categories[session['category']]['name']}\n\n"
                "⏳ *Simulating desktop reporting...*\n"
                "• Launching Telegram Desktop...\n"
                "• Viewing content...\n"
                "• Filing report...\n\n"
                "_This will take 20-40 seconds per account._",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        
        # Cleanup
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def _execute_and_notify(self, job_id: str, user_id: int, update: Update):
        """Execute job and notify user"""
        try:
            result = await self.reporting_engine.execute_job(job_id)
            
            if result.get("status") == "COMPLETED":
                status = f"✅ *Report Completed!*\n\nJob ID: `{job_id}`\nAccounts: {result['completed']}/{result['total']}"
            else:
                status = f"⚠️ *Report Issues*\n\nJob ID: `{job_id}`\nStatus: {result.get('status', 'FAILED')}"
            
            # Send notification
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(user_id, status, parse_mode='Markdown')
            
        except Exception as e:
            console.print(f"[red]❌ Job execution error: {e}[/red]")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        user_stats = self.user_manager.get_stats()
        account_stats = self.account_manager.get_stats()
        report_stats = self.reporting_engine.get_stats()
        proxy_stats = self.proxy_manager.get_stats()
        
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        stats_text = f"""
📊 *System Statistics*

*Your Role:* {role_text}
*Your Reports:* {self.user_manager.users[user.id].reports_made if user.id in self.user_manager.users else 0}

*👥 Users:*
• Total: {user_stats['total_users']}
• Owners: {user_stats['owners']}
• Sudo: {user_stats['sudo_users']}
• Regular: {user_stats['regular_users']}
• Total Reports: {user_stats['total_reports']}

*📱 Accounts:*
• Total: {account_stats['total_accounts']}
• Active: {account_stats['active_accounts']}
• Reports Today: {account_stats['reports_today']}
• Max per Account: {account_stats['max_reports_per_account']}

*📊 Reporting:*
• Total Jobs: {report_stats['total_jobs']}
• Active Jobs: {report_stats['active_jobs']}
• Successful: {report_stats['completed_jobs']}

*🌐 Proxies:*
• Total: {proxy_stats['total_proxies']}
• Active: {proxy_stats['active_proxies']}
• Fast: {proxy_stats['fast_country_proxies']}
• Avg Speed: {proxy_stats['average_response_time']}
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accounts command"""
        user = update.effective_user
        
        if not self.user_manager.can_add_accounts(user.id):
            await update.message.reply_text("❌ Permission denied.")
            return
        
        accounts = list(self.account_manager.accounts.values())
        
        if not accounts:
            await update.message.reply_text("📭 No accounts.")
            return
        
        text = "📱 *Accounts*\n\n"
        for i, acc in enumerate(accounts[:10], 1):
            status = "🟢" if acc.status == AccountStatus.ACTIVE else "🟡" if acc.status == AccountStatus.INACTIVE else "🔴"
            text += f"{i}. {status} `{acc.phone}`\n"
            text += f"   • Reports: {acc.report_count}/9\n"
            text += f"   • Total: {acc.total_reports}\n"
            text += f"   • Proxy: {acc.country if acc.country else 'Unknown'}\n"
            text += f"   • Device: {acc.device_model}\n\n"
        
        if len(accounts) > 10:
            text += f"\n_... and {len(accounts) - 10} more accounts_"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /jobs command"""
        user = update.effective_user
        
        jobs = self.reporting_engine.active_jobs
        
        if not jobs:
            await update.message.reply_text("📭 No active jobs.")
            return
        
        text = "📊 *Active Jobs*\n\n"
        for job_id, job in list(jobs.items())[:5]:
            status = "🟡" if job["status"] == "PROCESSING" else "🟢" if job["status"] == "COMPLETED" else "🔴"
            text += f"• {status} `{job_id}`\n"
            text += f"  Target: `{job['target'][:30]}...`\n"
            text += f"  Status: {job['status']}\n"
            text += f"  Accounts: {len(job.get('accounts_used', []))}\n\n"
        
        if len(jobs) > 5:
            text += f"\n_... and {len(jobs) - 5} more jobs_"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🆘 *Help*

*Basic Commands:*
/start - Start bot
/stats - View statistics
/report - Start reporting
/help - This message

*Account Commands (Owner/Sudo):*
/add - Add new account
/accounts - List accounts
/jobs - View jobs

*Admin Commands (Owner only):*
/addsudo [id] - Add sudo user
/listsudo - List sudo users
/removesudo [id] - Remove sudo user

*Proxy Setup:*
1. Create `data/data.txt`
2. Add proxies (one per line)
3. Format: ip:port or user:pass@ip:port

*Features:*
• Each account reports 9 times max
• Auto proxy rotation after 9 reports
• Desktop session simulation
• Proxy verification on startup
• Fast country prioritization
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

# ===== MAIN APPLICATION =====

class UltimateTelegramReportingBot:
    """Main bot application"""
    
    def __init__(self):
        # Initialize managers
        self.user_manager = UserManager()
        self.proxy_manager = UltimateProxyManager()
        self.account_manager = CompleteAccountManager(self.proxy_manager)
        self.reporting_engine = RealisticReportingEngine(
            self.account_manager,
            self.proxy_manager,
            self.user_manager
        )
        self.bot_handler = TelegramBotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine
        )
        
        # Bot application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("accounts", self.bot_handler.accounts_command))
        self.application.add_handler(CommandHandler("jobs", self.bot_handler.jobs_command))
        self.application.add_handler(CommandHandler("help", self.bot_handler.help_command))
        
        # Add account conversation
        add_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.bot_handler.add_command)],
            states={
                self.bot_handler.ADD_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_phone)
                ],
                self.bot_handler.ADD_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_otp)
                ],
                self.bot_handler.ADD_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_password)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.start_command)],
            allow_reentry=True
        )
        self.application.add_handler(add_handler)
        
        # Report conversation
        report_handler = ConversationHandler(
            entry_points=[CommandHandler("report", self.bot_handler.report_command)],
            states={
                self.bot_handler.REPORT_TARGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_target)
                ],
                self.bot_handler.REPORT_SUBCATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_category, pattern="^cat_|^cancel$")
                ],
                self.bot_handler.REPORT_DESCRIPTION: [
                    CallbackQueryHandler(self.bot_handler.handle_subcategory, pattern="^sub_|^cancel$")
                ]
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.start_command)],
            allow_reentry=True
        )
        self.application.add_handler(report_handler)
        
        # Description handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_description)
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        console.print(f"[red]❌ Error: {context.error}[/red]")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred.")
    
    async def initialize(self):
        """Initialize the system"""
        console.print("[cyan]🚀 Initializing Ultimate Telegram Reporting System v9.0[/cyan]")
        
        # Print banner
        self._print_banner()
        
        # Initialize proxy manager (verifies all proxies)
        proxy_initialized = await self.proxy_manager.initialize()
        
        if not proxy_initialized:
            console.print("[red]❌ Failed to initialize proxy manager[/red]")
            return False
        
        console.print("[green]✅ System initialized successfully[/green]")
        return True
    
    def _print_banner(self):
        """Print system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║     ULTIMATE TELEGRAM REPORTING SYSTEM v9.0                 ║
║     Complete Proxy Verification • 9 Reports Limit           ║
╠══════════════════════════════════════════════════════════════╣
║ Features:                                                    ║
║ • Proxy verification on startup                             ║
║ • Fast country prioritization                               ║
║ • 9 reports per account limit                               ║
║ • Automatic proxy rotation                                  ║
║ • Desktop session creation                                  ║
║ • Realistic reporting simulation                            ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
    
    async def run(self):
        """Run the bot"""
        initialized = await self.initialize()
        
        if not initialized:
            console.print("[red]❌ Failed to initialize system[/red]")
            return
        
        console.print("[green]✅ Starting bot...[/green]")
        
        # Start bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        console.print("[green]🤖 Bot is running. Press Ctrl+C to stop.[/green]")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Shutting down...[/yellow]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system"""
        console.print("[yellow]⚠️ Shutting down system...[/yellow]")
        
        # Save data
        self.user_manager._save_users()
        self.account_manager._save_accounts()
        self.reporting_engine._save_history()
        await self.proxy_manager.save_cache()
        
        # Disconnect clients
        for account in self.account_manager.accounts.values():
            if account.client and account.client.is_connected():
                await account.client.disconnect()
        
        # Stop bot
        if self.application.updater:
            await self.application.updater.stop()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        console.print("[green]✅ System shutdown complete[/green]")

# ===== MAIN ENTRY POINT =====

async def main():
    """Main entry point"""
    bot = UltimateTelegramReportingBot()
    
    try:
        await bot.run()
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Create user sessions attribute
    setattr(Update, '_user_sessions', {})
    
    # Run bot
    asyncio.run(main())
