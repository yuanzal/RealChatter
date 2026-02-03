# -*- coding: utf-8 -*-
from .chat_api import chat_router
from .health_api import health_router

__all__ = ["chat_router", "health_router"]