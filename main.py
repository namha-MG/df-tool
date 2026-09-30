"""
LagoFast Event Auto Tool - GUI Application
Developed with CustomTkinter & Python 3.11
"""
import os
import sys
import time
import datetime
from typing import List, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

from lagofast_api import DEFAULT_AID
from account_manager import AccountManager, Account
from worker import WorkerPool, TaskType

# Cấu hình giao diện CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PasteAccountsDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_submit):
        super().__init__(parent)
        self.title("Nhập danh sách tài khoản")
        self.geometry("620x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_submit = on_submit

        lbl_title = ctk.CTkLabel(
            self,
            text="Dán danh sách Gmail / Login Credential",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(pady=(15, 5))

        lbl_desc = ctk.CTkLabel(
            self,
            text="Hỗ trợ các định dạng (mỗi tài khoản 1 dòng):\n"
                 "• email|login_credential\n"
                 "• email----login_credential\n"
                 "• chỉ login_credential (tool sẽ tự lấy email qua API)",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0",
            justify="left"
        )
        lbl_desc.pack(padx=20, pady=(0, 10), anchor="w")

        self.textbox = ctk.CTkTextbox(self, width=580, height=230, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(padx=20, pady=5)
        self.textbox.focus_set()

        # Nút hành động
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(15, 10), fill="x")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Hủy",
            width=100,
            fg_color="#404040",
            hover_color="#505050",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(10, 0))

        btn_add = ctk.CTkButton(
            btn_frame,
            text="Thêm vào danh sách",
            width=160,
            fg_color="#2ea043",
            hover_color="#3fb950",
            command=self._handle_add
        )
        btn_add.pack(side="right")

    def _handle_add(self):
        text = self.textbox.get("1.0", "end")
        if self.on_submit(text):
            self.destroy()


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LagoFast Event Tool - Chia Sẻ & Quay Thưởng")
        self.geometry("1180x760")
        self.minsize(980, 650)

        self.acc_mgr = AccountManager()
        self.acc_mgr.load_cache()

        # Nếu danh sách rỗng, thêm tài khoản mẫu ban đầu để user tiện thử nghiệm
        if not self.acc_mgr.accounts:
            self.acc_mgr.add_from_text(
                "t524082017@gmail.com|20260930202934000000000001750220_dd2bb9ad64f943bf9a04"
            )

        self.worker_pool: WorkerPool = None

        self._init_styles()
        self._build_ui()
        self._populate_table()
        self._update_stats()

    def _init_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Cấu hình Treeview dark theme
        self.style.configure(
            "Custom.Treeview",
            background="#1e1e1e",
            foreground="#e6edf3",
            fieldbackground="#1e1e1e",
            borderwidth=0,
            rowheight=30,
            font=("Segoe UI", 10)
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background="#2d333b",
            foreground="#58a6ff",
            relief="flat",
            borderwidth=1,
            font=("Segoe UI", 10, "bold")
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", "#1f6feb")],
            foreground=[("selected", "#ffffff")]
        )
        self.style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#38404a")]
        )

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. HEADER & STATS
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#161b22")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")

        # Title
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=15, pady=10)
        
        lbl_app = ctk.CTkLabel(
            title_box,
            text="⚡ LagoFast Event Auto Tool",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#58a6ff"
        )
        lbl_app.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text="Tự động chia sẻ sự kiện & quay thưởng may mắn",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e"
        )
        lbl_sub.pack(anchor="w")

        # Stats Cards
        stats_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_frame.pack(side="right", padx=15, pady=10)

        self.card_total = self._create_stat_card(stats_frame, "👥 Tổng tài khoản", "0", "#58a6ff")
        self.card_shared = self._create_stat_card(stats_frame, "📤 Đã chia sẻ", "0", "#3fb950")
        self.card_times = self._create_stat_card(stats_frame, "🎯 Tổng lượt quay", "0", "#f0883e")
        self.card_prizes = self._create_stat_card(stats_frame, "🎁 Phần thưởng trúng", "0", "#a371f7")

        # 2. CONTROL TOOLBAR & SETTINGS
        ctrl_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#21262d")
        ctrl_frame.grid(row=1, column=0, padx=15, pady=6, sticky="ew")

        # Top row of toolbar: Action Buttons
        act_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        act_row.pack(fill="x", padx=12, pady=(10, 6))

        self.btn_auto_all = ctk.CTkButton(
            act_row,
            text="⚡ CHẠY TẤT CẢ (Chia sẻ + Quay)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#238636",
            hover_color="#2ea043",
            height=34,
            command=lambda: self._start_task(TaskType.AUTO_ALL)
        )
        self.btn_auto_all.pack(side="left", padx=(0, 8))

        self.btn_share = ctk.CTkButton(
            act_row,
            text="📤 Chia Sẻ Sự Kiện",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f6feb",
            hover_color="#388bfd",
            height=34,
            command=lambda: self._start_task(TaskType.SHARE_EVENT)
        )
        self.btn_share.pack(side="left", padx=4)

        self.btn_draw = ctk.CTkButton(
            act_row,
            text="🎲 Quay Thưởng",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8957e5",
            hover_color="#a371f7",
            height=34,
            command=lambda: self._start_task(TaskType.DRAW_LOTTERY)
        )
        self.btn_draw.pack(side="left", padx=4)

        self.btn_check = ctk.CTkButton(
            act_row,
            text="🔍 Kiểm Tra Info",
            font=ctk.CTkFont(size=12),
            fg_color="#30363d",
            hover_color="#484f58",
            height=34,
            command=lambda: self._start_task(TaskType.CHECK_INFO)
        )
        self.btn_check.pack(side="left", padx=4)

        self.btn_stop = ctk.CTkButton(
            act_row,
            text="🛑 DỪNG LẠI",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#da3633",
            hover_color="#f85149",
            height=34,
            state="disabled",
            command=self._stop_task
        )
        self.btn_stop.pack(side="left", padx=4)

        # Right side: Manage accounts
        self.btn_paste = ctk.CTkButton(
            act_row,
            text="➕ Dán danh sách",
            font=ctk.CTkFont(size=12),
            fg_color="#30363d",
            hover_color="#484f58",
            height=34,
            command=self._open_paste_dialog
        )
        self.btn_paste.pack(side="right", padx=(4, 0))

        self.btn_import = ctk.CTkButton(
            act_row,
            text="📂 Nhập File",
            font=ctk.CTkFont(size=12),
            fg_color="#30363d",
            hover_color="#484f58",
            height=34,
            command=self._import_file
        )
        self.btn_import.pack(side="right", padx=4)

        self.btn_export = ctk.CTkButton(
            act_row,
            text="💾 Xuất CSV",
            font=ctk.CTkFont(size=12),
            fg_color="#30363d",
            hover_color="#484f58",
            height=34,
            command=self._export_csv
        )
        self.btn_export.pack(side="right", padx=4)

        # Bottom row of toolbar: Settings
        settings_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        settings_row.pack(fill="x", padx=12, pady=(2, 8))

        lbl_aid = ctk.CTkLabel(settings_row, text="Event AID:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8b949e")
        lbl_aid.pack(side="left", padx=(0, 4))

        self.entry_aid = ctk.CTkEntry(settings_row, width=260, height=28, font=ctk.CTkFont(size=11))
        self.entry_aid.insert(0, DEFAULT_AID)
        self.entry_aid.pack(side="left", padx=(0, 15))

        lbl_threads = ctk.CTkLabel(settings_row, text="Số luồng:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8b949e")
        lbl_threads.pack(side="left", padx=(0, 4))

        self.combo_threads = ctk.CTkComboBox(settings_row, values=["1", "2", "3", "5", "8", "10"], width=70, height=28)
        self.combo_threads.set("3")
        self.combo_threads.pack(side="left", padx=(0, 15))

        lbl_delay = ctk.CTkLabel(settings_row, text="Delay (giây):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8b949e")
        lbl_delay.pack(side="left", padx=(0, 4))

        self.entry_delay = ctk.CTkEntry(settings_row, width=50, height=28)
        self.entry_delay.insert(0, "1.0")
        self.entry_delay.pack(side="left", padx=(0, 15))

        self.chk_spin_all = ctk.CTkCheckBox(
            settings_row,
            text="Tự động quay hết sạch lượt",
            font=ctk.CTkFont(size=11),
            checkbox_height=18,
            checkbox_width=18
        )
        self.chk_spin_all.select()
        self.chk_spin_all.pack(side="left", padx=5)

        btn_clear = ctk.CTkButton(
            settings_row,
            text="🗑️ Xóa tất cả",
            font=ctk.CTkFont(size=11),
            fg_color="#21262d",
            hover_color="#da3633",
            height=26,
            width=80,
            command=self._clear_all_accounts
        )
        btn_clear.pack(side="right", padx=(4, 0))

        btn_del_sel = ctk.CTkButton(
            settings_row,
            text="❌ Xóa đã chọn",
            font=ctk.CTkFont(size=11),
            fg_color="#21262d",
            hover_color="#b62324",
            height=26,
            width=90,
            command=self._delete_selected_accounts
        )
        btn_del_sel.pack(side="right", padx=4)

        # 3. MAIN CONTENT: TABLE & LOGS (PanedWindow)
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#0d1117", bd=0, sashwidth=6, sashrelief="flat")
        paned.grid(row=2, column=0, padx=15, pady=(4, 15), sticky="nsew")

        # Upper: Accounts Table Frame
        table_frame = ctk.CTkFrame(paned, corner_radius=10, fg_color="#161b22")
        paned.add(table_frame, height=380)

        # Treeview Table
        columns = ("stt", "email", "credential", "times", "shared", "prizes", "status", "note")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="extended"
        )

        self.tree.heading("stt", text="#")
        self.tree.heading("email", text="Email / Tài khoản")
        self.tree.heading("credential", text="Login Credential")
        self.tree.heading("times", text="Lượt quay")
        self.tree.heading("shared", text="Chia sẻ")
        self.tree.heading("prizes", text="Phần thưởng đã trúng")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("note", text="Chi tiết")

        self.tree.column("stt", width=45, anchor="center")
        self.tree.column("email", width=200, anchor="w")
        self.tree.column("credential", width=180, anchor="w")
        self.tree.column("times", width=75, anchor="center")
        self.tree.column("shared", width=85, anchor="center")
        self.tree.column("prizes", width=220, anchor="w")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("note", width=180, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        vsb.grid(row=0, column=1, sticky="ns", pady=(8, 0), padx=(0, 8))
        hsb.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Right-click context menu
        self.context_menu = tk.Menu(self, tearoff=0, bg="#21262d", fg="#ffffff", activebackground="#1f6feb", activeforeground="#ffffff")
        self.context_menu.add_command(label="⚡ Chạy tài khoản này (Auto All)", command=self._run_selected_auto)
        self.context_menu.add_command(label="📤 Chia sẻ sự kiện", command=self._run_selected_share)
        self.context_menu.add_command(label="🎲 Quay thưởng", command=self._run_selected_draw)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Sao chép Token (Credential)", command=self._copy_selected_credential)
        self.context_menu.add_command(label="❌ Xóa khỏi danh sách", command=self._delete_selected_accounts)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Lower: Bottom Panel (Progress & Logs)
        bottom_frame = ctk.CTkFrame(paned, corner_radius=10, fg_color="#161b22")
        paned.add(bottom_frame, height=220)

        # Progress bar bar
        prog_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        prog_row.pack(fill="x", padx=12, pady=(8, 4))

        self.lbl_progress = ctk.CTkLabel(
            prog_row,
            text="Sẵn sàng",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8b949e"
        )
        self.lbl_progress.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(prog_row, height=12, fg_color="#21262d", progress_color="#2ea043")
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(15, 0))

        # Logs Box Header
        log_header = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=12, pady=(2, 2))

        lbl_log_title = ctk.CTkLabel(
            log_header,
            text="📋 Nhật ký hoạt động (Live Logs)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#58a6ff"
        )
        lbl_log_title.pack(side="left")

        btn_clear_log = ctk.CTkButton(
            log_header,
            text="Xóa log",
            font=ctk.CTkFont(size=10),
            height=20,
            width=60,
            fg_color="#21262d",
            hover_color="#30363d",
            command=self._clear_logs
        )
        btn_clear_log.pack(side="right")

        # Logs Textbox
        self.txt_logs = ctk.CTkTextbox(
            bottom_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0d1117",
            text_color="#c9d1d9"
        )
        self.txt_logs.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Tag colors for logs
        self.txt_logs.tag_config("INFO", foreground="#58a6ff")
        self.txt_logs.tag_config("SUCCESS", foreground="#3fb950")
        self.txt_logs.tag_config("WARNING", foreground="#d29922")
        self.txt_logs.tag_config("ERROR", foreground="#f85149")
        self.txt_logs.tag_config("TIME", foreground="#8b949e")

        self.log("Ứng dụng khởi động thành công. Sẵn sàng xử lý!", "SUCCESS")

    def _create_stat_card(self, parent, title: str, value: str, color: str):
        card = ctk.CTkFrame(parent, fg_color="#21262d", corner_radius=8, width=130, height=48)
        card.pack(side="left", padx=5)
        card.pack_propagate(False)

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), text_color="#8b949e")
        lbl_title.pack(anchor="w", padx=8, pady=(4, 0))

        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=15, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=8, pady=(0, 4))
        return lbl_val

    def _update_stats(self):
        total = len(self.acc_mgr.accounts)
        shared = sum(1 for a in self.acc_mgr.accounts if a.shared == "Đã chia sẻ")
        times = sum(a.remain_times for a in self.acc_mgr.accounts)
        prizes = sum(len(a.prizes) for a in self.acc_mgr.accounts)

        self.card_total.configure(text=str(total))
        self.card_shared.configure(text=str(shared))
        self.card_times.configure(text=str(times))
        self.card_prizes.configure(text=str(prizes))

    def _populate_table(self):
        self.tree.delete(*self.tree.get_children())
        for acc in self.acc_mgr.accounts:
            self._insert_table_row(acc)

    def _insert_table_row(self, acc: Account):
        self.tree.insert(
            "",
            "end",
            iid=str(acc.index),
            values=(
                acc.index,
                acc.email or "(Chưa lấy email)",
                acc.short_credential,
                acc.remain_times,
                acc.shared,
                acc.display_prizes,
                acc.status,
                acc.note
            )
        )

    def _update_table_row(self, acc: Account):
        iid = str(acc.index)
        if self.tree.exists(iid):
            self.tree.item(
                iid,
                values=(
                    acc.index,
                    acc.email or "(Chưa lấy email)",
                    acc.short_credential,
                    acc.remain_times,
                    acc.shared,
                    acc.display_prizes,
                    acc.status,
                    acc.note
                )
            )
            self._update_stats()

    def log(self, message: str, level: str = "INFO"):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"[{now_str}] ", "TIME")
        self.txt_logs.insert("end", f"[{level}] ", level)
        self.txt_logs.insert("end", f"{message}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def _clear_logs(self):
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.configure(state="disabled")

    # --- Task Execution ---
    def _start_task(self, task_type: str, target_accounts: Optional[List[Account]] = None):
        accounts = target_accounts if target_accounts is not None else self.acc_mgr.accounts
        if not accounts:
            messagebox.showwarning("Thông báo", "Danh sách tài khoản đang rỗng! Vui lòng thêm tài khoản trước.")
            return

        aid = self.entry_aid.get().strip() or DEFAULT_AID
        try:
            threads = int(self.combo_threads.get())
        except Exception:
            threads = 3
        try:
            delay = float(self.entry_delay.get())
        except Exception:
            delay = 1.0

        auto_spin_all = bool(self.chk_spin_all.get())

        self._set_ui_running(True)
        self.progress_bar.set(0)
        self.lbl_progress.configure(text=f"Đang chạy: 0/{len(accounts)} (0%)")

        self.worker_pool = WorkerPool(
            aid=aid,
            delay_sec=delay,
            max_threads=threads,
            auto_spin_all=auto_spin_all,
            on_account_updated=lambda acc: self.after(0, self._on_worker_acc_update, acc),
            on_log=lambda msg, lvl: self.after(0, self.log, msg, lvl),
            on_progress=lambda cur, tot: self.after(0, self._on_worker_progress, cur, tot),
            on_finished=lambda: self.after(0, self._on_worker_finished)
        )
        self.log(f"Bắt đầu tác vụ [{task_type}] với {len(accounts)} tài khoản (Số luồng: {threads})...", "INFO")
        self.worker_pool.start_tasks(accounts, task_type)

    def _stop_task(self):
        if self.worker_pool:
            self.worker_pool.stop()
            self.btn_stop.configure(state="disabled")

    def _on_worker_acc_update(self, acc: Account):
        self._update_table_row(acc)
        self.acc_mgr.save_cache()

    def _on_worker_progress(self, current: int, total: int):
        ratio = current / total if total > 0 else 0
        self.progress_bar.set(ratio)
        self.lbl_progress.configure(text=f"Tiến độ: {current}/{total} ({int(ratio*100)}%)")

    def _on_worker_finished(self):
        self._set_ui_running(False)
        self.log("Tất cả tác vụ đã hoàn tất!", "SUCCESS")
        self.lbl_progress.configure(text="Hoàn tất tác vụ")
        self.acc_mgr.save_cache()
        self._update_stats()

    def _set_ui_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.btn_auto_all.configure(state=state)
        self.btn_share.configure(state=state)
        self.btn_draw.configure(state=state)
        self.btn_check.configure(state=state)
        self.btn_paste.configure(state=state)
        self.btn_import.configure(state=state)
        self.btn_export.configure(state=state)
        self.btn_stop.configure(state="normal" if running else "disabled")

    # --- Account Operations ---
    def _open_paste_dialog(self):
        def on_submit(text: str) -> bool:
            added = self.acc_mgr.add_from_text(text)
            if added > 0:
                self._populate_table()
                self._update_stats()
                self.log(f"Đã thêm thành công {added} tài khoản mới!", "SUCCESS")
                return True
            else:
                messagebox.showwarning("Thông báo", "Không tìm thấy tài khoản mới hợp lệ hoặc đã tồn tại!")
                return False

        PasteAccountsDialog(self, on_submit)

    def _import_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file chứa danh sách tài khoản",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            added = self.acc_mgr.add_from_text(text)
            self._populate_table()
            self._update_stats()
            self.log(f"Đã nhập {added} tài khoản từ file: {os.path.basename(path)}", "SUCCESS")
            messagebox.showinfo("Thành công", f"Đã thêm {added} tài khoản vào danh sách!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

    def _export_csv(self):
        if not self.acc_mgr.accounts:
            messagebox.showwarning("Thông báo", "Danh sách rỗng, không có dữ liệu để xuất!")
            return
        path = filedialog.asksaveasfilename(
            title="Lưu file CSV kết quả",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            self.acc_mgr.export_csv(path)
            self.log(f"Đã xuất dữ liệu ra file: {path}", "SUCCESS")
            messagebox.showinfo("Thành công", f"Đã xuất danh sách thành công ra:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")

    def _clear_all_accounts(self):
        if not self.acc_mgr.accounts:
            return
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa toàn bộ danh sách tài khoản?"):
            self.acc_mgr.clear()
            self._populate_table()
            self._update_stats()
            self.log("Đã xóa toàn bộ tài khoản.", "INFO")

    def _delete_selected_accounts(self):
        selected_iids = self.tree.selection()
        if not selected_iids:
            messagebox.showwarning("Thông báo", "Vui lòng chọn ít nhất một dòng để xóa!")
            return
        indices = [int(iid) - 1 for iid in selected_iids]
        self.acc_mgr.remove_at(indices)
        self._populate_table()
        self._update_stats()
        self.log(f"Đã xóa {len(selected_iids)} tài khoản được chọn.", "INFO")

    # --- Context Menu Callbacks ---
    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _get_selected_account_objects(self) -> List[Account]:
        selected_iids = self.tree.selection()
        result = []
        for iid in selected_iids:
            idx = int(iid) - 1
            if 0 <= idx < len(self.acc_mgr.accounts):
                result.append(self.acc_mgr.accounts[idx])
        return result

    def _run_selected_auto(self):
        accs = self._get_selected_account_objects()
        if accs:
            self._start_task(TaskType.AUTO_ALL, target_accounts=accs)

    def _run_selected_share(self):
        accs = self._get_selected_account_objects()
        if accs:
            self._start_task(TaskType.SHARE_EVENT, target_accounts=accs)

    def _run_selected_draw(self):
        accs = self._get_selected_account_objects()
        if accs:
            self._start_task(TaskType.DRAW_LOTTERY, target_accounts=accs)

    def _copy_selected_credential(self):
        accs = self._get_selected_account_objects()
        if accs:
            self.clipboard_clear()
            self.clipboard_append(accs[0].credential)
            self.log(f"Đã sao chép token của {accs[0].email or accs[0].short_credential} vào bộ nhớ tạm.", "INFO")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
