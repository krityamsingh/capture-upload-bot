#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM ENTERPRISE REPORTING SYSTEM v10.0
Complete Professional Solution with Proxy Verification & Realistic Desktop Simulation
Created: 2024
Version: 10.0
"""

import asyncio
import time
import re
import json
import logging
import random
import string
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import aiohttp
from collections import defaultdict
import urllib.parse

# ============================================
# SECTION 1: TELEGRAM LIBRARIES
# ============================================

# For Bot API (bot commands and user interface)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# For Telegram Client (actual reporting)
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneCodeExpiredError
)
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonPornography,
    InputReportReasonFake, InputReportReasonIllegalDrugs, InputReportReasonPersonalDetails,
    InputReportReasonCopyright, InputReportReasonOther
)

# For beautiful console output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ============================================
# SECTION 2: CONFIGURATION
# ============================================

# Bot Token (Replace with your actual bot token)
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# Owner IDs (Full control)
OWNER_IDS = [6118760915, 1366105247]

# Fast response countries (Telegram servers are fastest here)
FAST_COUNTRIES = ["Germany", "Netherlands", "Singapore", "Finland", "Ireland", "Japan"]

# File paths
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

# Data files
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "data.txt"  # User adds proxies here
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"
JOBS_FILE = DATA_DIR / "jobs.json"

# ============================================
# SECTION 3: DATA MODELS
# ============================================

class UserRole(Enum):
    """User roles for permission system"""
    OWNER = "OWNER"  # Full access
    SUDO = "SUDO"    # Can add accounts and report
    USER = "USER"    # Can only report

class AccountStatus(Enum):
    """Account status tracking"""
    ACTIVE = "ACTIVE"            # Ready to use
    INACTIVE = "INACTIVE"        # Not logged in
    BANNED = "BANNED"            # Banned by Telegram
    FLOOD_WAIT = "FLOOD_WAIT"    # Rate limited
    NEED_PASSWORD = "NEED_PASSWORD"  # 2FA required
    PROXY_FAILED = "PROXY_FAILED"    # Proxy not working

class ReportStatus(Enum):
    """Job status tracking"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class TelegramUser:
    """Represents a bot user with permissions"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    role: UserRole = UserRole.USER
    added_at: datetime = None
    reports_made: int = 0
    last_active: Optional[datetime] = None
    
    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary for JSON storage"""
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
    def from_dict(cls, data):
        """Create from dictionary"""
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            role=UserRole(data.get("role", "USER")),
            reports_made=data.get("reports_made", 0)
        )
        user.added_at = datetime.fromisoformat(data["added_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        return user

@dataclass
class ProxyEntry:
    """
    Represents a proxy with performance tracking
    Each proxy is tested and ranked by speed
    """
    proxy: str  # Format: ip:port or user:pass@ip:port
    country: str = "Unknown"
    is_active: bool = True
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    reports_used: int = 0  # How many reports done with this proxy
    priority: float = 1.0  # Higher = better
    verified: bool = False
    last_verified: Optional[datetime] = None
    
    def to_dict(self):
        """Convert to dictionary"""
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
            "verified": self.verified,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        entry = cls(
            proxy=data["proxy"],
            country=data["country"],
            is_active=data.get("is_active", True),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            avg_response_time=data.get("avg_response_time", 0.0),
            reports_used=data.get("reports_used", 0),
            priority=data.get("priority", 1.0),
            verified=data.get("verified", False)
        )
        if data.get("last_used"):
            entry.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_verified"):
            entry.last_verified = datetime.fromisoformat(data["last_verified"])
        return entry

@dataclass
class TelegramAccount:
    """
    Represents a Telegram account for reporting
    Each account has its own session, proxy, and report counter
    """
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    client: Optional[TelegramClient] = None
    status: AccountStatus = AccountStatus.INACTIVE
    report_count: int = 0  # Reports done in current cycle
    total_reports: int = 0  # All-time reports
    last_report_time: Optional[datetime] = None
    created_at: datetime = None
    last_used: Optional[datetime] = None
    country: Optional[str] = None
    device_model: str = "Desktop"
    system_version: str = "Windows 10"
    app_version: str = "4.0.0"
    proxy_verified: bool = False
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "phone": self.phone,
            "session_file": str(self.session_file),
            "proxy": self.proxy,
            "status": self.status.value,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "last_report_time": self.last_report_time.isoformat() if self.last_report_time else None,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "country": self.country,
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "proxy_verified": self.proxy_verified
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0),
            country=data.get("country"),
            device_model=data.get("device_model", "Desktop"),
            system_version=data.get("system_version", "Windows 10"),
            app_version=data.get("app_version", "4.0.0"),
            proxy_verified=data.get("proxy_verified", False)
        )
        account.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_report_time"):
            account.last_report_time = datetime.fromisoformat(data["last_report_time"])
        if data.get("last_used"):
            account.last_used = datetime.fromisoformat(data["last_used"])
        return account

@dataclass
class ReportJob:
    """
    Represents a reporting job
    Can target users, channels, or groups
    """
    target: str  # Username or link
    target_type: str  # "user", "channel", or "group"
    category: str  # Report category
    subcategory: str  # Specific violation
    description: str  # Detailed description
    created_by: int  # User ID who created
    created_at: datetime = None
    status: ReportStatus = ReportStatus.PENDING
    accounts_used: List[str] = None  # Phone numbers of accounts used
    results: List[Dict] = None  # Results from each account
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accounts_used is None:
            self.accounts_used = []
        if self.results is None:
            self.results = []
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "target": self.target,
            "target_type": self.target_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "accounts_used": self.accounts_used,
            "results": self.results
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        job = cls(
            target=data["target"],
            target_type=data["target_type"],
            category=data["category"],
            subcategory=data["subcategory"],
            description=data["description"],
            created_by=data["created_by"]
        )
        job.created_at = datetime.fromisoformat(data["created_at"])
        job.status = ReportStatus(data["status"])
        job.accounts_used = data.get("accounts_used", [])
        job.results = data.get("results", [])
        return job

# ============================================
# SECTION 4: PROXY MANAGER (CORE COMPONENT)
# ============================================

class ProxyManager:
    """
    MANAGES ALL PROXIES WITH INTELLIGENT ROTATION
    
    Logic:
    1. Load proxies from data.txt
    2. Verify each proxy by connecting to Telegram
    3. Measure response time for each proxy
    4. Prioritize proxies from fast countries
    5. Rotate proxies after 9 reports
    6. Track success/failure rates
    
    Features:
    • Automatic proxy verification
    • Speed-based prioritization
    • Country-based filtering
    • Failure detection and removal
    • Usage tracking and rotation
    """
    
    def __init__(self):
        self.proxies: List[ProxyEntry] = []  # All proxy entries
        self.proxy_history: Dict[str, List] = defaultdict(list)  # Account proxy history
        self.fast_countries = FAST_COUNTRIES
        self.max_reports_per_proxy = 9  # Rotate after 9 reports
        
    async def initialize(self) -> bool:
        """
        Initialize proxy manager
        Returns: True if successful, False if no proxies
        """
        console.print("[cyan]🔧 Initializing Proxy Manager...[/cyan]")
        
        # Step 1: Load proxies from file
        await self._load_proxies_from_file()
        
        if not self.proxies:
            console.print("[red]❌ No proxies found in data/data.txt[/red]")
            console.print("[yellow]💡 Add proxies to data/data.txt and restart[/yellow]")
            return False
        
        console.print(f"[green]✅ Loaded {len(self.proxies)} proxies[/green]")
        
        # Step 2: Load cache (previous performance data)
        await self._load_cache()
        
        # Step 3: Verify all proxies
        console.print("[yellow]🔍 Verifying proxies...[/yellow]")
        await self.verify_all_proxies()
        
        # Step 4: Display statistics
        self._display_stats()
        
        return True
    
    async def _load_proxies_from_file(self):
        """Load proxies from data.txt file"""
        try:
            # First, try to load from the data directory
            proxy_file_path = PROXY_FILE
            
            # If not in data directory, try to look in the current directory
            if not proxy_file_path.exists():
                # Also check in the root directory (for GitHub compatibility)
                root_proxy_file = Path("data.txt")
                if root_proxy_file.exists():
                    proxy_file_path = root_proxy_file
                    console.print(f"[yellow]📝 Found proxies in root directory: {proxy_file_path}[/yellow]")
                else:
                    # Try to create the file if it doesn't exist
                    console.print(f"[yellow]📝 Creating {PROXY_FILE}[/yellow]")
                    PROXY_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(PROXY_FILE, 'w', encoding='utf-8') as f:
                        f.write("# Add proxies here (one per line)\n# Format: ip:port or user:pass@ip:port\n")
                    console.print(f"[green]✅ Created proxy file at {PROXY_FILE}[/green]")
                    return
            
            console.print(f"[cyan]📂 Loading proxies from: {proxy_file_path}[/cyan]")
            
            with open(proxy_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            loaded = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Basic validation
                if ':' not in line:
                    console.print(f"[yellow]⚠️ Invalid proxy format: {line}[/yellow]")
                    continue
                
                # Detect country from proxy (if possible)
                country = self._detect_country(line)
                
                # Create proxy entry
                proxy_entry = ProxyEntry(
                    proxy=line,
                    country=country,
                    priority=2.0 if country in self.fast_countries else 1.0
                )
                
                self.proxies.append(proxy_entry)
                loaded += 1
            
            if loaded:
                console.print(f"[green]✅ Successfully loaded {loaded} proxies[/green]")
            else:
                console.print("[yellow]⚠️ No valid proxies found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Error loading proxies: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    def _detect_country(self, proxy: str) -> str:
        """
        Try to detect country from proxy string
        Looks for country codes or city names in proxy
        """
        proxy_lower = proxy.lower()
        
        # Country detection patterns
        patterns = {
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
            "uk": "United Kingdom",
            "gb": "United Kingdom",
            "fr": "France",
            "france": "France",
            "ru": "Russia",
            "russia": "Russia"
        }
        
        for pattern, country in patterns.items():
            if pattern in proxy_lower:
                return country
        
        return "Unknown"
    
    async def _load_cache(self):
        """Load proxy cache from previous sessions"""
        try:
            if PROXY_CACHE_FILE.exists():
                with open(PROXY_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Update existing proxies with cache data
                cache_map = {p["proxy"]: p for p in cache_data.get("proxies", [])}
                
                for proxy_entry in self.proxies:
                    if proxy_entry.proxy in cache_map:
                        cached = cache_map[proxy_entry.proxy]
                        proxy_entry.success_count = cached.get("success_count", 0)
                        proxy_entry.fail_count = cached.get("fail_count", 0)
                        proxy_entry.avg_response_time = cached.get("avg_response_time", 0.0)
                        proxy_entry.reports_used = cached.get("reports_used", 0)
                        proxy_entry.priority = cached.get("priority", 1.0)
                        proxy_entry.verified = cached.get("verified", False)
                        
                        if cached.get("last_used"):
                            proxy_entry.last_used = datetime.fromisoformat(cached["last_used"])
                        if cached.get("last_verified"):
                            proxy_entry.last_verified = datetime.fromisoformat(cached["last_verified"])
                
                console.print("[green]✅ Loaded proxy cache[/green]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading cache: {e}[/yellow]")
    
    async def save_cache(self):
        """Save proxy data to cache file"""
        try:
            cache_data = {
                "proxies": [p.to_dict() for p in self.proxies],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(PROXY_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            console.print("[green]✅ Proxy cache saved[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error saving cache: {e}[/red]")
    
    async def verify_all_proxies(self):
        """
        Verify all proxies by connecting to Telegram
        Tests each proxy and measures response time
        """
        console.print("[cyan]🔍 Starting proxy verification...[/cyan]")
        
        # Create verification tasks
        tasks = []
        for proxy_entry in self.proxies:
            # Skip if recently verified
            if proxy_entry.last_verified and (datetime.now() - proxy_entry.last_verified).seconds < 300:
                tasks.append(asyncio.sleep(0))
                continue
            
            task = self._verify_single_proxy(proxy_entry)
            tasks.append(task)
        
        # Run with limited concurrency
        batch_size = 5
        verified_count = 0
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            
            # Update progress
            verified = sum(1 for p in self.proxies[:i + batch_size] if p.verified)
            console.print(f"[cyan]📊 Verified {verified}/{len(self.proxies)} proxies[/cyan]")
            
            # Save cache after each batch
            await self.save_cache()
        
        # Sort by performance
        self._sort_proxies()
        
        working = sum(1 for p in self.proxies if p.verified and p.is_active)
        console.print(f"[green]✅ {working}/{len(self.proxies)} proxies working[/green]")
    
    async def _verify_single_proxy(self, proxy_entry: ProxyEntry) -> bool:
        """
        Verify a single proxy by connecting to Telegram
        Returns: True if proxy works, False otherwise
        """
        try:
            # Create a test client
            test_client = TelegramClient(
                str(SESSION_DIR / f"test_{hash(proxy_entry.proxy) % 1000}.session"),
                API_ID,
                API_HASH,
                timeout=10,
                connection_retries=1
            )
            
            # Set the proxy
            test_client.set_proxy(proxy_entry.proxy)
            
            # Measure response time
            start_time = time.time()
            
            # Try to connect
            await test_client.connect()
            
            # Test by getting DC info
            try:
                await test_client.get_me()
                response_time = time.time() - start_time
                
                # Update proxy stats
                proxy_entry.verified = True
                proxy_entry.is_active = True
                proxy_entry.success_count += 1
                proxy_entry.last_verified = datetime.now()
                
                # Calculate average response time
                if proxy_entry.avg_response_time == 0:
                    proxy_entry.avg_response_time = response_time
                else:
                    proxy_entry.avg_response_time = (
                        proxy_entry.avg_response_time * (proxy_entry.success_count - 1) + response_time
                    ) / proxy_entry.success_count
                
                # Adjust priority based on speed and country
                base_priority = 2.0 if proxy_entry.country in self.fast_countries else 1.0
                speed_factor = max(0.1, 1.0 / (response_time + 0.1))
                proxy_entry.priority = base_priority * speed_factor
                
                console.print(f"[green]✅ {proxy_entry.proxy[:30]}... ({response_time:.2f}s)[/green]")
                return True
                
            except Exception as e:
                console.print(f"[yellow]⚠️ {proxy_entry.proxy[:30]}... failed: {str(e)[:50]}[/yellow]")
                proxy_entry.fail_count += 1
                
            finally:
                await test_client.disconnect()
                
        except Exception as e:
            console.print(f"[red]❌ {proxy_entry.proxy[:30]}... error: {str(e)[:50]}[/red]")
            proxy_entry.fail_count += 1
        
        # Disable proxy if too many failures
        if proxy_entry.fail_count >= 3:
            proxy_entry.is_active = False
            proxy_entry.verified = False
        
        return False
    
    def _sort_proxies(self):
        """
        Sort proxies by:
        1. Verified status (working proxies first)
        2. Active status (enabled proxies first)
        3. Priority (higher priority first)
        4. Response time (faster first)
        5. Success count (more successful first)
        """
        self.proxies.sort(key=lambda x: (
            0 if x.verified else 1,
            0 if x.is_active else 1,
            -x.priority,  # Negative for descending
            x.avg_response_time if x.avg_response_time > 0 else 1000,
            -x.success_count
        ))
    
    def _display_stats(self):
        """Display proxy statistics in a nice table"""
        active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        fast_proxies = [p for p in active_proxies if p.country in self.fast_countries]
        
        table = Table(title="Proxy Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Details", style="yellow")
        
        table.add_row("Total Proxies", str(len(self.proxies)), "Loaded from data.txt")
        table.add_row("Active & Verified", str(len(active_proxies)), "Ready for use")
        table.add_row("Fast Countries", str(len(fast_proxies)), f"{', '.join(set(p.country for p in fast_proxies))[:40]}")
        
        # Show top 5 fastest proxies
        if active_proxies:
            fastest = sorted(active_proxies, key=lambda x: x.avg_response_time)[:5]
            speed_table = Table(title="Fastest Proxies", box=box.SIMPLE)
            speed_table.add_column("#", style="cyan")
            speed_table.add_column("Proxy", style="green")
            speed_table.add_column("Country", style="yellow")
            speed_table.add_column("Speed", style="magenta")
            
            for i, proxy in enumerate(fastest, 1):
                proxy_display = proxy.proxy[:20] + "..." if len(proxy.proxy) > 20 else proxy.proxy
                speed_table.add_row(str(i), proxy_display, proxy.country[:15], f"{proxy.avg_response_time:.2f}s")
            
            console.print(table)
            console.print(speed_table)
        else:
            console.print(table)
            console.print("[red]❌ No working proxies available[/red]")
    
    async def get_best_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """
        Get the best available proxy for an account
        Logic:
        1. Get active, verified proxies
        2. Filter out recently used proxies for this account
        3. Sort by priority and usage
        4. Return the best one
        """
        # Get available proxies (active, verified, not maxed out)
        available = [
            p for p in self.proxies 
            if p.is_active and p.verified and p.reports_used < self.max_reports_per_proxy
        ]
        
        if not available:
            # Fallback to any active proxy
            available = [p for p in self.proxies if p.is_active and p.verified]
        
        if not available:
            console.print("[red]❌ No proxies available[/red]")
            return None
        
        # Check account's proxy history
        if account_phone in self.proxy_history:
            recent_proxies = {entry["proxy"] for entry in self.proxy_history[account_phone][-3:]}
            
            # Filter out recently used proxies
            fresh_proxies = [p for p in available if p.proxy not in recent_proxies]
            if fresh_proxies:
                available = fresh_proxies
        
        # Sort by priority and usage
        available.sort(key=lambda x: (
            -x.priority,  # Higher priority first
            x.reports_used,  # Less used first
            x.avg_response_time  # Faster first
        ))
        
        if not available:
            return None
        
        # Select the best proxy
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
        
        console.print(f"[cyan]📡 Selected proxy for {account_phone}: {selected.country}[/cyan]")
        return selected.proxy
    
    async def rotate_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """
        Force rotate proxy for an account
        Used when account reaches report limit
        """
        # Mark current proxy as needing rotation
        if account_phone in self.proxy_history and self.proxy_history[account_phone]:
            last_proxy = self.proxy_history[account_phone][-1]["proxy"]
            
            for proxy in self.proxies:
                if proxy.proxy == last_proxy:
                    proxy.reports_used = self.max_reports_per_proxy
                    console.print(f"[yellow]🔄 Rotating proxy for {account_phone}[/yellow]")
                    break
        
        # Get new proxy
        return await self.get_best_proxy_for_account(account_phone)
    
    def mark_proxy_success(self, proxy_url: str, response_time: float):
        """Mark a proxy as successful after report"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.success_count += 1
                
                # Update average response time
                if proxy.avg_response_time == 0:
                    proxy.avg_response_time = response_time
                else:
                    proxy.avg_response_time = (
                        proxy.avg_response_time * (proxy.success_count - 1) + response_time
                    ) / proxy.success_count
                
                # Update priority
                if proxy.country in self.fast_countries:
                    base_priority = 2.0
                else:
                    base_priority = 1.0
                
                speed_factor = max(0.1, 1.0 / (response_time + 0.1))
                proxy.priority = base_priority * speed_factor
                
                proxy.last_used = datetime.now()
                break
    
    def mark_proxy_failed(self, proxy_url: str):
        """Mark a proxy as failed"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.fail_count += 1
                proxy.reports_used = self.max_reports_per_proxy  # Mark for rotation
                proxy.priority *= 0.7  # Reduce priority
                
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

# ============================================
# SECTION 5: USER MANAGER
# ============================================

class UserManager:
    """
    MANAGES BOT USERS WITH PERMISSIONS
    
    Three user levels:
    1. OWNER - Full access (pre-defined IDs)
    2. SUDO - Can add accounts and report (added by owners)
    3. USER - Can only report
    
    All user data is saved to users.json
    """
    
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self.owner_ids = OWNER_IDS
        
        self._initialize_owners()
        self._load_users()
    
    def _initialize_owners(self):
        """Initialize owner accounts from config"""
        for owner_id in self.owner_ids:
            if owner_id not in self.users:
                self.users[owner_id] = TelegramUser(
                    user_id=owner_id,
                    role=UserRole.OWNER,
                    added_at=datetime.now()
                )
        console.print(f"[green]✅ Initialized {len(self.owner_ids)} owners[/green]")
    
    def _load_users(self):
        """Load users from JSON file"""
        try:
            if USERS_FILE.exists():
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_data in data.values():
                    user = TelegramUser.from_dict(user_data)
                    self.users[user.user_id] = user
                
                console.print(f"[green]✅ Loaded {len(self.users)} users[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading users: {e}[/red]")
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Error saving users: {e}[/red]")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Add a new user (default role: USER)"""
        if user_id in self.users:
            return False
        
        user = TelegramUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            role=UserRole.USER,
            added_at=datetime.now()
        )
        
        self.users[user_id] = user
        self._save_users()
        
        console.print(f"[green]✅ Added user {user_id}[/green]")
        return True
    
    def promote_to_sudo(self, user_id: int) -> bool:
        """Promote user to SUDO (owners only)"""
        if user_id not in self.users:
            return False
        
        self.users[user_id].role = UserRole.SUDO
        self._save_users()
        
        console.print(f"[green]✅ Promoted {user_id} to SUDO[/green]")
        return True
    
    def demote_from_sudo(self, user_id: int) -> bool:
        """Demote SUDO to USER (owners only)"""
        if user_id not in self.users or user_id in self.owner_ids:
            return False
        
        self.users[user_id].role = UserRole.USER
        self._save_users()
        
        console.print(f"[yellow]⚠️ Demoted {user_id} to USER[/yellow]")
        return True
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id in self.owner_ids
    
    def is_sudo(self, user_id: int) -> bool:
        """Check if user is SUDO or owner"""
        if self.is_owner(user_id):
            return True
        return user_id in self.users and self.users[user_id].role == UserRole.SUDO
    
    def can_add_accounts(self, user_id: int) -> bool:
        """Check if user can add accounts (OWNER or SUDO)"""
        return self.is_owner(user_id) or self.is_sudo(user_id)
    
    def update_user_activity(self, user_id: int, username: str = None, first_name: str = None):
        """Update user's last activity time"""
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
        """Increment user's report count"""
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

# ============================================
# SECTION 6: ACCOUNT MANAGER
# ============================================

class AccountManager:
    """
    MANAGES TELEGRAM ACCOUNTS FOR REPORTING
    
    Features:
    • Add accounts with phone numbers
    • Create desktop sessions
    • Handle OTP verification
    • Handle 2FA passwords
    • Assign verified proxies
    • Track report counts
    • Rotate proxies after 9 reports
    
    Each account has:
    • Phone number
    • Session file
    • Assigned proxy
    • Report counter
    • Status (active/inactive/etc.)
    """
    
    def __init__(self, proxy_manager: ProxyManager):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.proxy_manager = proxy_manager
        self.max_reports_per_account = 9  # Rotate proxy after 9 reports
        
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from JSON file"""
        try:
            if ACCOUNTS_FILE.exists():
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for phone, acc_data in data.items():
                    account = TelegramAccount.from_dict(acc_data)
                    self.accounts[phone] = account
                
                console.print(f"[green]✅ Loaded {len(self.accounts)} accounts[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading accounts: {e}[/red]")
    
    def _save_accounts(self):
        """Save accounts to JSON file"""
        try:
            data = {phone: account.to_dict() for phone, account in self.accounts.items()}
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Error saving accounts: {e}[/red]")
    
    async def add_account(self, phone: str) -> Tuple[bool, str]:
        """
        Add a new account
        Returns: (success, message)
        """
        if phone in self.accounts:
            return False, "Account already exists"
        
        # Get a verified proxy for this account
        proxy = await self.proxy_manager.get_best_proxy_for_account(phone)
        if not proxy:
            return False, "No working proxies available"
        
        # Create session file path
        session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        # Create account
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.INACTIVE,
            proxy_verified=True
        )
        
        self.accounts[phone] = account
        self._save_accounts()
        
        console.print(f"[green]✅ Added account: {phone}[/green]")
        return True, f"Account {phone} added successfully"
    
    async def create_desktop_session(self, phone: str, update: Update, user_id: int) -> bool:
        """
        Create a desktop session for account
        This simulates Telegram Desktop app
        """
        try:
            if phone not in self.accounts:
                await update.message.reply_text("❌ Account not found.")
                return False
            
            account = self.accounts[phone]
            
            # Random desktop configuration (mimics real users)
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
                f"Telegram Desktop: {config['app_ver']}\n"
                f"Proxy: Verified ✅\n\n"
                f"⏳ Connecting to Telegram...",
                parse_mode='Markdown'
            )
            
            # Create Telegram client with desktop configuration
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
            
            # Set proxy
            if account.proxy:
                client.set_proxy(account.proxy)
            
            # Connect and request OTP
            await client.connect()
            
            await update.message.reply_text(
                "📱 *Sending Verification Code*\n\n"
                "Requesting login code from Telegram...",
                parse_mode='Markdown'
            )
            
            # Request OTP
            try:
                sent_code = await client.send_code_request(phone)
                phone_code_hash = sent_code.phone_code_hash
                
                # Store session data for OTP verification
                if not hasattr(update, '_user_sessions'):
                    update._user_sessions = {}
                
                update._user_sessions[user_id] = {
                    "phone": phone,
                    "client": client,
                    "phone_code_hash": phone_code_hash,
                    "step": "waiting_otp",
                    "created_at": datetime.now()
                }
                
                await update.message.reply_text(
                    f"✅ *Code Sent!*\n\n"
                    f"5-digit code sent to `{phone}`\n\n"
                    f"Reply with code: `12345`\n\n"
                    f"_Code expires in 5 minutes_",
                    parse_mode='Markdown'
                )
                
                return True
                
            except FloodWaitError as e:
                await update.message.reply_text(f"⏳ Wait {e.seconds}s before retrying.")
                return False
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Error creating session: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    async def verify_otp(self, phone: str, otp: str, update: Update, user_id: int) -> bool:
        """
        Verify OTP code
        Returns: True if successful, False otherwise
        """
        try:
            if not hasattr(update, '_user_sessions') or user_id not in update._user_sessions:
                await update.message.reply_text("❌ Session expired.")
                return False
            
            session_data = update._user_sessions[user_id]
            
            if session_data["phone"] != phone:
                await update.message.reply_text("❌ Phone mismatch.")
                return False
            
            client = session_data["client"]
            phone_code_hash = session_data["phone_code_hash"]
            
            await update.message.reply_text("🔐 Verifying code...", parse_mode='Markdown')
            
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
                    "🔒 *2FA Required*\n\n"
                    "This account has 2FA enabled.\n"
                    "Reply with your 2FA password:",
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
                    account.country = self._get_country_from_phone(me.phone)
                account.is_premium = getattr(me, 'premium', False)
            except:
                pass
            
            self._save_accounts()
            
            # Cleanup
            if user_id in update._user_sessions:
                del update._user_sessions[user_id]
            
            await update.message.reply_text(
                f"✅ *Login Successful!*\n\n"
                f"Account: `{phone}`\n"
                f"Status: Active ✅\n"
                f"Device: {account.device_model}\n"
                f"Country: {account.country or 'Unknown'}\n"
                f"Premium: {'⭐ Yes' if account.is_premium else 'No'}\n\n"
                f"Ready for reporting!",
                parse_mode='Markdown'
            )
            
            return True
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ Invalid code. Try again.")
            return False
        except PhoneCodeExpiredError:
            await update.message.reply_text("❌ Code expired. Start over.")
            if hasattr(update, '_user_sessions') and user_id in update._user_sessions:
                del update._user_sessions[user_id]
            return False
        except Exception as e:
            console.print(f"[red]❌ OTP verification error: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    async def verify_password(self, phone: str, password: str, update: Update, user_id: int) -> bool:
        """Verify 2FA password"""
        try:
            if not hasattr(update, '_user_sessions') or user_id not in update._user_sessions:
                await update.message.reply_text("❌ Session expired.")
                return False
            
            session_data = update._user_sessions[user_id]
            client = session_data["client"]
            
            await update.message.reply_text("🔐 Verifying 2FA...", parse_mode='Markdown')
            
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
                f"Account `{phone}` is now active.",
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Password verification error: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
            return False
    
    def _get_country_from_phone(self, phone: str) -> str:
        """Detect country from phone number prefix"""
        country_codes = {
            '+1': 'United States',
            '+44': 'United Kingdom',
            '+49': 'Germany',
            '+33': 'France',
            '+81': 'Japan',
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
        """
        Get available accounts for reporting
        Priority:
        1. Active accounts with reports left
        2. Inactive accounts (need activation)
        """
        available = []
        
        # Active accounts with reports left
        for account in self.accounts.values():
            if account.status == AccountStatus.ACTIVE and account.report_count < self.max_reports_per_account:
                available.append(account)
                if len(available) >= count:
                    break
        
        # Inactive accounts as backup
        if len(available) < count:
            inactive = [acc for acc in self.accounts.values() if acc.status == AccountStatus.INACTIVE]
            available.extend(inactive[:count - len(available)])
        
        return available[:count]
    
    async def rotate_proxy_for_account(self, phone: str) -> bool:
        """
        Rotate proxy for account after reaching report limit
        Returns: True if rotated, False if failed
        """
        if phone not in self.accounts:
            return False
        
        account = self.accounts[phone]
        
        # Check if rotation needed
        if account.report_count < self.max_reports_per_account:
            return True  # Not yet
        
        # Get new proxy
        new_proxy = await self.proxy_manager.rotate_proxy_for_account(phone)
        
        if new_proxy and new_proxy != account.proxy:
            account.proxy = new_proxy
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
        reports_today = sum(
            a.report_count for a in self.accounts.values() 
            if a.last_report_time and a.last_report_time.date() == today
        )
        
        return {
            "total_accounts": total,
            "active_accounts": active,
            "inactive_accounts": inactive,
            "total_reports": total_reports,
            "reports_today": reports_today,
            "max_reports_per_account": self.max_reports_per_account
        }

# ============================================
# SECTION 7: REPORTING ENGINE
# ============================================

class ReportingEngine:
    """
    HANDLES REALISTIC REPORTING
    
    Features:
    • Desktop simulation with realistic delays
    • Multiple accounts per report
    • Automatic proxy rotation
    • Failure handling
    • Report tracking
    
    Reporting flow:
    1. Get available accounts
    2. Check proxy rotation needs
    3. Simulate desktop behavior
    4. Execute report
    5. Update statistics
    6. Rotate proxies if needed
    """
    
    def __init__(self, account_manager: AccountManager, proxy_manager: ProxyManager, user_manager: UserManager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = []
        
        self._load_jobs()
        
        # Report categories
        self.categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs",
                "priority": "HIGH",
                "subcategories": {
                    1: "Drug Sales",
                    2: "Drug Promotion",
                    3: "Drug Recipes"
                }
            },
            "SPAM": {
                "name": "Spam",
                "priority": "MEDIUM",
                "subcategories": {
                    1: "Mass Spamming",
                    2: "Phishing Links",
                    3: "Financial Scams"
                }
            },
            "VIOLENCE": {
                "name": "Violence",
                "priority": "HIGH",
                "subcategories": {
                    1: "Threats",
                    2: "Terrorism",
                    3: "Extremism"
                }
            },
            "SEXUAL": {
                "name": "Sexual Content",
                "priority": "HIGH",
                "subcategories": {
                    1: "Exploitation",
                    2: "Harassment",
                    3: "Pornography"
                }
            }
        }
    
    def _load_jobs(self):
        """Load jobs from file"""
        try:
            if JOBS_FILE.exists():
                with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for job_data in data:
                    job = ReportJob.from_dict(job_data)
                    self.job_history.append(job)
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading jobs: {e}[/yellow]")
    
    def _save_jobs(self):
        """Save jobs to file"""
        try:
            data = [job.to_dict() for job in self.job_history[-100:]]  # Keep last 100
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Error saving jobs: {e}[/red]")
    
    async def create_job(self, target: str, target_type: str, category: str, 
                        subcategory: int, description: str, user_id: int) -> str:
        """Create a new report job"""
        if category not in self.categories:
            raise ValueError(f"Invalid category: {category}")
        
        if subcategory not in self.categories[category]["subcategories"]:
            raise ValueError(f"Invalid subcategory: {subcategory}")
        
        sub_name = self.categories[category]["subcategories"][subcategory]
        
        job = ReportJob(
            target=target,
            target_type=target_type,
            category=category,
            subcategory=sub_name,
            description=description,
            created_by=user_id
        )
        
        job_id = hashlib.md5(f"{datetime.now()}{random.random()}{target}".encode()).hexdigest()[:12]
        self.active_jobs[job_id] = job
        
        console.print(f"[cyan]📝 Created job {job_id} for {target}[/cyan]")
        return job_id
    
    async def execute_job(self, job_id: str) -> Dict:
        """
        Execute a report job
        Returns: Job results
        """
        if job_id not in self.active_jobs:
            return {"error": "Job not found"}
        
        job = self.active_jobs[job_id]
        job.status = ReportStatus.PROCESSING
        
        console.print(f"[cyan]🚀 Executing job {job_id}[/cyan]")
        
        # Get available accounts
        accounts = await self.account_manager.get_available_accounts(3)
        
        if not accounts:
            job.status = ReportStatus.FAILED
            return {"error": "No accounts available"}
        
        results = []
        
        # Process each account
        for i, account in enumerate(accounts):
            console.print(f"[yellow]👤 Account {i+1}/{len(accounts)}: {account.phone}[/yellow]")
            
            # Check proxy rotation
            if account.report_count >= self.account_manager.max_reports_per_account:
                console.print(f"[cyan]🔄 Rotating proxy for {account.phone}...[/cyan]")
                rotated = await self.account_manager.rotate_proxy_for_account(account.phone)
                if not rotated:
                    console.print(f"[red]❌ Failed to rotate proxy[/red]")
                    continue
            
            # Realistic delay between accounts
            if i > 0:
                delay = random.uniform(5.0, 15.0)
                console.print(f"[dim]⏳ Waiting {delay:.1f}s...[/dim]")
                await asyncio.sleep(delay)
            
            # Execute report
            result = await self._execute_report(account, job)
            results.append(result)
            
            if result.get("status") == "COMPLETED":
                job.accounts_used.append(account.phone)
                
                # Update account
                account.report_count += 1
                account.total_reports += 1
                account.last_report_time = datetime.now()
                
                # Mark proxy success
                if account.proxy and result.get("response_time"):
                    self.proxy_manager.mark_proxy_success(account.proxy, result["response_time"])
        
        job.results = results
        
        # Update job status
        completed = len([r for r in results if r.get("status") == "COMPLETED"])
        if completed > 0:
            job.status = ReportStatus.COMPLETED
        else:
            job.status = ReportStatus.FAILED
        
        # Save data
        self.account_manager._save_accounts()
        self.user_manager.increment_reports(job.created_by)
        
        # Move to history
        self.job_history.append(job)
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
        
        self._save_jobs()
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "completed": completed,
            "total": len(accounts),
            "results": results
        }
    
    async def _execute_report(self, account: TelegramAccount, job: ReportJob) -> Dict:
        """
        Execute a single report with desktop simulation
        """
        start_time = time.time()
        
        try:
            # Initialize client if needed
            if not account.client or not account.client.is_connected():
                await self._initialize_client(account)
            
            if not account.client or not account.client.is_connected():
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Client not connected"
                }
            
            # Resolve target
            target_entity = await self._resolve_target(account.client, job.target, job.target_type)
            if not target_entity:
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Target not found"
                }
            
            # Desktop simulation
            console.print(f"[dim]🖥️ Desktop simulation for {account.phone}[/dim]")
            
            # Simulate desktop steps
            steps = [
                ("Launching Telegram Desktop", 2.0, 4.0),
                ("Searching target", 1.5, 3.0),
                ("Viewing content", 3.0, 6.0),
                ("Opening menu", 1.0, 2.0),
                ("Selecting reason", 2.0, 4.0),
                ("Typing description", 3.0, 8.0),
                ("Submitting report", 1.0, 2.0),
            ]
            
            total_sim = 0
            for step, min_t, max_t in steps:
                delay = random.uniform(min_t, max_t)
                await asyncio.sleep(delay)
                total_sim += delay
            
            # Get report reason
            reason = self._get_reason(job.category)
            
            # Prepare message
            message = f"{job.subcategory}: {job.description[:200]}"
            
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
                "country": account.country,
                "simulation_time": total_sim,
                "response_time": response_time,
                "report_count": account.report_count
            }
            
        except FloodWaitError as e:
            account.status = AccountStatus.FLOOD_WAIT
            return {
                "account": account.phone,
                "status": "FLOOD_WAIT",
                "error": f"Wait {e.seconds}s"
            }
        except Exception as e:
            if account.proxy:
                self.proxy_manager.mark_proxy_failed(account.proxy)
            
            return {
                "account": account.phone,
                "status": "FAILED",
                "error": str(e)[:100]
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
            console.print(f"[red]❌ Client init failed for {account.phone}: {e}[/red]")
            account.status = AccountStatus.INACTIVE
            return False
    
    async def _resolve_target(self, client, target: str, target_type: str):
        """Resolve target entity"""
        try:
            target = target.strip()
            
            if target.startswith("@"):
                return await client.get_entity(target[1:])
            
            if "t.me/" in target:
                if target.startswith("https://t.me/joinchat/"):
                    return await client.get_entity(target)
                else:
                    username = target.split("/")[-1]
                    return await client.get_entity(username)
            
            return await client.get_entity(target)
            
        except Exception as e:
            console.print(f"[red]❌ Target resolution failed: {target} - {e}[/red]")
            return None
    
    def _get_reason(self, category: str):
        """Get Telethon report reason class"""
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
    
    def get_stats(self) -> Dict:
        """Get reporting statistics"""
        return {
            "total_jobs": len(self.job_history),
            "active_jobs": len(self.active_jobs),
            "completed_jobs": sum(1 for j in self.job_history if j.status == ReportStatus.COMPLETED),
            "failed_jobs": sum(1 for j in self.job_history if j.status == ReportStatus.FAILED)
        }

# ============================================
# SECTION 8: TELEGRAM BOT HANDLER
# ============================================

class BotHandler:
    """
    HANDLES TELEGRAM BOT COMMANDS
    
    Commands:
    • /start - Welcome message
    • /add - Add account (Owner/Sudo only)
    • /report - Start reporting
    • /stats - View statistics
    • /accounts - List accounts (Owner/Sudo only)
    • /jobs - View jobs
    • /help - Help message
    • /addsudo - Add sudo user (Owner only)
    • /listsudo - List sudo users (Owner only)
    • /removesudo - Remove sudo user (Owner only)
    """
    
    def __init__(self, user_manager: UserManager, account_manager: AccountManager, reporting_engine: ReportingEngine):
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
        
        role = "👑 Owner" if self.user_manager.is_owner(user.id) else \
               "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        text = f"""
🤖 *Telegram Reporting System v10.0*

*Your Role:* {role}

*Commands:*
/start - This message
/add - Add account (Owner/Sudo only)
/report - Start reporting
/stats - View statistics
/accounts - List accounts (Owner/Sudo only)
/jobs - View jobs
/help - Help

*Admin Commands:*
/addsudo [id] - Add sudo user (Owner only)
/listsudo - List sudo users (Owner only)
/removesudo [id] - Remove sudo user (Owner only)

*Proxy Setup:*
1. Add proxies to `data/data.txt`
2. Format: `ip:port` or `user:pass@ip:port`
3. Restart bot to verify proxies
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command"""
        user = update.effective_user
        
        if not self.user_manager.can_add_accounts(user.id):
            await update.message.reply_text("❌ Only Owner/Sudo can add accounts.")
            return
        
        self.user_sessions[user.id] = {"step": "phone"}
        
        await update.message.reply_text(
            "📱 *Add Account*\n\n"
            "Send phone number:\n"
            "Format: `+1234567890`\n\n"
            "_You'll receive an OTP on this phone._",
            parse_mode='Markdown'
        )
        
        return self.ADD_PHONE
    
    async def handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        phone = update.message.text.strip()
        
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text("❌ Invalid format. Use: `+1234567890`", parse_mode='Markdown')
            return self.ADD_PHONE
        
        # Add account
        success, message = await self.account_manager.add_account(phone)
        
        if not success:
            await update.message.reply_text(f"❌ {message}")
            return ConversationHandler.END
        
        self.user_sessions[user_id]["phone"] = phone
        
        # Create session
        created = await self.account_manager.create_desktop_session(phone, update, user_id)
        
        if created:
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
            await update.message.reply_text("❌ Invalid OTP. Format: `12345`", parse_mode='Markdown')
            return self.ADD_OTP
        
        phone = self.user_sessions[user_id]["phone"]
        
        # Verify OTP
        success = await self.account_manager.verify_otp(phone, otp, update, user_id)
        
        if success:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        else:
            # Check if password needed
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
            "Send target:\n"
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
        for cat_id, cat_info in self.reporting_engine.categories.items():
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
        
        cat_info = self.reporting_engine.categories[cat_id]
        
        # Show subcategories
        keyboard = []
        for sub_id, sub_name in cat_info["subcategories"].items():
            keyboard.append([InlineKeyboardButton(f"{sub_id}. {sub_name}", callback_data=f"sub_{sub_id}")])
        
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
        cat_info = self.reporting_engine.categories[cat_id]
        sub_name = cat_info["subcategories"][sub_id]
        
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_name
        
        await query.edit_message_text(
            f"📝 *Description*\n\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_name}\n\n"
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
            await update.message.reply_text("❌ Minimum 20 characters required.")
            return
        
        session = self.user_sessions[user_id]
        
        try:
            # Create job
            job_id = await self.reporting_engine.create_job(
                session["target"],
                session["target_type"],
                session["category"],
                session["subcategory"],
                description,
                user_id
            )
            
            # Execute in background
            asyncio.create_task(self._execute_and_notify(job_id, user_id))
            
            await update.message.reply_text(
                f"✅ *Report Started*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{session['target'][:50]}`\n\n"
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
    
    async def _execute_and_notify(self, job_id: str, user_id: int):
        """Execute job and notify user"""
        try:
            result = await self.reporting_engine.execute_job(job_id)
            
            if result.get("status") == "COMPLETED":
                text = f"✅ *Report Completed!*\n\nJob ID: `{job_id}`\nAccounts: {result['completed']}/{result['total']}"
            else:
                text = f"⚠️ *Report Issues*\n\nJob ID: `{job_id}`\nStatus: {result.get('status', 'FAILED')}"
            
            # Send notification
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(user_id, text, parse_mode='Markdown')
            
        except Exception as e:
            console.print(f"[red]❌ Job execution error: {e}[/red]")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        user_stats = self.user_manager.get_stats()
        account_stats = self.account_manager.get_stats()
        report_stats = self.reporting_engine.get_stats()
        proxy_stats = self.proxy_manager.get_stats()
        
        role = "👑 Owner" if self.user_manager.is_owner(user.id) else \
               "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        text = f"""
📊 *System Statistics*

*Your Role:* {role}
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
• Completed: {report_stats['completed_jobs']}

*🌐 Proxies:*
• Total: {proxy_stats['total_proxies']}
• Active: {proxy_stats['active_proxies']}
• Fast Countries: {proxy_stats['fast_country_proxies']}
• Avg Speed: {proxy_stats['average_response_time']}
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
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
            status = "🟡" if job.status == ReportStatus.PROCESSING else "🟢" if job.status == ReportStatus.COMPLETED else "🔴"
            text += f"• {status} `{job_id}`\n"
            text += f"  Target: `{job.target[:30]}...`\n"
            text += f"  Status: {job.status.value}\n"
            text += f"  Accounts: {len(job.accounts_used)}\n\n"
        
        if len(jobs) > 5:
            text += f"\n_... and {len(jobs) - 5} more jobs_"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        text = """
🆘 *Help Guide*

*Basic Commands:*
/start - Welcome message
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
4. Restart bot

*Features:*
• Each account reports 9 times max
• Auto proxy rotation after 9 reports
• Proxy verification on startup
• Desktop session simulation
• Fast country prioritization
• Realistic reporting delays
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')

# ============================================
# SECTION 9: MAIN APPLICATION
# ============================================

class TelegramReportingBot:
    """
    MAIN BOT APPLICATION
    
    Orchestrates all components:
    1. Proxy Manager - Handles proxies
    2. User Manager - Handles permissions
    3. Account Manager - Handles Telegram accounts
    4. Reporting Engine - Handles reporting
    5. Bot Handler - Handles Telegram commands
    """
    
    def __init__(self):
        # Initialize all managers
        self.user_manager = UserManager()
        self.proxy_manager = ProxyManager()
        self.account_manager = AccountManager(self.proxy_manager)
        self.reporting_engine = ReportingEngine(
            self.account_manager,
            self.proxy_manager,
            self.user_manager
        )
        self.bot_handler = BotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine
        )
        
        # Create Telegram bot application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup all handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all Telegram bot handlers"""
        
        # Basic commands
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
        
        # Description handler (outside conversation)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_description)
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        console.print(f"[red]❌ Bot Error: {context.error}[/red]")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred.")
    
    async def initialize(self) -> bool:
        """
        Initialize the entire system
        Returns: True if successful, False if failed
        """
        console.print("[cyan]🚀 Initializing Telegram Reporting System v10.0[/cyan]")
        
        # Print banner
        self._print_banner()
        
        # Initialize proxy manager (verifies proxies)
        console.print("[yellow]🔧 Initializing system components...[/yellow]")
        
        proxy_ok = await self.proxy_manager.initialize()
        if not proxy_ok:
            console.print("[red]❌ System initialization failed[/red]")
            return False
        
        console.print("[green]✅ System initialized successfully[/green]")
        return True
    
    def _print_banner(self):
        """Print system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║     TELEGRAM ENTERPRISE REPORTING SYSTEM v10.0              ║
║     Professional Solution with Proxy Verification           ║
╠══════════════════════════════════════════════════════════════╣
║ Features:                                                    ║
║ • Complete proxy verification on startup                    ║
║ • 9 reports per account limit                               ║
║ • Automatic proxy rotation                                  ║
║ • Fast country prioritization                               ║
║ • Desktop session simulation                                ║
║ • Owner/Sudo user management                                ║
║ • Realistic reporting delays                                ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
    
    async def run(self):
        """Run the bot"""
        # Initialize system
        initialized = await self.initialize()
        if not initialized:
            console.print("[red]❌ Cannot start without working proxies[/red]")
            console.print("[yellow]💡 Add proxies to data/data.txt and restart[/yellow]")
            return
        
        # Start bot
        console.print("[green]🤖 Starting Telegram bot...[/green]")
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        console.print("[green]✅ Bot is running![/green]")
        console.print("[yellow]📱 Use /start in Telegram to begin[/yellow]")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Shutting down...[/yellow]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system gracefully"""
        console.print("[yellow]🔧 Shutting down system...[/yellow]")
        
        # Save all data
        self.user_manager._save_users()
        self.account_manager._save_accounts()
        self.reporting_engine._save_jobs()
        await self.proxy_manager.save_cache()
        
        # Disconnect all Telegram clients
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

# ============================================
# SECTION 10: MAIN ENTRY POINT
# ============================================

async def main():
    """
    MAIN FUNCTION
    Entry point for the entire application
    """
    # Create global user sessions storage
    setattr(Update, '_user_sessions', {})
    
    # Create and run bot
    bot = TelegramReportingBot()
    
    try:
        await bot.run()
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())
