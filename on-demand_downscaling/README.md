# On-Demand Downscaling Notebook

This folder contains a Jupyter notebook called `on_demand_downscaling.ipynb`, which facilitates the workflow for the on-demand downscaling project. The objective is to downscale GCM data from a low-resolution (\~10 km) grid to a high-resolution (\~800 m) target grid in a small subregion of BC, and compute climate indices from that high-resolution data.

To run a cell in the notebook, click on it, then either press <b>Shift+Enter</b> or click on <b>Run&rarr;Run Selected</b> at the top left menu of the page.

To restart the notebook, click on <b>Kernel&rarr;Restart Kernel</b> at the top left menu of the page.

The workflow takes advantage of applications used in the DACCS project called "birds", which convert packages into web services. The notebook is split into two major sections.

## 1. Downscaling GCM Data

This step consists of downscaling a 3x3 degree low-resolution subset of a GCM dataset to a 2.5x2.5 degree high-resolution subset (the larger input subdomain ensures that the target grid is entirely contained within the input grid). It achieves this by using PCIC's [chickadee](https://github.com/pacificclimate/chickadee) service, which is based on the [ClimDown](https://github.com/pacificclimate/climdown) package, to run a process called [Climate Imprint](https://github.com/pacificclimate/ClimDown/blob/master/R/CI.R). The target grid used here is the one for the 1981-2010 BC PRISM climatologies.

In order to easily provide inputs to the service, the notebook contains an interactive map with various widgets. The inputs are as follows:
- The <b>center point</b> of the subdomains of the GCM/target regions
- The <b>region name</b> describing the chosen subregions
- The <b>climate variable</b> from the GCM input to downscale
- The <b>dataset</b> to use as the GCM input. Currently, you can choose between the daily PNWNAmet observations or the CMIP6 data. If you choose the CMIP6 data, you can further specify the following:
   - The <b>downscaling technique</b> originally used to downscale (either BCCAQv2 or MBCn)
   - The <b>climate model</b>
   - The <b>CanESM5 run</b> if CanESM5 is the selected model
   - The <b>emissions scenario</b>
   - The <b>downscaled period</b> dictating the time range to downscale the input data

After you specify your inputs, you can click on the `Run Downscaling` button to begin said process. You can even adjust your inputs and click on the button again to start multiple processes. These processes can be tracked with progress bars that appear below the map with approximate times to completion. Once your processes are completed, you can then check that they have finished without problems and download them if you wish.

## 2. Computing Climate Indices

After obtaining high-resolution data in step 1, you can compute climate indices from the results. These indices are computed using Ouranos's [finch](https://github.com/bird-house/finch/tree/master) service, which is based on their [xclim](https://github.com/Ouranosinc/xclim/tree/main) package. From the output files in step 1, you can filter which ones are used for obtaining indices, and the ones corresponding to the relevant climate variables will be enabled. Currently, a subset of the [core climdex indices](https://climate-scenarios.canada.ca/?page=climdex-indices) and degree days can be calculated with more to be available in the future. In appropriate cases, you can specify the threshold value and time resolution. The table below summarizes the available indices (refer to the climdex indices page for more details):

| Variable | Climdex Index Name | Index Name in Notebook | Threshold Value | Finch Process | 
| -------- | ------------------ | ---------------------- | ------------- | ------------- |
| pr | Rxnday | Max N-day Precip Amount | 1 day | max_n_day_precipitation_amount |
| | Simple Precipitation Intensity Index | Simple Precip Intensity Index | 1 mm/day | sdii |
| | Rnnmm | Days with Precip over Threshold of N-mm | 1 mm/day | wetdays |
| | Maximum Length of Dry Spell | Maximum Length of Dry Spell | 1 mm/day | cdd |
| | Maximum Length of Wet Spell | Maximum Length of Wet Spell | 1 mm/day | cwd |
| | PRCPTOT | Total Wet-Day Precip | 1 mm/day | wet_prcptot |
| tasmax | Summer Days | Summer Days | 25 degC | tx_days_above |
| | Ice Days | Ice Days | 0 degC | ice_days |
| | TXx | Hottest Day | NA | tx_max |
| | TXn | Coldest Day | NA | tx_min |
| tasmin | Frost Days | Frost Days | 0 degC | frost_days |
| | Tropical Nights | Tropical Nights | 20 degC | tropical_nights |
| | TNx | Hottest Night | NA | tn_max |
| | TNn | Coldest Night | NA | tn_min |
| tasmean | Growing Season Length | Growing Season Length | 5 degC | growing_season_length |
| | Cooling Degree Days | Cooling Degree Days | 18 degC | cooling_degree_days |
| | Freezing Degree Days | Freezing Degree Days | 0 degC | freezing_degree_days |
| | Growing Degree Days | Growing Degree Days | 5 degC | growing_degree_days |
| | Heating Degree Days | Heating Degree Days | 18 degC | heating_degree_days |
| tasmin+tasmax | Daily Temperature Range | Daily Temperature Range | NA | dtr |
| | Freeze-Thaw Days | Freeze-Thaw Days | 0 degC | freezethaw_spell_frequency |
| pr+tasmax | Precipitation as Snow | Precip as Snow | 0 degC | prsn |

After you specify which indices you want to compute, you can click on the `Calculate Indices` button to begin those processes. As for step 1, you can track them with progress bars that appear below the list, though approximate completion times are not available for all indices as they have not been tested extensively. From initial testing on the PNWNAmet data, we have found that the `Hottest Day` and `Coldest Night` indices take ~45 minutes, `Days with Precip over Threshold of N-mm` takes ~50 minutes, and `Growing Season Length` takes ~30 minutes. Also, as for step 1, you can check that the processes have completed successfully and download the output files.

Please note that for indices requiring multiple variables, you can only compute these if the metadata (e.g. region name, dataset group, CMIP6 parameters if applicable) for your selected downscaled output files are identical. For example, if you wish to compute `Precip as Snow`, then your `pr` and `tasmax` files must have the same region name, dataset group, and CMIP6 parameters if applicable.

## Additional Information

#### `CMIP6` Future Periods
Climate Imprint requires a baseline calibration period, which is 1981-2010 from the PRISM climatologies in this case. This calibration period must overlap with the time range of the GCM input. As such, when you select a future CMIP6 period (i.e. 2011-2040, 2041-2070, or 2071-2100), the tool will concatenate the CMIP6 data for the baseline period with the data for the future period, save that concatenated data to a temporary file, and then that temporary file will be passed to `chickadee`. The resulting output is thus high-resolution data for the baseline period and the future period. While that temporary file is being created, you cannot run other cells, so it would be best to start these processes after the ones for the 1950-2010 period and for PNWNAmet.

#### `tasmean` Calculations
Since daily `tasmean` data is unavailable by default, it is first calculated in step 1 by obtaining `tasmax` and `tasmin` subsets from the specified inputs, then passing them to `finch` to calculate low-resolution `tasmean` data. Afterwards, it is passed to `chickadee` to calculate high-resolution data as normal. The initial low-resolution `tasmean` calculation takes ~2 minutes for the PNWNAmet data, and while it is happening, you cannot run other cells, so it would be best to start these processes after the ones for other variables.

#### Preserving Outputs
The downscaled outputs from step 1 are quite large (~7.5 GB for CMIP6 and ~9 GB for PNWNAmet). Until we determine a location where we can store many of these outputs, we would prefer to not keep them around for long. As such, if you would like to preserve these outputs for later use, it is recommended that you download them using the URLs. Also note that restarting the notebook will not save the output URLs, so make a copy of their locations if you would like to access them later.

#### Calculating Indices from Downscaled Outputs from Previous Sessions
If you have saved the URL of a downscaled output that was created during a previous session, you can use this URL in the cell marked `add_previous_downscaled_output` in step VI. This will add it to the list of output files that can be used for computing indices. However, since we're currently storing these outputs in the short term, it is possible that it has been removed from our storage. In this case, you will have to recompute it in step 1 and save the new URL.

#### `helpers.py` Module
The notebook makes use of several helper functions and objects from the `helpers.py` module. While you do not need to look at it to understand how to use the notebook, interested readers and those with previous Python experience can do so to see the finer details on how the notebook is set up.