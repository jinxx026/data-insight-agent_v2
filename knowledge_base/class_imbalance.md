# Class Imbalance

Class imbalance occurs when one target class is much more common than another. For example, a churn dataset may contain 90% non-churn customers and 10% churn customers.

Imbalance can make accuracy misleading. A model that always predicts the majority class may achieve high accuracy while failing to identify the minority class.

For imbalanced classification, analysts should evaluate metrics such as precision, recall, F1-score, ROC-AUC, and PR-AUC. PR-AUC is especially useful when the positive class is rare.

Common techniques include stratified train-test splits, class weights, threshold tuning, oversampling, undersampling, and collecting more minority-class examples.

The right metric depends on business cost. In fraud detection, missing fraud may be more costly than reviewing false positives. In marketing, too many false positives may waste campaign budget.
