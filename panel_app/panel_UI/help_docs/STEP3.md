## 3. Computing Climate Indices

Next, choose which climate indices you want to calculate for your selected region and variables.

- The climate indices shown correspond to the climate variables specified in Step 2. If a desired index does not appear, you may have to return to Step 1. For example, if you want to compute Freeze-Thaw Days, you need to select BOTH Tmax and Tmin in Step 1.
- Select the climate indices you would like to compute. Note that **the processing time scales approximately with the number of indices**.
- Once you press Continue, **both downscaling and index calculations will be run as a single process** for your selections.
  - If you change your selection to “Daily Outputs Only” in the previous step, this page will be skipped and only downscaling will run.

### About the indices

- The indices are computed using Ouranos's [finch](https://github.com/bird-house/finch/tree/master) service, which is based on their [xclim](https://github.com/Ouranosinc/xclim/tree/main) package.
- The set of available indices includes most of the [core climdex indices](https://climate-scenarios.canada.ca/?page=climdex-indices) and degree days, supplemented by others that allow additional flexibility.  This index set will be reviewed regularly and may change in future.
- For some indices, you need to specify threshold value(s) and/or time resolution.
- Indices requiring multiple variables (e.g. “Extreme Temperature Range”) can only be computed if all required variables were slected in Step 1.

### The table below summarizes the available indices (refer to the Climdex indices page for more details):

| Variable              | Climdex Index Name / Description      | Threshold Value                                                | Finch Process                  |
| --------------------- | ------------------------------------- | -------------------------------------------------------------- | ------------------------------ |
| Tasmax (TX)           | Mean TX                               | NA                                                             | tx_mean                        |
|                       | Hottest Day                           | NA                                                             | tx_max                         |
|                       | Coldest Day                           | NA                                                             | tx_min                         |
|                       | Ice Days                              | 0 degC                                                         | ice_days                       |
|                       | Days Above a Specified TX             | 20 to 35 degC                                                  | tx_days_above                  |
| Tasmin (TN)           | Mean TN                               | NA                                                             | tn_mean                        |
|                       | Hottest Night                         | NA                                                             | tn_max                         |
|                       | Coldest Night                         | NA                                                             | tn_min                         |
|                       | Frost Days                            | 0 degC                                                         | frost_days                     |
|                       | Days Above a Specified TN             | 10 to 30 degC                                                  | tn_days_above                  |
|                       | Days Below a Specified TN             | -30 to 0 degC                                                  | tn_days_below                  |
| Tasmean (TM)          | Mean TM                               | NA                                                             | tg_mean                        |
|                       | Growing Season Length                 | 5 degC                                                         | growing_season_length          |
|                       | Growing Degree Days                   | 18 degC                                                        | growing_degree_days            |
|                       | Freezing Degree Days                  | 0 degC                                                         | freezing_degree_days           |
|                       | Heating Degree Days                   | 10 to 20 degC                                                  | heating_degree_days            |
|                       | Cooling Degree Days                   | 10 to 20 degC                                                  | cooling_degree_days            |
|                       | Cold Spell Days                       | -20 to -10 degC + number of days                               | cold_spell_days                |
| Pr                    | Max N-day Precip Amount               | 1 to 10 days                                                   | max_n_day_precipitation_amount |
|                       | Total Precipitation                   | NA                                                             | prcptot                        |
|                       | Average Wet-Day Precipitation (SDII)  | 1 mm/day                                                       | sdii                           |
|                       | Days with Precip over Threshold of N-mm | 1 to 30 mm/day                                               | wetdays                        |
|                       | Days Over Precip Percentile Threshold | percentile (0 to 99) + wetday threshold; percentile = 0 uses threshold-only mode | days_over_precip_thresh (percentile > 0), wetdays (percentile = 0) |
|                       | Maximum Length of Wet Spell           | 1 to 30 mm/day                                                 | cwd                            |
|                       | Maximum Length of Dry Spell           | 1 to 3 mm/day                                                  | cdd                            |
| Tasmin+Tasmax (TN+TX) | Extreme Temperature Range             | NA                                                             | etr                            |
|                       | Freeze-Thaw Days                      | NA                                                             | dlyfrzthw                      |
| Pr+Tasmean (pr+TM)    | Snowfall                              | Method: auer                                                   | prsn                           |
|                       | Rainfall                              | Method: auer                                                   | prlp                           |
| Tasmax (TX)           | Heat Wave Days                        | TX threshold + number of days                                  | heat_wave_index                |
| Tasmin+Tasmax (TN+TX) | Heat Wave Number                      | TN/TX threshold + number of days                               | heat_wave_frequency            |
|                       | Heat Wave Maximum Length              | TN/TX threshold + number of days                               | heat_wave_max_length           |

### How long does it take?

- Processing time varies by index and region (typically 5–20 minutes per index).
- **When finished, download links for your results will be emailed to you.**

---

> **Note:**  
> All results are temporary and will be **deleted after 7 days**.  
> Please download your files promptly from the emailed links.
