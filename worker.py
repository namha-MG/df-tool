"""
Worker Pool Module
Handles concurrent execution of API actions across accounts with rate-limiting,
auto-login with Username/Password via LoginService, skip completed accounts,
multi-round Share & Draw looping, automatic Gift Code extraction & file saving,
and thread-safe callbacks to GUI.
"""
import os
import sys
import time
import datetime
import re
import threading
from queue import Queue
from typing import List, Callable, Optional, Dict, Any
from lagofast_api import LagoFastAPI, DEFAULT_AID
from account_manager import Account
from login_service import LoginService

def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class TaskType:
    CHECK_INFO = "check_info"
    SHARE_EVENT = "share_event"
    DRAW_LOTTERY = "draw_lottery"
    AUTO_ALL = "auto_all"

class WorkerPool:
    def __init__(
        self,
        aid: str = DEFAULT_AID,
        delay_sec: float = 1.0,
        max_threads: int = 3,
        auto_spin_all: bool = True,
        only_uncompleted: bool = True,
        loop_count: int = 1,
        on_account_updated: Optional[Callable[[Account], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_code_saved: Optional[Callable[[str, str, str], None]] = None,
        on_finished: Optional[Callable[[], None]] = None
    ):
        self.aid = aid
        self.delay_sec = delay_sec
        self.max_threads = max_threads
        self.auto_spin_all = auto_spin_all
        self.only_uncompleted = only_uncompleted
        self.loop_count = max(1, loop_count)
        self.on_account_updated = on_account_updated
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_code_saved = on_code_saved
        self.on_finished = on_finished

        self.queue: Queue = Queue()
        self.stop_event = threading.Event()
        self.active_threads: List[threading.Thread] = []
        self.total_tasks = 0
        self.completed_tasks = 0
        self._lock = threading.Lock()
        self._browser_lock = threading.Lock()
        self._code_file_lock = threading.Lock()

    def log(self, message: str, level: str = "INFO"):
        if self.on_log:
            self.on_log(message, level)

    def is_running(self) -> bool:
        return any(t.is_alive() for t in self.active_threads)

    def stop(self):
        self.stop_event.set()
        self.log("Đang gửi yêu cầu dừng các luồng...", "WARNING")

    def _save_code_to_file(self, email: str, prize_label: str, code: str, pack_name: str = ""):
        with self._code_file_lock:
            try:
                app_dir = get_app_dir()
                os.makedirs(app_dir, exist_ok=True)

                if not pack_name:
                    pack_name = prize_label.split("(")[0].strip() if "(" in prize_label else prize_label

                # 1. File codes.txt lưu: Tên_Pack | Mã_Code
                codes_file = os.path.join(app_dir, "codes.txt")
                existing_content = ""
                if os.path.exists(codes_file):
                    with open(codes_file, "r", encoding="utf-8") as f:
                        existing_content = f.read()

                # Tránh lưu trùng lặp cùng 1 mã code
                if code not in existing_content:
                    with open(codes_file, "a", encoding="utf-8") as f:
                        f.write(f"{pack_name} | {code}\n")

                # 2. File codes_detailed.txt (chi tiết thời gian, email, tên pack, mã code)
                detailed_file = os.path.join(app_dir, "codes_detailed.txt")
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(detailed_file, "a", encoding="utf-8") as f:
                    f.write(f"[{now_str}] {email} | Pack: {pack_name} | Code: {code}\n")

                self.log(f"[{email}] 🔑 ĐÃ LƯU MÃ CODE VÀO FILE ({pack_name}): {code} (Xem codes.txt)", "SUCCESS")
                if self.on_code_saved:
                    self.on_code_saved(code, email, pack_name)
            except Exception as e:
                self.log(f"Lỗi khi ghi file code: {e}", "ERROR")

    def start_tasks(self, accounts: List[Account], task_type: str):
        if self.is_running():
            self.log("Tác vụ khác đang chạy, vui lòng đợi!", "WARNING")
            return

        self.stop_event.clear()
        self.queue = Queue()

        target_accounts = []
        for acc in accounts:
            if self.only_uncompleted and acc.completed and task_type == TaskType.AUTO_ALL:
                acc_label = acc.email or acc.short_credential
                self.log(f"[{acc_label}] Đã hoàn thành trước đó -> Bỏ qua", "INFO")
                continue
            target_accounts.append(acc)

        if not target_accounts:
            self.log("Tất cả tài khoản trong danh sách đã hoàn thành!", "SUCCESS")
            if self.on_finished:
                self.on_finished()
            return

        self.total_tasks = len(target_accounts)
        self.completed_tasks = 0

        for acc in target_accounts:
            self.queue.put((acc, task_type))

        self.active_threads = []
        # Chạy song song nhiều tài khoản theo max_threads đã cấu hình
        num_threads = min(self.max_threads, max(1, len(target_accounts)))

        for i in range(num_threads):
            t = threading.Thread(target=self._worker_loop, name=f"Worker-{i+1}", daemon=True)
            self.active_threads.append(t)
            t.start()

        threading.Thread(target=self._monitor_completion, daemon=True).start()

    def _monitor_completion(self):
        for t in self.active_threads:
            t.join()
        if self.on_finished:
            self.on_finished()

    def _ensure_login(self, acc: Account) -> bool:
        """
        Nếu tài khoản chưa có Login-Credential nhưng có mật khẩu,
        tiến hành đăng nhập bằng trình duyệt.
        Dùng lock để không mở quá nhiều trình duyệt cùng 1 giây.
        """
        if acc.credential:
            return True

        if not acc.password:
            acc.status = "Thiếu Token/MK"
            acc.note = "Chưa có Login-Credential và không có mật khẩu"
            self.log(f"[{acc.email}] Thiếu cả Token và Mật khẩu, không thể xử lý!", "ERROR")
            if self.on_account_updated:
                self.on_account_updated(acc)
            return False

        with self._browser_lock:
            # Double check sau khi lấy lock
            if acc.credential:
                return True

            acc.status = "Đang đăng nhập"
            if self.on_account_updated:
                self.on_account_updated(acc)

            ok, token, msg = LoginService.login_with_credentials(
                username=acc.email,
                password=acc.password,
                headless=False,
                timeout=60,
                on_log=self.log
            )
            if ok and token:
                acc.credential = token
                acc.status = "Đã đăng nhập"
                acc.note = "Đăng nhập thành công, đã lưu token"
                self.log(f"[{acc.email}] Đăng nhập thành công!", "SUCCESS")
                if self.on_account_updated:
                    self.on_account_updated(acc)
                return True
            else:
                acc.status = "Đăng nhập lỗi"
                acc.note = msg
                self.log(f"[{acc.email}] {msg}", "ERROR")
                if self.on_account_updated:
                    self.on_account_updated(acc)
                return False

    def _worker_loop(self):
        while not self.stop_event.is_set():
            try:
                acc, task_type = self.queue.get_nowait()
            except Exception:
                break

            try:
                self._process_account(acc, task_type)
            except Exception as e:
                acc.status = "Lỗi"
                acc.note = f"Exception: {str(e)}"
                self.log(f"[{acc.email or acc.short_credential}] Lỗi ngoại lệ: {e}", "ERROR")
                if self.on_account_updated:
                    self.on_account_updated(acc)
            finally:
                with self._lock:
                    self.completed_tasks += 1
                    if self.on_progress:
                        self.on_progress(self.completed_tasks, self.total_tasks)
                self.queue.task_done()
                if self.delay_sec > 0:
                    time.sleep(self.delay_sec)

    def _process_account(self, acc: Account, task_type: str):
        acc_label = acc.email or acc.short_credential

        # Kiểm tra xác thực (đăng nhập nếu cần)
        if not self._ensure_login(acc):
            return

        api = LagoFastAPI(login_credential=acc.credential, aid=self.aid)

        # 1. CHECK INFO
        if task_type == TaskType.CHECK_INFO:
            acc.status = "Đang kiểm tra"
            if self.on_account_updated:
                self.on_account_updated(acc)

            if not acc.email:
                ok_m, mem, _ = api.get_member_detail()
                if ok_m:
                    acc.email = mem.get("email") or mem.get("member_name") or ""
                    acc_label = acc.email or acc.short_credential

            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times
            
            ok_s, state, _ = api.get_change_state()
            if ok_s:
                can_share = state.get("can_share", 1)
                acc.shared = "Chưa" if can_share == 1 else "Đã chia sẻ"

            acc.status = "Thành công"
            acc.note = f"Lượt: {acc.remain_times} | Chia sẻ: {acc.shared}"
            self.log(f"[{acc_label}] Kiểm tra xong: Lượt quay={acc.remain_times}, Chia sẻ={acc.shared}", "SUCCESS")
            if self.on_account_updated:
                self.on_account_updated(acc)

        # 2. SHARE EVENT (Lặp N lần theo cấu hình)
        elif task_type == TaskType.SHARE_EVENT:
            acc.status = "Đang chia sẻ"
            if self.on_account_updated:
                self.on_account_updated(acc)

            shares = 0
            for i in range(1, self.loop_count + 1):
                if self.stop_event.is_set():
                    break
                self.log(f"[{acc_label}] Chia sẻ lần {i}/{self.loop_count}...", "INFO")
                ok_share, msg_share = api.share_activity()
                if ok_share:
                    shares += 1
                    acc.shared = f"Đã chia sẻ ({shares}/{self.loop_count})"
                    self.log(f"[{acc_label}] Lần {i}/{self.loop_count}: Chia sẻ thành công!", "SUCCESS")
                else:
                    self.log(f"[{acc_label}] Lần {i}/{self.loop_count}: {msg_share}", "WARNING")

                if i < self.loop_count and self.delay_sec > 0:
                    time.sleep(self.delay_sec)

            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            acc.status = f"Chia sẻ xong ({shares}/{self.loop_count})"
            acc.note = f"Đã chia sẻ {shares} lần. Tổng lượt quay: {acc.remain_times}"
            if self.on_account_updated:
                self.on_account_updated(acc)

        # 3. DRAW LOTTERY
        elif task_type == TaskType.DRAW_LOTTERY:
            acc.status = "Đang quay"
            if self.on_account_updated:
                self.on_account_updated(acc)

            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            if acc.remain_times <= 0:
                acc.status = "Hết lượt"
                acc.note = "Không còn lượt quay"
                self.log(f"[{acc_label}] Không có lượt quay nào!", "WARNING")
                if self.on_account_updated:
                    self.on_account_updated(acc)
                return

            spins = 0
            while acc.remain_times > 0 and not self.stop_event.is_set():
                spins += 1
                self.log(f"[{acc_label}] Bắt đầu quay lượt {spins}...", "INFO")
                ok_draw, prize, msg_draw = api.draw_lottery()
                if ok_draw:
                    label = prize.get("full_display_name") or prize.get("name") or "Quà tặng"
                    clean_code = prize.get("clean_code")
                    is_code = prize.get("is_code")

                    acc.prizes.append(label)
                    acc.remain_times = max(0, acc.remain_times - 1)
                    acc.status = f"Trúng: {label}"
                    self.log(f"[{acc_label}] 🎉 Chúc mừng trúng: {label}!", "SUCCESS")

                    # Trích xuất tên gói quà (bỏ ngoặc nếu có)
                    pack_name = str(prize.get("name") or prize.get("title") or "Quà tặng").strip()
                    if "(" in pack_name:
                        pack_name = pack_name.split("(")[0].strip()

                    # Trích xuất code dự phòng nếu clean_code chưa được nhận diện
                    if not clean_code:
                        m = re.search(r'([A-Za-z0-9]{4,6}-[A-Za-z0-9]{4,6}-[A-Za-z0-9]{4,6})', label)
                        if m:
                            clean_code = m.group(1).upper()
                            is_code = True

                    # Lưu mã code vào file txt nếu là quà dạng CD-Key / Gift Code
                    if is_code and clean_code:
                        self._save_code_to_file(acc.email or acc.short_credential, label, clean_code, pack_name=pack_name)
                else:
                    self.log(f"[{acc_label}] Quay thất bại: {msg_draw}", "WARNING")
                    acc.remain_times = 0
                    break

                if not self.auto_spin_all:
                    break

                time.sleep(1.0)

            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            acc.status = "Quay xong"
            acc.note = f"Đã quay {spins} lần. Quà: {acc.display_prizes}"
            if self.on_account_updated:
                self.on_account_updated(acc)

        # 4. AUTO ALL: Chạy song song từng acc với N vòng lặp [Chia sẻ + Quay]
        elif task_type == TaskType.AUTO_ALL:
            acc.status = "Đang tự động..."
            if self.on_account_updated:
                self.on_account_updated(acc)

            # Lấy email nếu thiếu
            if not acc.email:
                ok_m, mem, _ = api.get_member_detail()
                if ok_m:
                    acc.email = mem.get("email") or mem.get("member_name") or ""
                    acc_label = acc.email or acc.short_credential

            total_spins = 0
            successful_shares = 0
            rounds = self.loop_count

            self.log(f"[{acc_label}] Bắt đầu chu trình lặp {rounds} lần (Chia sẻ + Quay)...", "INFO")

            for round_idx in range(1, rounds + 1):
                if self.stop_event.is_set():
                    break

                self.log(f"[{acc_label}] 🔄 --- [Vòng {round_idx}/{rounds}] ---", "INFO")

                # Bước 1: Chia sẻ sự kiện nhận lượt quay
                ok_share, msg_share = api.share_activity()
                if ok_share:
                    successful_shares += 1
                    acc.shared = f"Đã chia sẻ ({round_idx}/{rounds})"
                    self.log(f"[{acc_label}] [Vòng {round_idx}] Chia sẻ sự kiện thành công!", "SUCCESS")
                else:
                    self.log(f"[{acc_label}] [Vòng {round_idx}] Chia sẻ: {msg_share}", "WARNING")

                time.sleep(self.delay_sec)

                # Bước 2: Kiểm tra số lượt quay
                ok_t, times, _ = api.get_remain_times()
                if ok_t:
                    acc.remain_times = times
                self.log(f"[{acc_label}] [Vòng {round_idx}] Số lượt quay khả dụng: {acc.remain_times}", "INFO")

                # Bước 3: Quay thưởng
                round_spins = 0
                while acc.remain_times > 0 and not self.stop_event.is_set():
                    round_spins += 1
                    total_spins += 1
                    self.log(f"[{acc_label}] [Vòng {round_idx}] Tiến hành quay lượt {round_spins}...", "INFO")
                    ok_draw, prize, msg_draw = api.draw_lottery()
                    if ok_draw:
                        label = prize.get("full_display_name") or prize.get("name") or "Quà tặng"
                        clean_code = prize.get("clean_code")
                        is_code = prize.get("is_code")

                        acc.prizes.append(label)
                        acc.remain_times = max(0, acc.remain_times - 1)
                        acc.status = f"Trúng: {label}"
                        self.log(f"[{acc_label}] [Vòng {round_idx}] 🎉 Trúng: {label}!", "SUCCESS")

                        # Trích xuất tên gói quà (bỏ ngoặc nếu có)
                        pack_name = str(prize.get("name") or prize.get("title") or "Quà tặng").strip()
                        if "(" in pack_name:
                            pack_name = pack_name.split("(")[0].strip()

                        # Trích xuất code dự phòng nếu clean_code chưa được nhận diện
                        if not clean_code:
                            m = re.search(r'([A-Za-z0-9]{4,6}-[A-Za-z0-9]{4,6}-[A-Za-z0-9]{4,6})', label)
                            if m:
                                clean_code = m.group(1).upper()
                                is_code = True

                        # Lưu mã code vào file txt nếu là quà dạng CD-Key / Gift Code
                        if is_code and clean_code:
                            self._save_code_to_file(acc.email or acc.short_credential, label, clean_code, pack_name=pack_name)
                    else:
                        self.log(f"[{acc_label}] [Vòng {round_idx}] {msg_draw}", "WARNING")
                        acc.remain_times = 0
                        break

                    if not self.auto_spin_all:
                        break
                    time.sleep(1.0)

                acc.note = f"Vòng {round_idx}/{rounds} | Quà: {acc.display_prizes}"
                if self.on_account_updated:
                    self.on_account_updated(acc)

                if round_idx < rounds and self.delay_sec > 0:
                    time.sleep(self.delay_sec)

            # Cập nhật số lượt cuối cùng
            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            acc.completed = True
            acc.status = f"Hoàn tất ({rounds} lần)"
            acc.note = f"Chia sẻ {successful_shares}/{rounds} lần | Quay {total_spins} lần | Quà: {acc.display_prizes}"
            self.log(f"[{acc_label}] Hoàn tất toàn bộ {rounds} vòng lặp!", "SUCCESS")
            if self.on_account_updated:
                self.on_account_updated(acc)
