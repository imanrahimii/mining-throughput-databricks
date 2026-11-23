# Azure Databricks mining throughput mini project

Prepared for Iman Rahimi | Personal practice | Instructions checked 22 November 2026

## What you are building

A mining planner wants to estimate tonnes processed during an upcoming machine shift and compare historical equipment performance. You will upload synthetic shift data, remove exact duplicates, quarantine invalid rows, store cleaned Delta tables, calculate energy intensity, and train a small Random Forest against a simple baseline. You then score ten planned shifts.

Allow 60–90 minutes after the workspace and compute are ready. You can stop after notebook 02 for the shorter data-engineering project. New workspace provisioning and permission fixes are additional time. Everything runs in Azure Databricks notebooks; VS Code, Azure ML, ADF and Azure SQL are not required.

The project deliberately uses only 610 input rows. Pandas does the small validation and modelling work, while Spark reads the original file, persists Delta tables and produces a daily SQL report. Shared Python functions perform the small-data validation, machine summary and modelling. This is platform practice, not a big-data benchmark. The model learns an artificial relationship in synthetic data and is not a production forecasting system.

## 1 Create your workspace

1. Sign in at https://portal.azure.com using the account and directory that own your Azure subscription.
2. Search Azure Databricks → Create, or Create a resource → Analytics → Azure Databricks.
3. Select a subscription you are permitted to use. Create a dedicated resource group named rg-iman-databricks-practice. Do not put this exercise in the resource group containing your teaching SQL databases.
4. Workspace name: adb-iman-mining-practice. Select an available region, preferably Australia East if offered with the needed features.
5. If Workspace type is offered, select Serverless for the simplest path, provided it is available to your subscription and region. The documented serverless workspace creation path is currently Public Preview. A Hybrid workspace can also use serverless notebook compute when enabled. Select a Unity Catalog-capable plan, such as Premium, where a plan is required. Review the actual pricing displayed before creating resources; this guide does not promise free compute.
6. Review + create → review subscription, region and configuration → Create. Wait for deployment success; it can take longer than a few minutes. Open the resource → Launch Workspace, or open it from the Databricks account Workspaces page.
7. In the Databricks sidebar find Workspace, Catalog and Compute. Catalog is where governed tables and volumes live; Workspace is where notebooks live. These are different locations.

If your Azure for Students or other subscription rejects creation, investigate the exact subscription/policy/quota error. Do not remove a spending limit or switch to pay-as-you-go just to bypass an error without reviewing the charges. A subscription can allow Azure SQL and still restrict Databricks. If Unity Catalog is missing, stop and ask the account administrator to enable/assign it; the core project depends on it.

## 2 Choose notebook compute

Preferred route: import a notebook in the next section, then select Serverless from its compute selector if available. In the Environment side pane choose an ML base environment if offered; otherwise use Standard and add only missing Python packages. Apply the environment before running cells. No GPU is needed.

Alternative when serverless is unavailable: Compute → Create compute. Use a permitted personal/single-node policy, one small supported CPU node, a currently supported LTS runtime with Unity Catalog support, and an auto-termination interval of 10–15 minutes if the policy permits. Runtime ML is convenient if available under your policy. Attach the same compute to all four notebooks. Do not create a multi-node cluster for 610 rows. Available policies and VM types vary; quota or access errors require an appropriate permitted configuration, not repeated retries.

Compute costs money while work is running. Auto-termination helps with idle classic compute; it is not an overall spending cap. Check subscription Cost Management and create a budget alert if appropriate. Alerts do not automatically stop spending.

## 3 Import the project notebooks

1. Download the ZIP and extract it on your computer.
2. In Databricks choose Workspace → your personal user folder. Create a folder MiningThroughputPractice using the folder menu.
3. Right-click that folder, or use its three-dot menu → Import → File. Import notebooks/00_setup.ipynb. Repeat for 01_clean_and_delta.ipynb, 02_report.ipynb and 03_model_and_score.ipynb. Import the individual notebooks, not the whole project ZIP.
4. Open 00_setup and attach your chosen compute. Run one cell at a time with the cell run button or Shift+Enter. Read the Markdown instructions between code cells. Do not Run all before the upload checkpoint.
5. The first code cell detects the current catalog and sets SCHEMA = iman_mining_lab. A catalog is a top-level Unity Catalog container; a schema is a group of objects inside it. This schema is unrelated to your Azure SQL databases week10/week11.
6. If the detected catalog is hive_metastore, system, unavailable or not writable, use Catalog to find a writable Unity Catalog catalog. Change CATALOG to that quoted name in the first code cell of ALL FOUR notebooks. Keep the same SCHEMA and VOLUME values everywhere. Do not type placeholder names literally.
7. Run the create-schema/create-volume cell. It prints the exact /Volumes/catalog/iman_mining_lab/project_files path. If CREATE SCHEMA fails, you need USE CATALOG and CREATE SCHEMA on a suitable catalog, or an administrator-created personal schema. Inside the schema you need USE SCHEMA, CREATE TABLE and CREATE VOLUME; file access requires READ VOLUME and WRITE VOLUME. Use only a personal lab schema you control.

## 4 Upload the two datasets

Open Catalog → the actual catalog printed in notebook 00 → iman_mining_lab → Volumes → project_files. Select Upload and choose data/mining_shifts_raw.csv and data/next_shifts.csv from the extracted package. Upload directly into project_files, without a nested data directory. If the interface has a Files tab, open that tab to find Upload.

Return to 00_setup and run the file-list/check cell. It must find both filenames. A table is not created simply by uploading a file. A volume stores files; later notebooks turn these data into managed Delta tables.

Run the package-version cell. pandas, numpy, scikit-learn and matplotlib are used; MLflow is optional. Most appropriate runtimes already provide these. Do not reinstall everything by default. requirements.txt lists dependency ranges, not an exact lock. Do not install pyspark or delta-spark over Databricks Runtime.

Serverless: if a package is missing, add its requirement line in the notebook Environment → Dependencies → Apply, then rerun the notebook from the top because Python may restart. Configure dependencies separately for each notebook that needs them. Classic compute: if necessary add a first cell such as %pip install "scikit-learn>=1.3,<2", then a separate cell dbutils.library.restartPython(), then rerun from the top. Avoid changing runtime-provided packages unless required. For reproducibility keep the printed environment versions with your results.

## 5 Run cleaning and Delta storage

Open 01_clean_and_delta. Check the catalog/schema configuration again. Run its cells in order.

The notebook strips surrounding whitespace, removes exact duplicate rows, converts numbers and dates, validates ranges, and keeps rejected records separately. Different values for the same shift_id cause a stop so you do not silently retain an arbitrary conflicting record. The input is retained as an all-text Bronze table. Valid rows become the typed Silver table. Rejected rows preserve source values with a general rejection reason.

Expected counts: raw 610 = 4 duplicate copies removed + 6 rejected + 600 accepted. The six invalid examples include negative planned hours, a nonnumeric hardness, a missing target, a malformed date, availability above one and negative energy.

Go to Catalog → your schema → Tables. Find bronze_shifts (610), rejected_shifts (6) and silver_shifts (600). Open a table and use its sample-data view if available. The notebook also displays rejects and asserts the clean count.

The writes overwrite these named project tables to make a practice rerun repeatable. Confirm that you are using your own iman_mining_lab schema. Raw data files in the volume are not overwritten. Bronze preserves original values but is a replaceable practice snapshot, not a production append-only history.

## 6 Produce a machine report

Run 02_report. The shared reporting function groups 600 valid shifts into 20 machine summaries, which Spark saves as Delta. Spark SQL produces the daily view. For each machine, report shifts, total tonnes, total kWh and energy intensity. The notebook saves gold_machine_summary and displays two bar charts plus a daily throughput table.

Energy intensity = SUM(energy_kwh) / SUM(actual_tonnes). Lower means less energy per tonne in these observations. A machine can have high throughput without the lowest energy intensity. Do not average per-shift ratios without considering their different tonne weights.

You can query the output in a Python notebook cell using the exact printed catalog. Example: spark.sql(f"SELECT * FROM {table('gold_machine_summary')} ORDER BY total_tonnes DESC").show(). The table helper is defined by the first configuration cell. This avoids querying a table in the wrong catalog/schema.

Checkpoint: 20 report rows and 30 shifts per machine. Compare your numbers with solutions/expected_machine_report.csv only after trying the task.

## 7 Train and evaluate a small model

Run 03_model_and_score after completing notebook 01. It reads the Silver Delta table and brings only the 600 rows into Pandas for scikit-learn.

Inputs assumed available before each shift: planned_hours, ore_hardness, feed_grade_pct, ambient_temp_c and prior_shift_availability. Target: actual_tonnes. The simulator assumes these inputs are known; in real work you must verify their timestamp and measurement availability. In particular a measured shift temperature would need to be replaced by a pre-shift forecast for a genuine forecast.

Training: September 1–20, 400 rows. Test: September 21–30, 200 rows. The same simulated machines appear across both periods, so this tests later shifts of known machines, not generalisation to unseen equipment. The mean predictor is your baseline. Random Forest is the candidate. No hyperparameter tuning uses the test data.

Read the baseline MAE, model MAE and R². MAE is average absolute error in tonnes. Locally, the supplied data produced about 145 tonnes baseline MAE and 35 tonnes model MAE; exact metrics can vary with library versions. This high synthetic score is not evidence of industrial forecast accuracy. Inspect the actual-versus-predicted plot and feature importance; importance is not causation.

The notebook then scores next_shifts.csv and saves predicted_shifts with ten rows. These are estimates without observed future outcomes, so you cannot compute their actual error yet. To try optional MLflow tracking, set RUN_MLFLOW = True and run the final cell. Find the experiment in your personal Workspace folder mining_throughput_practice, or in Experiments if shown. It logs parameters and metrics only; no model is registered, served or deployed.

## 8 Finish with evidence and shutdown

Save the cleaning counts, one machine chart, model/baseline metrics and ten predictions. Complete reflection.md: what did each stage do, why keep rejects, why hold out later dates, and what additional evidence would be needed before real use?

Classic compute: open Compute → your cluster → Terminate and confirm it is terminated. Serverless: cancel any active commands or jobs and disconnect the notebook when done; inspect active runs and usage. There is no classic cluster to terminate for serverless. Do not assume merely closing a browser cancels active work. This project creates no schedules, serving endpoints or SQL warehouses.

Your tables and uploaded files remain in managed cloud storage and can continue to incur storage charges. If this was a disposable environment, first export/download anything you need, then review its resources and delete only the dedicated practice resource group when you are finished. Never delete shared or teaching resource groups. No deletion command is included in the notebooks.

## Troubleshooting

No Catalog or hive_metastore only: choose a Unity Catalog-enabled workspace/catalog; do not change volume paths to legacy DBFS root as a workaround.
Permission denied creating schema or volume: use an assigned writable catalog/schema or ask the administrator for scoped permissions.
File not found: copy the volume path printed by 00_setup and check the two CSVs are at its root. Browser Workspace uploads and Catalog volume uploads are different destinations.
Table not found: run 01 first and ensure all four configuration cells use the same catalog/schema.
An assertion reports unexpected data counts: confirm you uploaded the original raw file, not reference_clean.csv or a spreadsheet-edited copy; inspect the reject/duplicate counts.
Missing Python module: use the package/environment steps above. Do not install PySpark over the runtime.
Compute cannot start: read the policy, region and quota error; try a permitted small CPU compute or eligible serverless option. Do not create multiple clusters.
MLflow experiment error: leave RUN_MLFLOW=False; complete reporting/scoring first and resolve personal experiment permissions later.

Validation boundary: the dataset arithmetic, cleaning logic, date split, notebook Python syntax and scikit-learn fitting were tested locally. Azure deployment, Spark/Delta execution, Unity Catalog permissions and MLflow writes require your live workspace and have not been executed on your account.

## Exercises for a second session

1. Before viewing the solutions, identify all six reject reasons by inspecting their source values. Improve the code to store a specific rule name for each rejection.
2. Change max_depth from 8 to 4. Use a validation period within the first 20 days to choose parameters; reserve the final 10 days for a single final evaluation.
3. Add residual summaries by machine and date. Are errors evenly distributed?
4. Add a new rejected example with conflicting shift_id values. Confirm the conflict assertion stops the run.
5. Explain how you would replace the simulator with timestamped operational data. Identify target availability, weather forecasts, sensor faults, downtime labels and delayed outcomes. This is design work, not a claim the toy model is deployment-ready.

## Official references

- [Workspace creation](https://learn.microsoft.com/en-us/azure/databricks/admin/workspace/create-workspace)
- [Compute settings](https://learn.microsoft.com/en-us/azure/databricks/compute/configure)
- [Notebook import](https://learn.microsoft.com/en-us/azure/databricks/notebooks/notebook-export-import)
- [Create a volume](https://learn.microsoft.com/en-us/azure/databricks/volumes/utility-commands)
- [Upload volume files](https://learn.microsoft.com/en-us/azure/databricks/volumes/volume-files)
- [Serverless dependencies](https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/dependencies)
- [MLflow tracking](https://learn.microsoft.com/en-us/azure/databricks/mlflow/tracking)

## Continuous integration revision

Read CI_GUIDE.html for GitHub setup, the deliberate-failure exercise and the exact test scope. Import notebooks/mining_core.py beside the notebooks in your Databricks Workspace. CI tests the same shared functions used by the notebooks. No CD is included.
