# Correlation Analysis

Correlation analysis measures how numerical variables move together. A high positive correlation means two variables tend to increase together. A high negative correlation means one variable tends to increase when the other decreases.

Correlation is useful for exploratory analysis, feature redundancy checks, and hypothesis generation. For example, tenure and total charges may be strongly correlated because long-term customers accumulate more total charges.

Correlation does not prove causation. Two features can be correlated because of a hidden third factor, time effects, leakage, or business rules.

Correlation heatmaps are useful when there are multiple numerical features. They provide a quick way to find strongly related variables.

Before modeling, highly correlated features may cause redundancy or instability in some models. However, tree-based models are often less sensitive to correlated features than linear models.
