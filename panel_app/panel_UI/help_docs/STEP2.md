In this step, you will configure the downscaling of climate model data to high-resolution grids for your selected region.

## What to do

1. **Choose a map location**  
   Click on the interactive map to select the center point for your study region.

   > - The **blue box** shows the medium-resolution input area region (1° x 1°).
   > - The **red box** shows the high-resolution output area (0.5° x 0.5°).

2. **Set parameters using the controls**

   - **Region name**: Assign a name to your region (for file naming/tracking).
   - **Climate variables**: Choose one or more variables (precipitation, temperature max/min/mean).
   - **Dataset**: Select the input dataset (PCIC-Blend or CanDCS). 
     - If you select CanDCS, you’ll need to specify the:
       - Downscaling technique (Univariate or Multivariate)
       - Climate model
       - CanESM5 run (if relevant)
       - Emissions scenario
       - Time period to downscale

3. **Continue**  
   Once all inputs are specified, click **Continue** to proceed.

---

## How it works

- This step uses PCIC’s [Chickadee](https://github.com/pacificclimate/chickadee) service (built on [ClimDown](https://github.com/pacificclimate/climdown)) to downscale medium-resolution climate data to a high-resolution PRISM-adjusted grid.
- The larger blue (input) region ensures your high-resolution target region is fully covered.

---

> **Note:** All output files are temporary and will be **deleted after 7 days**.  
> Please download your files promptly from the emailed links.
