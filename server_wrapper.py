#!/usr/bin/env python3
"""
Wrapper para ejecutar el servidor MCP en modo stdio sobre HTTP/SSE
Esto permite que n8n Cloud se conecte al servidor MCP
"""

import asyncio
import os
from src.server import main

if __name__ == "__main__":
    # El servidor MCP se ejecuta normalmente
    asyncio.run(main())
