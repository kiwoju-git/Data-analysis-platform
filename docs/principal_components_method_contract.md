# Principal Components Analysis method contract

Status: P0 implementation contract

Method ID: `eda.principal_components`

Method version: `0.1.0`

Result schema: `1`

## Statistical purpose

Principal Components Analysis (PCA) is an unsupervised exploratory method. It
uses no response variable. It finds orthogonal directions that successively
explain the largest available variance in a selected set of numeric variables.

PCA is distinct from Partial Least Squares Regression. PCA summarizes the
variance/correlation structure of `X` alone. PLS uses both predictors `X` and a
response `y` to construct components intended for prediction. PCA results must
not be described as supervised importance, causal effects, or a PLS model.

## Supported input

- 2-50 numeric variables;
- 3-20,000 usable rows;
- continuous or count measurement levels;
- no ID, datetime, text, or nominal-coded variables;
- complete-case missing policy across all selected variables;
- input order is preserved.

Missing rows are excluded from the multivariate matrix as a unit. No pairwise
matrix, imputation, or silent variable removal is used. A constant selected
variable raises `pca_constant_variable`.

## Matrix and scaling policy

`correlation` is the default:

1. calculate each sample mean and sample standard deviation with `ddof=1`;
2. center and divide each variable by that sample standard deviation;
3. calculate the sample correlation matrix with denominator `n - 1`.

`covariance`:

1. calculate each sample mean;
2. center each variable without scaling;
3. calculate the sample covariance matrix with denominator `n - 1`.

Minitab uses standardized data for correlation-matrix scores and centered raw
data for covariance-matrix scores. scikit-learn PCA centers but does not scale
features automatically, so this implementation performs correlation scaling
explicitly rather than relying on an implicit sklearn default.

Result provenance records matrix type, centered/standardized flags, `ddof=1`,
means, sample standard deviations, package versions, and input variable order.

## Calculation

1. build the complete-case matrix `X`;
2. transform it according to the matrix policy;
3. calculate the symmetric sample matrix `S = X'X / (n - 1)`;
4. use deterministic symmetric eigendecomposition;
5. sort eigenvalues and eigenvectors in descending eigenvalue order;
6. calculate scores `Z = XV`;
7. calculate explained proportion `lambda_j / sum(lambda)` and cumulative
   proportion;
8. calculate loadings as `V * sqrt(lambda)` and also retain eigenvectors;
9. calculate score-space distance using selected positive-variance components.

The maximum component count is `min(p, n - 1)`. Eigenvalues within a documented
floating tolerance below zero are clamped to zero. A materially negative value
raises `pca_eigendecomposition_failed`.

## Deterministic sign policy

Eigenvector signs are mathematically arbitrary. For each component, find the
loading with greatest absolute magnitude; ties use the first variable in input
order. Multiply the component by `-1` when that loading is negative. Apply the
same sign to eigenvectors, loadings, and all scores.

External reference tests compare eigenvalues and explained proportions directly
and compare eigenvector subspaces/sign-normalized vectors using this policy.
Repeated eigenvalues are documented as non-unique individual directions.

## Component selection

- `all`: calculate all available components and select all;
- `fixed`: select 1 through the validated maximum;
- `cumulative`: select the smallest number whose cumulative explained
  proportion reaches a threshold in `(0, 1]`.

All components remain in the stored eigenanalysis even when fewer components are
selected for plots and distances. Kaiser `eigenvalue > 1` may be displayed as a
reference in correlation mode but is never an automatic statistical decision.

## Distances and outlier reference

Observation distance is calculated in the selected positive-eigenvalue score
space as `sum(z_ij^2 / lambda_j)`. The result records the effective degrees of
freedom. The P0 reference line uses a chi-square quantile at the configured
alpha and is explicitly labeled an approximate exploratory reference. If no
positive selected eigenvalues exist, or the degrees of freedom is invalid, the
plot shows distances without a reference line and records the reason.

This reference is not an automatic proof that a row is erroneous. Rows above it
receive an exploratory outlier flag.

## Result schema

The result contains:

- method/sample metadata and exclusions;
- selected variable identities and display names;
- matrix type, means, standard deviations, and sample matrix;
- eigenvalues, proportions, cumulative proportions, selected flags;
- eigenvectors and loadings;
- all usable-row scores, distances, and outlier flags;
- bounded chart preview metadata;
- warnings and reproducibility provenance.

Charts use at most 5,000 deterministic points and score tables preview at most
500 rows. All usable rows participate in the calculation. Outlier rows are
preserved first in a chart preview; remaining indices are selected
deterministically. The full scores CSV contains every usable row.

## User-facing results

1. Method & Sample
2. Eigenanalysis
3. Eigenvectors / Loadings
4. Scree Plot
5. Score Plot
6. Loading Plot
7. Biplot
8. Outlier Plot
9. Scores preview
10. CSV and HTML export

SVG titles, descriptions, axes, point details, table headings, warnings, and
empty states are localized in Korean and English. Dataset column names and row
labels are user data and are not translated.

## Unsupported P0 scope

Categorical PCA, kernel PCA, sparse or robust PCA, imputation, rotation, factor
analysis, incremental PCA, supervised response, clustering, PCA control charts,
and PCA-based process monitoring remain unavailable.

## Official references

- Minitab, [Methods and formulas for Principal Components Analysis](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/multivariate/how-to/principal-components/methods-and-formulas/methods-and-formulas/)
- Minitab, [Interpret all statistics and graphs for PCA](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/multivariate/how-to/principal-components/interpret-the-results/all-statistics-and-graphs/)
- scikit-learn 1.7, [PCA API](https://scikit-learn.org/1.7/modules/generated/sklearn.decomposition.PCA.html)
- scikit-learn 1.7, [Decomposing signals in components](https://scikit-learn.org/1.7/modules/decomposition.html#pca)
