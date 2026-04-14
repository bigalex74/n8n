#!/usr/bin/env python3
"""
📊 Backup Metrics Exporter for Prometheus
Reads sync.log and repo state, exports metrics in Prometheus format.
Run: python3 backup_metrics.py --port 9199
"""

import os
import re
import time
import http.server
from datetime import datetime, timezone, timedelta

# MSK = UTC+3
MSK = timezone(timedelta(hours=3))
REPO_DIR = "/home/user/n8n-backups"
LOG_FILE = os.path.join(REPO_DIR, "sync.log")


METRICS_PORT = int(os.environ.get("BACKUP_METRICS_PORT", 9199))


def parse_sync_log():
    """Parse sync.log to extract backup history."""
    backups = []
    if not os.path.exists(LOG_FILE):
        return backups
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(
                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (?:✅|❌).*Sync (\S+)",
                    line,
                )
                if m:
                    ts_str, branch = m.group(1), m.group(2)
                    try:
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        ts = ts.replace(tzinfo=MSK)
                        ts_epoch = ts.timestamp()
                    except ValueError:
                        ts_epoch = 0
                    backups.append({"timestamp": ts_epoch, "branch": branch})

                if "❌ Cannot pull from remote" in line:
                    ts_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                    if ts_match:
                        ts_str = ts_match.group(1)
                        try:
                            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            ts = ts.replace(tzinfo=MSK)
                            ts_epoch = ts.timestamp()
                        except ValueError:
                            ts_epoch = 0
                        backups.append({"timestamp": ts_epoch, "branch": "failed", "error": True})
    except Exception:
        pass
    return sorted(backups, key=lambda x: x["timestamp"])


def get_repo_stats():
    """Get git repository stats."""
    stats = {"branches_total": 0, "branches_merged": 0}
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", REPO_DIR, "branch", "--list"],
            capture_output=True, text=True, timeout=10,
        )
        branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
        stats["branches_total"] = len(branches)
        stats["branches_merged"] = len([b for b in branches if b == "master"])
        stats["branches_pending"] = stats["branches_total"] - stats["branches_merged"]
    except Exception:
        pass
    return stats


def get_file_counts():
    """Count backed up files."""
    counts = {}
    dirs = {
        "workflows": "workflows_count",
        "docs": "docs_count",
        "ai_config": "ai_config_count",
        "telegram_apps": "apps_count",
        "system_db_backups": "db_tables_count",
        "infrastructure": "infra_count",
        "tools": "tools_count",
    }
    for dirname, metric_name in dirs.items():
        path = os.path.join(REPO_DIR, dirname)
        if os.path.isdir(path):
            counts[metric_name] = sum(
                len(files) for _, _, files in os.walk(path)
            )
        else:
            counts[metric_name] = 0
    return counts


def generate_metrics():
    """Generate Prometheus metrics."""
    now = time.time()
    backups = parse_sync_log()
    repo_stats = get_repo_stats()
    file_counts = get_file_counts()

    lines = []
    lines.append("# HELP backup_last_success_timestamp_seconds Timestamp of last successful backup")
    lines.append("# TYPE backup_last_success_timestamp_seconds gauge")

    lines.append("# HELP backup_last_status Status of last backup (1=success, 0=failure)")
    lines.append("# TYPE backup_last_status gauge")

    lines.append("# HELP backup_age_seconds Age of last successful backup in seconds")
    lines.append("# TYPE backup_age_seconds gauge")

    lines.append("# HELP backup_total_count Total number of successful backups")
    lines.append("# TYPE backup_total_count counter")

    lines.append("# HELP backup_failures_last_24h Number of failed backups in last 24h")
    lines.append("# TYPE backup_failures_last_24h counter")

    lines.append("# HELP backup_branches_total Total number of git branches")
    lines.append("# TYPE backup_branches_total gauge")

    lines.append("# HELP backup_branches_pending Number of pending (unmerged) branches")
    lines.append("# TYPE backup_branches_pending gauge")

    lines.append("# HELP backup_files_count Number of backed up files by category")
    lines.append("# TYPE backup_files_count gauge")

    # Last backup status
    if backups:
        last = backups[-1]
        is_success = not last.get("error", False)
        lines.append(f'backup_last_success_timestamp_seconds {last["timestamp"] if is_success else 0}')
        lines.append(f'backup_last_status {1 if is_success else 0}')
        lines.append(f'backup_age_seconds {now - last["timestamp"]}')
    else:
        lines.append("backup_last_success_timestamp_seconds 0")
        lines.append("backup_last_status 0")
        lines.append("backup_age_seconds 0")

    # Total count
    success_count = len([b for b in backups if not b.get("error", False)])
    lines.append(f"backup_total_count {success_count}")

    # Failures in last 24h
    day_ago = now - 86400
    failures_24h = len([b for b in backups if b.get("error", False) and b["timestamp"] > day_ago])
    lines.append(f"backup_failures_last_24h {failures_24h}")

    # Branch stats
    lines.append(f"backup_branches_total {repo_stats['branches_total']}")
    lines.append(f"backup_branches_pending {repo_stats.get('branches_pending', 0)}")

    # File counts
    for metric_name, count in file_counts.items():
        lines.append(f'backup_files_count{{category="{metric_name}"}} {count}')

    # Upstream info
    lines.append("# HELP backup_exporter_up Backup metrics exporter is running")
    lines.append("# TYPE backup_exporter_up gauge")
    lines.append("backup_exporter_up 1")

    return "\n".join(lines) + "\n"


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics" or self.path == "/":
            metrics = generate_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
    print(f"📊 Backup Metrics Exporter running on port {METRICS_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
