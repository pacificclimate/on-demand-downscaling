# On-Demand Downscaling Notebook

For best readability, this file should be opened in "Preview" mode: right click on README.md in the sidebar at left, then select <b>Open With&rarr;Markdown Preview<\b>.

This folder contains a Jupyter notebook called `on_demand_downscaling.ipynb`, which facilitates the workflow for this demonstration project. The objective is to statistically downscale an input variable on a medium resolution grid (\~10 km) to a high-resolution (\~800 m) target grid in a small subregion of BC, and also permit the computation of climate indices from that high-resolution data.

To run a cell in the notebook, click on it, then either press <b>Shift+Enter</b> or click on <b>Run&rarr;Run Selected</b> at the top left menu of the page.

To restart the notebook, click on <b>Kernel&rarr;Restart Kernel</b> at the top left menu of the page.

The workflow takes advantage of applications used in the DACCS project called "birds", which convert packages into web services. The notebook is split into two major sections.

### _Please note that all output files will be removed from PCIC servers after a period of two days. We encourage you to download any data you may need within this timeframe._

## 1. Downscaling Input Data

In the first step, a 3x3 degree subarea of an input dataset at \~10 km resolution (a previously downscaled GCM or gridded observations) is downscaled to an embedded 2.5x2.5 degree area at \~800 m resolution (the larger input domain ensures that the output grid is entirely contained within the input grid). This is achieved by applying a method called Climate Imprint (Hunter and Meentemeyer, 2005; Sobie and Murdock, 2017), to interpolate the coarser daily inputs to the finer resolution of a high-quality monthly climatology\---we use the BC PRISM 1981-2010 dataset for this purpose. The method is implemented in PCIC's [chickadee](https://github.com/pacificclimate/chickadee) service, based on the [ClimDown](https://github.com/pacificclimate/climdown) package.

In order to easily provide inputs to the service, the notebook contains an interactive map with various widgets. The inputs are as follows:

- The <b>center point</b> of the 3x3 degree subarea
- A user-specified <b>region name</b> for the chosen subarea
- The <b>climate variable</b> to be downscaled
- The <b>dataset</b> to use as the input. Currently, one can choose either the PNWNAmet observations or the CMIP6 downscaled and bias-corrected data. If the CMIP6 data are chosen, one must further specify:
  - The <b>downscaling technique</b> used to produce the input (either BCCAQv2 or MBCn)
  - The <b>climate model</b> (one run per model, except CanESM5)
  - The <b>CanESM5 run</b> (if CanESM5 selected)
  - The <b>future emissions scenario</b>
  - The <b>period</b> for which the downscaling is to be conducted (must include 1981-2010)

After specifying these options, click on the `Run Downscaling` button to begin processing.
A progress bar will appear below the map with an estimated (approximate!) time to completion.
The status of the process can be checked by running the cell below the map. When complete,
running this cell produces a link from which the output file (in NetCDF format) can be downloaded.
Since these data are at daily resolution, the download can take some time.<br>
_Note:_ After submitting one process, you can adjust inputs and click on the button again to start
additional processes. _However, this will slow the progress of each job, so should be used with this
in mind._

## 2. Computing Climate Indices

After obtaining high-resolution daily data in Step 1, you can compute climate indices from the results. These indices are computed using Ouranos's [finch](https://github.com/bird-house/finch/tree/master) service, which is based on their [xclim](https://github.com/Ouranosinc/xclim/tree/main) package. From the output files in Step 1, you can filter which ones are used for the index calculations. Which indices can be calculated depends on the input variable: the tool automatically shows which indices are enabled. Currently, a subset of the [core climdex indices](https://climate-scenarios.canada.ca/?page=climdex-indices) and degree days can be calculated, with more to be added in the future. For some indices, a threshold value and time chunking (annual/seasonal/monthly) can be specified. The table below summarizes the available indices:

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

After specifying which indices to compute, click on the `Calculate Indices` button to start the processes. As in Step 1, progress bars appear below the list: however, completion time estimates are not available for all indices at this time\---please be patient. From initial testing on the PNWNAmet data, we found that the `Hottest Day` and `Coldest Night` indices take ~45 minutes, `Days with Precip over Threshold of N-mm` takes ~50 minutes, and `Growing Season Length` takes ~30 minutes (minimum estimates, for a single user). As in Step 1, you can check the process status and download the output files when complete.

Note that indices requiring multiple variables can only be computed if the metadata (i.e. region name, dataset, and CMIP6 parameters, if applicable) for your selected downscaled output files are identical. For example, to compute `Daily Temperature Range`, the `tasmin` and `tasmax` files must have the same region name, dataset, and CMIP6 parameters (if applicable).

## Additional Information

#### `ERROR` Messages Below Progress Bars

Sometimes when a downscaling or index computation process is running, you might see a message that says `ERROR:root:Could not read status document.` or `ERROR:root:Could not parse XML response.`. In our testing, the processes have always successfully completed even with these messages, so they can be safely ignored.

#### `tasmean` Calculations

Since daily `tasmean` data is not an available input, if selected in Step 1 it must first be calculated from `tasmax` and `tasmin`, after which it is downscaled to high-resolution as normal. This adds a few minutes to the computation time and while it is happening you cannot run other cells.

#### Period selection

Although not obvious to users, this choice is closely tied to a dataset used in the climate imprint downscaling—i.e. the PRISM climatologies (1981-2010) found on PCIC's data portal. Since these are used in the initial daily downscaling for all variables, the selected period must include 1981-2010. While the interface could be modified to select a shorter period, e.g. 2041-2070, the calculations would still have to be performed from 1981-forward (or 2010 backward).

#### Preserving Outputs

The downscaled daily outputs from Step 1 are quite large: (~9 GB for PNWNAmet, ~7.5 GB for CMIP6 (1950-2010) and ~15 GB for CMIP6 (1981-2100). For this reason, we will not be retaining them on our server for long. _To reserve for later use, you should download them using the URLs provided. Moreover, if you will not be proceeding directly to the index calculations (Step 2), then you should make a record of the URLs from Step 1 if you would like to access them later. In general, the output URLs are not saved upon restarting the notebook or reconnecting to the tool._

#### Calculating Indices from Downscaled Outputs from Previous Sessions

If you have saved the URL of a downscaled output that was created during a previous session, you can paste it into the cell marked `add_previous_downscaled_outputs` in Step 2.VI. This will add it to the list of output files that can be used for computing indices. However, since we're not currently storing these outputs for very long, in some cases it may no longer be available. In that case, you will have to recompute it in Step 1 and save the new URL.

#### `helpers.py` Module

The notebook makes use of several helper functions and objects from the `helpers.py` Python module. While it's not needed to understand how to use the notebook, interested users can check it out for details on how the notebook is set up.

#### Feedback

We would appreciate any feedback on the tool, especially with regard to errors encountered, timing/performance, ease of use (although the tool is not targeted to beginners), etc. This can be sent to Charles Curry (RCI Lead) at pcic.support@uvic.ca. Thanks for being a test user for this tool!

#### No warranty

This beta tool is provided by the Pacific Climate Impacts Consortium with an open license on an “AS IS” basis without any warranty or representation, express or implied, as to its accuracy or completeness. For now, it is a beta product undergoing user testing. Any reliance you place upon the information obtained is your sole responsibility and strictly at your own risk. In no event will the Pacific Climate Impacts Consortium be liable for any loss or damage whatsoever, including without limitation, indirect or consequential loss or damage, arising from reliance upon the data derived from the tool.
