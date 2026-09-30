"""
Account Manager Module
Handles parsing, storage, caching, and export of accounts.
"""
import os
import json
import csv
from typing import List, Dict, Any, Optional

CACHE_FILE = "accounts_cache.json"

class Account:
    def __init__(
        self,
        index: int,
        credential: str,
        email: str = "",
        remain_times: int = 0,
        shared: str = "Chưa",
        prizes: Optional[List[str]] = None,
        status: str = "Chờ",
        note: str = ""
    ):
        self.index = index
        self.credential = credential.strip()
        self.email = email.strip()
        self.remain_times = remain_times
        self.shared = shared
        self.prizes = prizes or []
        self.status = status
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "credential": self.credential,
            "email": self.email,
            "remain_times": self.remain_times,
            "shared": self.shared,
            "prizes": self.prizes,
            "status": self.status,
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        return cls(
            index=data.get("index", 1),
            credential=data.get("credential", ""),
            email=data.get("email", ""),
            remain_times=data.get("remain_times", 0),
            shared=data.get("shared", "Chưa"),
            prizes=data.get("prizes", []),
            status=data.get("status", "Chờ"),
            note=data.get("note", "")
        )

    @property
    def display_prizes(self) -> str:
        if not self.prizes:
            return "-"
        return ", ".join(self.prizes)

    @property
    def short_credential(self) -> str:
        if len(self.credential) > 16:
            return self.credential[:8] + "..." + self.credential[-8:]
        return self.credential


class AccountManager:
    def __init__(self, cache_path: str = CACHE_FILE):
        self.cache_path = cache_path
        self.accounts: List[Account] = []

    def load_cache(self) -> None:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts = [Account.from_dict(item) for item in data]
                    self.reindex()
            except Exception as e:
                print(f"Error loading cache: {e}")

    def save_cache(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                data = [acc.to_dict() for acc in self.accounts]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def reindex(self) -> None:
        for i, acc in enumerate(self.accounts, 1):
            acc.index = i

    def add_from_text(self, text: str) -> int:
        """
        Thêm tài khoản từ chuỗi văn bản (dán hoặc đọc file).
        Hỗ trợ các định dạng:
        - email|credential
        - email:credential
        - email----credential
        - credential
        """
        lines = text.strip().splitlines()
        added_count = 0
        existing_creds = {acc.credential for acc in self.accounts}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            email = ""
            credential = ""

            for sep in ["----", "|", ":", ","]:
                if sep in line:
                    parts = line.split(sep, 1)
                    p0 = parts[0].strip()
                    p1 = parts[1].strip()
                    if "@" in p0:
                        email = p0
                        credential = p1
                    elif "@" in p1:
                        email = p1
                        credential = p0
                    else:
                        email = p0
                        credential = p1
                    break

            if not credential:
                credential = line

            if credential and credential not in existing_creds:
                existing_creds.add(credential)
                new_acc = Account(
                    index=len(self.accounts) + 1,
                    credential=credential,
                    email=email,
                    remain_times=0,
                    shared="Chưa",
                    prizes=[],
                    status="Chờ",
                    note=""
                )
                self.accounts.append(new_acc)
                added_count += 1

        self.reindex()
        self.save_cache()
        return added_count

    def clear(self) -> None:
        self.accounts.clear()
        self.save_cache()

    def remove_at(self, indices: List[int]) -> None:
        indices_set = set(indices)
        self.accounts = [acc for i, acc in enumerate(self.accounts) if i not in indices_set]
        self.reindex()
        self.save_cache()

    def export_csv(self, filepath: str) -> None:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["STT", "Email", "Login Credential", "Lượt quay", "Chia sẻ", "Phần thưởng trúng", "Trạng thái", "Ghi chú"])
            for acc in self.accounts:
                writer.writerow([
                    acc.index,
                    acc.email,
                    acc.credential,
                    acc.remain_times,
                    acc.shared,
                    acc.display_prizes,
                    acc.status,
                    acc.note
                ])

    def export_txt_creds(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            for acc in self.accounts:
                if acc.email:
                    f.write(f"{acc.email}|{acc.credential}\n")
                else:
                    f.write(f"{acc.credential}\n")
