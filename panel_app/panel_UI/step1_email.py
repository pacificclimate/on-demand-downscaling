import panel as pn
import requests
import os, re
from .state import get_state
from .config import MAGPIE_URL

pn.extension()

# https://github.com/Ouranosinc/Magpie/blob/595602d2cebae94223b952f0cf04a1caa64f6546/magpie/api/management/user/user_utils.py#L66
USERNAME_REGEX = re.compile(r"^[a-z0-9]+(?:[_\-\.][a-z0-9]+)*$")

# https://pavics-magpie.readthedocs.io/en/latest/configuration.html#envvar-MAGPIE_PASSWORD_MIN_LENGTH
MIN_PASSWORD_LEN = 12

EMAIL_REGEX = re.compile(r"^[^@\s]+@((?:[^@\s.]+\.)+[^@\s.]+|\[[0-9A-Fa-f:.]+\])$")


def looks_like_email(text: str) -> bool:
    return bool(EMAIL_REGEX.match(text.strip()))


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
    elif not looks_like_email(e):
        errs.append("Email does not look valid.")

    if u and looks_like_email(u):
        errs.append("Username must not be an email address.")
    if u and e and u.lower() == e.lower():
        errs.append("Username must be different from your email.")
    if len(p) < MIN_PASSWORD_LEN:
        errs.append(f"Password must be at least {MIN_PASSWORD_LEN} characters long.")
    return errs


def step1_authentication(next_step):
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
                state.user = username
                state.email = email
                welcome_md = pn.pane.Markdown(f"## Welcome, **{username}**!", width=400)
                continue_btn = pn.widgets.Button(name="Continue", button_type="primary")
                continue_btn.on_click(lambda event: next_step())
                return pn.Column(welcome_md, continue_btn)
        except Exception:
            pass

    # ---------- LOGIN FORM ----------
    login_username = pn.widgets.TextInput(name="Username")
    login_password = pn.widgets.PasswordInput(name="Password")
    login_submit = pn.widgets.Button(name="Login", button_type="primary")
    login_form = pn.Column(
        "# Step 1: Sign In or Register",
        login_username,
        login_password,
        login_submit,
        message,
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
        message,
        visible=False,
    )

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
                    state.user = username
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
        message.object = ""

    def go_to_login(event=None):
        login_form.visible = True
        register_form.visible = False
        message.object = ""

    # ---------- BUTTON HOOKUP ----------
    login_submit.on_click(login_user)
    reg_submit.on_click(register_user)
    back_button.on_click(go_to_login)

    # ---------- LOGIN & REGISTER TOGGLE BUTTONS ----------
    register_button = pn.widgets.Button(name="📝 Register", button_type="default")
    register_button.on_click(go_to_register)

    signin_panel[:] = [
        pn.Column(
            login_form,
            register_button,
            register_form,
        )
    ]

    return signin_panel
