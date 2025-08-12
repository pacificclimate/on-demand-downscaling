import panel as pn
import os
from .state import get_state, prev_step, set_step
from .widgets import build_panel_continue_button, summary_markdown
from .user_warnings import user_warn, get_user_warning_pane
from .email_results import send_summary_email
from .step2_downscale import update_state_from_controls
from .tasks import process_odds_job
from .config import INDEX_FUNCTIONS_STRUCTURE, PARAMS_TO_WATCH
from rq import Queue
import redis

# Connect to Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
conn = redis.from_url(redis_url)
q = Queue(connection=conn)


def step5_summary_view():
    update_state_from_controls()
    state = get_state()
    summary_md = pn.pane.Markdown(summary_markdown(state))
    launch_btn = build_panel_continue_button("Launch")
    back_btn = build_panel_continue_button("Back")

    def enable_launch(*events):
        launch_btn.disabled = False

    state.param.watch(enable_launch, PARAMS_TO_WATCH)

    def on_launch(event):
        launch_btn.disabled = True
        user_email = state.email
        if not user_email:
            user_warn("No email provided.", "warning")
            return
        summary = summary_markdown(state)
        try:
            send_summary_email(user_email, "Your ODDS Job Submission Summary", summary)
            user_warn("✅ Email sent! Jobs have been launched.", "success")
        except Exception as e:
            user_warn(f"❌ Email failed: {e}", "danger")

        if state.output_intent == "indices":
            # Indices only: use only variables needed for selected indices
            variables_to_downscale = set()
            for idx in state.indices_selected:
                var = idx["variable"]
                print(f"Adding index var: {var}")
                if idx["variable"] == "multivar":
                    variables_to_downscale.add("tasmin")
                    variables_to_downscale.add("tasmax")
                else:
                    variables_to_downscale.add(idx["variable"])
        else:
            # Downscale or both: use all selected variables
            variables_to_downscale = set(state.selected_variables)
            if "multivar" in variables_to_downscale:
                variables_to_downscale.discard("multivar")

        downscale_jobs = []
        for var in variables_to_downscale:
            ds_params = {
                "clim_var": var,
                "dataset": state.internal_dataset,
                "technique": state.internal_technique,
                "model": state.model,
                "canesm5_run": state.canesm5_run,
                "scenario": state.scenario,
                "period": state.period,
                "region": state.region,
                "center_point": getattr(state, "center_point", None),
                "bounds": getattr(state, "map_bounds", None),
            }
            downscale_jobs.append(ds_params)

        index_jobs = []
        for idx in state.indices_selected:
            func_name = next(
                func
                for name, func in INDEX_FUNCTIONS_STRUCTURE[idx["variable"]]
                if name == idx["index_name"]
            )
            ix_params = {
                "index_name": idx["index_name"],
                "func_name": func_name,
                "variable": idx["variable"],
                "resolution": idx.get("resolution"),
                "threshold": idx.get("threshold"),
            }
            index_jobs.append(ix_params)

        job_params = {
            "output_intent": state.output_intent,
            "downscale_jobs": downscale_jobs,
            "index_jobs": index_jobs,
            "user_email": user_email,
        }

        job = q.enqueue(
            "panel_app.panel_UI.tasks.process_odds_job",
            user_email,
            job_params,
            job_timeout=60 * 60 * 6,
        )

        user_warn(f"Job submitted! Job ID: {job.get_id()}", "success")

    def on_prev(event):
        if state.output_intent == "downscale":
            set_step(state.current_step - 2)
        else:
            prev_step()

    launch_btn.on_click(on_launch)
    back_btn.on_click(on_prev)
    return pn.Column(
        summary_md,
        pn.Row(back_btn, launch_btn),
        get_user_warning_pane(),
        width=1200,
        sizing_mode="fixed",
    )
