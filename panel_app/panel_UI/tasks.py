from .wps_wrappers import run_single_downscaling, run_single_index
from .email_results import send_summary_email


def process_odds_job(user_email, job_params):
    output_intent = job_params.get("output_intent", "downscale")  # default fallback
    print(f"user_email: {user_email}")
    print(f"params: {job_params}")

    downscale_results = []
    index_results = []

    for ds_params in job_params.get("downscale_jobs", []):
        output = run_single_downscaling(ds_params)
        downscale_results.append(output)

    # Only run indices if needed
    if output_intent in ("indices", "both"):
        for ix_params in job_params.get("index_jobs", []):
            print("\nDEBUG: Downscale results:")
            for ds in downscale_results:
                print(ds)
            print("\nDEBUG: Index job:", ix_params)
            output = run_single_index(ix_params, downscale_results)
            index_results.append(output)
    email_lines = []
    if output_intent in ("downscale", "both"):
        email_lines.append("Downscaling outputs:")
        for ds in downscale_results:
            email_lines.append(f"- {ds.get('clim_var')}: {ds.get('fileserver_url')}")

    if output_intent in ("indices", "both"):
        email_lines.append("\nCalculated Indices:")
        for idx in index_results:
            email_lines.append(f"- {idx}")

    email_body = "\n".join(email_lines)

    send_summary_email(
        user_email,
        "ODDS Results",
        email_body,
    )
    return "Done"
