# Missing Values

Missing value analysis identifies how much data is unavailable in each column. Missing values can distort summary statistics, charts, and machine learning features.

For numerical features, common strategies include median imputation, mean imputation, adding a missing indicator, or removing the column when missingness is too high. Median imputation is often more robust than mean imputation when the data is skewed.

For categorical features, common strategies include adding an `Unknown` category, using the mode, or filtering rows when missingness means invalid records.

For datetime fields, missing timestamps may indicate incomplete events, delayed tracking, or data collection failures. They should not be blindly filled before understanding the business process.

For target variables, missing labels are usually more serious because supervised modeling cannot train on rows without labels. Rows with missing labels are often excluded from training, but they may still be useful for prediction.

The decision to delete or fill missing values should depend on missing rate, feature type, business meaning, and whether missingness itself carries signal.
