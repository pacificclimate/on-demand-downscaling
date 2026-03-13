In this step, you will specify the region of interest, input data, type of downscaling performed, emissions scenario, and period for downscaling.
## What to do

1. **Choose a map location**  
   Click on the interactive map to select the center point for your study region. You may have to click and drag the map to expose the part of Canada you’re interested in.

   > - The **blue box** shows the medium-resolution input area region (1° x 1°).
   > - The **red box** shows the high-resolution output area (0.5° x 0.5°).

   The ‘Shift center’ feature allows you to move the boxes by 0.5° in latitude or longitude. This can be helpful for constructing a larger mosaic from individual downscaled maps.


2. **Set parameters using the controls**

   - **Region name**: Assign a name to your region (for file naming/tracking).
   - **Climate variables**: Choose the desired variable(s): daily total precipitation, daily mean, maximum or minimum temperature. To choose more than one variable, hold the Shift key while clicking the button.
   - **Dataset**: Select the input dataset (PCIC-Blend or CanDCS). 
     - If you select CanDCS, you’ll need to specify the:
       - Downscaling technique (Univariate or Multivariate)
       - Global climate model
       - CanESM5 run (if this model selected; 10 runs available)
       - Emissions scenario
       - Time period to downscale

3. **Continue**  
   Once all inputs are specified, click **Continue** to proceed.

---

## How it works

- This step uses PCIC’s [Chickadee](https://github.com/pacificclimate/chickadee) service (built on [ClimDown](https://github.com/pacificclimate/climdown)) to downscale medium-resolution climate data to a high-resolution grid.
- See PCIC’s [Daily Gridded Meteorological Datasets](https://www.uvic.ca/pcic/data-analysis-tools/data-portal/daily-gridded-meteorology/index.php) and [Statistically Downscaled Climate Scenarios](https://www.uvic.ca/pcic/data-analysis-tools/data-portal/statistically-downscaled-scenarios/index.php) pages for more information on the data inputs.
- See PCIC’s Monthly Climatologies page for more information on the high-resolution target grid.
- Chickadee implements the Climate Imprint method, described further in the paper of Sobie and Murdock (J. Appl. Meteorol. & Clim., 2017, https://doi.org/10.1175/JAMC-D-16-0287.1).
- The larger blue (input) region ensures your high-resolution target region is fully covered.

---

> **Note:** All output files are temporary and will be **deleted after 7 days**.  
> Please download your files promptly from the emailed links.
