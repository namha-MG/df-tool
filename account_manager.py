"""
Account Manager Module
Handles parsing, storage, caching, and export of accounts with username/password/token support.
Accurately parses formats like: mail|pass|recovery_mail
"""
import os
import json
import csv
from typing import List, Dict, Any, Optional

CACHE_FILE = "accounts_cache.json"

def is_login_credential(s: str) -> bool:
    s = s.strip()
    if "@" in s:
        return False
    if len(s) >= 40 and "_" in s:
        parts = s.split("_", 1)
        if parts[0].isdigit() and len(parts[0]) >= 20:
            return True
    return False

class Account:
    def __init__(
        self,
        index: int,
        credential: str = "",
        email: str = "",
        password: str = "",
        remain_times: int = 0,
        shared: str = "Chưa",
        prizes: Optional[List[str]] = None,
        status: str = "Chờ",
        note: str = "",
        completed: bool = False
    ):
        self.index = index
        self.credential = credential.strip()
        self.email = email.strip()
        self.password = password.strip()
        self.remain_times = remain_times
        self.shared = shared
        self.prizes = prizes or []
        self.status = status
        self.note = note
        self.completed = completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "credential": self.credential,
            "email": self.email,
            "password": self.password,
            "remain_times": self.remain_times,
            "shared": self.shared,
            "prizes": self.prizes,
            "status": self.status,
            "note": self.note,
            "completed": self.completed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        return cls(
            index=data.get("index", 1),
            credential=data.get("credential", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            remain_times=data.get("remain_times", 0),
            shared=data.get("shared", "Chưa"),
            prizes=data.get("prizes", []),
            status=data.get("status", "Chờ"),
            note=data.get("note", ""),
            completed=data.get("completed", False)
        )

    @property
    def display_prizes(self) -> str:
        if not self.prizes:
            return "-"
        return ", ".join(self.prizes)

    @property
    def short_credential(self) -> str:
        if not self.credential:
            return "(Chưa có token)"
        if len(self.credential) > 16:
            return self.credential[:8] + "..." + self.credential[-8:]
        return self.credential

    @property
    def short_password(self) -> str:
        if not self.password:
            return "-"
        return "••••••"


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
        Thêm tài khoản từ chuỗi văn bản.
        Hỗ trợ các định dạng:
        - mail|pass|mail_khoi_phuc  (Định dạng chuẩn của người dùng)
        - mail|pass|mail_khoi_phuc|token
        - username|password
        - email|password
        - email|login_credential
        - login_credential
        """
        lines = text.strip().splitlines()
        added_count = 0
        existing_keys = {acc.email or acc.credential for acc in self.accounts}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            email = ""
            password = ""
            credential = ""
            note = ""

            # Thử các dấu phân cách phổ biến
            parts = []
            for sep in ["----", "|", ":", ","]:
                if sep in line:
                    parts = [p.strip() for p in line.split(sep)]
                    break

            if len(parts) >= 3:
                # Định dạng: mail | pass | mail_khoi_phuc ...
                email = parts[0]
                password = parts[1]

                # Kiểm tra các phần còn lại xem có token không
                for extra in parts[2:]:
                    if is_login_credential(extra):
                        credential = extra
                        break
                
                # Nếu không phải token và có @, lưu làm ghi chú mail khôi phục
                if not credential and "@" in parts[2]:
                    note = f"KP: {parts[2]}"
                elif not credential and parts[2]:
                    note = parts[2]

            elif len(parts) == 2:
                p0, p1 = parts[0], parts[1]
                if is_login_credential(p1):
                    email = p0
                    credential = p1
                elif is_login_credential(p0):
                    email = p1
                    credential = p0
                else:
                    email = p0
                    password = p1
            elif len(parts) == 1:
                p0 = parts[0]
                if is_login_credential(p0):
                    credential = p0
                else:
                    email = p0
            else:
                if is_login_credential(line):
                    credential = line
                else:
                    email = line

            unique_key = email or credential
            if unique_key and unique_key not in existing_keys:
                existing_keys.add(unique_key)
                new_acc = Account(
                    index=len(self.accounts) + 1,
                    credential=credential,
                    email=email,
                    password=password,
                    remain_times=0,
                    shared="Chưa",
                    prizes=[],
                    status="Chờ",
                    note=note,
                    completed=False
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

    def reset_status_all(self) -> None:
        for acc in self.accounts:
            acc.completed = False
            acc.status = "Chờ"
            acc.note = ""
        self.save_cache()

    def export_csv(self, filepath: str) -> None:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["STT", "Email / Username", "Mật khẩu", "Login Credential", "Lượt quay", "Chia sẻ", "Phần thưởng trúng", "Trạng thái", "Đã hoàn thành", "Ghi chú"])
            for acc in self.accounts:
                writer.writerow([
                    acc.index,
                    acc.email,
                    acc.password,
                    acc.credential,
                    acc.remain_times,
                    acc.shared,
                    acc.display_prizes,
                    acc.status,
                    "Có" if acc.completed else "Chưa",
                    acc.note
                ])
