# Feature Types

Field type detection maps raw dataframe columns to analysis roles. Pandas dtypes such as `int64`, `float64`, and `object` are not enough because they do not describe business meaning.

An ID field usually has a name such as `customer_id`, `order_id`, `uuid`, or `key`, or has a very high unique value ratio. ID fields are useful for joins and traceability, but they should usually be excluded from feature statistics, correlation analysis, and modeling.

A numerical feature is a quantitative variable with enough distinct values to analyze distributions, ranges, outliers, and correlations. Examples include age, price, tenure, revenue, and monthly charges.

A categorical feature represents groups or labels. It can be stored as strings or as low-cardinality numbers. Examples include gender, region, contract type, payment method, and product category.

A datetime feature stores dates or timestamps. It supports trend analysis, seasonality checks, cohort analysis, and time-window filtering.

A text feature contains longer free-form strings such as support notes, reviews, descriptions, and comments. Text fields usually need text-specific processing such as length analysis, keyword extraction, embeddings, or sentiment analysis.

A target variable is the outcome label for modeling or business comparison. Names such as `churn`, `fraud`, `label`, `target`, `default`, or `converted` often indicate target variables. Target variables should be checked for class balance before modeling.
