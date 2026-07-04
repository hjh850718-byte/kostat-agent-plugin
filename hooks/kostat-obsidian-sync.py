#!/usr/bin/env python3
"""
kostat-obsidian-sync.py
Obsidian vault로 KOSTAT 문서를 동기화합니다.

설정 우선순위:
  1. 환경변수  OBSIDIAN_VAULT_PATH, OBSIDIAN_TARGET_DIR
  2. hooks/obsidian-config.json  (vault_path, target_dir)
"""
import json
import os
import shutil
import sys
from pathlib import Path

def _load_config():
    config_file = Path(__file__).parent / "obsidian-config.json"
    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

_cfg = _load_config()
VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", _cfg.get("vault_path", ""))
TARGET_DIR = os.environ.get("OBSIDIAN_TARGET_DIR", _cfg.get("target_dir", "KOSTAT"))

SYNC_FILES = [
    "docs/11. KOSTAT 보고서 체크리스트.md",
]

def main():
    if not VAULT_PATH:
        print("[obsidian-sync] OBSIDIAN_VAULT_PATH 환경변수가 설정되지 않았습니다. 건너뜁니다.")
        sys.exit(0)

    vault = Path(VAULT_PATH)
    if not vault.exists():
        print(f"[obsidian-sync] 볼트 경로를 찾을 수 없습니다: {vault}")
        sys.exit(0)

    target = vault / TARGET_DIR
    target.mkdir(parents=True, exist_ok=True)

    plugin_dir = Path(os.environ.get("PLUGIN_DIR", Path(__file__).parent.parent))

    synced = []
    for rel_path in SYNC_FILES:
        src = plugin_dir / rel_path
        if not src.exists():
            print(f"[obsidian-sync] 파일 없음: {src}")
            continue
        dst = target / src.name
        shutil.copy2(src, dst)
        synced.append(dst.name)

    if synced:
        print(f"[obsidian-sync] {len(synced)}개 동기화 완료 → {target}")
        for f in synced:
            print(f"  ✓ {f}")
    else:
        print("[obsidian-sync] 동기화할 파일 없음.")

if __name__ == "__main__":
    main()
