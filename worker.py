"""
Worker Pool Module
Handles concurrent execution of API actions across accounts with rate-limiting,
auto-login with Username/Password via LoginService, skip completed accounts,
and thread-safe callbacks to GUI.
"""
import time
import threading
from queue import Queue
from typing import List, Callable, Optional, Dict, Any
from lagofast_api import LagoFastAPI, DEFAULT_AID
from account_manager import Account
from login_service import LoginService

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
        on_account_updated: Optional[Callable[[Account], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_finished: Optional[Callable[[], None]] = None
    ):
        self.aid = aid
        self.delay_sec = delay_sec
        self.max_threads = max_threads
        self.auto_spin_all = auto_spin_all
        self.only_uncompleted = only_uncompleted
        self.on_account_updated = on_account_updated
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_finished = on_finished

        self.queue: Queue = Queue()
        self.stop_event = threading.Event()
        self.active_threads: List[threading.Thread] = []
        self.total_tasks = 0
        self.completed_tasks = 0
        self._lock = threading.Lock()

    def log(self, message: str, level: str = "INFO"):
        if self.on_log:
            self.on_log(message, level)

    def is_running(self) -> bool:
        return any(t.is_alive() for t in self.active_threads)

    def stop(self):
        self.stop_event.set()
        self.log("Đang gửi yêu cầu dừng các luồng...", "WARNING")

    def start_tasks(self, accounts: List[Account], task_type: str):
        if self.is_running():
            self.log("Tác vụ khác đang chạy, vui lòng đợi!", "WARNING")
            return

        self.stop_event.clear()
        self.queue = Queue()

        # Lọc danh sách tài khoản nếu bật chế độ chỉ chạy tài khoản chưa hoàn thành
        target_accounts = []
        for acc in accounts:
            if self.only_uncompleted and acc.completed and task_type == TaskType.AUTO_ALL:
                acc_label = acc.email or acc.short_credential
                self.log(f"[{acc_label}] Đã hoàn thành trước đó -> Bỏ qua", "INFO")
                continue
            target_accounts.append(acc)

        if not target_accounts:
            self.log("Tất cả tài khoản trong danh sách đã hoàn thành! (Không có tài khoản nào cần chạy)", "SUCCESS")
            if self.on_finished:
                self.on_finished()
            return

        self.total_tasks = len(target_accounts)
        self.completed_tasks = 0

        for acc in target_accounts:
            self.queue.put((acc, task_type))

        self.active_threads = []
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
        tiến hành đăng nhập để lấy token.
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

        # 2. SHARE EVENT
        elif task_type == TaskType.SHARE_EVENT:
            acc.status = "Đang chia sẻ"
            if self.on_account_updated:
                self.on_account_updated(acc)

            self.log(f"[{acc_label}] Gửi request chia sẻ sự kiện...", "INFO")
            ok_share, msg_share = api.share_activity()
            
            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            if ok_share:
                acc.shared = "Đã chia sẻ"
                acc.status = "Chia sẻ OK"
                acc.note = f"Chia sẻ thành công (+1 lượt, tổng {acc.remain_times})"
                self.log(f"[{acc_label}] {acc.note}", "SUCCESS")
            else:
                acc.status = "Chia sẻ lỗi"
                acc.note = msg_share
                self.log(f"[{acc_label}] {msg_share}", "WARNING")

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
                    prize_name = prize.get("name") or "Quà tặng"
                    item = prize.get("item", "")
                    label = f"{prize_name} ({item}h)" if item else prize_name
                    acc.prizes.append(label)
                    acc.remain_times = max(0, acc.remain_times - 1)
                    acc.status = f"Trúng: {label}"
                    self.log(f"[{acc_label}] 🎉 Chúc mừng trúng: {label}!", "SUCCESS")
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

        # 4. AUTO ALL: Chia sẻ + Quay thưởng (1 lần duy nhất cho mỗi acc)
        elif task_type == TaskType.AUTO_ALL:
            acc.status = "Đang tự động..."
            if self.on_account_updated:
                self.on_account_updated(acc)

            # Bước 1: Lấy email nếu thiếu
            if not acc.email:
                ok_m, mem, _ = api.get_member_detail()
                if ok_m:
                    acc.email = mem.get("email") or mem.get("member_name") or ""
                    acc_label = acc.email or acc.short_credential

            # Bước 2: Chia sẻ sự kiện nhận lượt quay
            self.log(f"[{acc_label}] [1/2] Chia sẻ sự kiện...", "INFO")
            ok_share, msg_share = api.share_activity()
            if ok_share:
                acc.shared = "Đã chia sẻ"
                self.log(f"[{acc_label}] Chia sẻ thành công!", "SUCCESS")
            else:
                self.log(f"[{acc_label}] Chia sẻ: {msg_share}", "WARNING")

            time.sleep(0.8)

            # Bước 3: Lấy số lượt quay
            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times
            self.log(f"[{acc_label}] [2/2] Số lượt quay khả dụng: {acc.remain_times}", "INFO")

            # Bước 4: Quay tất cả lượt
            spins = 0
            while acc.remain_times > 0 and not self.stop_event.is_set():
                spins += 1
                self.log(f"[{acc_label}] Tiến hành quay lượt {spins}...", "INFO")
                ok_draw, prize, msg_draw = api.draw_lottery()
                if ok_draw:
                    prize_name = prize.get("name") or "Quà tặng"
                    item = prize.get("item", "")
                    label = f"{prize_name} ({item}h)" if item else prize_name
                    acc.prizes.append(label)
                    acc.remain_times = max(0, acc.remain_times - 1)
                    self.log(f"[{acc_label}] 🎉 Trúng thưởng: {label}!", "SUCCESS")
                else:
                    self.log(f"[{acc_label}] {msg_draw}", "WARNING")
                    acc.remain_times = 0
                    break
                time.sleep(1.0)

            # Cập nhật số lượt cuối
            ok_t, times, _ = api.get_remain_times()
            if ok_t:
                acc.remain_times = times

            # Đánh dấu đã hoàn thành thành công
            acc.completed = True
            acc.status = "Hoàn tất"
            acc.note = f"Chia sẻ OK | Trúng: {acc.display_prizes}"
            self.log(f"[{acc_label}] Hoàn tất toàn bộ quy trình! Đánh dấu hoàn thành.", "SUCCESS")
            if self.on_account_updated:
                self.on_account_updated(acc)
