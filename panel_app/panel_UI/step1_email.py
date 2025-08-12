import panel as pn
import requests
from .state import get_state
from .config import MAGPIE_URL

pn.extension()


def step1_authentication(next_step):
    state = get_state()
    signin_panel = pn.Column(width=500, margin=(20, 20))

    message = pn.pane.Markdown("")

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
                auth_cookie = None
                for cookie in session.cookies:
                    if cookie.name == "auth_tkt":
                        auth_cookie = cookie.value
                        break

                if not auth_cookie:
                    message.object = "⚠️ No auth_tkt cookie found after login"
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
                    next_step()
                else:
                    message.object = (
                        "⚠️ Login succeeded but /session did not confirm authentication."
                    )
            else:
                message.object = f"❌ Login failed: {response.status_code}"
        except Exception as e:
            message.object = f"🚨 Login error: {str(e)}"

    def register_user(event):
        try:
            response = requests.post(
                f"{MAGPIE_URL}/register/users",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "user_name": reg_username.value,
                    "email": reg_email.value,
                    "password": reg_password.value,
                },
            )
            if response.status_code == 201:
                message.object = "✅ Registration successful! Check your email."
            elif response.status_code == 409:
                message.object = "⚠️ This user is already pending registration."
            else:
                message.object = (
                    f"❌ Registration failed: {response.status_code}, {response.text}"
                )
        except Exception as e:
            message.object = f"🚨 Registration error: {str(e)}"

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
