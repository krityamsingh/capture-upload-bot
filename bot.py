#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM ENTERPRISE REPORTING SYSTEM v8.0
Ultimate Realistic Human Simulation with Desktop Client Emulation
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

# Fast response countries (Telegram servers in these countries respond fastest)
FAST_COUNTRIES = ["Germany", "Netherlands", "Singapore", "Finland", "Ireland", "United States", "Japan"]

# Session and data directories
SESSION_DIR = Path("sessions")
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
EXPORTS_DIR = Path("exports")
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "data.txt"  # Changed from proxy.txt to data.txt
JOB_HISTORY_FILE = DATA_DIR / "job_history.json"

# Create directories
for dir_path in [SESSION_DIR, DATA_DIR, LOGS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ===== ENHANCED DATA MODELS =====

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
    """Telegram account with enhanced session management"""
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
            "app_version": self.app_version
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
            app_version=data.get("app_version", "4.0.0")
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
class ReportJob:
    """Enhanced reporting job with realistic delays"""
    target: str
    target_type: str  # "user", "channel", "group"
    reason_category: str
    reason_subcategory: str
    description: str
    accounts_needed: int = 3
    priority: ReportPriority = ReportPriority.MEDIUM
    schedule_time: Optional[datetime] = None
    created_by: int = None
    created_at: datetime = field(default_factory=datetime.now)
    status: ReportStatus = ReportStatus.PENDING
    assigned_accounts: List[str] = field(default_factory=list)
    completed_accounts: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    random_delay_enabled: bool = True
    delay_min: float = 5.0
    delay_max: float = 15.0
    simulate_desktop: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "target_type": self.target_type,
            "reason_category": self.reason_category,
            "reason_subcategory": self.reason_subcategory,
            "description": self.description,
            "accounts_needed": self.accounts_needed,
            "priority": self.priority.value,
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "assigned_accounts": self.assigned_accounts,
            "completed_accounts": self.completed_accounts,
            "results": self.results,
            "user_agent": self.user_agent,
            "random_delay_enabled": self.random_delay_enabled,
            "delay_min": self.delay_min,
            "delay_max": self.delay_max,
            "simulate_desktop": self.simulate_desktop
        }

# ===== ULTRA REALISTIC HUMAN SIMULATION SYSTEM =====

class HumanBehaviorSimulator:
    """Simulates ultra-realistic human behavior for reporting"""
    
    def __init__(self):
        self.human_patterns = {
            "fast_typer": {"wpm": 70, "error_rate": 0.03, "pause_frequency": 0.2},
            "normal_typer": {"wpm": 40, "error_rate": 0.05, "pause_frequency": 0.3},
            "slow_typer": {"wpm": 25, "error_rate": 0.08, "pause_frequency": 0.4}
        }
        
        self.thinking_times = {
            "quick": (1.5, 3.0),
            "normal": (3.0, 6.0),
            "thorough": (5.0, 10.0)
        }
        
        self.mouse_movements = {
            "slow": {"speed": 0.8, "jitter": 0.1},
            "normal": {"speed": 1.2, "jitter": 0.15},
            "fast": {"speed": 2.0, "jitter": 0.2}
        }
        
        self.attention_span = {
            "short": (8.0, 15.0),
            "normal": (15.0, 30.0),
            "long": (25.0, 45.0)
        }
    
    async def simulate_human_typing(self, text: str, typer_type: str = "normal") -> float:
        """Simulates realistic typing with human imperfections"""
        config = self.human_patterns.get(typer_type, self.human_patterns["normal"])
        words_per_minute = config["wpm"]
        error_rate = config["error_rate"]
        pause_frequency = config["pause_frequency"]
        
        # Calculate base time (words per minute to seconds per character)
        chars_per_second = (words_per_minute * 5) / 60  # Average 5 chars per word
        
        total_time = 0
        words = text.split()
        
        for word_idx, word in enumerate(words):
            # Type each character
            for char_idx, char in enumerate(word):
                # Base typing time with variation
                char_time = 1.0 / chars_per_second
                char_time *= random.uniform(0.8, 1.2)  # Natural variation
                
                await asyncio.sleep(char_time)
                total_time += char_time
                
                # Simulate typing errors
                if random.random() < error_rate:
                    # Backspace error
                    backspace_time = char_time * random.uniform(0.5, 0.8)
                    await asyncio.sleep(backspace_time)
                    total_time += backspace_time
                    
                    # Retype character
                    retype_time = char_time * random.uniform(0.9, 1.1)
                    await asyncio.sleep(retype_time)
                    total_time += retype_time
            
            # Space between words
            space_time = 0.1 * random.uniform(0.8, 1.2)
            await asyncio.sleep(space_time)
            total_time += space_time
            
            # Natural pauses between words (like thinking)
            if random.random() < pause_frequency:
                pause_time = random.uniform(0.3, 1.2)
                await asyncio.sleep(pause_time)
                total_time += pause_time
        
        return total_time
    
    async def simulate_thinking(self, complexity: str = "normal") -> float:
        """Simulates thinking before taking action"""
        min_time, max_time = self.thinking_times.get(complexity, self.thinking_times["normal"])
        
        # Base thinking time
        thinking_time = random.uniform(min_time, max_time)
        
        # Add micro-movements (small pauses)
        micro_pauses = random.randint(2, 5)
        for _ in range(micro_pauses):
            micro_pause = random.uniform(0.2, 0.5)
            await asyncio.sleep(micro_pause)
            thinking_time += micro_pause
        
        return thinking_time
    
    async def simulate_mouse_movement(self, target_count: int = 1) -> float:
        """Simulates realistic mouse movement to targets"""
        total_time = 0
        
        for i in range(target_count):
            # Movement time to target
            move_time = random.uniform(0.3, 1.2)
            
            # Add jitter (human hand shaking)
            jitter_count = random.randint(1, 3)
            for _ in range(jitter_count):
                jitter = random.uniform(0.05, 0.15)
                await asyncio.sleep(jitter)
                move_time += jitter
            
            # Hover time before click
            hover_time = random.uniform(0.1, 0.4)
            await asyncio.sleep(hover_time)
            move_time += hover_time
            
            total_time += move_time
        
        return total_time
    
    async def simulate_reading(self, word_count: int) -> float:
        """Simulates reading time for content"""
        # Average reading speed: 200-250 words per minute
        reading_speed = random.uniform(200, 250)  # words per minute
        words_per_second = reading_speed / 60
        
        reading_time = word_count / words_per_second
        
        # Add natural reading variations
        reading_time *= random.uniform(0.8, 1.3)
        
        # Add occasional re-reading
        if random.random() < 0.2:  # 20% chance of re-reading
            reread_portion = random.uniform(0.1, 0.3)  # Reread 10-30%
            reading_time += reading_time * reread_portion
        
        await asyncio.sleep(reading_time)
        return reading_time
    
    async def simulate_scrolling(self, pages: int = 1) -> float:
        """Simulates realistic scrolling behavior"""
        total_time = 0
        
        for page in range(pages):
            # Initial scroll
            scroll_time = random.uniform(1.0, 2.5)
            await asyncio.sleep(scroll_time)
            total_time += scroll_time
            
            # Pause to read
            pause_time = random.uniform(2.0, 5.0)
            await asyncio.sleep(pause_time)
            total_time += pause_time
            
            # Small adjustment scroll
            if random.random() < 0.7:  # 70% chance of small adjustment
                adj_time = random.uniform(0.3, 0.8)
                await asyncio.sleep(adj_time)
                total_time += adj_time
        
        return total_time
    
    async def simulate_network_latency(self) -> float:
        """Simulates realistic network latency"""
        latency = random.uniform(0.1, 1.5)  # Network delay
        await asyncio.sleep(latency)
        return latency
    
    async def simulate_full_desktop_report_flow(self, target_type: str, description_length: int = 50) -> Dict[str, float]:
        """Simulates complete desktop reporting flow"""
        flow_times = {}
        
        # 1. Opening Telegram Desktop
        console.print("[dim]Launching Telegram Desktop...[/dim]")
        launch_time = random.uniform(2.0, 4.0)
        await asyncio.sleep(launch_time)
        flow_times["launch"] = launch_time
        
        # 2. Searching for target
        console.print("[dim]Searching for target...[/dim]")
        search_time = random.uniform(1.5, 3.0)
        await asyncio.sleep(search_time)
        flow_times["search"] = search_time
        
        # 3. Opening target profile/channel
        console.print("[dim]Opening target...[/dim]")
        open_time = random.uniform(1.0, 2.5)
        await asyncio.sleep(open_time)
        flow_times["open_target"] = open_time
        
        # 4. Viewing content (scrolling)
        console.print("[dim]Viewing content...[/dim]")
        view_time = await self.simulate_scrolling(random.randint(1, 3))
        flow_times["view_content"] = view_time
        
        # 5. Thinking about reporting
        console.print("[dim]Considering report...[/dim]")
        think_time = await self.simulate_thinking("normal")
        flow_times["thinking"] = think_time
        
        # 6. Opening menu (mouse movement)
        console.print("[dim]Opening menu...[/dim]")
        menu_time = await self.simulate_mouse_movement(1)
        flow_times["open_menu"] = menu_time
        
        # 7. Clicking report option
        console.print("[dim]Clicking report...[/dim]")
        click_time = random.uniform(0.2, 0.5)
        await asyncio.sleep(click_time)
        flow_times["click_report"] = click_time
        
        # 8. Loading report dialog
        console.print("[dim]Loading report dialog...[/dim]")
        dialog_time = random.uniform(0.5, 1.5)
        await asyncio.sleep(dialog_time)
        flow_times["dialog_load"] = dialog_time
        
        # 9. Selecting report reason
        console.print("[dim]Selecting reason...[/dim]")
        reason_time = random.uniform(1.0, 2.0)
        await asyncio.sleep(reason_time)
        flow_times["select_reason"] = reason_time
        
        # 10. Typing description (if needed)
        if description_length > 0:
            console.print("[dim]Typing description...[/dim]")
            # Generate dummy text of approximate length
            dummy_text = " ".join(["word" for _ in range(description_length // 5)])
            type_time = await self.simulate_human_typing(dummy_text, "normal")
            flow_times["typing"] = type_time
        
        # 11. Final review
        console.print("[dim]Reviewing report...[/dim]")
        review_time = random.uniform(2.0, 4.0)
        await asyncio.sleep(review_time)
        flow_times["review"] = review_time
        
        # 12. Submitting report
        console.print("[dim]Submitting report...[/dim]")
        submit_time = random.uniform(0.3, 0.8)
        await asyncio.sleep(submit_time)
        flow_times["submit"] = submit_time
        
        # 13. Waiting for confirmation
        console.print("[dim]Waiting for confirmation...[/dim]")
        confirm_time = random.uniform(1.0, 2.5)
        await asyncio.sleep(confirm_time)
        flow_times["confirmation"] = confirm_time
        
        return flow_times

# ===== ENHANCED PROXY MANAGER =====

class RealisticProxyManager:
    """Proxy manager that uses proxies from data.txt and rotates them intelligently"""
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.proxy_history: Dict[str, List] = defaultdict(list)
        self.country_stats: Dict[str, Dict] = defaultdict(lambda: {"success": 0, "fail": 0, "response_time": []})
        self.fast_countries = FAST_COUNTRIES
        self.reports_per_proxy = 9  # Rotate proxy after 9 reports
        self.last_refresh = None
        
    async def load_proxies(self):
        """Load proxies from data.txt file"""
        console.print("[cyan]Loading proxies from data.txt...[/cyan]")
        
        if not PROXY_FILE.exists():
            console.print("[yellow]data.txt not found. Creating empty file.[/yellow]")
            PROXY_FILE.parent.mkdir(parents=True, exist_ok=True)
            PROXY_FILE.write_text("# Add proxies in format: ip:port or user:pass@ip:port\n")
            return
        
        try:
            with open(PROXY_FILE, 'r') as f:
                lines = f.readlines()
            
            proxy_count = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Basic proxy format validation
                if ':' in line:
                    # Try to extract country from proxy (if format includes it)
                    country = self._detect_country_from_proxy(line)
                    
                    self.proxies.append({
                        "proxy": line,
                        "country": country,
                        "success_count": 0,
                        "fail_count": 0,
                        "avg_response_time": 1.0,
                        "last_used": None,
                        "reports_done": 0,
                        "is_active": True,
                        "priority": 1.0 if country in self.fast_countries else 0.5
                    })
                    proxy_count += 1
            
            console.print(f"[green]Loaded {proxy_count} proxies from data.txt[/green]")
            
            if not self.proxies:
                console.print("[yellow]No valid proxies found in data.txt[/yellow]")
                return
            
            # Sort proxies by priority (fast countries first)
            self._prioritize_proxies()
            
            # Display proxy stats
            self._display_proxy_stats()
            
        except Exception as e:
            console.print(f"[red]Error loading proxies: {e}[/red]")
    
    def _detect_country_from_proxy(self, proxy: str) -> str:
        """Try to detect country from proxy format"""
        # This is a simple detection - in real use, you might use GeoIP
        proxy_lower = proxy.lower()
        
        country_patterns = {
            "de": "Germany",
            "ger": "Germany",
            "nl": "Netherlands",
            "netherlands": "Netherlands",
            "sg": "Singapore",
            "singapore": "Singapore",
            "us": "United States",
            "usa": "United States",
            "united states": "United States",
            "fi": "Finland",
            "finland": "Finland",
            "ie": "Ireland",
            "ireland": "Ireland",
            "jp": "Japan",
            "japan": "Japan"
        }
        
        for pattern, country in country_patterns.items():
            if pattern in proxy_lower:
                return country
        
        return "Unknown"
    
    def _prioritize_proxies(self):
        """Prioritize proxies based on country and performance"""
        # Sort by: fast country > success rate > response time
        self.proxies.sort(key=lambda x: (
            0 if x["country"] in self.fast_countries else 1,
            -x["success_count"],  # Negative for descending
            x["avg_response_time"]
        ))
    
    def _display_proxy_stats(self):
        """Display proxy statistics"""
        country_dist = defaultdict(int)
        active_proxies = [p for p in self.proxies if p["is_active"]]
        
        for proxy in active_proxies:
            country_dist[proxy["country"]] += 1
        
        table = Table(title="Proxy Statistics", box=box.ROUNDED)
        table.add_column("Country", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Status", style="yellow")
        
        for country, count in sorted(country_dist.items(), key=lambda x: x[1], reverse=True):
            status = "⚡ FAST" if country in self.fast_countries else "✓ OK"
            table.add_row(country, str(count), status)
        
        console.print(table)
    
    async def get_best_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """Get the best available proxy for an account"""
        available = [p for p in self.proxies if p["is_active"] and p["reports_done"] < self.reports_per_proxy]
        
        if not available:
            console.print("[yellow]No available proxies, trying any proxy[/yellow]")
            available = self.proxies
        
        # Prioritize proxies not used by this account recently
        account_history = self.proxy_history.get(account_phone, [])
        recent_proxies = {entry["proxy"] for entry in account_history[-5:]}  # Last 5 proxies used
        
        # Filter out recently used proxies
        fresh_proxies = [p for p in available if p["proxy"] not in recent_proxies]
        
        if fresh_proxies:
            available = fresh_proxies
        
        # Sort by priority
        available.sort(key=lambda x: (
            0 if x["country"] in self.fast_countries else 1,
            -x["success_count"],
            x["avg_response_time"]
        ))
        
        if not available:
            return None
        
        selected = available[0]
        selected["last_used"] = datetime.now()
        selected["reports_done"] += 1
        
        # Record in history
        self.proxy_history[account_phone].append({
            "proxy": selected["proxy"],
            "time": datetime.now().isoformat(),
            "country": selected["country"]
        })
        
        # Limit history size
        if len(self.proxy_history[account_phone]) > 20:
            self.proxy_history[account_phone] = self.proxy_history[account_phone][-20:]
        
        console.print(f"[cyan]Selected proxy for {account_phone}: {selected['country']}[/cyan]")
        return selected["proxy"]
    
    def mark_proxy_success(self, proxy_url: str, response_time: float):
        """Mark proxy as successful"""
        for proxy in self.proxies:
            if proxy["proxy"] == proxy_url:
                proxy["success_count"] += 1
                # Update average response time
                current_avg = proxy["avg_response_time"]
                new_avg = (current_avg * (proxy["success_count"] - 1) + response_time) / proxy["success_count"]
                proxy["avg_response_time"] = new_avg
                break
    
    def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        for proxy in self.proxies:
            if proxy["proxy"] == proxy_url:
                proxy["fail_count"] += 1
                proxy["reports_done"] = self.reports_per_proxy  # Mark for rotation
                
                # Disable proxy if too many failures
                if proxy["fail_count"] >= 3:
                    proxy["is_active"] = False
                    console.print(f"[red]Proxy disabled due to failures: {proxy_url[:30]}...[/red]")
                break
    
    def rotate_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """Force rotate proxy for an account"""
        if account_phone in self.proxy_history and self.proxy_history[account_phone]:
            last_proxy = self.proxy_history[account_phone][-1]["proxy"]
            
            # Mark last proxy as needing rotation
            for proxy in self.proxies:
                if proxy["proxy"] == last_proxy:
                    proxy["reports_done"] = self.reports_per_proxy
                    break
        
        # Get new proxy
        return self.get_best_proxy_for_account(account_phone)
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        total = len(self.proxies)
        active = sum(1 for p in self.proxies if p["is_active"])
        fast = sum(1 for p in self.proxies if p["country"] in self.fast_countries and p["is_active"])
        
        return {
            "total_proxies": total,
            "active_proxies": active,
            "fast_country_proxies": fast,
            "fast_countries": self.fast_countries
        }

# ===== USER MANAGEMENT SYSTEM =====

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
        console.print(f"[green]Initialized {len(self.owner_ids)} owners[/green]")
    
    def _load_users(self):
        """Load users from file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.values():
                        user = TelegramUser.from_dict(user_data)
                        self.users[user.user_id] = user
                console.print(f"[green]Loaded {len(self.users)} users[/green]")
        except Exception as e:
            console.print(f"[red]Error loading users: {e}[/red]")
    
    def _save_users(self):
        """Save users to file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving users: {e}[/red]")
    
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
        
        console.print(f"[green]Added user {user_id} with role {role.value}[/green]")
        return True
    
    def promote_to_sudo(self, user_id: int) -> bool:
        """Promote user to sudo"""
        if user_id not in self.users:
            return False
        
        self.users[user_id].role = UserRole.SUDO
        self._save_users()
        
        console.print(f"[green]Promoted user {user_id} to SUDO[/green]")
        return True
    
    def demote_from_sudo(self, user_id: int) -> bool:
        """Demote user from sudo"""
        if user_id not in self.users or user_id in self.owner_ids:
            return False
        
        self.users[user_id].role = UserRole.USER
        self._save_users()
        
        console.print(f"[yellow]Demoted user {user_id} to USER[/yellow]")
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

# ===== ACCOUNT MANAGER WITH SESSION CREATION =====

class AccountManager:
    """Manage Telegram accounts with session creation"""
    
    def __init__(self, proxy_manager: RealisticProxyManager):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.proxy_manager = proxy_manager
        self.accounts_file = ACCOUNTS_FILE
        self.reports_per_account = 9  # Rotate proxy after 9 reports
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
                console.print(f"[green]Loaded {len(self.accounts)} accounts[/green]")
        except Exception as e:
            console.print(f"[red]Error loading accounts: {e}[/red]")
    
    def _save_accounts(self):
        """Save accounts to file"""
        try:
            data = {phone: account.to_dict() for phone, account in self.accounts.items()}
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving accounts: {e}[/red]")
    
    async def add_account(self, phone: str, session_file: Path = None) -> Tuple[bool, str]:
        """Add a new account - returns (success, message)"""
        if phone in self.accounts:
            return False, "Account already exists"
        
        if not session_file:
            session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        # Get a good proxy for this account
        proxy = await self.proxy_manager.get_best_proxy_for_account(phone)
        if not proxy:
            return False, "No proxies available"
        
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.INACTIVE
        )
        
        self.accounts[phone] = account
        self._save_accounts()
        
        console.print(f"[green]Added account: {phone} with proxy from {account.country}[/green]")
        return True, f"Account {phone} added successfully"
    
    async def create_session(self, phone: str, bot_handler, update: Update) -> bool:
        """Create session for account with interactive login"""
        try:
            if phone not in self.accounts:
                await update.message.reply_text("❌ Account not found. Please add account first.")
                return False
            
            account = self.accounts[phone]
            
            # Random device configuration (mimics real Telegram Desktop)
            device_configs = [
                {"model": "Desktop", "sys_ver": "Windows 10", "app_ver": "4.0.0"},
                {"model": "Desktop", "sys_ver": "Windows 11", "app_ver": "4.1.0"},
                {"model": "Mac", "sys_ver": "macOS 14.0", "app_ver": "4.0.0"},
                {"model": "Linux", "sys_ver": "Ubuntu 22.04", "app_ver": "3.8.0"},
            ]
            
            device = random.choice(device_configs)
            account.device_model = device["model"]
            account.system_version = device["sys_ver"]
            account.app_version = device["app_ver"]
            
            await update.message.reply_text(
                f"🔐 *Creating Desktop Session*\n\n"
                f"Phone: `{phone}`\n"
                f"Device: {device['model']} ({device['sys_ver']})\n"
                f"App Version: {device['app_ver']}\n"
                f"Proxy: {account.country if account.country else 'Auto'}\n\n"
                f"⏳ Please wait while connecting...",
                parse_mode='Markdown'
            )
            
            # Create client with device configuration
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
            
            # Set proxy if available
            if account.proxy:
                client.set_proxy(account.proxy)
            
            # Start connection
            await client.connect()
            
            # Request code
            await update.message.reply_text(
                "📱 *Sending Login Code*\n\n"
                "Requesting verification code from Telegram...\n"
                "This may take a moment.",
                parse_mode='Markdown'
            )
            
            sent_code = await client.send_code_request(phone)
            
            # Store in user session for OTP verification
            user_id = update.effective_user.id
            if hasattr(bot_handler, 'user_sessions'):
                bot_handler.user_sessions[user_id] = {
                    "phone": phone,
                    "client": client,
                    "sent_code": sent_code,
                    "step": "waiting_otp"
                }
            
            await update.message.reply_text(
                f"✅ *Code Sent Successfully*\n\n"
                f"A 5-digit login code has been sent to `{phone}`\n\n"
                f"Please send the code in format: `12345`\n\n"
                f"_You have 5 minutes to enter the code._",
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating session: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return False
    
    async def verify_otp(self, phone: str, otp: str, bot_handler, update: Update) -> bool:
        """Verify OTP and complete login"""
        try:
            user_id = update.effective_user.id
            
            if user_id not in bot_handler.user_sessions:
                await update.message.reply_text("❌ Session expired. Please start over.")
                return False
            
            session_data = bot_handler.user_sessions[user_id]
            
            if session_data["phone"] != phone:
                await update.message.reply_text("❌ Phone number mismatch.")
                return False
            
            client = session_data["client"]
            sent_code = session_data["sent_code"]
            
            await update.message.reply_text(
                "🔐 *Verifying Code...*\n\n"
                "Logging into Telegram Desktop...",
                parse_mode='Markdown'
            )
            
            # Sign in with code
            try:
                await client.sign_in(phone, code=otp, phone_code_hash=sent_code.phone_code_hash)
            except SessionPasswordNeededError:
                # 2FA required
                bot_handler.user_sessions[user_id]["step"] = "need_password"
                await update.message.reply_text(
                    "🔒 *Two-Factor Authentication Required*\n\n"
                    "This account has 2FA enabled.\n"
                    "Please send your 2FA password:",
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
                    # Extract country code from phone
                    if me.phone.startswith('+'):
                        account.country = self._get_country_from_phone(me.phone)
                account.is_premium = getattr(me, 'premium', False)
            except:
                pass
            
            self._save_accounts()
            
            # Cleanup session
            if user_id in bot_handler.user_sessions:
                del bot_handler.user_sessions[user_id]
            
            await update.message.reply_text(
                f"✅ *Login Successful!*\n\n"
                f"Account: `{phone}`\n"
                f"Status: Active\n"
                f"Device: {account.device_model}\n"
                f"Country: {account.country if account.country else 'Unknown'}\n"
                f"Premium: {'Yes' if account.is_premium else 'No'}\n\n"
                f"🎯 Ready for realistic reporting!",
                parse_mode='Markdown'
            )
            
            return True
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ Invalid code. Please try again.")
            return False
        except PhoneCodeExpiredError:
            await update.message.reply_text("❌ Code expired. Please start over.")
            return False
        except Exception as e:
            console.print(f"[red]Error verifying OTP: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return False
    
    async def verify_password(self, phone: str, password: str, bot_handler, update: Update) -> bool:
        """Verify 2FA password"""
        try:
            user_id = update.effective_user.id
            
            if user_id not in bot_handler.user_sessions:
                await update.message.reply_text("❌ Session expired.")
                return False
            
            session_data = bot_handler.user_sessions[user_id]
            client = session_data["client"]
            
            await update.message.reply_text(
                "🔐 *Verifying 2FA Password...*",
                parse_mode='Markdown'
            )
            
            # Sign in with password
            await client.sign_in(password=password)
            
            # Update account status
            account = self.accounts[phone]
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            self._save_accounts()
            
            # Cleanup session
            if user_id in bot_handler.user_sessions:
                del bot_handler.user_sessions[user_id]
            
            await update.message.reply_text(
                f"✅ *2FA Login Successful!*\n\n"
                f"Account `{phone}` is now active and ready.",
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error verifying password: {e}[/red]")
            await update.message.reply_text(f"❌ Error: {str(e)}")
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
    
    def get_available_accounts(self, count: int) -> List[TelegramAccount]:
        """Get available accounts for reporting"""
        available = []
        for account in self.accounts.values():
            if account.status == AccountStatus.ACTIVE and account.report_count < self.reports_per_account:
                available.append(account)
                if len(available) >= count:
                    break
        
        # If not enough active accounts, try inactive ones
        if len(available) < count:
            inactive = [acc for acc in self.accounts.values() 
                       if acc.status == AccountStatus.INACTIVE]
            for account in inactive[:count - len(available)]:
                available.append(account)
        
        return available[:count]
    
    def get_stats(self) -> Dict:
        """Get account statistics"""
        total = len(self.accounts)
        active = sum(1 for a in self.accounts.values() if a.status == AccountStatus.ACTIVE)
        inactive = sum(1 for a in self.accounts.values() if a.status == AccountStatus.INACTIVE)
        banned = sum(1 for a in self.accounts.values() if a.status == AccountStatus.BANNED)
        
        total_reports = sum(a.total_reports for a in self.accounts.values())
        today = datetime.now().date()
        reports_today = sum(a.report_count for a in self.accounts.values() 
                           if a.last_report_time and a.last_report_time.date() == today)
        
        # Count proxies by country
        proxy_countries = defaultdict(int)
        for account in self.accounts.values():
            if account.country:
                proxy_countries[account.country] += 1
        
        return {
            "total_accounts": total,
            "active_accounts": active,
            "inactive_accounts": inactive,
            "banned_accounts": banned,
            "total_reports": total_reports,
            "reports_today": reports_today,
            "proxy_countries": dict(proxy_countries)
        }

# ===== ULTRA REALISTIC REPORTING ENGINE =====

class RealisticReportingEngine:
    """Ultra-realistic reporting engine that mimics human desktop behavior"""
    
    def __init__(self, account_manager: AccountManager, proxy_manager: RealisticProxyManager, user_manager: UserManager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.human_simulator = HumanBehaviorSimulator()
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = []
        
        self._load_history()
        
        # Report categories
        self.report_categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs & Substances",
                "priority": ReportPriority.CRITICAL,
                "desktop_requires_description": True,
                "subcategories": {
                    1: {"name": "Drug Trafficking", "description": "Selling or distributing illegal drugs"},
                    2: {"name": "Drug Promotion", "description": "Promoting drug use or sale"},
                    3: {"name": "Drug Manufacturing", "description": "Manufacturing of illegal substances"},
                    4: {"name": "Drug Recipes", "description": "Sharing instructions for drug production"},
                    5: {"name": "Prescription Drug Abuse", "description": "Abuse of prescription medications"},
                }
            },
            "SPAM": {
                "name": "Spam & Scams",
                "priority": ReportPriority.HIGH,
                "desktop_requires_description": True,
                "subcategories": {
                    1: {"name": "Mass Spamming", "description": "Mass messaging or posting"},
                    2: {"name": "Phishing Links", "description": "Malicious links or phishing"},
                    3: {"name": "Financial Scams", "description": "Financial fraud or scams"},
                    4: {"name": "Fake Giveaways", "description": "Fake contests or giveaways"},
                    5: {"name": "Bot Networks", "description": "Bot accounts or networks"},
                }
            },
            "VIOLENCE": {
                "name": "Violence & Threats",
                "priority": ReportPriority.CRITICAL,
                "desktop_requires_description": True,
                "subcategories": {
                    1: {"name": "Physical Threats", "description": "Threats of physical harm"},
                    2: {"name": "Death Threats", "description": "Threats to kill someone"},
                    3: {"name": "Terrorist Content", "description": "Terrorism-related material"},
                    4: {"name": "Extremist Content", "description": "Hate speech or extremism"},
                    5: {"name": "Violent Content", "description": "Graphic violence or gore"},
                }
            },
            "SEXUAL": {
                "name": "Sexual Content",
                "priority": ReportPriority.HIGH,
                "desktop_requires_description": True,
                "subcategories": {
                    1: {"name": "Non-Consensual", "description": "Non-consensual intimate media"},
                    2: {"name": "Child Exploitation", "description": "Child sexual abuse material"},
                    3: {"name": "Sexual Harassment", "description": "Unwanted sexual advances"},
                    4: {"name": "Pornography", "description": "Adult pornographic content"},
                    5: {"name": "Sexual Services", "description": "Prostitution or escort services"},
                }
            },
            "FRAUD": {
                "name": "Fraud & Deception",
                "priority": ReportPriority.HIGH,
                "desktop_requires_description": True,
                "subcategories": {
                    1: {"name": "Identity Theft", "description": "Stealing personal information"},
                    2: {"name": "Fake Accounts", "description": "Impersonation or fake identity"},
                    3: {"name": "Payment Fraud", "description": "Fraudulent payment requests"},
                    4: {"name": "Account Hacking", "description": "Hacking or unauthorized access"},
                    5: {"name": "Credit Card Fraud", "description": "Credit card information theft"},
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
        
        job = ReportJob(
            target=target,
            target_type=target_type,
            reason_category=category,
            reason_subcategory=subcategory_info["name"],
            description=description,
            accounts_needed=3,  # Use 3 accounts for better success
            priority=self.report_categories[category]["priority"],
            created_by=user_id,
            simulate_desktop=True,
            delay_min=8.0,
            delay_max=20.0
        )
        
        job_id = hashlib.md5(f"{datetime.now()}{random.random()}{target}".encode()).hexdigest()[:12]
        self.active_jobs[job_id] = job
        
        console.print(f"[green]Created job {job_id} for target {target}[/green]")
        return job_id
    
    async def execute_job(self, job_id: str) -> Dict:
        """Execute a report job with ultra-realistic simulation"""
        if job_id not in self.active_jobs:
            return {"error": "Job not found"}
        
        job = self.active_jobs[job_id]
        job.status = ReportStatus.PROCESSING
        
        console.print(f"[cyan]Executing job {job_id} with ultra-realistic simulation[/cyan]")
        
        # Get available accounts
        accounts = self.account_manager.get_available_accounts(job.accounts_needed)
        
        if len(accounts) < job.accounts_needed:
            job.status = ReportStatus.FAILED
            return {"error": f"Insufficient accounts. Need {job.accounts_needed}, have {len(accounts)}"}
        
        # Assign accounts
        job.assigned_accounts = [acc.phone for acc in accounts]
        
        # Execute reports with realistic delays between accounts
        results = []
        for i, account in enumerate(accounts):
            console.print(f"[yellow]Account {i+1}/{len(accounts)}: {account.phone}[/yellow]")
            
            # Realistic delay between account reports (like different people)
            if i > 0:
                delay = random.uniform(job.delay_min, job.delay_max)
                console.print(f"[dim]Human delay: {delay:.1f}s before next person reports...[/dim]")
                await asyncio.sleep(delay)
            
            # Execute single report with ultra-realistic simulation
            result = await self._execute_realistic_report(account, job)
            results.append(result)
            
            if result["status"] == "COMPLETED":
                job.completed_accounts.append(account.phone)
            
            # Update account stats
            account.report_count += 1
            account.total_reports += 1
            account.last_report_time = datetime.now()
            
            # Rotate proxy if reached limit
            if account.report_count >= self.account_manager.reports_per_account:
                new_proxy = self.proxy_manager.rotate_proxy_for_account(account.phone)
                if new_proxy:
                    account.proxy = new_proxy
                    account.last_proxy_rotation = datetime.now()
                    account.report_count = 0
                    console.print(f"[cyan]Rotated proxy for {account.phone}[/cyan]")
        
        job.results = results
        
        # Update job status
        completed = len(job.completed_accounts)
        if completed >= job.accounts_needed:
            job.status = ReportStatus.COMPLETED
        elif completed > 0:
            job.status = ReportStatus.PARTIAL
        else:
            job.status = ReportStatus.FAILED
        
        # Add to history
        self.job_history.append(job)
        self._save_history()
        
        # Update user stats
        if job.created_by:
            self.user_manager.increment_reports(job.created_by)
        
        # Save account changes
        self.account_manager._save_accounts()
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "completed": len(job.completed_accounts),
            "total": job.accounts_needed,
            "results": results,
            "total_simulation_time": sum(r.get("simulation_time", 0) for r in results if "simulation_time" in r)
        }
    
    async def _execute_realistic_report(self, account: TelegramAccount, job: ReportJob) -> Dict:
        """Execute single report with ultra-realistic desktop simulation"""
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
                    "time": 0
                }
            
            # Resolve target
            target_entity = await self._resolve_target(account.client, job.target, job.target_type)
            if not target_entity:
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Could not resolve target",
                    "time": time.time() - start_time
                }
            
            # Ultra-realistic desktop simulation
            console.print(f"[dim]Simulating human desktop reporting for {account.phone}[/dim]")
            
            # Get simulation times for each step
            flow_times = await self.human_simulator.simulate_full_desktop_report_flow(
                job.target_type, 
                len(job.description) if job.description else 0
            )
            
            total_simulation_time = sum(flow_times.values())
            
            # Prepare report reason
            reason_class = self._get_reason_class(job.reason_category)
            reason = reason_class()
            
            # For user reports, simulate viewing profile photo
            if job.target_type == "user":
                await self._simulate_profile_photo_viewing(account.client, target_entity)
            
            # Desktop-style report requires message
            report_message = ""
            if job.description:
                report_message = self._format_desktop_report_description(job.description, job.reason_subcategory)
            
            # Execute actual report (Telegram Desktop style)
            report_request = ReportPeerRequest(
                peer=target_entity,
                reason=reason,
                message=report_message[:300] if report_message else ""
            )
            
            await account.client(report_request)
            
            # Mark proxy success
            if account.proxy:
                self.proxy_manager.mark_proxy_success(account.proxy, total_simulation_time)
            
            total_time = time.time() - start_time
            
            return {
                "account": account.phone,
                "status": "COMPLETED",
                "time": total_time,
                "simulation_time": total_simulation_time,
                "proxy": account.proxy,
                "country": account.country,
                "device": account.device_model,
                "flow_steps": flow_times,
                "message": "Reported via Telegram Desktop simulation"
            }
            
        except FloodWaitError as e:
            account.status = AccountStatus.FLOOD_WAIT
            return {
                "account": account.phone,
                "status": "FLOOD_WAIT",
                "error": f"Flood wait: {e.seconds}s",
                "time": time.time() - start_time
            }
        except Exception as e:
            if account.proxy:
                self.proxy_manager.mark_proxy_failed(account.proxy)
            
            return {
                "account": account.phone,
                "status": "FAILED",
                "error": str(e),
                "time": time.time() - start_time
            }
    
    async def _initialize_client(self, account: TelegramAccount) -> bool:
        """Initialize Telegram client for account"""
        try:
            if account.client and account.client.is_connected():
                return True
            
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
            
            if account.proxy:
                client.set_proxy(account.proxy)
            
            await client.start()
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to initialize client for {account.phone}: {e}[/red]")
            account.status = AccountStatus.INACTIVE
            return False
    
    async def _simulate_profile_photo_viewing(self, client, user_entity):
        """Simulate viewing profile photo (human behavior)"""
        try:
            full_user = await client(GetFullUserRequest(user_entity))
            
            if hasattr(full_user, 'profile_photo') and full_user.profile_photo:
                console.print("[dim]Viewing profile photo...[/dim]")
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                # Simulate right-click or menu interaction
                console.print("[dim]Opening profile options...[/dim]")
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
                return True
        except:
            pass
        return False
    
    def _format_desktop_report_description(self, description: str, subcategory: str) -> str:
        """Format description like a human would in Telegram Desktop"""
        templates = [
            f"Reporting for {subcategory}. Details: {description}",
            f"Violation: {subcategory}. {description}",
            f"Reason: {subcategory}. Additional info: {description}",
            f"I'm reporting this for {subcategory}. Here's why: {description}"
        ]
        
        template = random.choice(templates)
        return template[:500]  # Telegram limit
    
    def _get_reason_class(self, category: str):
        """Get Telethon reason class from category"""
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
        """Resolve target from various formats"""
        try:
            target = target.strip()
            
            # Handle different formats
            if target.startswith("https://t.me/"):
                username = target.split("/")[-1]
                if username.startswith("+"):
                    # Invite link
                    return await client.get_entity(target)
                else:
                    return await client.get_entity(username)
            
            elif target.startswith("@"):
                return await client.get_entity(target[1:])
            
            elif target.isdigit():
                if target_type == "user":
                    return await client.get_entity(PeerUser(int(target)))
                elif target_type == "channel":
                    return await client.get_entity(PeerChannel(int(target)))
                else:
                    return await client.get_entity(int(target))
            
            else:
                # Try as-is
                return await client.get_entity(target)
                
        except Exception as e:
            console.print(f"[red]Failed to resolve target {target}: {e}[/red]")
            return None
    
    def _save_history(self):
        """Save job history"""
        try:
            data = [job.to_dict() for job in self.job_history[-100:]]
            with open(JOB_HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving history: {e}[/red]")
    
    def _load_history(self):
        """Load job history"""
        try:
            if JOB_HISTORY_FILE.exists():
                with open(JOB_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    for job_data in data:
                        job = self._dict_to_job(job_data)
                        self.job_history.append(job)
        except Exception as e:
            console.print(f"[yellow]Error loading history: {e}[/yellow]")
    
    def _dict_to_job(self, data: Dict) -> ReportJob:
        """Convert dict to ReportJob"""
        job = ReportJob(
            target=data["target"],
            target_type=data["target_type"],
            reason_category=data["reason_category"],
            reason_subcategory=data["reason_subcategory"],
            description=data["description"],
            accounts_needed=data.get("accounts_needed", 3),
            priority=ReportPriority(data["priority"]),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"]),
            simulate_desktop=data.get("simulate_desktop", True),
            delay_min=data.get("delay_min", 8.0),
            delay_max=data.get("delay_max", 20.0)
        )
        
        if data.get("schedule_time"):
            job.schedule_time = datetime.fromisoformat(data["schedule_time"])
        
        job.status = ReportStatus(data["status"])
        job.assigned_accounts = data.get("assigned_accounts", [])
        job.completed_accounts = data.get("completed_accounts", [])
        job.results = data.get("results", [])
        
        return job
    
    def get_stats(self) -> Dict:
        """Get reporting engine statistics"""
        return {
            "total_jobs": len(self.job_history),
            "active_jobs": len(self.active_jobs),
            "completed_jobs": sum(1 for j in self.job_history if j.status == ReportStatus.COMPLETED),
            "failed_jobs": sum(1 for j in self.job_history if j.status == ReportStatus.FAILED)
        }

# ===== TELEGRAM BOT HANDLER =====

class TelegramBotHandler:
    """Handle Telegram bot commands with conversation flows"""
    
    def __init__(self, user_manager: UserManager, account_manager: AccountManager, reporting_engine: RealisticReportingEngine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        
        # Conversation states
        self.ADD_ACCOUNT_PHONE, self.ADD_ACCOUNT_OTP, self.ADD_ACCOUNT_PASSWORD = range(3)
        self.REPORT_TARGET, self.REPORT_TYPE, self.REPORT_CATEGORY, self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(5)
        
        # Temporary session storage
        self.user_sessions: Dict[int, Dict] = {}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Update user activity
        self.user_manager.update_user_activity(
            user.id, 
            user.username, 
            user.first_name
        )
        
        role = self.user_manager.get_user_role(user.id)
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        welcome_text = f"""
🤖 *Telegram Enterprise Reporting System v8.0*

*Your Role:* {role_text}

*Features:*
• Ultra-realistic human simulation
• Desktop client emulation
• Proxy rotation (9 reports/account)
• Multi-account support
• Real Telegram Desktop sessions
• Intelligent proxy selection

*Available Commands:*
/start - Show this message
/add - Add new account (Owner/Sudo only)
/report - Start realistic reporting
/stats - View system statistics
/accounts - List all accounts
/jobs - View active jobs
/help - Show help

*Admin Commands (Owner only):*
/addsudo [id] - Add sudo user
/listsudo - List sudo users
/removesudo [id] - Remove sudo user
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - Add new account"""
        user = update.effective_user
        
        # Check permissions
        if not self.user_manager.can_add_accounts(user.id):
            await update.message.reply_text("❌ Permission denied. Owner/Sudo required.")
            return
        
        # Start conversation
        self.user_sessions[user.id] = {"step": "phone"}
        
        await update.message.reply_text(
            "📱 *Add New Telegram Account*\n\n"
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`\n\n"
            "_You must have access to this phone to receive OTP._",
            parse_mode='Markdown'
        )
        
        return self.ADD_ACCOUNT_PHONE
    
    async def handle_add_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input for account addition"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        phone = update.message.text.strip()
        
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ Invalid phone number format.\n"
                "Please use international format: `+1234567890`",
                parse_mode='Markdown'
            )
            return self.ADD_ACCOUNT_PHONE
        
        # Add account to manager
        success, message = await self.account_manager.add_account(phone)
        
        if not success:
            await update.message.reply_text(f"❌ {message}")
            return ConversationHandler.END
        
        # Store in session
        self.user_sessions[user_id]["phone"] = phone
        
        # Create session
        session_created = await self.account_manager.create_session(phone, self, update)
        
        if session_created:
            return self.ADD_ACCOUNT_OTP
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
        
        # Validate OTP
        if not re.match(r'^\d{5}$', otp):
            await update.message.reply_text(
                "❌ Invalid OTP format.\n"
                "Please send 5-digit code: `12345`",
                parse_mode='Markdown'
            )
            return self.ADD_ACCOUNT_OTP
        
        phone = self.user_sessions[user_id]["phone"]
        
        # Verify OTP
        success = await self.account_manager.verify_otp(phone, otp, self, update)
        
        if success:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        else:
            # Check if password is needed
            if user_id in self.user_sessions and self.user_sessions[user_id].get("step") == "need_password":
                return self.ADD_ACCOUNT_PASSWORD
            else:
                return self.ADD_ACCOUNT_OTP
    
    async def handle_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 2FA password"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        password = update.message.text.strip()
        phone = self.user_sessions[user_id]["phone"]
        
        # Verify password
        success = await self.account_manager.verify_password(phone, password, self, update)
        
        if success:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
        
        return ConversationHandler.END
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command - Start reporting"""
        user = update.effective_user
        
        # Update activity
        self.user_manager.update_user_activity(user.id, user.username, user.first_name)
        
        # Start conversation
        self.user_sessions[user.id] = {"step": "target"}
        
        await update.message.reply_text(
            "📝 *Start Realistic Report*\n\n"
            "Please send the target link or username:\n\n"
            "• User: `@username` or `https://t.me/username`\n"
            "• Channel: `@channelname` or `https://t.me/channelname`\n"
            "• Group: `https://t.me/joinchat/xxxxxx`\n\n"
            "_This will simulate human desktop reporting._",
            parse_mode='Markdown'
        )
        
        return self.REPORT_TARGET
    
    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle target input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        target = update.message.text.strip()
        
        # Determine target type
        target_type = "user"  # default
        
        if target.startswith("https://t.me/joinchat/"):
            target_type = "group"
        elif "t.me/" in target and not target.startswith("@"):
            # Try to determine from URL
            if "joinchat" in target:
                target_type = "group"
            else:
                # Could be user or channel
                target_type = "channel"  # assume channel for URLs
        
        self.user_sessions[user_id]["target"] = target
        self.user_sessions[user_id]["target_type"] = target_type
        
        # Show categories
        keyboard = []
        row = []
        for cat_id, cat_info in self.reporting_engine.report_categories.items():
            row.append(InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_report")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Target: `{target[:50]}`\n"
            f"Type: {target_type}\n\n"
            "Select report category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_CATEGORY
    
    async def handle_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_report":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        cat_id = query.data.replace("cat_", "")
        self.user_sessions[user_id]["category"] = cat_id
        
        cat_info = self.reporting_engine.report_categories[cat_id]
        
        # Show subcategories
        keyboard = []
        for sub_id, sub_info in cat_info["subcategories"].items():
            keyboard.append([InlineKeyboardButton(
                f"{sub_id}. {sub_info['name']}",
                callback_data=f"sub_{sub_id}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_report")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📑 *{cat_info['name']}*\n\n"
            "Select specific violation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_subcategory_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subcategory selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_report":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        sub_id = int(query.data.replace("sub_", ""))
        cat_id = self.user_sessions[user_id]["category"]
        
        cat_info = self.reporting_engine.report_categories[cat_id]
        sub_info = cat_info["subcategories"][sub_id]
        
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_info["name"]
        
        await query.edit_message_text(
            f"📝 *Provide Detailed Description*\n\n"
            f"Target: `{self.user_sessions[user_id]['target']}`\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_info['name']}\n\n"
            "Please provide a detailed description (min 30 chars):\n\n"
            "_Example:_ 'This user is posting illegal drug sales in their channel "
            "with contact information and prices shown.'",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report description"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return
        
        description = update.message.text.strip()
        
        if len(description) < 30:
            await update.message.reply_text(
                "❌ Description too short. Minimum 30 characters required."
            )
            return
        
        # Get all data from session
        session = self.user_sessions[user_id]
        target = session["target"]
        target_type = session["target_type"]
        category = session["category"]
        subcategory = session["subcategory"]
        
        try:
            # Create report job
            job_id = await self.reporting_engine.create_report_job(
                target, target_type, category, subcategory, description, user_id
            )
            
            # Start execution in background
            asyncio.create_task(self._execute_and_notify(job_id, user_id))
            
            await update.message.reply_text(
                f"✅ *Realistic Report Started*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{target[:50]}`\n"
                f"Category: {self.reporting_engine.report_categories[category]['name']}\n\n"
                "⏳ *Simulating human desktop behavior...*\n"
                "• Launching Telegram Desktop...\n"
                "• Viewing content...\n"
                "• Typing description...\n"
                "• Submitting report...\n\n"
                "_This will take 30-60 seconds per account._",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        
        # Cleanup
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def _execute_and_notify(self, job_id: str, user_id: int):
        """Execute job and notify user"""
        try:
            result = await self.reporting_engine.execute_job(job_id)
            
            # Prepare status message
            if result.get("status") == "COMPLETED":
                status_text = (
                    f"✅ *Report Completed Successfully!*\n\n"
                    f"Job ID: `{job_id}`\n"
                    f"Status: {result['status']}\n"
                    f"Accounts used: {result['completed']}/{result['total']}\n"
                    f"Total simulation time: {result.get('total_simulation_time', 0):.1f}s\n\n"
                    f"🎯 *Successfully reported from {result['completed']} realistic desktop sessions*"
                )
            elif result.get("status") == "PARTIAL":
                status_text = (
                    f"⚠️ *Report Partially Completed*\n\n"
                    f"Job ID: `{job_id}`\n"
                    f"Status: {result.get('status', 'PARTIAL')}\n"
                    f"Accounts completed: {result.get('completed', 0)}/{result.get('total', 0)}\n"
                    f"Some accounts may have failed or hit limits."
                )
            else:
                status_text = (
                    f"❌ *Report Failed*\n\n"
                    f"Job ID: `{job_id}`\n"
                    f"Status: {result.get('status', 'FAILED')}\n"
                    f"Error: {result.get('error', 'Unknown error')}"
                )
            
            # Send notification via bot
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(
                chat_id=user_id,
                text=status_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            console.print(f"[red]Error in job execution: {e}[/red]")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        # Get all stats
        user_stats = self.user_manager.get_stats()
        account_stats = self.account_manager.get_stats()
        report_stats = self.reporting_engine.get_stats()
        proxy_stats = self.proxy_manager.get_stats()
        
        role = self.user_manager.get_user_role(user.id)
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        # Format proxy countries
        proxy_countries = account_stats.get("proxy_countries", {})
        countries_text = "\n".join([f"  • {c}: {n}" for c, n in list(proxy_countries.items())[:5]])
        if len(proxy_countries) > 5:
            countries_text += f"\n  • ... and {len(proxy_countries) - 5} more"
        
        stats_text = (
            f"📊 *System Statistics*\n\n"
            f"*Your Role:* {role_text}\n"
            f"*Your Reports:* {self.user_manager.users[user.id].reports_made if user.id in self.user_manager.users else 0}\n\n"
            
            f"*👥 Users:*\n"
            f"  • Total: {user_stats['total_users']}\n"
            f"  • Owners: {user_stats['owners']}\n"
            f"  • Sudo: {user_stats['sudo_users']}\n"
            f"  • Regular: {user_stats['regular_users']}\n"
            f"  • Total Reports: {user_stats['total_reports']}\n\n"
            
            f"*📱 Accounts:*\n"
            f"  • Total: {account_stats['total_accounts']}\n"
            f"  • Active: {account_stats['active_accounts']}\n"
            f"  • Reports Today: {account_stats['reports_today']}\n"
            f"  • Total Reports: {account_stats['total_reports']}\n"
            f"  • Proxy Countries:\n{countries_text}\n\n"
            
            f"*📊 Reporting:*\n"
            f"  • Total Jobs: {report_stats['total_jobs']}\n"
            f"  • Active Jobs: {report_stats['active_jobs']}\n"
            f"  • Successful: {report_stats['completed_jobs']}\n\n"
            
            f"*🌐 Proxies:*\n"
            f"  • Total: {proxy_stats['total_proxies']}\n"
            f"  • Active: {proxy_stats['active_proxies']}\n"
            f"  • Fast Countries: {len(proxy_stats['fast_countries'])}"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accounts command - List all accounts"""
        user = update.effective_user
        
        if not self.user_manager.can_add_accounts(user.id):
            await update.message.reply_text("❌ Permission denied. Owner/Sudo required.")
            return
        
        accounts = self.account_manager.accounts.values()
        
        if not accounts:
            await update.message.reply_text("📭 No accounts added yet.")
            return
        
        accounts_text = "📱 *All Accounts*\n\n"
        
        for i, acc in enumerate(list(accounts)[:20], 1):  # Show first 20
            status_icon = "🟢" if acc.status == AccountStatus.ACTIVE else "🟡" if acc.status == AccountStatus.INACTIVE else "🔴"
            premium_icon = "⭐" if acc.is_premium else ""
            
            accounts_text += (
                f"*{i}. {status_icon} {acc.phone}* {premium_icon}\n"
                f"   • Status: {acc.status.value}\n"
                f"   • Reports: {acc.report_count}/9 (Total: {acc.total_reports})\n"
                f"   • Country: {acc.country if acc.country else 'Unknown'}\n"
                f"   • Device: {acc.device_model}\n"
                f"   • Last used: {acc.last_used.strftime('%Y-%m-%d %H:%M') if acc.last_used else 'Never'}\n\n"
            )
        
        if len(accounts) > 20:
            accounts_text += f"\n_... and {len(accounts) - 20} more accounts_"
        
        await update.message.reply_text(accounts_text, parse_mode='Markdown')
    
    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /jobs command - List active jobs"""
        user = update.effective_user
        
        active_jobs = self.reporting_engine.active_jobs
        
        if not active_jobs:
            await update.message.reply_text("📭 No active jobs.")
            return
        
        jobs_text = "📊 *Active Jobs*\n\n"
        
        for job_id, job in list(active_jobs.items())[:10]:  # Show first 10
            status_icon = "🟡" if job.status == ReportStatus.PROCESSING else "🟢" if job.status == ReportStatus.COMPLETED else "🔴"
            
            jobs_text += (
                f"*{job_id}* {status_icon}\n"
                f"   • Target: `{job.target[:30]}...`\n"
                f"   • Type: {job.target_type}\n"
                f"   • Status: {job.status.value}\n"
                f"   • Accounts: {len(job.completed_accounts)}/{job.accounts_needed}\n"
                f"   • Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        if len(active_jobs) > 10:
            jobs_text += f"\n_... and {len(active_jobs) - 10} more jobs_"
        
        await update.message.reply_text(jobs_text, parse_mode='Markdown')
    
    async def addsudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addsudo command - Add sudo user (Owner only)"""
        user = update.effective_user
        
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a user ID.\n"
                "Example: `/addsudo 123456789`",
                parse_mode='Markdown'
            )
            return
        
        try:
            sudo_id = int(context.args[0])
            
            if sudo_id == user.id:
                await update.message.reply_text("❌ You cannot add yourself as sudo.")
                return
            
            success = self.user_manager.promote_to_sudo(sudo_id)
            
            if success:
                await update.message.reply_text(f"✅ User `{sudo_id}` promoted to SUDO.", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to promote user.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    
    async def listsudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listsudo command - List sudo users (Owner only)"""
        user = update.effective_user
        
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        sudo_users = []
        for user_obj in self.user_manager.users.values():
            if user_obj.role == UserRole.SUDO:
                sudo_users.append(user_obj)
        
        if not sudo_users:
            await update.message.reply_text("📭 No sudo users found.")
            return
        
        sudo_text = "⚡ *Sudo Users*\n\n"
        for i, sudo in enumerate(sudo_users, 1):
            sudo_text += (
                f"*{i}. ID:* `{sudo.user_id}`\n"
                f"   • Username: @{sudo.username if sudo.username else 'N/A'}\n"
                f"   • Name: {sudo.first_name if sudo.first_name else 'N/A'}\n"
                f"   • Added: {sudo.added_at.strftime('%Y-%m-%d')}\n"
                f"   • Reports: {sudo.reports_made}\n\n"
            )
        
        await update.message.reply_text(sudo_text, parse_mode='Markdown')
    
    async def removesudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removesudo command - Remove sudo user (Owner only)"""
        user = update.effective_user
        
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a user ID.\n"
                "Example: `/removesudo 123456789`",
                parse_mode='Markdown'
            )
            return
        
        try:
            sudo_id = int(context.args[0])
            
            if sudo_id == user.id:
                await update.message.reply_text("❌ You cannot remove yourself.")
                return
            
            success = self.user_manager.demote_from_sudo(sudo_id)
            
            if success:
                await update.message.reply_text(f"✅ User `{sudo_id}` demoted from SUDO.", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to demote user.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🆘 *Help & Usage Guide*

*Basic Commands:*
/start - Start the bot
/stats - View system statistics
/report - Start realistic reporting
/help - Show this help

*Account Management (Owner/Sudo):*
/add - Add new Telegram account
/accounts - List all accounts
/jobs - View active jobs

*Admin Commands (Owner only):*
/addsudo [id] - Add sudo user
/listsudo - List sudo users
/removesudo [id] - Remove sudo user

*How Reporting Works:*
1. Each account reports max 9 times
2. After 9 reports, proxy is rotated
3. Uses realistic human simulation
4. Desktop client emulation
5. Intelligent proxy selection

*Proxy Requirements:*
• Add proxies to `data/data.txt`
• Format: `ip:port` or `user:pass@ip:port`
• Fast countries: Germany, Netherlands, Singapore, etc.

*Note:* This bot simulates human behavior for educational purposes only.
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

# ===== MAIN APPLICATION =====

class RealisticTelegramReportingBot:
    """Main application class"""
    
    def __init__(self):
        # Initialize managers
        self.user_manager = UserManager()
        self.proxy_manager = RealisticProxyManager()
        self.account_manager = AccountManager(self.proxy_manager)
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
        """Setup Telegram bot handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("accounts", self.bot_handler.accounts_command))
        self.application.add_handler(CommandHandler("jobs", self.bot_handler.jobs_command))
        self.application.add_handler(CommandHandler("addsudo", self.bot_handler.addsudo_command))
        self.application.add_handler(CommandHandler("listsudo", self.bot_handler.listsudo_command))
        self.application.add_handler(CommandHandler("removesudo", self.bot_handler.removesudo_command))
        self.application.add_handler(CommandHandler("help", self.bot_handler.help_command))
        
        # Conversation handler for adding accounts
        add_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.bot_handler.add_command)],
            states={
                self.bot_handler.ADD_ACCOUNT_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_add_phone)
                ],
                self.bot_handler.ADD_ACCOUNT_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_otp)
                ],
                self.bot_handler.ADD_ACCOUNT_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_password)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.start_command)],
            allow_reentry=True
        )
        self.application.add_handler(add_conv_handler)
        
        # Conversation handler for reporting
        report_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("report", self.bot_handler.report_command)],
            states={
                self.bot_handler.REPORT_TARGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_report_target)
                ],
                self.bot_handler.REPORT_CATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_category_selection, pattern="^cat_|^cancel_report$")
                ],
                self.bot_handler.REPORT_DESCRIPTION: [
                    CallbackQueryHandler(self.bot_handler.handle_subcategory_selection, pattern="^sub_|^cancel_report$")
                ]
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.start_command)],
            allow_reentry=True
        )
        self.application.add_handler(report_conv_handler)
        
        # Handler for report description (outside conversation handler for flexibility)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_report_description)
        )
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        console.print(f"[red]Error: {context.error}[/red]")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    
    async def initialize(self):
        """Initialize the system"""
        console.print("[cyan]Initializing Realistic Telegram Reporting System v8.0[/cyan]")
        
        # Print banner
        self._print_banner()
        
        # Load proxies
        await self.proxy_manager.load_proxies()
        
        console.print("[green]System initialized successfully[/green]")
    
    def _print_banner(self):
        """Print system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║     REALISTIC TELEGRAM REPORTING SYSTEM v8.0                ║
║     Ultra-Realistic Human Simulation • Desktop Emulation    ║
╠══════════════════════════════════════════════════════════════╣
║ Owners: 6118760915, 1366105247                              ║
║ Features:                                                    ║
║ • Real Telegram Desktop sessions                            ║
║ • Human behavior simulation (typing, thinking, scrolling)   ║
║ • Proxy rotation after 9 reports                            ║
║ • Fast country prioritization (Germany, Netherlands, etc.)  ║
║ • Multi-account support                                     ║
║ • Owner/Sudo system                                         ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
    
    async def run(self):
        """Run the bot"""
        await self.initialize()
        
        console.print("[green]Starting bot with realistic human simulation...[/green]")
        
        # Start bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        console.print("[green]✅ Bot is running. Press Ctrl+C to stop.[/green]")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system"""
        console.print("[yellow]Shutting down system...[/yellow]")
        
        # Save data
        self.user_manager._save_users()
        self.account_manager._save_accounts()
        self.reporting_engine._save_history()
        
        # Disconnect all clients
        for account in self.account_manager.accounts.values():
            if account.client and account.client.is_connected():
                await account.client.disconnect()
        
        # Stop bot
        if self.application.updater:
            await self.application.updater.stop()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        console.print("[green]System shutdown complete[/green]")

# ===== MAIN ENTRY POINT =====

async def main():
    """Main entry point"""
    bot = RealisticTelegramReportingBot()
    
    try:
        await bot.run()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        # Try to save data on crash
        try:
            bot.user_manager._save_users()
            bot.account_manager._save_accounts()
            bot.reporting_engine._save_history()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
