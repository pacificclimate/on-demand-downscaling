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
- Indices requiring multiple variables (e.g. “Daily Temperature Range”) can only be computed if you selected all required variables with identical region and dataset parameters.

### The table below summarizes the available indices (refer to the climdex indices page for more details):

| Variable      | Climdex Index Name                   | Index Name in Notebook                  | Threshold Value | Finch Process                  |
| ------------- | ------------------------------------ | --------------------------------------- | --------------- | ------------------------------ |
| pr            | Rxnday                               | Max N-day Precip Amount                 | 1 day           | max_n_day_precipitation_amount |
|               | Simple Precipitation Intensity Index | Simple Precip Intensity Index           | 1 mm/day        | sdii                           |
|               | Rnnmm                                | Days with Precip over Threshold of N-mm | 1 mm/day        | wetdays                        |
|               | Maximum Length of Dry Spell          | Maximum Length of Dry Spell             | 1 mm/day        | cdd                            |
|               | Maximum Length of Wet Spell          | Maximum Length of Wet Spell             | 1 mm/day        | cwd                            |
|               | PRCPTOT                              | Total Wet-Day Precip                    | 1 mm/day        | wet_prcptot                    |
| tasmax        | Summer Days                          | Summer Days                             | 25 degC         | tx_days_above                  |
|               | Ice Days                             | Ice Days                                | 0 degC          | ice_days                       |
|               | TXx                                  | Hottest Day                             | NA              | tx_max                         |
|               | TXn                                  | Coldest Day                             | NA              | tx_min                         |
| tasmin        | Frost Days                           | Frost Days                              | 0 degC          | frost_days                     |
|               | Tropical Nights                      | Tropical Nights                         | 20 degC         | tropical_nights                |
|               | TNx                                  | Hottest Night                           | NA              | tn_max                         |
|               | TNn                                  | Coldest Night                           | NA              | tn_min                         |
| tasmean       | Growing Season Length                | Growing Season Length                   | 5 degC          | growing_season_length          |
|               | Cooling Degree Days                  | Cooling Degree Days                     | 18 degC         | cooling_degree_days            |
|               | Freezing Degree Days                 | Freezing Degree Days                    | 0 degC          | freezing_degree_days           |
|               | Growing Degree Days                  | Growing Degree Days                     | 5 degC          | growing_degree_days            |
|               | Heating Degree Days                  | Heating Degree Days                     | 18 degC         | heating_degree_days            |
| tasmin+tasmax | Daily Temperature Range              | Daily Temperature Range                 | NA              | dtr                            |
|               | Freeze-Thaw Days                     | Freeze-Thaw Days                        | 0 degC          | freezethaw_spell_frequency     |

### How long does it take?

- Processing time varies by index and region (typically 5–20 minutes per index).
- **When finished, download links for your results will be emailed to you.**

---

> **Note:**  
> All results are temporary and will be **deleted after 7 days**.  
> Please download your files promptly from the emailed links.
