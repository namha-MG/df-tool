"""
LagoFast API Service
Handles authentication, member info, event sharing, and lucky draw spinning.
"""
import requests
import json
import time
from typing import Dict, Any, Optional, Tuple

DEFAULT_AID = "7f01ceea3e054f9aa7a3f92c4aea8a86"
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
DEFAULT_APP_UA = "browser/system_type/system_version/1/LagoFast/1.0.0/5c7da4dd55e9692f47a2fff6b287c350/lang"

class LagoFastAPI:
    def __init__(self, login_credential: str, aid: str = DEFAULT_AID, proxy: Optional[str] = None):
        self.login_credential = login_credential.strip()
        self.aid = aid.strip()
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }
        self.headers = {
            "accept": "*/*",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "client-language": "vi",
            "login-credential": self.login_credential,
            "origin": "https://www.lagofast.com",
            "referer": f"https://www.lagofast.com/vi/act/?aid={self.aid}",
            "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": DEFAULT_UA,
            "useragent": DEFAULT_APP_UA,
            "content-type": "application/json;charset=UTF-8"
        }
        self.session.cookies.set("cid", "1", domain=".lagofast.com")

    def get_member_detail(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Lấy thông tin thành viên (email, uid, member_name...)
        Returns: (success, data, message)
        """
        url = "https://cbs.lagofast.com/api/common_bll/v1/member/detail"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                email = data.get("email") or data.get("member_name") or "Unknown"
                return True, data, f"Thành công ({email})"
            else:
                return False, {}, f"Lỗi HTTP {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            return False, {}, f"Lỗi kết nối: {str(e)}"

    def get_remain_times(self) -> Tuple[bool, int, str]:
        """
        Lấy số lượt quay còn lại
        Returns: (success, times, message)
        """
        url = f"https://act.lagofast.com/api/act/v1/activity/remain/times/{self.aid}"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                times = data.get("times", 0)
                return True, times, f"Còn {times} lượt quay"
            else:
                return False, 0, f"Lỗi HTTP {resp.status_code}"
        except Exception as e:
            return False, 0, f"Lỗi kết nối: {str(e)}"

    def get_change_state(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Kiểm tra trạng thái nhiệm vụ (can_share, can_sign...)
        """
        url = f"https://act.lagofast.com/api/act/v1/change/state/{self.aid}"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                return True, resp.json(), "OK"
            return False, {}, f"Lỗi HTTP {resp.status_code}"
        except Exception as e:
            return False, {}, f"Lỗi kết nối: {str(e)}"

    def share_activity(self) -> Tuple[bool, str]:
        """
        Nhiệm vụ: Chia sẻ sự kiện nhận lượt quay
        Returns: (success, message)
        """
        url = f"https://act.lagofast.com/api/act/v1/change/get/{self.aid}/share_activity"
        try:
            resp = self.session.post(url, headers=self.headers, json={}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state")
                return True, f"Chia sẻ thành công (state: {state})"
            else:
                try:
                    err = resp.json()
                    msg = err.get("err_msg") or err.get("message") or resp.text
                except Exception:
                    msg = resp.text[:100]
                return False, f"Thất bại ({resp.status_code}): {msg}"
        except Exception as e:
            return False, f"Lỗi kết nối: {str(e)}"

    def draw_lottery(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Quay thưởng (Lucky Draw)
        Returns: (success, prize_data, message)
        """
        url = f"https://act.lagofast.com/api/act/v1/luck/draw/{self.aid}"
        try:
            resp = self.session.post(url, headers=self.headers, json={}, timeout=15)
            if resp.status_code == 200:
                prize = resp.json()
                prize_name = prize.get("name") or prize.get("title") or "Quà tặng"
                item_val = prize.get("item", "")
                full_name = f"{prize_name} ({item_val}h)" if item_val else prize_name
                return True, prize, f"Trúng: {full_name}"
            else:
                try:
                    err = resp.json()
                    err_code = err.get("err_code")
                    err_msg = err.get("err_msg") or ""
                    if err_code == "1001" or "次数已用完" in err_msg:
                        return False, {}, "Hết lượt quay"
                    return False, {}, f"Lỗi ({err_code}): {err_msg}"
                except Exception:
                    return False, {}, f"Lỗi HTTP {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            return False, {}, f"Lỗi kết nối: {str(e)}"
