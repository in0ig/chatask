"""
Docker / Compose 部署时，业务数据源常保留本机开发配置 host=127.0.0.1 或 localhost。
在容器内这些地址指向容器自身，导致 pymysql 2003 Connection refused。

通过环境变量 CHATBI_DATASOURCE_LOCALHOST_REMAP 将上述 host 重写为 compose 中的 MySQL 服务名（如 mysql），
并可选用 CHATBI_DATASOURCE_LOCALHOST_REMAP_PORT 覆盖端口；未设置时若原端口为 3307 则改为 3306（常见宿主机映射）。
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def remap_mysql_datasource_host(config: Dict[str, Any]) -> Dict[str, Any]:
    if not config:
        return config
    remap_host = os.environ.get("CHATBI_DATASOURCE_LOCALHOST_REMAP", "").strip()
    if not remap_host:
        return config

    raw_host = (config.get("host") or "").strip()
    h = raw_host.lower()
    if h not in ("127.0.0.1", "localhost", "::1"):
        return config

    out = dict(config)
    out["host"] = remap_host

    remap_port_raw = os.environ.get("CHATBI_DATASOURCE_LOCALHOST_REMAP_PORT", "").strip()
    if remap_port_raw:
        try:
            out["port"] = int(remap_port_raw)
        except ValueError:
            logger.warning(
                "忽略无效的 CHATBI_DATASOURCE_LOCALHOST_REMAP_PORT=%r", remap_port_raw
            )
    else:
        try:
            p = int(out.get("port") or 3306)
        except (TypeError, ValueError):
            p = 3306
        # 宿主机常见 3307:3306 映射；在 compose 网内应连服务 3306
        if p == 3307:
            out["port"] = 3306

    logger.info(
        "Docker MySQL 数据源映射: %s:%s -> %s:%s",
        raw_host,
        config.get("port"),
        out.get("host"),
        out.get("port"),
    )
    return out
