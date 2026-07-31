import html
import math
import os
import re
from time import time

import panel as pn
import redis
import requests

from .config import MAGPIE_URL
from .email_results import send_summary_email
from .one_time_auth import (
    ONE_TIME_AUTH_ACCESS_TTL_SECONDS,
    ONE_TIME_AUTH_CODE_DIGITS,
    ONE_TIME_AUTH_RESEND_SECONDS,
    ONE_TIME_AUTH_TOKEN_TTL_SECONDS,
    OneTimeAuthRateLimited,
    create_challenge,
    revoke_challenge,
    verify_challenge,
)
from .state import get_state

pn.extension()

# https://github.com/Ouranosinc/Magpie/blob/595602d2cebae94223b952f0cf04a1caa64f6546/magpie/api/management/user/user_utils.py#L66
USERNAME_REGEX = re.compile(r"^[a-z0-9]+(?:[_\-\.][a-z0-9]+)*$")

# https://pavics-magpie.readthedocs.io/en/latest/configuration.html#envvar-MAGPIE_PASSWORD_MIN_LENGTH
MIN_PASSWORD_LEN = 12

EMAIL_REGEX = re.compile(r"^[^@\s]+@((?:[^@\s.]+\.)+[^@\s.]+|\[[0-9A-Fa-f:.]+\])$")


def email_validation_error(text: str) -> str | None:
    value = (text or "").strip()
    # The configured mail relay does not deliver tagged addresses. Comments can
    # also resolve to an untagged mailbox while producing a different quota key.
    if "+" in value or "(" in value or ")" in value:
        return (
            "Email tags (+tag) and comments (...) are not permitted. "
            "Enter your base email address."
        )
    if not EMAIL_REGEX.match(value):
        return "Enter a valid email address."
    return None


def looks_like_email(text: str) -> bool:
    return email_validation_error(text) is None


def validate_registration(username: str, email: str, password: str):
    errs = []
    u = (username or "").strip()
    e = (email or "").strip()
    p = password or ""

    if not u:
        errs.append("Username is required.")
    else:
        if len(u) > 64:
            errs.append(
                "Username must be at most 64 characters long."
            )  # https://pavics-magpie.readthedocs.io/en/latest/configuration.html#envvar-MAGPIE_USER_NAME_MAX_LENGTH
        if not USERNAME_REGEX.match(u):
            errs.append(
                "Username must be lowercase letters or digits, with optional (_ . -) separators between them."
            )
    if not e:
        errs.append("Email is required.")
    elif email_error := email_validation_error(e):
        errs.append(email_error)

    if u and looks_like_email(u):
        errs.append("Username must not be an email address.")
    if u and e and u.lower() == e.lower():
        errs.append("Username must be different from your email.")
    if len(p) < MIN_PASSWORD_LEN:
        errs.append(f"Password must be at least {MIN_PASSWORD_LEN} characters long.")
    return errs


def step0_authentication(next_step):
    state = get_state()
    signin_panel = pn.Column(width=500, margin=(20, 20))

    message = pn.pane.Markdown("", sizing_mode="stretch_width")

    def show_message(msg, level="danger"):
        colors = {
            "success": "green",
            "warning": "orange",
            "danger": "red",
            "info": "blue",
        }
        color = colors.get(level, "black")
        message.object = f"<span style='color:{color}; font-weight:bold'>{msg}</span>"
        message.markdown = False

    user = getattr(state, "user", None)
    is_auth = getattr(state, "authenticated", False)

    if is_auth and user:
        welcome_md = pn.pane.Markdown(f"## Welcome, **{user}**!", width=400)
        continue_btn = pn.widgets.Button(name="Continue", button_type="primary")
        continue_btn.on_click(lambda event: next_step())
        return pn.Column(welcome_md, continue_btn)

    # Attempt auto-login from cookie if present
    if "auth_tkt" in pn.state.cookies and not is_auth:
        try:
            r = requests.get(
                f"{MAGPIE_URL}/session",
                cookies={"auth_tkt": pn.state.cookies["auth_tkt"]},
                timeout=3,
            )
            if r.status_code == 200 and r.json().get("authenticated"):
                username = r.json().get("user", {}).get("user_name", "user")
                email = r.json().get("user", {}).get("email", "user")
                state.authenticated = True
                state.auth_method = "account"
                state.auth_expires_at = 0
                state.user = username
                state.username = username
                state.email = email
                welcome_md = pn.pane.Markdown(f"## Welcome, **{username}**!", width=400)
                continue_btn = pn.widgets.Button(name="Continue", button_type="primary")
                continue_btn.on_click(lambda event: next_step())
                return pn.Column(welcome_md, continue_btn)
        except Exception:
            pass

    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # ---------- LOGIN FORM ----------
    login_username = pn.widgets.TextInput(name="Username")
    login_password = pn.widgets.PasswordInput(name="Password")
    login_submit = pn.widgets.Button(name="Login", button_type="primary")
    login_form = pn.Column(
        "# Sign In or Register",
        login_username,
        login_password,
        login_submit,
    )

    # ---------- REGISTER FORM ----------
    reg_username = pn.widgets.TextInput(name="Username")
    reg_email = pn.widgets.TextInput(name="Email")
    reg_password = pn.widgets.PasswordInput(name="Password")
    reg_submit = pn.widgets.Button(name="Register", button_type="primary")
    back_button = pn.widgets.Button(name="⬅ Back to Login", button_type="default")

    register_form = pn.Column(
        "# Register",
        reg_username,
        reg_email,
        reg_password,
        reg_submit,
        back_button,
        visible=False,
    )

    # ---------- ONE-TIME EMAIL AUTH ----------
    one_time_email = pn.widgets.TextInput(name="Email", placeholder="you@example.com")
    send_code_btn = pn.widgets.Button(name="Email me a code", button_type="primary")
    one_time_back = pn.widgets.Button(name="⬅ Back to Login", button_type="default")
    one_time_form = pn.Column(
        "# One-time access",
        "Enter your email and we’ll send you a short-lived access code. No account is required.",
        one_time_email,
        send_code_btn,
        one_time_back,
        visible=False,
    )

    token_input = pn.widgets.TextInput(
        name="Access code",
        placeholder=f"{ONE_TIME_AUTH_CODE_DIGITS}-digit code",
        max_length=ONE_TIME_AUTH_CODE_DIGITS,
    )
    verify_code_btn = pn.widgets.Button(name="Continue", button_type="primary")
    different_email_btn = pn.widgets.Button(
        name="Use a different email", button_type="default"
    )
    token_destination = pn.pane.HTML("")
    token_form = pn.Column(
        "# Enter your access code",
        token_destination,
        token_input,
        verify_code_btn,
        different_email_btn,
        visible=False,
    )
    current_challenge = {"value": None}

    # ---------- CALLBACKS ----------

    def login_user(event):
        state = get_state()
        login_submit.disabled = True
        try:
            session = requests.Session()

            response = session.post(
                f"{MAGPIE_URL}/signin",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "user_name": login_username.value,
                    "password": login_password.value,
                },
            )

            if response.status_code == 200:
                # Extract auth_tkt cookie
                auth_cookie = next(
                    (c.value for c in session.cookies if c.name == "auth_tkt"), None
                )
                if not auth_cookie:
                    show_message("⚠️ No auth_tkt cookie found after login.", "warning")
                    return
                session_check = requests.get(
                    f"{MAGPIE_URL}/session", cookies=session.cookies
                )
                if session_check.status_code == 200 and session_check.json().get(
                    "authenticated"
                ):
                    # Set only in per-session state
                    username = (
                        session_check.json().get("user", {}).get("user_name", "user")
                    )
                    email = session_check.json().get("user", {}).get("email", "user")
                    state.authenticated = True
                    state.auth_method = "account"
                    state.auth_expires_at = 0
                    state.user = username
                    state.username = username
                    state.email = email
                    pn.state.cookies.update({"auth_tkt": auth_cookie})
                    show_message(f"Welcome, **{username}**!", "success")
                    next_step()
            elif response.status_code == 401:
                show_message(
                    "Invalid username or password. Please try again.", "danger"
                )
                login_password.value = ""
            else:
                try:
                    detail = response.json().get("detail")
                except Exception:
                    detail = response.text.strip()
                show_message(
                    f"Login failed ({response.status_code}): {detail}", "danger"
                )

        except requests.Timeout:
            show_message(
                "Server did not respond in time. Please try again later.", "warning"
            )
        except Exception as e:
            show_message(f"Login error: {e}", "danger")
        finally:
            login_submit.disabled = False

    def register_user(event):
        errs = validate_registration(
            reg_username.value, reg_email.value, reg_password.value
        )
        if errs:
            show_message(
                "Please fix the following:<br>• " + "<br>• ".join(errs), "warning"
            )
            return
        reg_submit.disabled = True
        reg_submit.name = "Registering…"
        try:
            response = requests.post(
                f"{MAGPIE_URL}/register/users",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "user_name": reg_username.value.strip(),
                    "email": reg_email.value.strip(),
                    "password": reg_password.value,
                },
                timeout=10,
            )
            if response.status_code == 201:
                show_message(
                    "✅ Registration successful! Check your email to confirm.",
                    "success",
                )
            elif response.status_code == 409:
                show_message(
                    "A user with this username or email already exists or is pending registration.",
                    "warning",
                )
            elif response.status_code == 400:
                try:
                    data = response.json()
                    srv_errs = data.get("errors") or data.get("detail") or response.text
                    if isinstance(srv_errs, list):
                        srv_errs = "<br>• " + "<br>• ".join(map(str, srv_errs))
                    show_message(f"❌ Registration failed:<br>{srv_errs}", "danger")
                except Exception:
                    show_message(f"❌ Registration failed: {response.text}", "danger")
            else:
                show_message(
                    f"❌ Registration failed ({response.status_code}): {response.text}",
                    "danger",
                )
        except Exception as e:
            show_message(f"🚨 Registration error: {e}", "danger")
        finally:
            reg_submit.disabled = False
            reg_submit.name = "Register"

    def go_to_register(event):
        login_form.visible = False
        register_form.visible = True
        one_time_form.visible = False
        token_form.visible = False
        message.object = ""

    def go_to_login(event=None):
        login_form.visible = True
        register_form.visible = False
        one_time_form.visible = False
        token_form.visible = False
        message.object = ""

    def go_to_one_time(event=None):
        login_form.visible = False
        register_form.visible = False
        token_form.visible = False
        one_time_form.visible = True
        message.object = ""

    def send_one_time_code(event):
        email = one_time_email.value.strip()
        if email_error := email_validation_error(email):
            show_message(email_error, "warning")
            return

        send_code_btn.disabled = True
        send_code_btn.name = "Sending…"
        challenge = None
        try:
            challenge = create_challenge(redis_client, email)
            minutes = max(1, math.ceil(ONE_TIME_AUTH_TOKEN_TTL_SECONDS / 60))
            send_summary_email(
                challenge.email,
                "Your CODDS one-time access code",
                (
                    f"Your CODDS access code is: {challenge.code}\n\n"
                    f"This code expires in {minutes} minutes and can only be used once.\n"
                    "If you did not request it, you can ignore this email."
                ),
            )
            current_challenge["value"] = challenge
            token_destination.object = (
                f"We sent a code to <strong>{html.escape(challenge.email)}</strong>. "
                f"It expires in {minutes} minutes."
            )
            one_time_form.visible = False
            token_form.visible = True
            token_input.value = ""
            show_message("Code sent. Check your inbox and spam folder.", "success")
        except OneTimeAuthRateLimited:
            show_message(
                f"A code was sent recently. Please wait {ONE_TIME_AUTH_RESEND_SECONDS} seconds before requesting another.",
                "warning",
            )
        except Exception as exc:
            if challenge is not None:
                revoke_challenge(redis_client, challenge)
            show_message(f"Could not send an access code: {exc}", "danger")
        finally:
            send_code_btn.disabled = False
            send_code_btn.name = "Email me a code"

    def verify_one_time_code(event):
        challenge = current_challenge["value"]
        if challenge is None:
            go_to_one_time()
            show_message("Request a new access code.", "warning")
            return

        verify_code_btn.disabled = True
        try:
            result = verify_challenge(
                redis_client, challenge.challenge_id, token_input.value
            )
            if result.status == "verified":
                state = get_state()
                state.authenticated = True
                state.auth_method = "one_time"
                state.auth_expires_at = time() + ONE_TIME_AUTH_ACCESS_TTL_SECONDS
                state.email = result.email
                state.user = result.email
                state.username = ""
                current_challenge["value"] = None
                next_step()
                return
            if result.status == "invalid":
                show_message("That code is not correct. Please try again.", "danger")
                token_input.value = ""
            elif result.status == "too_many_attempts":
                current_challenge["value"] = None
                go_to_one_time()
                show_message("Too many incorrect attempts. Request a new code.", "danger")
            else:
                current_challenge["value"] = None
                go_to_one_time()
                show_message("That code has expired. Request a new one.", "warning")
        except Exception as exc:
            show_message(f"Could not verify the access code: {exc}", "danger")
        finally:
            verify_code_btn.disabled = False

    def use_different_email(event=None):
        current_challenge["value"] = None
        go_to_one_time()

    # ---------- BUTTON HOOKUP ----------
    login_submit.on_click(login_user)
    reg_submit.on_click(register_user)
    back_button.on_click(go_to_login)
    send_code_btn.on_click(send_one_time_code)
    verify_code_btn.on_click(verify_one_time_code)
    one_time_back.on_click(go_to_login)
    different_email_btn.on_click(use_different_email)

    # ---------- LOGIN & REGISTER TOGGLE BUTTONS ----------
    register_button = pn.widgets.Button(name="📝 Register", button_type="default")
    register_button.on_click(go_to_register)
    one_time_button = pn.widgets.Button(
        name="✉ One-time email access", button_type="default"
    )
    one_time_button.on_click(go_to_one_time)

    signin_panel[:] = [
        pn.Column(
            login_form,
            pn.Row(register_button, one_time_button),
            register_form,
            one_time_form,
            token_form,
            message,
        )
    ]

    return signin_panel
