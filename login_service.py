"""
Login Service Module
Handles authentication using Username/Password via automated browser.
Captures the Login-Credential session token automatically.
"""
import time
from typing import Tuple, Optional, Callable

# Explicit imports for PyInstaller packaging
import selenium
import selenium.webdriver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
import selenium.webdriver.chrome.webdriver
import selenium.webdriver.chromium.webdriver

try:
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    import selenium.webdriver.edge.webdriver
except Exception:
    pass

class LoginService:
    @staticmethod
    def _create_driver(headless: bool = False):
        # 1. Thử dùng Chrome
        try:
            options = ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=540,760")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            return webdriver.Chrome(options=options)
        except Exception as e_chrome:
            # 2. Thử fallback sang Microsoft Edge có sẵn trên Windows
            try:
                edge_options = EdgeOptions()
                if headless:
                    edge_options.add_argument("--headless=new")
                edge_options.add_argument("--window-size=540,760")
                edge_options.add_argument("--disable-blink-features=AutomationControlled")
                edge_options.add_argument("--log-level=3")
                edge_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
                return webdriver.Edge(options=edge_options)
            except Exception:
                raise e_chrome

    @staticmethod
    def login_with_credentials(
        username: str,
        password: str,
        headless: bool = False,
        timeout: int = 60,
        on_log: Optional[Callable[[str, str], None]] = None
    ) -> Tuple[bool, str, str]:
        """
        Đăng nhập vào LagoFast bằng username/password qua trình duyệt tự động.
        Tự động điền thông tin, click đăng nhập và trích xuất Login-Credential.
        """
        def log(msg: str, lvl: str = "INFO"):
            if on_log:
                on_log(msg, lvl)

        log(f"[{username}] Đang mở trình duyệt để đăng nhập...", "INFO")

        driver = None
        try:
            driver = LoginService._create_driver(headless=headless)
            driver.get("https://www.lagofast.com/en/user/signin/")
            time.sleep(2.0)

            # 1. Điền Email / Username
            try:
                email_inp = driver.find_element(By.NAME, "email.value")
                email_inp.clear()
                email_inp.send_keys(username)
            except Exception as e:
                return False, "", f"Không tìm thấy ô nhập email: {e}"

            # 2. Điền Password
            try:
                pwd_inp = driver.find_element(By.NAME, "email.password")
                pwd_inp.clear()
                pwd_inp.send_keys(password)
            except Exception as e:
                return False, "", f"Không tìm thấy ô nhập mật khẩu: {e}"

            # 3. Đồng ý điều khoản
            try:
                chk = driver.find_element(By.NAME, "email.agreement")
                if not chk.is_selected():
                    driver.execute_script("arguments[0].click();", chk)
            except Exception:
                pass

            # 4. Click nút Log in
            try:
                submit_btn = driver.find_element(By.XPATH, "//button[contains(., 'Log in') or contains(., 'SIGNIN')]")
                driver.execute_script("arguments[0].click();", submit_btn)
                log(f"[{username}] Đã gửi thông tin đăng nhập, đang chờ token...", "INFO")
            except Exception as e:
                return False, "", f"Không tìm thấy nút đăng nhập: {e}"

            # 5. Chờ cookie Login-Credential xuất hiện
            start_time = time.time()
            notified_captcha = False

            while time.time() - start_time < timeout:
                time.sleep(1.0)

                cookies = driver.get_cookies()
                for c in cookies:
                    if c.get("name") == "Login-Credential" and c.get("value"):
                        token = c.get("value")
                        log(f"[{username}] Đăng nhập thành công! Đã lấy được token.", "SUCCESS")
                        return True, token, "Đăng nhập thành công"

                # Kiểm tra xem có thông báo lỗi sai mật khẩu không
                error_tips = driver.find_elements(By.XPATH, "//*[contains(@class, 'errorTip') or contains(@class, 'ant-message')]")
                for tip in error_tips:
                    txt = tip.text.strip()
                    if txt and any(w in txt.lower() for w in ["password", "incorrect", "wrong", "fail", "not exist"]):
                        return False, "", f"Lỗi: {txt}"

                # Kiểm tra captcha xuất hiện
                geetest_box = driver.find_elements(By.CLASS_NAME, "geetest_holder")
                if geetest_box and not notified_captcha:
                    notified_captcha = True
                    log(f"[{username}] Vui lòng trượt xác minh Captcha trên cửa sổ trình duyệt...", "WARNING")

            return False, "", f"Hết thời gian chờ đăng nhập ({timeout}s)"

        except Exception as e:
            return False, "", f"Lỗi trình duyệt: {str(e)}"
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
