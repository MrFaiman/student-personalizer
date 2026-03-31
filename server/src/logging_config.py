import logging
import logging.handlers
import os
import sys


def setup_logging() -> None:
    """Configure structured JSON logging for the application.

    SIEM integration (MoE section 4.4):
    Set SYSLOG_HOST and SYSLOG_PORT env vars to forward all logs to a remote
    SIEM/syslog receiver using RFC 5424 format over UDP (default) or TCP.
    """
    log_level = logging.DEBUG if os.getenv("ENABLE_DEBUG", "").lower() in ("1", "true", "yes") else logging.INFO
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    try:
        from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    except ImportError:
        formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")  # type: ignore[assignment]

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(console)
    root.addHandler(file_handler)

    # SIEM / syslog handler (RFC 5424) - enabled when SYSLOG_HOST is set
    syslog_host = os.getenv("SYSLOG_HOST", "")
    if syslog_host:
        syslog_port = int(os.getenv("SYSLOG_PORT", "514"))
        syslog_socktype_env = os.getenv("SYSLOG_SOCKTYPE", "udp").lower()
        import socket
        syslog_socktype = socket.SOCK_DGRAM if syslog_socktype_env == "udp" else socket.SOCK_STREAM
        syslog_handler = logging.handlers.SysLogHandler(
            address=(syslog_host, syslog_port),
            facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
            socktype=syslog_socktype,
        )
        # RFC 5424-compatible format: priority, version, timestamp, hostname, appname, procid, msgid, msg
        syslog_formatter = logging.Formatter(
            fmt="student-personalizer %(levelname)s %(name)s %(message)s",
        )
        syslog_handler.setFormatter(syslog_formatter)
        syslog_handler.setLevel(logging.INFO)  # Only INFO+ to SIEM (no DEBUG noise)
        root.addHandler(syslog_handler)
        logging.getLogger(__name__).info(
            "siem_syslog_enabled",
            extra={"host": syslog_host, "port": syslog_port, "socktype": syslog_socktype_env},
        )

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
