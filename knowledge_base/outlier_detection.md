# Outlier Detection

Outlier detection finds values that are unusually far from the main distribution. Outliers can represent valid rare behavior, data entry errors, fraud, system bugs, or exceptional business events.

The IQR method is a common rule-based approach. It computes the first quartile Q1, third quartile Q3, and interquartile range IQR = Q3 - Q1. Values below Q1 - 1.5 * IQR or above Q3 + 1.5 * IQR are flagged as potential outliers.

IQR is useful for exploratory data analysis because it is based on percentiles and is less sensitive to extreme values than mean and standard deviation.

Outliers should not be automatically deleted. Analysts should inspect whether they are valid extreme values, measurement errors, or values requiring transformation. Possible treatments include capping, winsorization, log transformation, segmentation, or leaving them unchanged.

In business datasets, outliers can be important signals. For example, unusually high transaction amounts may indicate VIP customers or fraud risk.
