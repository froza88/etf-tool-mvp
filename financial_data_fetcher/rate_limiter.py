#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RateLimiter - 限流管理器

指数退避、多账号轮换、并发控制。
"""

import time


class RateLimiter:
    """限流管理器"""

    def __init__(self, max_per_minute=60):
        self.max_per_minute = max_per_minute
        self.calls = []

    def wait_if_needed(self):
        """如达到限流阈值则等待"""
        now = time.time()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= self.max_per_minute:
            sleep_time = 60 - (now - self.calls[0]) + 1
            if sleep_time > 0:
                print(f"  限流等待 {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        self.calls.append(time.time())

    def exponential_backoff(self, attempt, max_wait=60):
        """指数退避等待"""
        wait = min(2 ** attempt, max_wait)
        time.sleep(wait)
        return wait
