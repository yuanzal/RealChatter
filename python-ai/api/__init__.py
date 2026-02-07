# -*- coding: utf-8 -*-
from .chat_api import chat_router
from .health_api import health_router
from .ai_api import ai_router

__all__ = ["chat_router", "health_router", "ai_router"]