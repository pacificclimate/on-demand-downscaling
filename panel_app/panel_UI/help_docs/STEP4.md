## 4. Computing Climate Indices

Now, choose which climate indices you want to calculate for your selected region and variables.

**How this works:**

- You have already chosen the climate variables to downscale and your study region.
- Now, select up to **8 climate indices** you would like to compute (The list will update automatically to match your chosen variables.).
- Once you continue, **both downscaling and index calculations will be run as a single process** for your selections.
  - If you change your selection to “High-resolution Outputs Only” in the previous step, this page will be skipped and only downscaling will run.

### About the indices

- These indices are computed using Ouranos's [finch](https://github.com/bird-house/finch/tree/master) service, which is based on their [xclim](https://github.com/Ouranosinc/xclim/tree/main) package.
- Currently, a subset of the [core climdex indices](https://climate-scenarios.canada.ca/?page=climdex-indices) and degree days can be calculated with more to be available in the future. In appropriate cases, you can specify the threshold value and time resolution.
- Indices requiring multiple variables (e.g. “Extreme Temperature Range”) can only be computed if you selected all required variables with identical region and dataset parameters.

### The table below summarizes the available indices (refer to the climdex indices page for more details):

| Variable              | Climdex Index Name / Description      | Index Name in Notebook                  | Threshold Value                                                | Finch Process                  |
| --------------------- | ------------------------------------- | --------------------------------------- | -------------------------------------------------------------- | ------------------------------ |
| tasmax (tx)           | TX Mean                               | Mean                                    | NA                                                             | tx_mean                        |
|                       | TXx                                   | Hottest Day                             | NA                                                             | tx_max                         |
|                       | TXn                                   | Coldest Day                             | NA                                                             | tx_min                         |
|                       | Ice Days                              | Ice Days                                | 0 degC                                                         | ice_days                       |
|                       | TX Above Threshold                    | Days Above a Specified TX               | 20 to 35 degC                                                  | tx_days_above                  |
| tasmin (tn)           | TN Mean                               | Mean                                    | NA                                                             | tn_mean                        |
|                       | TNx                                   | Hottest Night                           | NA                                                             | tn_max                         |
|                       | TNn                                   | Coldest Night                           | NA                                                             | tn_min                         |
|                       | Frost Days                            | Frost Days                              | 0 degC                                                         | frost_days                     |
|                       | TN Above Threshold                    | Days Above a Specified TN               | 10 to 30 degC                                                  | tn_days_above                  |
|                       | TN Below Threshold                    | Days Below a Specified TN               | -30 to 0 degC                                                  | tn_days_below                  |
| tasmean (tm)          | TM Mean                               | Mean                                    | NA                                                             | tg_mean                        |
|                       | Growing Season Length                 | Growing Season Length                   | 5 degC                                                         | growing_season_length          |
|                       | Growing Degree Days                   | Growing Degree Days                     | 18 degC                                                        | growing_degree_days            |
|                       | Freezing Degree Days                  | Freezing Degree Days                    | 0 degC                                                         | freezing_degree_days           |
|                       | Heating Degree Days                   | Heating Degree Days                     | 10 to 20 degC                                                  | heating_degree_days            |
|                       | Cooling Degree Days                   | Cooling Degree Days                     | 10 to 20 degC                                                  | cooling_degree_days            |
|                       | Cold Spell Days                       | Cold Spell Days                         | -20 to -10 degC + number of days                               | cold_spell_days                |
| pr                    | Rxnday                                | Max N-day Precip Amount                 | 1 to 10 days                                                   | max_n_day_precipitation_amount |
|                       | PRCPTOT                               | Total Precipitation                     | NA                                                             | prcptot                        |
|                       | SDII                                  | Average Wet-Day Precipitation (SDII)    | 1 mm/day                                                       | sdii                           |
|                       | Rnnmm                                 | Days with Precip over Threshold of N-mm | 1 to 30 mm/day                                                 | wetdays                        |
|                       | Days Over Precip Percentile Threshold | Days Over Precip Percentile Threshold   | percentile (0 to 99) + wetday threshold; percentile = 0 uses threshold-only mode | days_over_precip_thresh (percentile > 0), wetdays (percentile = 0) |
|                       | Maximum Length of Wet Spell           | Maximum Length of Wet Spell             | 1 to 30 mm/day                                                 | cwd                            |
|                       | Maximum Length of Dry Spell           | Maximum Length of Dry Spell             | 1 to 3 mm/day                                                  | cdd                            |
| tasmin+tasmax (tn+tx) | Extreme Temperature Range             | Extreme Temperature Range               | NA                                                             | etr                            |
|                       | Freeze-Thaw Days                      | Freeze-Thaw Days                        | NA                                                             | dlyfrzthw                      |
| pr+tasmean (pr+tm)    | Snowfall                              | Snowfall                                | Method: auer                                                   | prsn                           |
|                       | Rainfall                              | Rainfall                                | Method: auer                                                   | prlp                           |
| tasmax (tx)           | Heat Wave Days                        | Heat Wave Days                          | TX threshold + number of days                                  | heat_wave_index                |
| tasmin+tasmax (tn+tx) | Heat Wave Number                      | Heat Wave Number                        | TN/TX threshold + number of days                               | heat_wave_frequency            |
|                       | Heat Wave Maximum Length              | Heat Wave Maximum Length                | TN/TX threshold + number of days                               | heat_wave_max_length           |

### How long does it take?

- Processing time varies by index and region (typically 5–20 minutes per index).
- **When finished, download links for your results will be emailed to you.**

---

> **Note:**  
> All results are temporary and will be **deleted after 7 days**.  
> Please download your files promptly from the emailed links.
